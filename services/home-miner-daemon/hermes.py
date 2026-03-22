#!/usr/bin/env python3
"""
Zend Hermes Adapter

Sits between external Hermes agent and Zend gateway contract.
Enforces capability boundaries: Hermes can observe and summarize,
but cannot issue control commands or read user messages.

Architecture:
  Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine

References:
  references/hermes-adapter.md
  references/event-spine.md
  references/observability.md
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List, Optional

from spine import EventKind, append_event, get_events

# Hermite capability set — observe + summarize, NOT control
HERMES_CAPABILITIES = ["observe", "summarize"]

# Event kinds Hermes is allowed to read from the spine
# Blocks user_message and other sensitive events
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """Established Hermes connection state."""

    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    authority_scope: List[str]

    def to_dict(self) -> dict:
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at,
            "authority_scope": self.authority_scope,
        }


# ---------------------------------------------------------------------------
# Token validation helpers
# ---------------------------------------------------------------------------

def _parse_authority_token(token: str) -> dict:
    """
    Parse a base64-encoded JSON authority token.

    Token format (JSON, then base64):
    {
      "principal_id": "...",
      "hermes_id": "...",
      "capabilities": ["observe", "summarize"],
      "expires_at": "ISO 8601 timestamp",
      "signature": "..."   # not verified in milestone 1
    }

    Raises ValueError on malformed token.
    """
    try:
        payload_bytes = token.encode()
        # In milestone 1 the token is plain JSON for simplicity.
        # Real deployment replaces this with a proper signed JWT.
        raw = payload_bytes.decode("utf-8")
        data = json.loads(raw)
        return data
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"HERMES_INVALID_TOKEN: {exc}") from exc


def _is_token_expired(expires_at_str: str) -> bool:
    """Return True if the ISO 8601 expiration timestamp is in the past."""
    try:
        expires_at = datetime.fromisoformat(expires_at_str)
        # Normalize to UTC for comparison
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at
    except (ValueError, TypeError):
        # Treat malformed timestamps as expired (deny by default)
        return True


# ---------------------------------------------------------------------------
# Core adapter functions
# ---------------------------------------------------------------------------

def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish a Hermes connection.

    Raises ValueError if the token is:
      - malformed
      - expired
      - requests a capability outside the Hermes scope

    Returns a HermesConnection with observe+summarize capabilities.
    """
    data = _parse_authority_token(authority_token)

    principal_id = data.get("principal_id")
    hermes_id = data.get("hermes_id")
    capabilities = data.get("capabilities", [])
    expires_at = data.get("expires_at")

    if not principal_id:
        raise ValueError("HERMES_INVALID_TOKEN: missing principal_id")
    if not hermes_id:
        raise ValueError("HERMES_INVALID_TOKEN: missing hermes_id")

    # Reject expired tokens
    if expires_at and _is_token_expired(expires_at):
        raise ValueError("HERMES_TOKEN_EXPIRED")

    # Enforce Hermes capability scope: only observe + summarize allowed
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_INVALID_CAPABILITY: '{cap}' is not in "
                f"the Hermes scope {HERMES_CAPABILITIES}"
            )

    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        authority_scope=capabilities,
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.

    Requires 'observe' capability. Raises PermissionError if missing.

    Delegates to the daemon's internal miner simulator to avoid
    an HTTP hop in-process.
    """
    if "observe" not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: observe capability required for read_status"
        )

    # Import here to avoid circular dependency at module load time
    from daemon import miner as _miner

    snapshot = _miner.get_snapshot()
    return {
        "source": "hermes_adapter",
        "principal_id": connection.principal_id,
        "hermes_id": connection.hermes_id,
        "snapshot": snapshot,
    }


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: Optional[List[str]] = None,
) -> dict:
    """
    Append a Hermes summary event to the event spine.

    Requires 'summarize' capability. Raises PermissionError if missing.

    Args:
        connection: Active Hermes connection
        summary_text: Human-readable summary string
        authority_scope: Override scope to record (defaults to connection.capabilities)

    Returns the appended SpineEvent as a dict.
    """
    if "summarize" not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: summarize capability required for append_summary"
        )

    scope = authority_scope or connection.authority_scope

    event = append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text,
            "authority_scope": scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id,
        },
    )

    return {
        "event_id": event.id,
        "principal_id": event.principal_id,
        "kind": event.kind,
        "created_at": event.created_at,
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]:
    """
    Return events Hermes is permitted to read.

    Filters out user_message and all other event kinds not in
    HERMES_READABLE_EVENTS. Over-fetches to account for filtering
    then trims to the requested limit.

    Args:
        connection: Active Hermes connection
        limit: Maximum number of events to return (default 20)

    Returns list of event dicts (most recent first).
    """
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]

    # Over-fetch: filtering may remove many events
    all_events = get_events(limit=limit * 3)

    filtered = [e for e in all_events if e.kind in readable_kinds]

    return [
        {
            "id": e.id,
            "principal_id": e.principal_id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
        }
        for e in filtered[:limit]
    ]


# ---------------------------------------------------------------------------
# Pairing helpers
# ---------------------------------------------------------------------------

PAIRING_STORE_FILE = None  # Set lazily via _get_pairing_store_path


def _get_pairing_store_path() -> str:
    """Return path to the Hermes pairing store, relative to state dir."""
    import os
    from pathlib import Path

    state_dir = os.environ.get(
        "ZEND_STATE_DIR",
        str(Path(__file__).resolve().parents[2] / "state"),
    )
    return os.path.join(state_dir, "hermes-pairing-store.json")


def pair_hermes(hermes_id: str, device_name: str) -> HermesConnection:
    """
    Create (or re-create) a Hermes pairing record with observe+summarize.

    Pairing is idempotent: calling with the same hermes_id overwrites the
    existing record.

    Returns the new HermesConnection.
    """
    import os

    store_path = _get_pairing_store_path()
    os.makedirs(os.path.dirname(store_path), exist_ok=True)

    if os.path.exists(store_path):
        with open(store_path, "r") as f:
            store = json.load(f)
    else:
        store = {}

    # Load principal (create if absent)
    from store import load_or_create_principal

    principal = load_or_create_principal()

    # Build pairing
    expires_at = datetime.now(timezone.utc).isoformat()
    record = {
        "hermes_id": hermes_id,
        "device_name": device_name,
        "principal_id": principal.id,
        "capabilities": HERMES_CAPABILITIES,
        "paired_at": datetime.now(timezone.utc).isoformat(),
        "token_expires_at": expires_at,
    }
    store[hermes_id] = record

    with open(store_path, "w") as f:
        json.dump(store, f, indent=2)

    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal.id,
        capabilities=HERMES_CAPABILITIES,
        connected_at=record["paired_at"],
        authority_scope=HERMES_CAPABILITIES,
    )


def get_hermes_pairing(hermes_id: str) -> Optional[HermesConnection]:
    """Return Hermes pairing record if one exists for this hermes_id."""
    import os

    store_path = _get_pairing_store_path()
    if not os.path.exists(store_path):
        return None

    with open(store_path, "r") as f:
        store = json.load(f)

    record = store.get(hermes_id)
    if not record:
        return None

    return HermesConnection(
        hermes_id=record["hermes_id"],
        principal_id=record["principal_id"],
        capabilities=record["capabilities"],
        connected_at=record["paired_at"],
        authority_scope=record["capabilities"],
    )


def build_authority_token(connection: HermesConnection, expires_in_hours: int = 24) -> str:
    """
    Build a plain-JSON authority token for a Hermes connection.

    In milestone 1 this is plain JSON. Real deployment replaces this
    with a signed JWT/JWK mechanism.

    Args:
        connection: HermesConnection to encode
        expires_in_hours: Token validity window (default 24)

    Returns a UTF-8 JSON string (base64 not required for in-process use).
    """
    from datetime import timedelta

    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    payload = {
        "principal_id": connection.principal_id,
        "hermes_id": connection.hermes_id,
        "capabilities": connection.capabilities,
        "expires_at": expires_at.isoformat(),
        "signature": "milestone-1-placeholder",
    }
    return json.dumps(payload)
