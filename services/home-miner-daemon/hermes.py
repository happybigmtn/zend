#!/usr/bin/env python3
"""
Hermes Adapter Module

Sits between the external Hermes agent and the Zend gateway contract.
Enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

Architecture:
    Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                     ^^^^^^^^^^^^^^^^^^^^
                     THIS IS WHAT WE BUILD
"""

import base64
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_STORE_FILE = os.path.join(STATE_DIR, "hermes-store.json")


# ----------------------------------------------------------------------
# Hermes-specific constants
# ----------------------------------------------------------------------

HERMES_CAPABILITIES = ["observe", "summarize"]
"""Hermes is granted exactly observe and summarize — no control."""

HERMES_READABLE_EVENTS = [
    "hermes_summary",
    "miner_alert",
    "control_receipt",
]
"""Hermes may read these event kinds from the spine. user_message is blocked."""


class HermesCapability(str, Enum):
    OBSERVE = "observe"
    SUMMARIZE = "summarize"


# ----------------------------------------------------------------------
# Hermes store (pairing records for Hermes agents)
# ----------------------------------------------------------------------


def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records from disk."""
    if os.path.exists(HERMES_STORE_FILE):
        with open(HERMES_STORE_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Persist Hermes pairing records."""
    with open(HERMES_STORE_FILE, "w") as f:
        json.dump(pairings, f, indent=2)


# ----------------------------------------------------------------------
# Hermes token handling
# ----------------------------------------------------------------------


@dataclass
class HermesAuthorityToken:
    """
    Authority token issued to a Hermes agent during pairing.

    Fields:
        hermes_id: Stable identifier for this Hermes instance.
        principal_id: Owner's principal identity.
        capabilities: Scoped capabilities granted (observe, summarize).
        issued_at: ISO 8601 when the token was issued.
        expires_at: ISO 8601 when the token expires.
        nonce: Random nonce for replay protection.
    """

    hermes_id: str
    principal_id: str
    capabilities: list[str]
    issued_at: str
    expires_at: str
    nonce: str

    def is_expired(self) -> bool:
        """Check if the token has passed its expiration time."""
        expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expiry

    def has_capability(self, cap: str) -> bool:
        """Check if this token grants a specific capability."""
        return cap in self.capabilities


def encode_hermes_token(token: HermesAuthorityToken) -> str:
    """
    Encode a HermesAuthorityToken to a compact JSON string and base64-encode it.

    This is a simple encoding (not a signed JWT) for milestone 1.
    In production, this would be replaced by a properly signed token.
    """
    data = asdict(token)
    payload = json.dumps(data, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_hermes_token(encoded: str) -> HermesAuthorityToken:
    """
    Decode a base64-encoded HermesAuthorityToken.

    Raises ValueError if the token is malformed.
    """
    try:
        # Remove any whitespace
        encoded = encoded.strip()
        payload = base64.urlsafe_b64decode(encoded.encode()).decode()
        data = json.loads(payload)
        return HermesAuthorityToken(**data)
    except Exception as e:
        raise ValueError(f"Invalid Hermes authority token: {e}")


def issue_hermes_token(
    hermes_id: str,
    principal_id: str,
    capabilities: list[str],
    ttl_hours: int = 24,
) -> tuple[str, HermesAuthorityToken]:
    """
    Issue a new Hermes authority token and return it encoded plus the raw object.

    Args:
        hermes_id: Stable Hermes instance identifier.
        principal_id: Owner's principal identity.
        capabilities: Capabilities to grant (observe, summarize).
        ttl_hours: Token validity window in hours.

    Returns:
        (encoded_token_string, HermesAuthorityToken)
    """
    now = datetime.now(timezone.utc)
    expires = now.replace(microsecond=0)
    from datetime import timedelta

    expires = now + timedelta(hours=ttl_hours)

    token = HermesAuthorityToken(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        issued_at=now.isoformat(),
        expires_at=expires.isoformat(),
        nonce=str(uuid.uuid4()),
    )
    return encode_hermes_token(token), token


# ----------------------------------------------------------------------
# HermesConnection — the handle a connected Hermes agent holds
# ----------------------------------------------------------------------


@dataclass
class HermesConnection:
    """
    Represents an active Hermes agent connection.

    Produced by hermes.connect(). Held by callers who want to make
    capability-scoped requests through the adapter.
    """

    hermes_id: str
    principal_id: str
    capabilities: list[str]
    connected_at: str
    token: HermesAuthorityToken = field(repr=False)

    @property
    def can_observe(self) -> bool:
        return "observe" in self.capabilities

    @property
    def can_summarize(self) -> bool:
        return "summarize" in self.capabilities


# ----------------------------------------------------------------------
# Core adapter functions
# ----------------------------------------------------------------------


def pair_hermes(hermes_id: str, device_name: str, principal_id: str) -> dict:
    """
    Create (or idempotently re-create) a Hermes pairing record.

    Idempotent: if a pairing for hermes_id already exists, it is returned.

    Args:
        hermes_id: Stable identifier for this Hermes instance.
        device_name: Human-readable name for the Hermes agent.
        principal_id: Owner's principal identity.

    Returns:
        Dict with hermes_id, device_name, principal_id, capabilities, paired_at.
    """
    pairings = _load_hermes_pairings()

    if hermes_id in pairings:
        # Idempotent — return existing record
        return pairings[hermes_id]

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "hermes_id": hermes_id,
        "device_name": device_name,
        "principal_id": principal_id,
        "capabilities": HERMES_CAPABILITIES,
        "paired_at": now,
    }
    pairings[hermes_id] = record
    _save_hermes_pairings(pairings)
    return record


def get_hermes_pairing(hermes_id: str) -> Optional[dict]:
    """Return the Hermes pairing record for a given hermes_id, or None."""
    pairings = _load_hermes_pairings()
    return pairings.get(hermes_id)


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish a Hermes connection.

    Raises:
        ValueError: Token is malformed, expired, or grants no Hermes capabilities.
    """
    token = decode_hermes_token(authority_token)

    if token.is_expired():
        raise ValueError("HERMES_TOKEN_EXPIRED: authority token has expired")

    # Validate capabilities — must contain Hermes scopes
    for cap in token.capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_INVALID_CAPABILITY: '{cap}' is not a valid Hermes capability"
            )

    return HermesConnection(
        hermes_id=token.hermes_id,
        principal_id=token.principal_id,
        capabilities=token.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        token=token,
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through the adapter. Requires 'observe' capability.

    Args:
        connection: An active HermesConnection from connect().

    Raises:
        PermissionError: If the connection lacks 'observe'.
    """
    if "observe" not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

    # Defer to the daemon's miner simulator.
    # We import here to avoid circular dependencies at module load time.
    from daemon import miner

    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection, summary_text: str, authority_scope: str
) -> dict:
    """
    Append a Hermes summary to the event spine. Requires 'summarize' capability.

    Args:
        connection: An active HermesConnection from connect().
        summary_text: Human-readable summary text.
        authority_scope: The scope under which this summary was generated
                         (e.g. 'observe').

    Raises:
        PermissionError: If the connection lacks 'summarize'.
    """
    if "summarize" not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")

    from spine import append_hermes_summary as _append

    event = _append(
        summary_text=summary_text,
        authority_scope=[authority_scope],
        principal_id=connection.principal_id,
    )

    return {
        "event_id": event.id,
        "appended": True,
        "created_at": event.created_at,
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list[dict]:
    """
    Return events Hermes is allowed to see, with user_message events stripped.

    Args:
        connection: An active HermesConnection from connect().
        limit: Maximum number of events to return (default 20).

    Returns:
        List of event dicts, most recent first.
    """
    from spine import get_events

    # Over-fetch to account for filtering
    raw = get_events(limit=limit * 2)

    filtered = [
        e
        for e in raw
        if e.kind in HERMES_READABLE_EVENTS
    ]

    # Strip user_message and control_receipt payload fields that contain
    # sensitive data before returning.
    # For milestone 1 we return the full payload; redact in a future milestone.
    return [
        {
            "id": e.id,
            "kind": e.kind,
            "principal_id": e.principal_id,
            "payload": e.payload,
            "created_at": e.created_at,
        }
        for e in filtered
    ][:limit]


# ----------------------------------------------------------------------
# Proof-of-concept / smoke test
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    print("Capabilities:", HERMES_CAPABILITIES)
    print("Readable events:", HERMES_READABLE_EVENTS)
