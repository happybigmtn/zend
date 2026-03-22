#!/usr/bin/env python3
"""
Hermes Adapter Module

Sits between the external Hermes agent and the Zend gateway contract.
Enforces capability scope: Hermes can observe and summarize, but cannot
issue control commands or read user messages.

Architecture:
  Hermes Gateway → Hermes Adapter → Zend Gateway Contract → Event Spine
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import json
import os
import uuid
from pathlib import Path

from spine import append_event, get_events, EventKind, SpineEvent
from store import load_or_create_principal


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Hermes is granted only observe and summarize — never control.
HERMES_CAPABILITIES: List[str] = ['observe', 'summarize']

# Events Hermes is allowed to read from the spine.
HERMES_READABLE_EVENTS: List[EventKind] = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Hermes headers use "Hermes <hermes_id>" scheme (distinct from device auth).
HERMES_AUTH_PREFIX = "Hermes "


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """Established Hermes session. Carries principal context and granted scope."""

    hermes_id: str
    principal_id: str
    capabilities: List[str]       # Always a subset of HERMES_CAPABILITIES
    connected_at: str             # ISO 8601 UTC timestamp

    def to_dict(self) -> dict:
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at,
        }


@dataclass
class HermesPairing:
    """Hermes pairing record stored alongside device pairings."""

    hermes_id: str
    principal_id: str
    device_name: str              # Human-readable name (e.g. "hermes-agent")
    capabilities: List[str]
    paired_at: str
    token: str                    # Bearer token issued at pairing time
    token_expires_at: str


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _hermes_pairing_file() -> str:
    state_dir = os.environ.get(
        "ZEND_STATE_DIR",
        str(Path(__file__).resolve().parents[2] / "state")
    )
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "hermes-pairing-store.json")


def _load_hermes_pairings() -> dict:
    """Load all Hermes pairing records from disk."""
    path = _hermes_pairing_file()
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict) -> None:
    """Persist Hermes pairing records to disk."""
    with open(_hermes_pairing_file(), 'w') as f:
        json.dump(pairings, f, indent=2)


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def _decode_authority_token(token: str) -> dict:
    """
    Decode a Hermes authority token.

    Token format (JSON, base64-encoded for transport):
      {
        "hermes_id": "hermes-001",
        "principal_id": "...",
        "capabilities": ["observe", "summarize"],
        "expires_at": "2026-03-22T12:00:00Z"
      }

    In milestone 1, tokens are stored as plain JSON in the pairing store.
    A real deployment would use signed JWTs or similar — this is a simulator.
    """
    try:
        data = json.loads(token)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("HERMES_INVALID_TOKEN: token must be valid JSON")

    required = ('hermes_id', 'principal_id', 'capabilities', 'expires_at')
    for field in required:
        if field not in data:
            raise ValueError(f"HERMES_INVALID_TOKEN: missing field '{field}'")

    # Check expiration
    try:
        expires = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("HERMES_INVALID_TOKEN: invalid expires_at format")

    if expires <= datetime.now(timezone.utc):
        raise ValueError("HERMES_TOKEN_EXPIRED: authority token has expired")

    # Reject control capability at connect time
    for cap in data['capabilities']:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_INVALID_CAPABILITY: '{cap}' not in {HERMES_CAPABILITIES}"
            )

    return data


# ---------------------------------------------------------------------------
# Public adapter API
# ---------------------------------------------------------------------------

def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish a Hermes connection.

    Raises ValueError if the token is invalid, expired, or requests
    a capability outside the Hermes scope.
    """
    data = _decode_authority_token(authority_token)

    # Store-level check: ensure Hermes ID is actually paired
    pairings = _load_hermes_pairings()
    stored = pairings.get(data['hermes_id'])
    if stored is None:
        raise ValueError("HERMES_NOT_PAIRED: Hermes ID has no pairing record")

    return HermesConnection(
        hermes_id=data['hermes_id'],
        principal_id=data['principal_id'],
        capabilities=data['capabilities'],
        connected_at=datetime.now(timezone.utc).isoformat(),
    )


def pair(hermes_id: str, device_name: str, validity_hours: int = 24) -> HermesPairing:
    """
    Create or re-create a Hermes pairing record.

    Pairing is idempotent: calling with the same hermes_id replaces the
    existing record and issues a fresh token.

    Returns the HermesPairing with the raw authority token.
    """
    principal = load_or_create_principal()

    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=validity_hours)

    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token=json.dumps({
            "hermes_id": hermes_id,
            "principal_id": principal.id,
            "capabilities": HERMES_CAPABILITIES,
            "expires_at": expires_at.isoformat(),
        }),
        token_expires_at=expires_at.isoformat(),
    )

    pairings = _load_hermes_pairings()
    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)

    return pairing


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.

    Requires 'observe' capability. Raises PermissionError if absent.
    Delegates to the miner simulator to keep the adapter thin.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

    # Import here to avoid circular import; daemon.py has the miner global.
    from daemon import miner
    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str = "observe",
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.

    Requires 'summarize' capability. Raises PermissionError if absent.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")

    event = append_event(
        principal_id=connection.principal_id,
        kind=EventKind.HERMES_SUMMARY,
        payload={
            "summary_text": summary_text,
            "authority_scope": [authority_scope],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id,
        }
    )
    return event


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]:
    """
    Return events Hermes is permitted to see.

    Blocks user_message and any event kind not in HERMES_READABLE_EVENTS.
    Over-fetches to account for filtering, then trims to limit.
    """
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    all_events = get_events(limit=limit * 2)

    filtered = [
        e for e in all_events
        if e.kind in readable_kinds
    ]
    return filtered[:limit]


def is_hermes_authenticated(headers: dict) -> Optional[str]:
    """
    Extract and return hermes_id from a 'Authorization: Hermes <id>' header.

    Returns None if the header is absent or malformed.
    """
    auth = headers.get('Authorization', '')
    if not auth.startswith(HERMES_AUTH_PREFIX):
        return None
    return auth[len(HERMES_AUTH_PREFIX):].strip() or None


def check_hermes_capability(authenticated_id: str, required_capability: str) -> bool:
    """
    Verify that the given hermes_id has a stored pairing with the required
    capability and that the stored token has not expired.
    """
    pairings = _load_hermes_pairings()
    record = pairings.get(authenticated_id)
    if not record:
        return False

    if required_capability not in record['capabilities']:
        return False

    try:
        expires = datetime.fromisoformat(
            record['token_expires_at'].replace('Z', '+00:00')
        )
        return expires > datetime.now(timezone.utc)
    except ValueError:
        return False
