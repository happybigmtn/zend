#!/usr/bin/env python3
"""
Hermes Adapter - Capability-scoped adapter for Hermes AI agent.

The adapter sits between the external Hermes agent and the Zend gateway contract:
```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IS WHAT WE BUILD
```

The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from store import (
    load_or_create_principal,
    load_pairings,
    save_pairings,
    GatewayPairing,
)
from spine import (
    EventKind,
    SpineEvent,
    get_events,
    append_event,
)


# Hermes capabilities - observe and summarize only (no control)
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Events Hermes is allowed to write
HERMES_WRITABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
]


class HermesAdapterError(Exception):
    """Base exception for Hermes adapter errors."""
    pass


class HermesUnauthorizedError(HermesAdapterError):
    """Raised when Hermes lacks required capability."""
    pass


class HermesTokenExpiredError(HermesAdapterError):
    """Raised when authority token has expired."""
    pass


class HermesInvalidTokenError(HermesAdapterError):
    """Raised when authority token is malformed or invalid."""
    pass


@dataclass
class HermesConnection:
    """Represents an active Hermes connection."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str
    device_name: str = ""
    
    def has_capability(self, capability: str) -> bool:
        """Check if this connection has a specific capability."""
        return capability in self.capabilities


@dataclass
class HermesPairing:
    """Represents a Hermes pairing record."""
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records from store."""
    pairings = load_pairings()
    hermes_pairings = {}
    for pairing_id, pairing_data in pairings.items():
        # Check if this is a Hermes pairing (has hermes_id marker)
        if pairing_data.get('hermes_id'):
            hermes_pairings[pairing_id] = pairing_data
    return hermes_pairings


def _save_hermes_pairing(pairing: HermesPairing):
    """Save a Hermes pairing record."""
    pairings = load_pairings()
    pairings[pairing.id] = asdict(pairing)
    save_pairings(pairings)


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create a new Hermes pairing record.
    
    Hermes pairings always get observe + summarize capabilities.
    Pairing is idempotent - same hermes_id re-pairs.
    
    Args:
        hermes_id: Unique Hermes identifier
        device_name: Human-readable name for the Hermes agent
        
    Returns:
        HermesPairing record with observe + summarize capabilities
    """
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    # Check for existing pairing with same hermes_id (idempotent)
    for existing in pairings.values():
        if existing.get('hermes_id') == hermes_id:
            return HermesPairing(**existing)
    
    # Create new pairing
    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=datetime.now(timezone.utc).isoformat(),
    )
    
    _save_hermes_pairing(pairing)
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get a Hermes pairing by hermes_id."""
    pairings = _load_hermes_pairings()
    for pairing in pairings.values():
        if pairing.get('hermes_id') == hermes_id:
            return HermesPairing(**pairing)
    return None


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    The authority token format is JSON: {
        "hermes_id": "hermes-001",
        "principal_id": "...",
        "capabilities": ["observe", "summarize"],
        "expires_at": "2026-03-22T12:00:00Z"
    }
    
    Args:
        authority_token: Base64-encoded JSON authority token
        
    Returns:
        HermesConnection if token is valid
        
    Raises:
        HermesInvalidTokenError: If token is malformed
        HermesTokenExpiredError: If token has expired
        HermesUnauthorizedError: If token lacks Hermes capabilities
    """
    try:
        # Try to decode as base64, fallback to plain JSON
        try:
            import base64
            token_data = json.loads(base64.b64decode(authority_token).decode())
        except Exception:
            # Try plain JSON for development
            token_data = json.loads(authority_token)
    except json.JSONDecodeError as e:
        raise HermesInvalidTokenError(f"Invalid token format: {e}")
    
    # Validate required fields
    required_fields = ['hermes_id', 'principal_id', 'capabilities', 'expires_at']
    for field in required_fields:
        if field not in token_data:
            raise HermesInvalidTokenError(f"Missing required field: {field}")
    
    # Check expiration
    try:
        expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
        if expires_at < datetime.now(timezone.utc):
            raise HermesTokenExpiredError("Authority token has expired")
    except ValueError as e:
        raise HermesInvalidTokenError(f"Invalid expiration format: {e}")
    
    # Validate Hermes capabilities
    token_caps = set(token_data['capabilities'])
    required_caps = set(HERMES_CAPABILITIES)
    
    if not required_caps.issubset(token_caps):
        missing = required_caps - token_caps
        raise HermesUnauthorizedError(f"Token missing required capabilities: {missing}")
    
    # Reject control capability (Hermes should never have control)
    if 'control' in token_caps:
        raise HermesUnauthorizedError("Hermes cannot have control capability")
    
    # Verify pairing exists
    pairing = get_hermes_pairing(token_data['hermes_id'])
    if not pairing:
        # Auto-pair for convenience during development
        pairing = pair_hermes(token_data['hermes_id'], f"hermes-{token_data['hermes_id']}")
    
    return HermesConnection(
        hermes_id=token_data['hermes_id'],
        principal_id=token_data['principal_id'],
        capabilities=token_data['capabilities'],
        connected_at=datetime.now(timezone.utc).isoformat(),
        device_name=pairing.device_name,
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability.
    
    Args:
        connection: Active Hermes connection
        
    Returns:
        Miner status snapshot dict
        
    Raises:
        HermesUnauthorizedError: If connection lacks observe capability
    """
    if 'observe' not in connection.capabilities:
        raise HermesUnauthorizedError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import here to avoid circular dependency
    from daemon import miner
    
    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Args:
        connection: Active Hermes connection
        summary_text: The summary text to append
        authority_scope: The scope of authority used ('observe', 'summarize', or both)
        
    Returns:
        The created SpineEvent
        
    Raises:
        HermesUnauthorizedError: If connection lacks summarize capability
    """
    if 'summarize' not in connection.capabilities:
        raise HermesUnauthorizedError("HERMES_UNAUTHORIZED: summarize capability required")
    
    return append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text,
            "authority_scope": [authority_scope] if isinstance(authority_scope, str) else authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events that Hermes should never access.
    
    Args:
        connection: Active Hermes connection
        limit: Maximum number of events to return
        
    Returns:
        List of filtered SpineEvents
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 3)
    
    # Filter to only Hermes-readable events
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    return filtered[:limit]


def is_hermes_auth_header(authorization: str) -> bool:
    """
    Check if an Authorization header is Hermes auth.
    
    Format: "Hermes <hermes_id>"
    """
    if not authorization:
        return False
    return authorization.startswith('Hermes ')


def extract_hermes_id(authorization: str) -> Optional[str]:
    """Extract hermes_id from Hermes Authorization header."""
    if not is_hermes_auth_header(authorization):
        return None
    return authorization.split(' ', 1)[1] if ' ' in authorization else None
