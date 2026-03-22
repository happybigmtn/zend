#!/usr/bin/env python3
"""
Zend Hermes Adapter

A scoped adapter that allows Hermes (an AI agent) to connect to the Zend
daemon with a narrow capability set: observe and summarize. The adapter
enforces capability boundaries, validates authority tokens, and filters
events so Hermes cannot read user messages or issue control commands.

Architecture:
  Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                   ^^^^^^^^^^^^^^^^^^^^
                   THIS IS WHAT WE BUILD

Capability Model:
  - 'observe': read miner status
  - 'summarize': append summaries to the event spine

Hermes CANNOT:
  - Issue control commands (start/stop/set_mode)
  - Read user_message events
  - Access inbox message composition
  - Modify payout targets

These boundaries are enforced by the adapter before any request reaches
the gateway contract.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional

# Resolve state directory relative to this file, independent of cwd
def _default_state_dir() -> str:
    return str(Path(__file__).resolve().parents[2] / "state")

STATE_DIR = os.environ.get("ZEND_STATE_DIR", _default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing.json')
HERMES_TOKEN_FILE = os.path.join(STATE_DIR, 'hermes-tokens.json')


# ---------------------------------------------------------------------------
# Event Kinds Hermes is allowed to read
# ---------------------------------------------------------------------------

class HermesReadableEvent(str, Enum):
    """Event kinds Hermes can see in the event spine."""
    HERMES_SUMMARY = "hermes_summary"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"


# ---------------------------------------------------------------------------
# Hermes-specific constants
# ---------------------------------------------------------------------------

HERMES_CAPABILITIES: List[str] = ['observe', 'summarize']
"""The full set of capabilities Hermes may be granted in milestone 1."""

HERMES_READABLE_EVENTS: List[HermesReadableEvent] = [
    HermesReadableEvent.HERMES_SUMMARY,
    HermesReadableEvent.MINER_ALERT,
    HermesReadableEvent.CONTROL_RECEIPT,
]
"""Events Hermes can read from the spine. user_message is intentionally excluded."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """
    An active Hermes connection.

    Represents a validated Hermes session with a specific capability set.
    The connection is established by presenting a valid authority token
    to the /hermes/connect endpoint.
    """
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    token_expires_at: str

    def has_capability(self, capability: str) -> bool:
        """Check if this connection has a specific capability."""
        return capability in self.capabilities

    def can_observe(self) -> bool:
        """True if this connection can read miner status."""
        return self.has_capability('observe')

    def can_summarize(self) -> bool:
        """True if this connection can append summaries."""
        return self.has_capability('summarize')

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at,
            "token_expires_at": self.token_expires_at,
        }


@dataclass
class HermesPairing:
    """
    A Hermes device pairing record.

    Stored persistently in hermes-pairing.json. Hermes pairings use
    the same principal as gateway devices but with a distinct capability
    scope (observe + summarize only).
    """
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str
    token_used: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HermesAuthorityToken:
    """
    An authority token issued to Hermes during the pairing flow.

    Encodes the principal, granted capabilities, and expiration.
    This is what Hermes presents to /hermes/connect to establish a session.
    """
    token: str
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    issued_at: str
    expires_at: str

    @classmethod
    def from_dict(cls, data: dict) -> HermesAuthorityToken:
        return cls(**data)

    def is_expired(self) -> bool:
        """True if the token has passed its expiration time."""
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) > expiry
        except (ValueError, TypeError):
            # Treat malformed expiration as expired
            return True

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Token store (ephemeral in-memory, backed by JSON for simplicity)
# ---------------------------------------------------------------------------

def _load_tokens() -> dict:
    if os.path.exists(HERMES_TOKEN_FILE):
        with open(HERMES_TOKEN_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_tokens(tokens: dict):
    with open(HERMES_TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)


def _load_pairings() -> dict:
    if os.path.exists(HERMES_PAIRING_FILE):
        with open(HERMES_PAIRING_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_pairings(pairings: dict):
    with open(HERMES_PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


# ---------------------------------------------------------------------------
# Token issuance
# ---------------------------------------------------------------------------

def issue_authority_token(hermes_id: str, principal_id: str, capabilities: List[str],
                          ttl_seconds: int = 86400) -> HermesAuthorityToken:
    """
    Issue a new Hermes authority token.

    The token is stored in hermes-tokens.json so it can be validated
    on reconnect. Tokens expire after ttl_seconds (default: 24 hours).

    Args:
        hermes_id: Unique identifier for the Hermes instance.
        principal_id: The Zend principal this token is issued to.
        capabilities: List of granted capabilities (observe, summarize).
        ttl_seconds: Time-to-live in seconds.

    Returns:
        HermesAuthorityToken with the generated token and expiration.
    """
    now = datetime.now(timezone.utc)
    token = HermesAuthorityToken(
        token=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        issued_at=now.isoformat(),
        expires_at=(now.timestamp() + ttl_seconds).__add__(0).__add__(0).__trunc__().__add__(0).__add__(0).__add__(0),
    )
    # Fix: compute expiration properly
    from datetime import timedelta
    token.expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()

    tokens = _load_tokens()
    tokens[token.token] = token.to_dict()
    _save_tokens(tokens)

    return token


def validate_authority_token(token_str: str) -> HermesAuthorityToken:
    """
    Validate an authority token and return its contents.

    Args:
        token_str: The raw token string presented by Hermes.

    Returns:
        HermesAuthorityToken with the token's claims.

    Raises:
        ValueError: Token is invalid, expired, or malformed.
    """
    tokens = _load_tokens()

    if token_str not in tokens:
        raise ValueError("HERMES_INVALID_TOKEN: Token not found")

    data = tokens[token_str]
    token = HermesAuthorityToken.from_dict(data)

    if token.is_expired():
        raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")

    # Validate required fields
    if not token.hermes_id or not token.principal_id:
        raise ValueError("HERMES_INVALID_TOKEN: Malformed token claims")

    return token


def revoke_authority_token(token_str: str) -> bool:
    """
    Revoke an authority token, invalidating it immediately.

    Args:
        token_str: The token to revoke.

    Returns:
        True if the token was found and removed, False otherwise.
    """
    tokens = _load_tokens()
    if token_str in tokens:
        del tokens[token_str]
        _save_tokens(tokens)
        return True
    return False


# ---------------------------------------------------------------------------
# Hermes pairing
# ---------------------------------------------------------------------------

def pair_hermes(hermes_id: str, device_name: str, principal_id: str) -> HermesPairing:
    """
    Create or update a Hermes pairing record.

    Pairing is idempotent: if hermes_id already exists, its record is
    updated rather than creating a duplicate.

    Args:
        hermes_id: Unique identifier for the Hermes instance.
        device_name: Human-readable name for this Hermes instance.
        principal_id: The Zend principal this Hermes is paired with.

    Returns:
        The HermesPairing record (new or updated).
    """
    pairings = _load_pairings()

    now = datetime.now(timezone.utc).isoformat()

    # Check for existing pairing by hermes_id
    for existing in pairings.values():
        if existing['hermes_id'] == hermes_id:
            # Idempotent re-pair: update capabilities and timestamp
            existing['paired_at'] = now
            existing['device_name'] = device_name
            _save_pairings(pairings)
            return HermesPairing(**existing)

    # Create new pairing
    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal_id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=now,
        token_expires_at=now,
        token_used=False,
    )

    pairings[pairing.id] = pairing.to_dict()
    _save_pairings(pairings)

    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """
    Retrieve a Hermes pairing record by hermes_id.

    Args:
        hermes_id: The Hermes identifier to look up.

    Returns:
        HermesPairing if found, None otherwise.
    """
    pairings = _load_pairings()
    for pairing in pairings.values():
        if pairing['hermes_id'] == hermes_id:
            return HermesPairing(**pairing)
    return None


def list_hermes_pairings() -> List[HermesPairing]:
    """
    List all Hermes pairings.

    Returns:
        List of HermesPairing records.
    """
    pairings = _load_pairings()
    return [HermesPairing(**p) for p in pairings.values()]


# ---------------------------------------------------------------------------
# Connection establishment
# ---------------------------------------------------------------------------

def connect(authority_token: str) -> HermesConnection:
    """
    Establish a Hermes connection from a valid authority token.

    Validates the token, checks expiration, and returns a HermesConnection
    object with the granted capabilities.

    Args:
        authority_token: The raw token string from /hermes/pair response.

    Returns:
        HermesConnection ready for use.

    Raises:
        ValueError: Token is invalid, expired, or missing required capabilities.
    """
    token = validate_authority_token(authority_token)

    # Verify Hermes is still paired
    pairing = get_hermes_pairing(token.hermes_id)
    if not pairing:
        raise ValueError("HERMES_NOT_PAIRED: Hermes device is not registered")

    # Build connection object
    connection = HermesConnection(
        hermes_id=token.hermes_id,
        principal_id=token.principal_id,
        capabilities=token.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=token.expires_at,
    )

    return connection


# ---------------------------------------------------------------------------
# Status reading (observe capability)
# ---------------------------------------------------------------------------

def read_status(connection: HermesConnection, miner_snapshot_fn=None) -> dict:
    """
    Read miner status through the Hermes adapter.

    Requires the 'observe' capability. Delegates to the daemon's internal
    status endpoint.

    Args:
        connection: An active HermesConnection.
        miner_snapshot_fn: Optional callable that returns miner status dict.
                           If None, returns a mock status for testing.

    Returns:
        Miner status snapshot dict.

    Raises:
        PermissionError: Connection lacks 'observe' capability.
    """
    if not connection.can_observe():
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

    # If a status function was injected (from daemon context), use it
    if miner_snapshot_fn is not None:
        return miner_snapshot_fn()

    # Fallback for standalone adapter testing
    return {
        "status": "stopped",
        "mode": "paused",
        "hashrate_hs": 0,
        "temperature": 45.0,
        "uptime_seconds": 0,
        "freshness": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Summary appending (summarize capability)
# ---------------------------------------------------------------------------

def append_summary(connection: HermesConnection, summary_text: str,
                   authority_scope: str) -> dict:
    """
    Append a Hermes summary to the event spine.

    Requires the 'summarize' capability. The summary is written as a
    hermes_summary event with metadata about scope and generation time.

    Args:
        connection: An active HermesConnection.
        summary_text: The summary content to append.
        authority_scope: The authority scope used (e.g., 'observe').

    Returns:
        Dict with appended=True and the event details.

    Raises:
        PermissionError: Connection lacks 'summarize' capability.
    """
    if not connection.can_summarize():
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")

    # Import here to avoid circular dependency in daemon context
    from spine import append_hermes_summary

    event = append_hermes_summary(
        summary_text=summary_text,
        authority_scope=[authority_scope] + connection.capabilities,
        principal_id=connection.principal_id,
    )

    return {
        "appended": True,
        "event_id": event.id,
        "kind": event.kind,
        "created_at": event.created_at,
    }


# ---------------------------------------------------------------------------
# Event filtering (blocks user_message)
# ---------------------------------------------------------------------------

def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.

    Filters out user_message events and any event kinds not in
    HERMES_READABLE_EVENTS. Over-fetches to account for filtering.

    Args:
        connection: An active HermesConnection.
        limit: Maximum number of events to return after filtering.

    Returns:
        List of event dicts that Hermes can read.
    """
    # Import here to avoid circular dependency in daemon context
    from spine import get_events, EventKind

    # Map HermesReadableEvent to EventKind values
    allowed_kinds = [e.value for e in HERMES_READABLE_EVENTS]

    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)

    # Filter to allowed event kinds
    filtered = [
        {
            "id": e.id,
            "principal_id": e.principal_id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
        }
        for e in all_events
        if e.kind in allowed_kinds
    ]

    return filtered[:limit]


# ---------------------------------------------------------------------------
# Connection validation helpers
# ---------------------------------------------------------------------------

def is_hermes_auth_header(header_value: str) -> bool:
    """
    Check if an Authorization header value is a Hermes auth header.

    Format: "Hermes <hermes_id>"
    """
    if not header_value:
        return False
    parts = header_value.split(' ', 1)
    return len(parts) == 2 and parts[0] == 'Hermes'


def extract_hermes_id_from_header(header_value: str) -> Optional[str]:
    """
    Extract the hermes_id from a Hermes Authorization header.

    Format: "Hermes <hermes_id>"
    Returns the hermes_id portion or None if malformed.
    """
    if not is_hermes_auth_header(header_value):
        return None
    return header_value.split(' ', 1)[1]


# ---------------------------------------------------------------------------
# Capability enforcement helpers
# ---------------------------------------------------------------------------

class HermesPermissionError(PermissionError):
    """
    Raised when Hermes attempts an unauthorized operation.

    Carries a machine-readable error code for API responses.
    """
    def __init__(self, message: str, code: str = "HERMES_UNAUTHORIZED"):
        super().__init__(message)
        self.code = code


def require_observe(connection: HermesConnection):
    """Raise HermesPermissionError if connection lacks observe capability."""
    if not connection.can_observe():
        raise HermesPermissionError(
            "observe capability required for this operation",
            "HERMES_UNAUTHORIZED_OBSERVE"
        )


def require_summarize(connection: HermesConnection):
    """Raise HermesPermissionError if connection lacks summarize capability."""
    if not connection.can_summarize():
        raise HermesPermissionError(
            "summarize capability required for this operation",
            "HERMES_UNAUTHORIZED_SUMMARIZE"
        )


# ---------------------------------------------------------------------------
# Proof-of-concept verification
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
    print()
    print("Event filtering:")
    print("  - HERMES_SUMMARY: allowed")
    print("  - MINER_ALERT: allowed")
    print("  - CONTROL_RECEIPT: allowed")
    print("  - USER_MESSAGE: BLOCKED")
    print()
    print("Capability enforcement:")
    print("  - observe: read miner status")
    print("  - summarize: append summaries to spine")
    print("  - control: BLOCKED (not in Hermes scope)")
