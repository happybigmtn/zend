#!/usr/bin/env python3
"""
Hermes Adapter Module

Hermes is an AI agent that can connect to the Zend daemon through this adapter.
The adapter enforces a capability boundary: Hermes can observe and summarize,
but cannot issue control commands or read user messages.

The adapter sits between the external Hermes agent and the Zend gateway contract:

    Hermes → Hermes Adapter → Event Spine

Enforces:
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
from enum import Enum
from pathlib import Path
from typing import Optional


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_STORE_FILE = os.path.join(STATE_DIR, 'hermes-store.json')


class EventKind(str, Enum):
    """Event kinds supported by the spine."""
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"


# Hermes capability constants
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


@dataclass
class HermesConnection:
    """Represents an active Hermes connection."""
    hermes_id: str
    principal_id: str
    capabilities: list
    connected_at: str

    def has_capability(self, cap: str) -> bool:
        """Check if connection has a specific capability."""
        return cap in self.capabilities


@dataclass
class HermesPairing:
    """Hermes pairing record stored in the hermes store."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: list
    paired_at: str
    token: str
    token_expires_at: str


def _load_hermes_store() -> dict:
    """Load Hermes pairing records from store."""
    if os.path.exists(HERMES_STORE_FILE):
        with open(HERMES_STORE_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_store(store: dict):
    """Save Hermes pairing records to store."""
    with open(HERMES_STORE_FILE, 'w') as f:
        json.dump(store, f, indent=2)


def _parse_authority_token(token: str) -> dict:
    """Parse authority token into components.
    
    Authority token format: base64(json({
        "hermes_id": "...",
        "principal_id": "...",
        "capabilities": ["observe", "summarize"],
        "expires_at": "ISO8601 timestamp"
    }))
    """
    import base64
    
    try:
        # Remove 'Hermes ' prefix if present
        if token.startswith('Hermes '):
            token = token[7:]
        
        decoded = base64.b64decode(token).decode('utf-8')
        data = json.loads(decoded)
        
        required_fields = ['hermes_id', 'principal_id', 'capabilities', 'expires_at']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        return data
    except Exception as e:
        raise ValueError(f"Invalid authority token: {e}")


def _is_token_expired(expires_at: str) -> bool:
    """Check if token has expired."""
    try:
        expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expires
    except (ValueError, AttributeError):
        return True


def pair_hermes(hermes_id: str, device_name: str, principal_id: str) -> HermesPairing:
    """Create a new Hermes pairing record.
    
    This is idempotent - same hermes_id will update existing pairing.
    """
    store = _load_hermes_store()
    
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc)
    expires = expires.replace(year=expires.year + 1)  # 1 year expiry
    
    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal_id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES.copy(),
        paired_at=datetime.now(timezone.utc).isoformat(),
        token=token,
        token_expires_at=expires.isoformat()
    )
    
    store[hermes_id] = asdict(pairing)
    _save_hermes_store(store)
    
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing by hermes_id."""
    store = _load_hermes_store()
    if hermes_id in store:
        return HermesPairing(**store[hermes_id])
    return None


def connect(authority_token: str) -> HermesConnection:
    """Validate authority token and establish Hermes connection.
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities.
    """
    # Parse and validate token
    token_data = _parse_authority_token(authority_token)
    
    # Check expiration
    if _is_token_expired(token_data['expires_at']):
        raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")
    
    # Validate capabilities
    for cap in token_data['capabilities']:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_INVALID_CAPABILITY: '{cap}' is not a valid Hermes capability")
    
    # Verify hermes_id exists in store
    pairing = get_hermes_pairing(token_data['hermes_id'])
    if not pairing:
        raise ValueError("HERMES_UNAUTHORIZED: Hermes not registered")
    
    # Verify capabilities match
    if set(token_data['capabilities']) != set(pairing.capabilities):
        raise ValueError("HERMES_CAPABILITY_MISMATCH: Token capabilities do not match registration")
    
    return HermesConnection(
        hermes_id=token_data['hermes_id'],
        principal_id=token_data['principal_id'],
        capabilities=token_data['capabilities'],
        connected_at=datetime.now(timezone.utc).isoformat()
    )


def read_status(connection: HermesConnection) -> dict:
    """Read miner status through adapter.
    
    Requires 'observe' capability.
    
    Raises:
        PermissionError: If Hermes lacks observe capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import here to avoid circular dependency
    from daemon import miner
    
    status = miner.get_snapshot()
    
    # Strip sensitive fields Hermes shouldn't see
    return {
        "status": status["status"],
        "mode": status["mode"],
        "hashrate_hs": status["hashrate_hs"],
        "temperature": status["temperature"],
        "uptime_seconds": status["uptime_seconds"],
        "hermes_connected_at": connection.connected_at,
        "capabilities": connection.capabilities
    }


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict:
    """Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Raises:
        PermissionError: If Hermes lacks summarize capability.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    # Import here to avoid circular dependency
    from spine import append_event, EventKind
    
    event = append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "hermes_id": connection.hermes_id,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    )
    
    return {
        "appended": True,
        "event_id": event.id,
        "created_at": event.created_at
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """Return events Hermes is allowed to see.
    
    Filters out user_message events and returns only Hermes-readable events.
    """
    # Import here to avoid circular dependency
    from spine import get_events
    
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 3)
    
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    
    filtered = [
        {
            "id": e.id,
            "principal_id": e.principal_id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at
        }
        for e in all_events
        if e.kind in readable_kinds
    ]
    
    return filtered[:limit]


def generate_authority_token(hermes_id: str, principal_id: str, capabilities: list) -> str:
    """Generate an authority token for Hermes.
    
    This is a utility function for testing and pairing flow.
    Returns a base64-encoded token string.
    """
    import base64
    
    expires = datetime.now(timezone.utc)
    expires = expires.replace(hour=expires.hour + 1)  # 1 hour validity
    
    token_data = {
        "hermes_id": hermes_id,
        "principal_id": principal_id,
        "capabilities": capabilities,
        "expires_at": expires.isoformat()
    }
    
    encoded = base64.b64encode(json.dumps(token_data).encode()).decode()
    return encoded


def get_hermes_events(hermes_id: str, limit: int = 20) -> list:
    """Get Hermes-specific events from the spine.
    
    Returns only events generated by this hermes_id.
    """
    from spine import get_events
    
    all_events = get_events(limit=limit * 3)
    
    hermes_events = [
        {
            "id": e.id,
            "principal_id": e.principal_id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at
        }
        for e in all_events
        if e.kind == EventKind.HERMES_SUMMARY.value and e.payload.get("hermes_id") == hermes_id
    ]
    
    return hermes_events[:limit]
