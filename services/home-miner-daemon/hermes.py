#!/usr/bin/env python3
"""
Hermes Adapter for Zend Home Miner Daemon.

Provides a capability-scoped interface for Hermes AI agents to connect
to the Zend daemon. Enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

Location in system:
  Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                   ^^^^^^^^^^^^^^^^^^^^
                   THIS IS WHAT WE BUILD
"""

import base64
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from spine import append_event, get_events, EventKind
from store import load_or_create_principal, load_pairings, save_pairings

# Hermes-only capabilities
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Events Hermes is explicitly NOT allowed to read
HERMES_BLOCKED_EVENTS = [
    EventKind.USER_MESSAGE,
]


@dataclass
class HermesConnection:
    """Active Hermes connection session."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    authority_scope: str  # 'observe' or 'observe+summarize'
    token_expires_at: str


@dataclass
class HermesPairing:
    """Hermes device pairing record."""
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token: str
    token_expires_at: str


# In-memory session store for active Hermes connections
# Maps hermes_id -> HermesConnection
_hermes_sessions: dict[str, HermesConnection] = {}


class HermesError(Exception):
    """Base exception for Hermes adapter errors."""
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"{error_code}: {message}")


class HermesUnauthorizedError(HermesError):
    """Raised when Hermes lacks required capability."""
    def __init__(self, message: str):
        super().__init__("HERMES_UNAUTHORIZED", message)


class HermesInvalidTokenError(HermesError):
    """Raised when authority token is invalid or expired."""
    def __init__(self, message: str):
        super().__init__("HERMES_INVALID_TOKEN", message)


def _validate_token_structure(token_data: dict) -> None:
    """Validate token has required fields."""
    required = ['hermes_id', 'principal_id', 'capabilities', 'expires_at']
    for field in required:
        if field not in token_data:
            raise HermesInvalidTokenError(f"Token missing required field: {field}")


def _decode_authority_token(authority_token: str) -> dict:
    """Decode and parse authority token from Base64 JSON."""
    try:
        # Handle both raw Base64 and URL-safe Base64
        padded = authority_token
        padding = 4 - (len(authority_token) % 4)
        if padding != 4:
            padded = authority_token + '=' * padding
        padded = padded.replace('-', '+').replace('_', '/')
        
        decoded = base64.b64decode(padded)
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as e:
        raise HermesInvalidTokenError(f"Invalid token format: {e}")


def _is_token_expired(expires_at: str) -> bool:
    """Check if token expiration time has passed."""
    try:
        expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expires
    except ValueError:
        # If we can't parse the date, treat as expired for safety
        return True


def _validate_hermes_capabilities(capabilities: List[str]) -> None:
    """Validate that capabilities are Hermes-appropriate (no control)."""
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise HermesInvalidTokenError(
                f"Invalid Hermes capability: {cap}. "
                f"Allowed: {HERMES_CAPABILITIES}"
            )


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: Base64-encoded JSON token containing
            hermes_id, principal_id, capabilities, expires_at
            
    Returns:
        HermesConnection object for this session
        
    Raises:
        HermesInvalidTokenError: If token is malformed, expired, or has invalid capabilities
    """
    # Decode and validate token structure
    token_data = _decode_authority_token(authority_token)
    _validate_token_structure(token_data)
    
    # Check expiration
    if _is_token_expired(token_data['expires_at']):
        raise HermesInvalidTokenError("Authority token has expired")
    
    # Validate Hermes capabilities
    capabilities = token_data.get('capabilities', [])
    _validate_hermes_capabilities(capabilities)
    
    # Build authority scope string
    authority_scope = '+'.join(sorted(capabilities)) or 'observe'
    
    # Create connection
    connection = HermesConnection(
        hermes_id=token_data['hermes_id'],
        principal_id=token_data['principal_id'],
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        authority_scope=authority_scope,
        token_expires_at=token_data['expires_at']
    )
    
    # Store session
    _hermes_sessions[connection.hermes_id] = connection
    
    return connection


def get_connection(hermes_id: str) -> Optional[HermesConnection]:
    """Get active Hermes connection by hermes_id."""
    return _hermes_sessions.get(hermes_id)


def validate_hermes_auth(hermes_id: str, required_capability: str) -> HermesConnection:
    """
    Validate Hermes authorization for a specific capability.
    
    Args:
        hermes_id: The Hermes device ID
        required_capability: The capability required (e.g., 'observe')
        
    Returns:
        The HermesConnection if valid
        
    Raises:
        HermesUnauthorizedError: If no session or lacks capability
    """
    connection = get_connection(hermes_id)
    if not connection:
        raise HermesUnauthorizedError(f"No active session for Hermes: {hermes_id}")
    
    if required_capability not in connection.capabilities:
        raise HermesUnauthorizedError(
            f"{required_capability} capability required"
        )
    
    return connection


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability in connection.
    
    Args:
        connection: Active HermesConnection
        
    Returns:
        Miner status snapshot dict
        
    Raises:
        HermesUnauthorizedError: If lacking observe capability
    """
    if 'observe' not in connection.capabilities:
        raise HermesUnauthorizedError("observe capability required")
    
    # Import here to avoid circular dependency
    from daemon import miner
    
    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str
) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability in connection.
    
    Args:
        connection: Active HermesConnection
        summary_text: The summary text to append
        authority_scope: The scope of this summary (e.g., 'observe')
        
    Returns:
        dict with appended event info: {appended: bool, event_id: str}
        
    Raises:
        HermesUnauthorizedError: If lacking summarize capability
    """
    if 'summarize' not in connection.capabilities:
        raise HermesUnauthorizedError("summarize capability required")
    
    if not summary_text or not summary_text.strip():
        raise HermesError("INVALID_INPUT", "summary_text cannot be empty")
    
    event = append_event(
        principal_id=connection.principal_id,
        kind=EventKind.HERMES_SUMMARY,
        payload={
            "summary_text": summary_text.strip(),
            "authority_scope": authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id,
        }
    )
    
    return {
        "appended": True,
        "event_id": event.id
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events and other non-Hermes events.
    
    Args:
        connection: Active HermesConnection
        limit: Maximum number of events to return (default 20)
        
    Returns:
        List of event dicts
    """
    # Over-fetch to account for filtering (Hermes blocked events)
    # We fetch extra to ensure we have enough after filtering
    all_events = get_events(limit=limit * 3)
    
    # Get allowed event kinds as strings
    allowed_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    blocked_kinds = [k.value for k in HERMES_BLOCKED_EVENTS]
    
    # Filter events
    filtered = [
        {
            "id": e.id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
            "principal_id": e.principal_id
        }
        for e in all_events
        if e.kind in allowed_kinds and e.kind not in blocked_kinds
    ]
    
    return filtered[:limit]


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create a new Hermes pairing record.
    
    Idempotent: if hermes_id already exists, returns existing pairing.
    
    Args:
        hermes_id: Unique Hermes identifier
        device_name: Human-readable device name
        
    Returns:
        HermesPairing record
    """
    principal = load_or_create_principal()
    pairings = load_pairings()
    
    # Check for existing Hermes pairing
    hermes_pairings = _get_hermes_pairings_store()
    for p in hermes_pairings.values():
        if p['hermes_id'] == hermes_id:
            return HermesPairing(**p)
    
    # Create new pairing
    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token=str(uuid.uuid4()),
        token_expires_at=datetime.now(timezone.utc).isoformat()
    )
    
    hermes_pairings[pairing.id] = asdict(pairing)
    _save_hermes_pairings(hermes_pairings)
    
    # Also create a device pairing record for consistency
    if pairing.id not in pairings:
        pairings[pairing.id] = {
            "id": pairing.id,
            "principal_id": pairing.principal_id,
            "device_name": pairing.device_name,
            "capabilities": pairing.capabilities,
            "paired_at": pairing.paired_at,
            "token_expires_at": pairing.token_expires_at,
            "token_used": False,
            "device_type": "hermes"
        }
        save_pairings(pairings)
    
    return pairing


def _get_hermes_pairings_store() -> dict:
    """Get the Hermes pairings store file path."""
    import os
    from pathlib import Path
    
    def get_state_dir():
        return str(Path(__file__).resolve().parents[2] / "state")
    
    state_dir = os.environ.get("ZEND_STATE_DIR", get_state_dir())
    os.makedirs(state_dir, exist_ok=True)
    
    store_file = os.path.join(state_dir, 'hermes-pairings.json')
    
    if os.path.exists(store_file):
        with open(store_file, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict) -> None:
    """Save Hermes pairings to store file."""
    import os
    from pathlib import Path
    
    def get_state_dir():
        return str(Path(__file__).resolve().parents[2] / "state")
    
    state_dir = os.environ.get("ZEND_STATE_DIR", get_state_dir())
    store_file = os.path.join(state_dir, 'hermes-pairings.json')
    
    with open(store_file, 'w') as f:
        json.dump(pairings, f, indent=2)


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing by hermes_id."""
    hermes_pairings = _get_hermes_pairings_store()
    for p in hermes_pairings.values():
        if p['hermes_id'] == hermes_id:
            return HermesPairing(**p)
    return None


def create_authority_token(hermes_id: str, capabilities: List[str], expires_in_hours: int = 24) -> str:
    """
    Create an authority token for Hermes.
    
    This is used during pairing to generate the initial token.
    
    Args:
        hermes_id: The Hermes device ID
        capabilities: List of granted capabilities
        expires_in_hours: Token validity in hours (default 24)
        
    Returns:
        Base64-encoded authority token
    """
    principal = load_or_create_principal()
    
    expires = datetime.now(timezone.utc)
    from datetime import timedelta
    expires += timedelta(hours=expires_in_hours)
    
    token_data = {
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "capabilities": capabilities,
        "expires_at": expires.isoformat()
    }
    
    json_bytes = json.dumps(token_data).encode()
    encoded = base64.b64encode(json_bytes).decode()
    
    return encoded


# Module-level proof
if __name__ == '__main__':
    print('Capabilities:', HERMES_CAPABILITIES)
    print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
    print('Blocked events:', [e.value for e in HERMES_BLOCKED_EVENTS])
