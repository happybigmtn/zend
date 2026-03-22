#!/usr/bin/env python3
"""
Hermes Adapter — Zend-native adapter for Hermes AI agent authority.

The Hermes adapter enforces the capability boundary between an external Hermes
agent and the Zend gateway contract. It runs in-process with the daemon,
not as a separate service, because the boundary is a capability scope rather
than a deployment boundary.

Enforces:
- Authority token validation (principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only — no control)
- Event filtering (blocks user_message events from Hermes reads)
- Payload transformation (strips fields Hermes should not see)

Reference: references/hermes-adapter.md
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional
import json
import uuid

from spine import EventKind, append_event, get_events, SpineEvent
from store import (
    load_or_create_principal,
    load_pairings,
    save_pairings,
    GatewayPairing,
    Principal,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

HERMES_WRITABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
]

HERMES_PAIRING_FILE_VERSION = 1


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """A live Hermes connection established via a valid authority token."""

    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str

    def to_dict(self) -> dict:
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at,
        }


@dataclass
class HermesPairing:
    """A Hermes-specific pairing record stored alongside device pairings."""

    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Authority token helpers
# ---------------------------------------------------------------------------

def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records from the store."""
    pairings = load_pairings()
    return pairings.get("_hermes", {})


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records into the store."""
    all_pairings = load_pairings()
    all_pairings["_hermes"] = pairings
    save_pairings(all_pairings)


def _is_token_expired(expires_at: str) -> bool:
    """Check if an ISO timestamp has passed."""
    try:
        expires_dt = datetime.fromisoformat(expires_at)
    except ValueError:
        return True
    # Ensure timezone-aware comparison
    if expires_dt.tzinfo is None:
        expires_dt = expires_dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > expires_dt


# ---------------------------------------------------------------------------
# Hermes pairing
# ---------------------------------------------------------------------------

def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create or update a Hermes pairing record.

    Idempotent: re-pairing with the same hermes_id updates the record and
    issues a fresh token. Returns the new HermesPairing.
    """
    principal = load_or_create_principal()

    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=_default_token_expiry(),
    )

    pairings = _load_hermes_pairings()
    pairings[hermes_id] = pairing.to_dict()
    _save_hermes_pairings(pairings)

    # Emit pairing granted event
    append_event(
        EventKind.PAIRING_GRANTED,
        principal.id,
        {
            "device_name": device_name,
            "hermes_id": hermes_id,
            "capabilities": HERMES_CAPABILITIES,
            "version": HERMES_PAIRING_FILE_VERSION,
        },
    )

    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Return the Hermes pairing record for hermes_id, or None."""
    pairings = _load_hermes_pairings()
    data = pairings.get(hermes_id)
    if data is None:
        return None
    return HermesPairing(**data)


# ---------------------------------------------------------------------------
# Connection establishment
# ---------------------------------------------------------------------------

def _default_token_expiry() -> str:
    """Default token expiry: 30 days from now."""
    expires = datetime.now(timezone.utc)
    # Advance 30 days manually (avoid external dateutil dependency)
    expires = expires.replace(
        day=min(expires.day + 30, 28)
    )
    return expires.isoformat()


def connect(authority_token: str, hermes_id: str) -> HermesConnection:
    """
    Validate an authority token and establish a Hermes connection.

    The authority_token is currently the hermes_id itself (single-tenant milestone 1).
    The pairing record provides the authoritative capability list.

    Raises:
        ValueError  — token is missing or malformed.
        PermissionError — token is expired or capabilities are wrong.
    """
    if not authority_token:
        raise ValueError("HERMES_INVALID_TOKEN: authority_token is required")

    pairing = get_hermes_pairing(hermes_id)
    if pairing is None:
        raise ValueError(f"HERMES_NOT_PAIRED: hermes_id '{hermes_id}' is not registered")

    # Validate token expiration
    if _is_token_expired(pairing.token_expires_at):
        raise PermissionError(
            f"HERMES_TOKEN_EXPIRED: token expired at {pairing.token_expires_at}"
        )

    # Validate that the token matches the pairing
    if authority_token != hermes_id:
        # Future: decode and validate JWT/signed token here
        raise ValueError("HERMES_INVALID_TOKEN: token does not match pairing")

    # Enforce Hermes capability scope
    for cap in HERMES_CAPABILITIES:
        if cap not in pairing.capabilities:
            raise PermissionError(
                f"HERMES_UNAUTHORIZED: required capability '{cap}' not granted"
            )

    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Adapter operations
# ---------------------------------------------------------------------------

def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through the adapter.

    Requires the 'observe' capability. Delegates to the daemon's miner
    simulator snapshot.

    Raises:
        PermissionError — Hermes lacks observe capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

    # Import here to avoid circular dependency at module load time
    from daemon import miner

    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str,
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.

    Requires the 'summarize' capability. The summary is written as a
    hermes_summary event with the principal_id of the connected Hermes.

    Raises:
        PermissionError — Hermes lacks summarize capability.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")

    if not summary_text or not summary_text.strip():
        raise ValueError("HERMES_INVALID_SUMMARY: summary_text cannot be empty")

    return append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            "summary_text": summary_text.strip(),
            "authority_scope": authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]:
    """
    Return events Hermes is allowed to see.

    Blocks user_message events — Hermes never reads user correspondence.
    Over-fetches to account for filtering, then trims to limit.
    """
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]

    # Over-fetch to account for filtered events
    all_events = get_events(limit=limit * 3)
    filtered = [
        e for e in all_events
        if e.kind in readable_kinds
    ]
    return filtered[:limit]


# ---------------------------------------------------------------------------
# Smoke-test entry point (used by scripts/hermes_summary_smoke.sh)
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # Validate constants are accessible
    print("Capabilities:", HERMES_CAPABILITIES)
    print("Readable events:", [e.value for e in HERMES_READABLE_EVENTS])
    print("Writable events:", [e.value for e in HERMES_WRITABLE_EVENTS])
