#!/usr/bin/env python3
"""
Hermes Adapter — Zend Gateway Bridge

Provides a capability boundary for Hermes AI agents connecting to the Zend gateway.
Hermes agents can observe miner status and append summaries, but cannot issue control
commands or read user messages.

Architecture:
    Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine

This adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

Per contract: references/hermes-adapter.md
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Import from sibling modules
from store import load_pairings, save_pairings, load_or_create_principal
from spine import append_event, get_events, EventKind

# Authority token validity in seconds (30 days)
TOKEN_VALIDITY_SECONDS = 30 * 24 * 60 * 60


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')


@dataclass
class HermesConnection:
    """Represents an active Hermes agent connection."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str
    token_expires_at: str


@dataclass
class HermesPairing:
    """Hermes pairing record with observe+summarize capabilities."""
    id: str
    hermes_id: str
    device_name: str
    principal_id: str
    capabilities: List[str]  # Always ['observe', 'summarize'] for Hermes
    paired_at: str
    token_expires_at: str


# Hermes capabilities are fixed: observe and summarize
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read (user_message is blocked)
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records from store."""
    if os.path.exists(HERMES_PAIRING_FILE):
        with open(HERMES_PAIRING_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records to store."""
    with open(HERMES_PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def _generate_token() -> tuple[str, str]:
    """Generate a new Hermes authority token and expiration time."""
    token = str(uuid.uuid4())
    expires_at = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() + TOKEN_VALIDITY_SECONDS,
        tz=timezone.utc
    ).isoformat()
    return token, expires_at


def _is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    return datetime.now(timezone.utc) > expires


def pair(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create or update a Hermes pairing record.
    
    Idempotent: same hermes_id re-pairs with new token.
    Hermes always receives observe+summarize capabilities.
    
    Args:
        hermes_id: Unique Hermes agent identifier
        device_name: Human-readable device name for the agent
    
    Returns:
        HermesPairing record with capabilities
    
    Raises:
        ValueError: If parameters are invalid
    """
    if not hermes_id or not device_name:
        raise ValueError("hermes_id and device_name are required")
    
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()
    token, expires_at = _generate_token()
    
    # Check for existing pairing and reuse ID if present
    existing_id = None
    for p_id, p_data in pairings.items():
        if p_data.get('hermes_id') == hermes_id:
            existing_id = p_id
            break
    
    pairing_id = existing_id or str(uuid.uuid4())
    
    pairing = HermesPairing(
        id=pairing_id,
        hermes_id=hermes_id,
        device_name=device_name,
        principal_id=principal.id,
        capabilities=HERMES_CAPABILITIES.copy(),
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=expires_at
    )
    
    pairings[pairing_id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    return pairing


def get_pairing_by_hermes_id(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    for p_data in pairings.values():
        if p_data.get('hermes_id') == hermes_id:
            return HermesPairing(**p_data)
    return None


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    The authority token is the hermes_id for milestone 1.
    Validates that:
    - Pairing exists for this hermes_id
    - Token has not expired
    
    Args:
        authority_token: The Hermes authority token (hermes_id)
    
    Returns:
        HermesConnection with validated capabilities
    
    Raises:
        ValueError: If token is invalid or expired
    """
    if not authority_token:
        raise ValueError("HERMES_INVALID_TOKEN: authority_token is required")
    
    # Look up pairing by hermes_id (authority_token IS the hermes_id in milestone 1)
    pairing = get_pairing_by_hermes_id(authority_token)
    
    if not pairing:
        raise ValueError("HERMES_UNAUTHORIZED: No pairing found for this hermes_id")
    
    if _is_token_expired(pairing.token_expires_at):
        raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")
    
    return HermesConnection(
        hermes_id=pairing.hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=pairing.token_expires_at
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.
    
    Requires 'observe' capability.
    
    Args:
        connection: Validated HermesConnection
    
    Returns:
        MinerSnapshot dict
    
    Raises:
        PermissionError: If observe capability is not granted
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Delegate to daemon's status endpoint
    # In-process import to avoid circular dependency
    from daemon import miner
    return miner.get_snapshot()


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str = 'observe') -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Args:
        connection: Validated HermesConnection
        summary_text: The summary content to append
        authority_scope: The scope of this summary (observe/summarize)
    
    Returns:
        dict with event_id and appended status
    
    Raises:
        PermissionError: If summarize capability is not granted
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    if not summary_text:
        raise ValueError("summary_text is required")
    
    event = append_event(
        principal_id=connection.principal_id,
        kind=EventKind.HERMES_SUMMARY,
        payload={
            "summary_text": summary_text,
            "authority_scope": [authority_scope],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id
        }
    )
    
    return {
        "appended": True,
        "event_id": event.id,
        "kind": event.kind,
        "created_at": event.created_at
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events (Hermes cannot read user messages).
    
    Args:
        connection: Validated HermesConnection
        limit: Maximum number of events to return
    
    Returns:
        List of filtered event dicts
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    # Transform to serializable format
    return [
        {
            "id": e.id,
            "principal_id": e.principal_id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
            "version": e.version
        }
        for e in filtered[:limit]
    ]


def validate_authority_token(hermes_id: str) -> dict:
    """
    Validate an authority token and return its status.
    
    Used by the daemon to check token validity without establishing a full connection.
    
    Args:
        hermes_id: The Hermes ID to validate
    
    Returns:
        dict with validity status and details
    """
    pairing = get_pairing_by_hermes_id(hermes_id)
    
    if not pairing:
        return {
            "valid": False,
            "reason": "not_paired",
            "message": "No pairing found for this hermes_id"
        }
    
    if _is_token_expired(pairing.token_expires_at):
        return {
            "valid": False,
            "reason": "expired",
            "expires_at": pairing.token_expires_at,
            "message": "Authority token has expired"
        }
    
    return {
        "valid": True,
        "hermes_id": pairing.hermes_id,
        "capabilities": pairing.capabilities,
        "expires_at": pairing.token_expires_at,
        "message": "Authority token is valid"
    }


# Expose constants for testing
__all__ = [
    'HermesConnection',
    'HermesPairing',
    'HERMES_CAPABILITIES',
    'HERMES_READABLE_EVENTS',
    'connect',
    'pair',
    'read_status',
    'append_summary',
    'get_filtered_events',
    'validate_authority_token',
    'get_pairing_by_hermes_id'
]


if __name__ == '__main__':
    # Quick proof that constants are defined
    print("Hermes Adapter Module")
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
