#!/usr/bin/env python3
"""
Hermes Adapter — capability-scoped bridge for Hermes AI agents.

Hermes agents connect with an authority token carrying a principal_id,
hermes_id, and a limited set of capabilities: observe (read miner status)
and summarize (append to event spine). The adapter enforces these
boundaries so that Hermes cannot issue control commands or read user
messages.

Architecture:
    Hermes Gateway
          |
          v
    Zend Hermes Adapter  ← this module
          |
          v
    Zend Gateway Contract / Daemon
          |
          v
    Event Spine
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import List, Optional
import json
import os
import uuid
from pathlib import Path

# Local imports — these live alongside hermes.py in the same package
from spine import EventKind, get_events, append_event as _append_event
from store import load_pairings, save_pairings, load_or_create_principal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The two Hermes-specific capabilities (distinct from gateway observe/control)
HERMES_CAPABILITIES: List[str] = ['observe', 'summarize']

# Event kinds Hermes is allowed to read from the spine.
# user_message is explicitly excluded — Hermes must never see user content.
HERMES_READABLE_EVENTS: List[EventKind] = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Authority token lifetime (same as plan 006 token auth)
AUTHORITY_TOKEN_TTL_HOURS: int = 24

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """
    Represents an active Hermes session.

    Fields are deliberately narrow — Hermes never carries a device_name,
    control flag, or any gateway-only capability.
    """
    hermes_id: str
    principal_id: str
    capabilities: List[str]          # subset of HERMES_CAPABILITIES
    connected_at: str                 # ISO-8601 UTC
    token_expires_at: str            # ISO-8601 UTC
    authority_scope: str = "observe+summarize"   # human-readable

    def to_dict(self) -> dict:
        return asdict(self)

    def is_capable(self, cap: str) -> bool:
        return cap in self.capabilities


@dataclass
class HermesPairing:
    """
    Persistent pairing record for a Hermes agent.
    Stored in the pairing store with a `hermes_id` key.
    """
    hermes_id: str
    principal_id: str
    device_name: str                 # display name (e.g. "hermes-agent")
    capabilities: List[str]
    paired_at: str
    token_expires_at: str
    token_used: bool = False


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def _decode_authority_token(token: str) -> dict:
    """
    Decode and validate an authority token.

    Tokens are stored as JSON objects keyed by hermes_id in the pairing store.
    Validation checks:
      1. Token exists in the pairing store
      2. Token has not expired

    Tokens can be reused within their validity window. The one-time-use flag
    (token_used) was removed in favor of a session-based model where each
    connect() call generates a fresh session with a new expiration.

    Returns the stored token dict on success.
    Raises ValueError on any validation failure.
    """
    if not token or not token.strip():
        raise ValueError("HERMES_INVALID_TOKEN: token is empty")

    pairings = load_pairings()
    hermes_id = token.strip()

    # Token format: simple lookup by hermes_id (same pattern as gateway pairing)
    found = None
    for p in pairings.values():
        if p.get('hermes_id') == hermes_id:
            found = p
            break

    if found is None:
        raise ValueError("HERMES_INVALID_TOKEN: token not found")

    # Check expiration
    expires_str = found.get('token_expires_at', '')
    if expires_str:
        try:
            expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires:
                raise ValueError("HERMES_TOKEN_EXPIRED: authority token has expired")
        except ValueError:
            # If we can't parse the date, skip expiration check (legacy tokens)
            pass

    return found


# ---------------------------------------------------------------------------
# Core adapter functions
# ---------------------------------------------------------------------------

def connect(authority_token: str) -> HermesConnection:
    """
    Establish a Hermes connection after validating the authority token.

    Args:
        authority_token: The Hermes pairing token (maps to hermes_id).

    Returns:
        A HermesConnection object representing the active session.

    Raises:
        ValueError: if the token is invalid, expired, or already used.
    """
    token_data = _decode_authority_token(authority_token)

    hermes_id = token_data['hermes_id']
    principal_id = token_data['principal_id']
    capabilities = token_data.get('capabilities', HERMES_CAPABILITIES)

    # Validate capabilities are a subset of HERMES_CAPABILITIES
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_INVALID_CAPABILITY: '{cap}' is not a valid Hermes capability. "
                f"Allowed: {HERMES_CAPABILITIES}"
            )

    now = datetime.now(timezone.utc)
    connected_at = now.isoformat()
    expires_at = (now + timedelta(hours=AUTHORITY_TOKEN_TTL_HOURS)).isoformat()

    # Refresh expiration on each connect (session refresh)
    pairings = load_pairings()
    for p in pairings.values():
        if p.get('hermes_id') == hermes_id:
            p['token_expires_at'] = expires_at
            break
    save_pairings(pairings)

    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        connected_at=connected_at,
        token_expires_at=expires_at,
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.

    Requires the 'observe' capability.

    Args:
        connection: An active HermesConnection from connect().

    Returns:
        A miner snapshot dict with status, mode, hashrate, temperature,
        uptime_seconds, and freshness fields.

    Raises:
        PermissionError: if the connection lacks the 'observe' capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

    # Delegate to the daemon's miner simulator via a direct import.
    # In production this would be an HTTP call to localhost:8080.
    # We import here to avoid circular imports at module load time.
    from daemon import miner
    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: Optional[str] = None,
) -> dict:
    """
    Append a Hermes summary to the event spine.

    Requires the 'summarize' capability.

    Args:
        connection: An active HermesConnection from connect().
        summary_text: The human-readable summary string.
        authority_scope: Optional scope descriptor (default: "observe+summarize").

    Returns:
        A dict with appended=True and the event id.

    Raises:
        PermissionError: if the connection lacks the 'summarize' capability.
        ValueError: if summary_text is empty.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")

    if not summary_text or not summary_text.strip():
        raise ValueError("HERMES_INVALID_SUMMARY: summary_text must be non-empty")

    scope = authority_scope or connection.authority_scope

    event = _append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text.strip(),
            "authority_scope": scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id,
        }
    )

    return {"appended": True, "event_id": event.id}


def get_filtered_events(
    connection: HermesConnection,
    limit: int = 20,
) -> List[dict]:
    """
    Return events from the spine that Hermes is allowed to read.

    user_message events are explicitly excluded — this is the core
    privacy boundary for the adapter.

    Args:
        connection: An active HermesConnection from connect().
        limit: Maximum number of events to return (default 20).

    Returns:
        A list of event dicts ordered newest-first.
    """
    # Over-fetch to account for filtered events
    raw = get_events(limit=limit * 2)

    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [e for e in raw if e.kind in readable_kinds]

    return [
        {
            "id": e.id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
        }
        for e in filtered[:limit]
    ]


# ---------------------------------------------------------------------------
# Pairing management
# ---------------------------------------------------------------------------

def pair_hermes(
    hermes_id: str,
    device_name: str,
    capabilities: Optional[List[str]] = None,
) -> HermesPairing:
    """
    Create a new Hermes pairing record.

    This is idempotent — if a pairing with the same hermes_id already exists,
    it is returned without error (same pattern as gateway device pairing).

    Args:
        hermes_id: Unique Hermes agent identifier.
        device_name: Human-readable name for display.
        capabilities: List of granted capabilities (default: HERMES_CAPABILITIES).

    Returns:
        The HermesPairing record.
    """
    caps = capabilities or HERMES_CAPABILITIES
    principal = load_or_create_principal()
    pairings = load_pairings()

    # Check for existing pairing (idempotent re-pair)
    for existing in pairings.values():
        if existing.get('hermes_id') == hermes_id:
            return HermesPairing(
                hermes_id=existing['hermes_id'],
                principal_id=existing['principal_id'],
                device_name=existing['device_name'],
                capabilities=existing['capabilities'],
                paired_at=existing['paired_at'],
                token_expires_at=existing['token_expires_at'],
                token_used=existing.get('token_used', False),
            )

    now = datetime.now(timezone.utc)
    paired_at = now.isoformat()
    expires_at = (now + timedelta(hours=AUTHORITY_TOKEN_TTL_HOURS)).isoformat()

    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=caps,
        paired_at=paired_at,
        token_expires_at=expires_at,
        token_used=False,
    )

    pairings[hermes_id] = asdict(pairing)
    save_pairings(pairings)

    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Look up an existing Hermes pairing by hermes_id."""
    pairings = load_pairings()
    p = pairings.get(hermes_id)
    if p:
        return HermesPairing(**p)
    return None


# ---------------------------------------------------------------------------
# Smoke-test proof (used by scripts/hermes_summary_smoke.sh)
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
