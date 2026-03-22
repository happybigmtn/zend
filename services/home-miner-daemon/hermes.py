#!/usr/bin/env python3
"""
Zend Hermes Adapter

Hermes connects to the Zend daemon through this adapter. The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

The adapter is a capability boundary, not a deployment boundary. It enforces
scope by filtering requests before they reach the gateway contract. Running it
in-process avoids network-hop complexity.

Architecture:
    Hermes Gateway → Zend Hermes Adapter → Event Spine
"""

import base64
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Local imports
from spine import EventKind, get_events, append_event
from store import load_pairings, save_pairings, load_or_create_principal


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HERMES_CAPABILITIES = ['observe', 'summarize']
"""Hermes may only request observe and summarize — never control."""

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
"""Events Hermes is permitted to read. user_message is explicitly excluded."""


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """
    Represents an active Hermes session established through the adapter.

    Fields:
        hermes_id:  Stable identifier for this Hermes agent.
        principal_id: The Zend principal this Hermes is acting on behalf of.
        capabilities: Granted capability set — a subset of HERMES_CAPABILITIES.
        connected_at: ISO 8601 timestamp of connection establishment.
    """
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str


# ---------------------------------------------------------------------------
# Hermes Pairing Store
# ---------------------------------------------------------------------------

def _get_hermes_store_path() -> Path:
    state_dir = os.environ.get(
        "ZEND_STATE_DIR",
        str(Path(__file__).resolve().parents[2] / "state")
    )
    os.makedirs(state_dir, exist_ok=True)
    return Path(state_dir) / "hermes-pairings.json"


def load_hermes_pairings() -> dict:
    """Load all Hermes pairing records. Returns empty dict if none exist."""
    path = _get_hermes_store_path()
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def save_hermes_pairings(pairings: dict):
    """Persist Hermes pairing records."""
    with open(_get_hermes_store_path(), 'w') as f:
        json.dump(pairings, f, indent=2)


def get_hermes_pairing(hermes_id: str) -> Optional[dict]:
    """Return the pairing record for hermes_id, or None if not paired."""
    pairings = load_hermes_pairings()
    return pairings.get(hermes_id)


def is_hermes_paired(hermes_id: str) -> bool:
    """True if hermes_id has an active pairing record."""
    return hermes_id in load_hermes_pairings()


# ---------------------------------------------------------------------------
# Token Validation
# ---------------------------------------------------------------------------

def _decode_token(authority_token: str) -> dict:
    """
    Decode a base64-encoded JSON authority token.

    Token schema:
        principal_id  — Zend principal this Hermes is acting on behalf of
        hermes_id    — Hermes agent identifier
        capabilities — list of granted capabilities
        expires_at   — ISO 8601 expiration timestamp

    Returns the decoded payload dict.
    Raises ValueError if the token is malformed or cannot be decoded.
    """
    try:
        raw = base64.urlsafe_b64decode(authority_token.encode()).decode()
        return json.loads(raw)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid authority token encoding: {exc}") from exc


def _is_token_expired(expires_at: str) -> bool:
    """Return True if the ISO timestamp has passed UTC now."""
    try:
        expiry = datetime.fromisoformat(expires_at)
        # Normalize to UTC for comparison
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expiry
    except ValueError:
        # Treat malformed timestamps as expired
        return True


def _validate_capabilities(requested: list) -> list:
    """
    Intersect requested capabilities with HERMES_CAPABILITIES.
    Returns only capabilities Hermes is permitted to hold.
    Raises ValueError if any requested capability is outside the Hermes scope.
    """
    invalid = [c for c in requested if c not in HERMES_CAPABILITIES]
    if invalid:
        raise ValueError(
            f"Hermes cannot request capabilities outside its scope: {invalid}. "
            f"Allowed: {HERMES_CAPABILITIES}"
        )
    return [c for c in requested if c in HERMES_CAPABILITIES]


# ---------------------------------------------------------------------------
# Adapter Interface
# ---------------------------------------------------------------------------

def pair(hermes_id: str, device_name: str) -> dict:
    """
    Register a Hermes agent for the first time or re-pair an existing one.
    Idempotent: calling again with the same hermes_id overwrites the record.

    Hermes always receives observe + summarize capabilities. It never receives
    control.

    Args:
        hermes_id:   Stable identifier assigned to this Hermes agent.
        device_name: Human-readable name for this agent (e.g. "hermes-prod-01").

    Returns:
        The created (or updated) pairing record as a dict.
    """
    principal = load_or_create_principal()
    pairings = load_hermes_pairings()

    record = {
        "id": str(uuid.uuid4()),
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "device_name": device_name,
        "capabilities": HERMES_CAPABILITIES,
        "paired_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime(2099, 12, 31, tzinfo=timezone.utc).isoformat(),
    }

    pairings[hermes_id] = record
    save_hermes_pairings(pairings)

    # Emit a pairing event so it appears in the inbox
    append_event(
        EventKind.PAIRING_GRANTED,
        principal.id,
        {
            "device_name": device_name,
            "granted_capabilities": HERMES_CAPABILITIES,
            "agent": "hermes",
        }
    )

    return record


def connect(authority_token: str) -> HermesConnection:
    """
    Validate an authority token and establish a Hermes connection.

    Validation steps:
    1. Decode and parse the base64 JSON token.
    2. Check the token has not expired.
    3. Verify hermes_id is a known pairing.
    4. Intersect token capabilities with HERMES_CAPABILITIES.
    5. Check that the token's hermes_id matches the pairing record.

    Args:
        authority_token: Base64-encoded JSON authority token from Hermes.

    Returns:
        A HermesConnection object representing the active session.

    Raises:
        ValueError: Token is invalid, expired, unknown, or has disallowed capabilities.
        PermissionError: hermes_id in token does not match the pairing record.
    """
    if not authority_token or not authority_token.strip():
        raise ValueError("HERMES_INVALID_TOKEN: authority token is empty")

    try:
        payload = _decode_token(authority_token)
    except ValueError as exc:
        raise ValueError(f"HERMES_INVALID_TOKEN: {exc}") from exc

    required_fields = ('principal_id', 'hermes_id', 'capabilities', 'expires_at')
    missing = [f for f in required_fields if f not in payload]
    if missing:
        raise ValueError(
            f"HERMES_INVALID_TOKEN: token missing required fields: {missing}"
        )

    if _is_token_expired(payload['expires_at']):
        raise ValueError(
            f"HERMES_TOKEN_EXPIRED: token expired at {payload['expires_at']}"
        )

    pairing = get_hermes_pairing(payload['hermes_id'])
    if pairing is None:
        raise PermissionError(
            f"HERMES_UNAUTHORIZED: unknown hermes_id '{payload['hermes_id']}'. "
            f"Pair with POST /hermes/pair first."
        )

    if pairing['principal_id'] != payload['principal_id']:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: principal_id mismatch between token and pairing"
        )

    allowed = _validate_capabilities(payload['capabilities'])

    return HermesConnection(
        hermes_id=payload['hermes_id'],
        principal_id=payload['principal_id'],
        capabilities=allowed,
        connected_at=datetime.now(timezone.utc).isoformat(),
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.

    Requires 'observe' capability. Returns a status dict with the same shape
    as the daemon's /status endpoint, augmented with a 'capabilities' field so
    Hermes can introspect what it may do.

    Args:
        connection: An active HermesConnection returned by connect().

    Returns:
        Miner status dict.

    Raises:
        PermissionError: Connection lacks 'observe' capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: observe capability required to read miner status"
        )

    # Import here to avoid circular reference — daemon holds the miner instance
    from daemon import miner

    snapshot = miner.get_snapshot()
    snapshot['hermes_capabilities'] = connection.capabilities
    snapshot['hermes_id'] = connection.hermes_id
    return snapshot


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str,
) -> dict:
    """
    Append a Hermes summary event to the event spine.

    Requires 'summarize' capability. The summary is associated with the
    connection's principal_id and tagged with the authority_scope so readers
    can see which delegated authority generated it.

    Args:
        connection:     An active HermesConnection returned by connect().
        summary_text:   The human-readable summary produced by Hermes.
        authority_scope: The capability under which Hermes produced this
                        summary (e.g. "observe").

    Returns:
        The created SpineEvent as a dict.

    Raises:
        PermissionError: Connection lacks 'summarize' capability.
        ValueError:      summary_text is empty.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: summarize capability required to append summaries"
        )

    if not summary_text or not summary_text.strip():
        raise ValueError("HERMES_INVALID_SUMMARY: summary_text must not be empty")

    event = append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            "summary_text": summary_text.strip(),
            "authority_scope": authority_scope,
            "hermes_id": connection.hermes_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    return asdict(event)


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is permitted to read, filtered by event kind.

    Excludes user_message events. Over-fetches by 2× the limit to account for
    filtering, then slices to the requested count.

    Args:
        connection: An active HermesConnection returned by connect().
        limit:      Maximum number of events to return (default 20).

    Returns:
        List of SpineEvent dicts, most recent first.
    """
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]

    # Over-fetch to account for user_message filtering
    all_events = get_events(limit=limit * 2)

    filtered = [
        e for e in all_events
        if e.kind in readable_kinds
    ]

    return [asdict(e) for e in filtered[:limit]]


# ---------------------------------------------------------------------------
# Token Generation (for use by the daemon / CLI)
# ---------------------------------------------------------------------------

def issue_authority_token(
    hermes_id: str,
    principal_id: str,
    capabilities: List[str],
    expires_at: Optional[str] = None,
) -> str:
    """
    Issue a new authority token for a Hermes agent.

    This is used by the daemon when Hermes connects via /hermes/connect.
    The token encodes the granted capabilities and expiration so Hermes can
    reconnect later without a new pairing flow.

    Args:
        hermes_id:     The Hermes agent's stable identifier.
        principal_id:   The Zend principal this Hermes acts on behalf of.
        capabilities:  List of granted capabilities.
        expires_at:    Optional ISO timestamp for expiration.
                       Defaults to 24 hours from now.

    Returns:
        Base64-encoded JSON authority token string.
    """
    if expires_at is None:
        expires_at = (
            datetime.now(timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        from datetime import timedelta
        expires_at = (expires_at + timedelta(days=1)).isoformat()

    payload = {
        "principal_id": principal_id,
        "hermes_id": hermes_id,
        "capabilities": capabilities,
        "expires_at": expires_at,
    }

    raw = json.dumps(payload, separators=(',', ':'))
    return base64.urlsafe_b64encode(raw.encode()).decode()


# ---------------------------------------------------------------------------
# Proof of Interface
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Hermes Adapter Interface")
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
    print(f"Paired Hermes IDs: {list(load_hermes_pairings().keys())}")
