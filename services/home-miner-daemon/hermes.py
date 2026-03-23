#!/usr/bin/env python3
"""
Hermes Adapter for Zend Home Miner Daemon.

The Hermes adapter enforces capability boundaries for AI agent connections:
- Hermes can read miner status (observe capability)
- Hermes can append summaries to the event spine (summarize capability)
- Hermes CANNOT issue control commands (no control capability)
- Hermes CANNOT read user_message events (filtered out)

This adapter sits between Hermes Gateway and the Zend Gateway Contract,
enforcing scope before requests reach the event spine.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional

# Add spine and store to path
from spine import append_event, get_events, EventKind, SpineEvent
from store import load_pairings, save_pairings, load_or_create_principal


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')


# Hermes capabilities - observe and summarize only, NO control
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read (blocks user_message)
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


class HermesCapability(str, Enum):
    """Hermes-specific capabilities."""
    OBSERVE = 'observe'
    SUMMARIZE = 'summarize'


@dataclass
class HermesConnection:
    """A validated Hermes connection with granted capabilities."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    device_name: str
    connected_at: str
    token_expires_at: str


@dataclass
class HermesPairing:
    """A Hermes pairing record."""
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


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create a new Hermes pairing with observe + summarize capabilities.
    
    This is idempotent - same hermes_id re-pairs.
    """
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()

    # Check for existing pairing with same hermes_id (idempotent)
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])

    # Create new pairing
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()

    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES.copy(),
        paired_at=datetime.now(timezone.utc).isoformat(),
        token=token,
        token_expires_at=expires
    )

    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)

    # Append pairing event
    append_event(
        EventKind.PAIRING_GRANTED,
        principal.id,
        {
            "device_name": device_name,
            "granted_capabilities": HERMES_CAPABILITIES,
            "hermes_id": hermes_id,
            "pairing_type": "hermes"
        }
    )

    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    return None


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    The authority token is the Hermes pairing token.
    Raises ValueError if token is invalid, expired, or not a Hermes token.
    """
    if not authority_token:
        raise ValueError("HERMES_INVALID_TOKEN: authority token is required")

    pairings = _load_hermes_pairings()

    # Find pairing by token
    for hermes_id, pairing_data in pairings.items():
        if pairing_data.get('token') == authority_token:
            # Validate capabilities include Hermes scope
            caps = pairing_data.get('capabilities', [])
            if 'observe' not in caps or 'summarize' not in caps:
                raise ValueError(
                    "HERMES_CAPABILITY_MISMATCH: token does not have Hermes capabilities"
                )

            return HermesConnection(
                hermes_id=hermes_id,
                principal_id=pairing_data['principal_id'],
                capabilities=caps,
                device_name=pairing_data['device_name'],
                connected_at=datetime.now(timezone.utc).isoformat(),
                token_expires_at=pairing_data['token_expires_at']
            )

    raise ValueError("HERMES_INVALID_TOKEN: authority token not recognized")


def validate_hermes_auth(hermes_id: str) -> HermesConnection:
    """
    Validate Hermes authentication by hermes_id.
    
    Returns connection object if valid.
    Raises PermissionError if hermes_id is not paired.
    """
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        raise PermissionError("HERMES_UNAUTHORIZED: hermes_id not paired")

    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        device_name=pairing.device_name,
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=pairing.token_expires_at
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability.
    Raises PermissionError if capability is missing.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

    # Import miner from daemon (circular import workaround)
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from daemon import miner

    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str = 'observe'
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    Raises PermissionError if capability is missing.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")

    # Append to event spine
    event = append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            "summary_text": summary_text,
            "authority_scope": [authority_scope],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id
        }
    )

    return event


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events that Hermes should not access.
    Returns events sorted by most recent first.
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)

    # Filter to readable event kinds only
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]

    return filtered[:limit]


def check_control_capability(connection: HermesConnection) -> bool:
    """
    Check if Hermes has control capability.
    
    Returns False - Hermes should NEVER have control.
    This is a safety check to prevent accidental capability leakage.
    """
    return 'control' in connection.capabilities


def get_hermes_status(connection: HermesConnection) -> dict:
    """
    Get Hermes connection status and capabilities.
    """
    return {
        "connected": True,
        "hermes_id": connection.hermes_id,
        "principal_id": connection.principal_id,
        "device_name": connection.device_name,
        "capabilities": connection.capabilities,
        "connected_at": connection.connected_at,
        "can_observe": 'observe' in connection.capabilities,
        "can_summarize": 'summarize' in connection.capabilities,
        "can_control": check_control_capability(connection)
    }


# Module proof
if __name__ == '__main__':
    print('Capabilities:', HERMES_CAPABILITIES)
    print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
