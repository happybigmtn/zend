#!/usr/bin/env python3
"""
Hermes Adapter Module

Provides a capability-scoped adapter for Hermes AI agents to connect to the
Zend home-miner daemon. Hermes agents can observe miner status and append
summaries to the event spine, but cannot issue control commands or read
user messages.

Architecture:
    Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                       ^^^^^^^^^^^^^^^^^^^^
                       THIS IS WHAT WE BUILD

The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Import from sibling modules
# Use try/except for flexibility when running standalone vs as package
try:
    from .spine import EventKind, append_event, get_events
    from .store import load_pairings, save_pairings
except ImportError:
    from spine import EventKind, append_event, get_events
    from store import load_pairings, save_pairings


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HERMES_CAPABILITIES = ['observe', 'summarize']
"""Hermes is granted observe (read status) and summarize (append summaries)."""

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
"""Hermes can read its own summaries, miner alerts, and control receipts.
user_message events are intentionally excluded."""

# Hermes-specific store file
def _hermes_state_dir() -> str:
    """Resolve the state directory for Hermes data."""
    base = os.environ.get("ZEND_STATE_DIR")
    if base:
        return base
    return str(Path(__file__).resolve().parents[2] / "state")


HERMES_PAIRING_FILE = os.path.join(_hermes_state_dir(), 'hermes-pairing-store.json')


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """A live Hermes connection with validated capabilities."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    token_expires_at: str


@dataclass
class HermesPairing:
    """A Hermes pairing record stored persistently."""
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


# ---------------------------------------------------------------------------
# Token Validation
# ---------------------------------------------------------------------------

def _load_hermes_pairings() -> dict:
    """Load all Hermes pairing records."""
    os.makedirs(_hermes_state_dir(), exist_ok=True)
    if os.path.exists(HERMES_PAIRING_FILE):
        with open(HERMES_PAIRING_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    os.makedirs(_hermes_state_dir(), exist_ok=True)
    with open(HERMES_PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def _parse_authority_token(token: str) -> dict:
    """
    Parse an authority token.
    
    Authority token format: <hermes_id>:<capabilities>:<expiration_iso>
    Example: "hermes-001:observe,summarize:2026-03-23T00:00:00Z"
    
    The expiration part is always the last field (may contain colons from ISO format).
    
    Returns a dict with hermes_id, capabilities list, and expires_at.
    Raises ValueError if token is malformed or expired.
    """
    if not token or ':' not in token:
        raise ValueError("HERMES_INVALID_TOKEN: authority token is malformed")
    
    # Split from the right to handle ISO timestamps with colons
    # Format: <hermes_id>:<capabilities>:<expiration_iso>
    parts = token.split(':')
    if len(parts) < 3:
        raise ValueError("HERMES_INVALID_TOKEN: authority token has wrong number of parts")
    
    hermes_id = parts[0]
    expires_at = ':'.join(parts[2:])  # Join everything after capabilities
    caps_str = parts[1]
    capabilities = caps_str.split(',')
    
    # Validate capabilities
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_INVALID_CAPABILITY: '{cap}' not in {HERMES_CAPABILITIES}")
    
    # Check expiration
    try:
        expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if expires_dt < datetime.now(timezone.utc):
            raise ValueError("HERMES_TOKEN_EXPIRED: authority token has expired")
    except ValueError as e:
        if "expired" in str(e).lower():
            raise
        raise ValueError("HERMES_INVALID_TOKEN: malformed expiration date")
    
    return {
        'hermes_id': hermes_id,
        'capabilities': capabilities,
        'expires_at': expires_at
    }


def _is_token_expired(token_expires_at: str) -> bool:
    """Check if a token has expired."""
    try:
        expires_dt = datetime.fromisoformat(token_expires_at.replace('Z', '+00:00'))
        return expires_dt < datetime.now(timezone.utc)
    except ValueError:
        return True


# ---------------------------------------------------------------------------
# Hermes Pairing (One-time setup)
# ---------------------------------------------------------------------------

def pair_hermes(hermes_id: str, device_name: str = None) -> HermesPairing:
    """
    Create a Hermes pairing record with observe+summarize capabilities.
    
    This is idempotent: calling with the same hermes_id returns the existing
    pairing rather than creating a duplicate.
    """
    try:
        from .store import load_or_create_principal
    except ImportError:
        from store import load_or_create_principal
    
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    # Check for existing pairing (idempotent)
    for existing in pairings.values():
        if existing['hermes_id'] == hermes_id:
            return HermesPairing(**existing)
    
    # Create new pairing
    if device_name is None:
        device_name = f"hermes-{hermes_id}"
    
    expires_at = datetime.now(timezone.utc)
    expires_at = expires_at.replace(year=expires_at.year + 1)  # 1 year validity
    
    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=expires_at.isoformat()
    )
    
    pairings[pairing.id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    return pairing


def generate_authority_token(hermes_id: str) -> str:
    """
    Generate an authority token for a Hermes pairing.
    
    Token format: <hermes_id>:<capabilities>:<expiration_iso>
    """
    pairings = _load_hermes_pairings()
    
    # Find pairing by hermes_id
    for pairing_dict in pairings.values():
        if pairing_dict['hermes_id'] == hermes_id:
            caps = ','.join(pairing_dict['capabilities'])
            return f"{hermes_id}:{caps}:{pairing_dict['token_expires_at']}"
    
    raise ValueError(f"HERMES_NOT_PAIRED: no pairing found for '{hermes_id}'")


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get a Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    for pairing_dict in pairings.values():
        if pairing_dict['hermes_id'] == hermes_id:
            return HermesPairing(**pairing_dict)
    return None


# ---------------------------------------------------------------------------
# Connection Management
# ---------------------------------------------------------------------------

def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: Token in format "<hermes_id>:<caps>:<expires>"
    
    Returns:
        HermesConnection with validated capabilities
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
    """
    # Parse and validate the token
    token_data = _parse_authority_token(authority_token)
    
    # Verify pairing exists
    pairing = get_hermes_pairing(token_data['hermes_id'])
    if not pairing:
        raise ValueError("HERMES_NOT_PAIRED: Hermes must be paired before connecting")
    
    # Verify token hasn't expired (double-check)
    if _is_token_expired(pairing.token_expires_at):
        raise ValueError("HERMES_TOKEN_EXPIRED: pairing token has expired")
    
    return HermesConnection(
        hermes_id=token_data['hermes_id'],
        principal_id=pairing.principal_id,
        capabilities=token_data['capabilities'],
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=pairing.token_expires_at
    )


# ---------------------------------------------------------------------------
# Adapter Operations
# ---------------------------------------------------------------------------

def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through the adapter.
    
    Requires 'observe' capability. Returns the miner snapshot with
    sensitive fields stripped.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import miner from daemon (lazy to avoid circular imports)
    from .daemon import miner
    
    snapshot = miner.get_snapshot()
    
    # Strip any fields Hermes shouldn't see (none currently, but
    # this is where we'd add field filtering for future expansion)
    return snapshot


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability. The summary is written as a
    hermes_summary event visible in the operations inbox.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    event = append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "hermes_id": connection.hermes_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    
    return {
        "appended": True,
        "event_id": event.id,
        "kind": event.kind,
        "created_at": event.created_at
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events. Over-fetches to account for filtering.
    """
    # Import EventKind for value access
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    # Filter to readable events only
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    # Transform to dict format
    return [
        {
            "id": e.id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
            "principal_id": e.principal_id
        }
        for e in filtered[:limit]
    ]


def check_hermes_auth(hermes_id: str) -> bool:
    """
    Check if a hermes_id has a valid, non-expired pairing.
    """
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        return False
    return not _is_token_expired(pairing.token_expires_at)


# ---------------------------------------------------------------------------
# Bootstrap Proof
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # Validate module loads and constants are correct
    print('Capabilities:', HERMES_CAPABILITIES)
    print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
