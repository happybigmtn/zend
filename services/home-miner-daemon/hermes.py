#!/usr/bin/env python3
"""
Hermes Adapter for Zend

The Hermes adapter sits between the external Hermes agent and the Zend gateway
contract. It enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)
"""

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Import from sibling modules
from spine import append_event, get_events, EventKind
from store import load_or_create_principal, load_pairings, save_pairings

# Constants
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# State directory for Hermes-specific state
def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_STORE_FILE = os.path.join(STATE_DIR, 'hermes-store.json')


@dataclass
class HermesConnection:
    """Represents an active Hermes connection."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    authority_token: str


@dataclass
class HermesPairing:
    """Represents a Hermes pairing record."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


def _load_hermes_pairings() -> dict:
    """Load all Hermes pairing records."""
    if os.path.exists(HERMES_STORE_FILE):
        with open(HERMES_STORE_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    with open(HERMES_STORE_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def pair_hermes(hermes_id: str, device_name: str, capabilities: List[str] = None) -> HermesPairing:
    """
    Create or update a Hermes pairing record.
    
    This is idempotent - pairing the same hermes_id updates the existing record.
    """
    if capabilities is None:
        capabilities = HERMES_CAPABILITIES.copy()
    
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    # Create pairing
    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=capabilities,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=datetime.now(timezone.utc).isoformat()  # Token validity set on connect
    )
    
    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    # Append pairing event to spine
    append_event(
        EventKind.PAIRING_REQUESTED,
        principal.id,
        {
            "device_name": device_name,
            "requested_capabilities": capabilities,
            "device_type": "hermes"
        }
    )
    
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get a Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    return None


def generate_authority_token(hermes_id: str, capabilities: List[str], expires_hours: int = 24) -> str:
    """Generate an authority token for Hermes connection."""
    token_data = {
        "hermes_id": hermes_id,
        "capabilities": capabilities,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + (expires_hours * 3600),
            tz=timezone.utc
        ).isoformat()
    }
    return json.dumps(token_data)


def _parse_authority_token(token: str) -> dict:
    """Parse and validate an authority token."""
    try:
        data = json.loads(token)
        
        # Check required fields
        if 'hermes_id' not in data:
            raise ValueError("Token missing hermes_id")
        if 'capabilities' not in data:
            raise ValueError("Token missing capabilities")
        if 'expires_at' not in data:
            raise ValueError("Token missing expires_at")
        
        # Check expiration
        expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        if expires_at < datetime.now(timezone.utc):
            raise ValueError("Token expired")
        
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid token format: {e}")


def _validate_token_capabilities(capabilities: List[str]) -> None:
    """Validate that token capabilities are within Hermes scope."""
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"Invalid Hermes capability: {cap}. Must be one of {HERMES_CAPABILITIES}")


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Raises ValueError if token is invalid, expired, or has wrong capabilities.
    """
    # Parse and validate token
    token_data = _parse_authority_token(authority_token)
    
    hermes_id = token_data['hermes_id']
    capabilities = token_data['capabilities']
    
    # Validate capabilities are within Hermes scope
    _validate_token_capabilities(capabilities)
    
    # Verify pairing exists
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        raise ValueError(f"No pairing found for Hermes ID: {hermes_id}")
    
    # Create connection
    connection = HermesConnection(
        hermes_id=hermes_id,
        principal_id=pairing.principal_id,
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        authority_token=authority_token
    )
    
    return connection


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability in the connection.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import here to avoid circular dependency
    from daemon import miner
    
    # Get the snapshot
    snapshot = miner.get_snapshot()
    
    # Transform payload - strip fields Hermes shouldn't see
    return {
        "status": snapshot.get("status"),
        "mode": snapshot.get("mode"),
        "hashrate_hs": snapshot.get("hashrate_hs"),
        "temperature": snapshot.get("temperature"),
        "uptime_seconds": snapshot.get("uptime_seconds"),
        "freshness": snapshot.get("freshness"),
        "source": "hermes_adapter"
    }


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability in the connection.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    # Create the event
    event = append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            "summary_text": summary_text,
            "authority_scope": [authority_scope] if isinstance(authority_scope, str) else authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id
        }
    )
    
    return {
        "appended": True,
        "event_id": event.id,
        "created_at": event.created_at
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events and returns only:
    - hermes_summary
    - miner_alert
    - control_receipt
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    # Filter to Hermes-readable events only
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    # Transform events - strip fields Hermes shouldn't see
    result = []
    for event in filtered[:limit]:
        result.append({
            "id": event.id,
            "kind": event.kind,
            "payload": event.payload,
            "created_at": event.created_at
        })
    
    return result


def check_control_denied(connection: HermesConnection) -> dict:
    """
    Check if a control attempt would be denied.
    
    This is used to verify the adapter correctly blocks control commands.
    """
    if 'control' in connection.capabilities:
        return {
            "would_allow": True,
            "reason": "Control capability present (Hermes should never have this)"
        }
    return {
        "would_allow": False,
        "reason": "HERMES_UNAUTHORIZED: Hermes adapter blocks control commands",
        "error_code": "HERMES_UNAUTHORIZED"
    }


# Exported for testing
__all__ = [
    'HermesConnection',
    'HermesPairing',
    'HERMES_CAPABILITIES',
    'HERMES_READABLE_EVENTS',
    'connect',
    'read_status',
    'append_summary',
    'get_filtered_events',
    'pair_hermes',
    'generate_authority_token',
    'check_control_denied'
]
