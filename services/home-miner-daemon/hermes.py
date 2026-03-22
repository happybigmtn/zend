#!/usr/bin/env python3
"""
Hermes Adapter for Zend Home Miner Daemon.

The Hermes adapter is a capability boundary that sits between the external
Hermes agent and the Zend gateway contract. It enforces:

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

from spine import append_event, get_events, EventKind
from store import load_or_create_principal, get_pairing_by_device

# Hermes capabilities: observe and summarize, no control
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Events Hermes is NOT allowed to read (filtered out)
HERMES_BLOCKED_EVENTS = [
    EventKind.USER_MESSAGE,
    EventKind.PAIRING_REQUESTED,
    EventKind.PAIRING_GRANTED,
    EventKind.CAPABILITY_REVOKED,
]


@dataclass
class HermesConnection:
    """Represents an active Hermes connection with validated capabilities."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str

    def has_capability(self, cap: str) -> bool:
        """Check if connection has a specific capability."""
        return cap in self.capabilities


@dataclass
class HermesPairing:
    """Hermes-specific pairing record."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token: str
    token_expires_at: str


def _get_hermes_store_path() -> Path:
    """Get the path to the Hermes pairing store."""
    from store import STATE_DIR
    return Path(STATE_DIR) / 'hermes-pairings.json'


def _load_hermes_pairings() -> dict:
    """Load all Hermes pairing records."""
    store_path = _get_hermes_store_path()
    if store_path.exists():
        with open(store_path, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    store_path = _get_hermes_store_path()
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with open(store_path, 'w') as f:
        json.dump(pairings, f, indent=2)


def is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    try:
        expires = datetime.fromisoformat(expires_at)
        return datetime.now(timezone.utc) > expires
    except (ValueError, TypeError):
        return True


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create a new Hermes pairing record with observe + summarize capabilities.
    
    This is idempotent: calling with the same hermes_id returns the existing
    pairing rather than creating a duplicate.
    """
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()

    # Idempotent: return existing pairing if hermes_id already exists
    if hermes_id in pairings:
        data = pairings[hermes_id]
        return HermesPairing(**data)

    # Create new pairing
    token = str(uuid.uuid4())
    paired_at = datetime.now(timezone.utc).isoformat()
    # Token expires in 30 days
    expires = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0) 
               + datetime.timedelta(days=30)).isoformat()

    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=paired_at,
        token=token,
        token_expires_at=expires
    )

    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)

    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get a Hermes pairing by hermes_id."""
    pairings = _load_hermes_pairings()
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    return None


def generate_authority_token(hermes_id: str) -> str:
    """
    Generate an authority token for Hermes.
    
    The token is a base64-encoded JSON structure containing:
    - hermes_id: The Hermes agent identifier
    - principal_id: The principal this Hermes represents
    - capabilities: The granted capabilities
    - expires_at: Token expiration timestamp
    """
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        raise ValueError(f"Hermes pairing not found: {hermes_id}")

    token_data = {
        'hermes_id': hermes_id,
        'principal_id': pairing.principal_id,
        'capabilities': pairing.capabilities,
        'expires_at': pairing.token_expires_at
    }

    import base64
    token = base64.b64encode(json.dumps(token_data).encode()).decode()
    return token


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Raises ValueError if:
    - Token is malformed
    - Token is expired
    - Token capabilities don't match Hermes requirements
    """
    import base64

    try:
        # Decode token
        token_bytes = base64.b64decode(authority_token.encode())
        token_data = json.loads(token_bytes)
    except Exception as e:
        raise ValueError(f"Invalid authority token: {e}")

    # Validate required fields
    for field in ['hermes_id', 'principal_id', 'capabilities', 'expires_at']:
        if field not in token_data:
            raise ValueError(f"Token missing required field: {field}")

    # Check expiration
    if is_token_expired(token_data['expires_at']):
        raise ValueError("Authority token has expired")

    # Validate capabilities match Hermes requirements
    token_caps = set(token_data['capabilities'])
    hermes_caps = set(HERMES_CAPABILITIES)
    
    if not token_caps.issubset(hermes_caps):
        invalid = token_caps - hermes_caps
        raise ValueError(f"Token contains invalid Hermes capabilities: {invalid}")

    # Verify pairing exists
    pairing = get_hermes_pairing(token_data['hermes_id'])
    if not pairing:
        raise ValueError(f"Hermes pairing not found: {token_data['hermes_id']}")

    return HermesConnection(
        hermes_id=token_data['hermes_id'],
        principal_id=token_data['principal_id'],
        capabilities=token_data['capabilities'],
        connected_at=datetime.now(timezone.utc).isoformat()
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.
    
    Requires 'observe' capability. Returns miner snapshot with status,
    mode, hashrate, temperature, uptime, and freshness.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

    # Import here to avoid circular imports
    from daemon import miner
    return miner.get_snapshot()


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability. Creates a hermes_summary event
    with the summary text, authority scope, and generation timestamp.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")

    event = append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
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
        "created_at": event.created_at
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.
    
    Filters out:
    - user_message events (privacy)
    - pairing_requested/granted events (not relevant to Hermes)
    - capability_revoked events (admin only)
    
    Over-fetches to account for filtering, then trims to limit.
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 3)

    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    
    # Filter to only readable events
    filtered = [e for e in all_events if e.kind in readable_kinds]

    # Strip sensitive fields from events
    sanitized = []
    for event in filtered:
        sanitized_event = {
            "id": event.id,
            "kind": event.kind,
            "principal_id": event.principal_id,
            "payload": _sanitize_payload(event.kind, event.payload),
            "created_at": event.created_at
        }
        sanitized.append(sanitized_event)

    return sanitized[:limit]


def _sanitize_payload(kind: str, payload: dict) -> dict:
    """
    Strip fields from payload that Hermes shouldn't see.
    
    Currently passes through all fields but this is where we'd
    add field-level filtering if needed in the future.
    """
    # For milestone 1, Hermes sees all fields of readable events
    return payload


def get_hermes_capabilities() -> List[str]:
    """Return the list of Hermes capabilities."""
    return HERMES_CAPABILITIES.copy()


def get_hermes_readable_events() -> List[str]:
    """Return the list of event kinds Hermes can read."""
    return [k.value for k in HERMES_READABLE_EVENTS]
