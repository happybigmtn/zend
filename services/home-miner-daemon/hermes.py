#!/usr/bin/env python3
"""
Hermes Adapter Module

Provides a capability-scoped interface for AI agents (Hermes) to interact
with the Zend daemon's event spine and status endpoints.

Hermes capabilities are 'observe' and 'summarize' - independent from gateway
'observe' and 'control'. Hermes cannot issue control commands or read user messages.
"""

import json
import base64
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

# Import from sibling modules
from spine import EventKind, SpineEvent, get_events, append_event
from store import load_pairings, save_pairings, load_or_create_principal

# Hermes capability constants
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# In-memory connection store for active Hermes connections
# Maps hermes_id -> HermesConnection
_hermes_connections: dict[str, 'HermesConnection'] = {}


@dataclass
class HermesConnection:
    """Represents an active Hermes connection with capability scope."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str


def _decode_jwt_payload(token: str) -> dict:
    """
    Decode a JWT token payload (base64url encoded).
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict
        
    Raises:
        ValueError: If token format is invalid
    """
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format: expected 3 parts")
        
        # Decode payload (second part)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += '=' * padding
        
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)
        
    except (ValueError, json.JSONDecodeError, Exception) as e:
        raise ValueError(f"Invalid token format: {e}")


def _is_token_expired(payload: dict) -> bool:
    """
    Check if a token has expired.
    
    Args:
        payload: Decoded JWT payload with 'exp' field
        
    Returns:
        True if token is expired or missing exp field
    """
    exp = payload.get('exp')
    if exp is None:
        return True  # No expiration means expired
    return time.time() > exp


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: JWT token containing hermes_id, principal_id,
                        capabilities, and expiration
        
    Returns:
        HermesConnection object if token is valid
        
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
    """
    # Decode token
    try:
        payload = _decode_jwt_payload(authority_token)
    except ValueError as e:
        raise ValueError(f"HERMES_INVALID_TOKEN: {e}")
    
    # Check expiration
    if _is_token_expired(payload):
        raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")
    
    # Extract required fields
    hermes_id = payload.get('hermes_id')
    principal_id = payload.get('principal_id')
    capabilities = payload.get('capabilities', [])
    
    # Validate hermes_id
    if not hermes_id:
        raise ValueError("HERMES_INVALID_TOKEN: Missing hermes_id")
    
    # Validate principal_id
    if not principal_id:
        raise ValueError("HERMES_INVALID_TOKEN: Missing principal_id")
    
    # Validate capabilities - must be subset of HERMES_CAPABILITIES
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_INVALID_CAPABILITY: '{cap}' not allowed for Hermes")
    
    # Create connection
    connection = HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat()
    )
    
    # Store connection
    _hermes_connections[hermes_id] = connection
    
    return connection


def get_connection(hermes_id: str) -> Optional[HermesConnection]:
    """
    Get an active Hermes connection by hermes_id.
    
    Args:
        hermes_id: Hermes identifier
        
    Returns:
        HermesConnection if found and active, None otherwise
    """
    return _hermes_connections.get(hermes_id)


def disconnect(hermes_id: str) -> bool:
    """
    Disconnect a Hermes session.
    
    Args:
        hermes_id: Hermes identifier
        
    Returns:
        True if disconnected, False if not found
    """
    if hermes_id in _hermes_connections:
        del _hermes_connections[hermes_id]
        return True
    return False


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability.
    
    Args:
        connection: Active Hermes connection
        
    Returns:
        Miner status dict
        
    Raises:
        PermissionError: If observe capability is missing
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import here to avoid circular import
    from daemon import miner
    
    # Get status snapshot from miner
    return miner.get_snapshot()


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Args:
        connection: Active Hermes connection
        summary_text: The summary text to append
        authority_scope: The scope of the summary (e.g., 'observe')
        
    Returns:
        The created SpineEvent
        
    Raises:
        PermissionError: If summarize capability is missing
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    # Append to spine
    return append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id
        }
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list[SpineEvent]:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events.
    
    Args:
        connection: Active Hermes connection
        limit: Maximum number of events to return
        
    Returns:
        List of filtered SpineEvent objects
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    # Filter to readable event kinds
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    return filtered[:limit]


def pair_hermes(hermes_id: str, device_name: str) -> dict:
    """
    Create a Hermes pairing record in the store.
    
    Hermes pairings get observe+summarize capabilities.
    
    Args:
        hermes_id: Unique Hermes identifier
        device_name: Human-readable device name
        
    Returns:
        Pairing record dict
    """
    principal = load_or_create_principal()
    pairings = load_pairings()
    
    # Check for existing pairing (idempotent)
    for existing in pairings.values():
        if existing.get('hermes_id') == hermes_id:
            return existing
    
    # Create new pairing with Hermes capabilities
    pairing_id = f"hermes-{hermes_id}"
    pairing = {
        "id": pairing_id,
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "device_name": device_name,
        "capabilities": HERMES_CAPABILITIES.copy(),
        "paired_at": datetime.now(timezone.utc).isoformat(),
        "type": "hermes"
    }
    
    pairings[pairing_id] = pairing
    save_pairings(pairings)
    
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[dict]:
    """
    Get a Hermes pairing by hermes_id.
    
    Args:
        hermes_id: Hermes identifier
        
    Returns:
        Pairing dict if found, None otherwise
    """
    pairings = load_pairings()
    for pairing in pairings.values():
        if pairing.get('hermes_id') == hermes_id:
            return pairing
    return None


def list_hermes_pairings() -> list[dict]:
    """
    List all Hermes pairings.
    
    Returns:
        List of Hermes pairing dicts
    """
    pairings = load_pairings()
    return [p for p in pairings.values() if p.get('type') == 'hermes']


# Module-level proof of concept
if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
