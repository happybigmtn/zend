#!/usr/bin/env python3
"""
Hermes Adapter - Zend-native capability boundary for Hermes AI agents.

The Hermes adapter sits between the external Hermes agent and the Zend gateway
contract, enforcing a narrow capability scope:
- observe: read miner status
- summarize: append summaries to the event spine

Hermes CANNOT issue control commands or read user_message events.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')

# Hermes capabilities are observe and summarize only - NOT control
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read from the spine
HERMES_READABLE_EVENTS = [
    'hermes_summary',
    'miner_alert',
    'control_receipt',
]


@dataclass
class HermesConnection:
    """Active Hermes connection with validated capabilities."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    device_name: str = "hermes-agent"


@dataclass
class HermesPairing:
    """Hermes pairing record in the store."""
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token: str
    token_expires_at: str


def _load_hermes_pairings() -> dict:
    """Load all Hermes pairing records."""
    if os.path.exists(HERMES_PAIRING_FILE):
        with open(HERMES_PAIRING_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    with open(HERMES_PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def load_principal_id() -> str:
    """Load the principal ID from the principal store."""
    from .store import load_or_create_principal
    principal = load_or_create_principal()
    return principal.id


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    The authority token is a pairing token issued during Hermes pairing.
    This validates the token exists and is not expired.
    
    Raises:
        ValueError: if token is invalid, expired, or has wrong capabilities.
    """
    pairings = _load_hermes_pairings()
    
    # Find pairing by token
    pairing_data = None
    for p in pairings.values():
        if p.get('token') == authority_token:
            pairing_data = p
            break
    
    if not pairing_data:
        raise ValueError("HERMES_INVALID_TOKEN: authority token not found")
    
    # Check expiration
    expires_at = datetime.fromisoformat(pairing_data['token_expires_at'])
    if expires_at < datetime.now(timezone.utc):
        raise ValueError("HERMES_TOKEN_EXPIRED: authority token has expired")
    
    # Validate capabilities
    capabilities = pairing_data.get('capabilities', [])
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_UNAUTHORIZED: capability '{cap}' not permitted for Hermes")
    
    return HermesConnection(
        hermes_id=pairing_data['hermes_id'],
        principal_id=pairing_data['principal_id'],
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        device_name=pairing_data.get('device_name', 'hermes-agent')
    )


def pair_hermes(hermes_id: str, device_name: str = "hermes-agent") -> HermesPairing:
    """
    Create a new Hermes pairing with observe and summarize capabilities.
    
    This is idempotent - pairing the same hermes_id again returns the existing
    pairing with a fresh token.
    """
    principal_id = load_principal_id()
    pairings = _load_hermes_pairings()
    
    # Check for existing pairing (idempotent)
    for existing in pairings.values():
        if existing['hermes_id'] == hermes_id:
            # Refresh token on re-pair
            existing['token'] = str(uuid.uuid4())
            existing['token_expires_at'] = datetime.now(timezone.utc).isoformat()
            _save_hermes_pairings(pairings)
            return HermesPairing(**existing)
    
    # Create new pairing
    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal_id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token=str(uuid.uuid4()),
        token_expires_at=datetime.now(timezone.utc).isoformat()
    )
    
    pairings[pairing.id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    return pairing


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability in the connection.
    
    Raises:
        PermissionError: if observe capability is not granted.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import miner simulator from daemon
    from .daemon import miner
    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str = "observe"
) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability in the connection.
    
    Args:
        connection: Active Hermes connection
        summary_text: The summary content to append
        authority_scope: The scope of this summary (observe/summarize)
    
    Returns:
        dict with appended event details
    
    Raises:
        PermissionError: if summarize capability is not granted.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    # Import spine functions
    from .spine import append_hermes_summary, append_event, EventKind
    
    event = append_hermes_summary(
        summary_text=summary_text,
        authority_scope=[authority_scope],
        principal_id=connection.principal_id
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
    
    This filters out user_message events that Hermes should never access.
    Over-fetches to account for filtering, then trims to limit.
    
    Args:
        connection: Active Hermes connection
        limit: Maximum number of events to return
    
    Returns:
        List of filtered SpineEvent objects
    """
    from .spine import get_events
    
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    # Filter to only readable event kinds
    filtered = [
        e for e in all_events 
        if e.kind in HERMES_READABLE_EVENTS
    ]
    
    return filtered[:limit]


def validate_hermes_auth(hermes_id: str) -> HermesConnection:
    """
    Validate that a hermes_id is paired and return its connection.
    
    This is used by the daemon to validate Hermes authorization headers.
    
    Raises:
        ValueError: if hermes_id is not paired.
    """
    pairings = _load_hermes_pairings()
    
    for p in pairings.values():
        if p['hermes_id'] == hermes_id:
            return HermesConnection(
                hermes_id=p['hermes_id'],
                principal_id=p['principal_id'],
                capabilities=p['capabilities'],
                connected_at=p['paired_at'],
                device_name=p.get('device_name', 'hermes-agent')
            )
    
    raise ValueError(f"HERMES_NOT_PAIRED: {hermes_id} is not paired")


# Module-level proof of constants
if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 50)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {HERMES_READABLE_EVENTS}")
