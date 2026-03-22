#!/usr/bin/env python3
"""
Hermes Adapter - Zend gateway adapter for Hermes AI agent.

The Hermes adapter sits between the external Hermes agent and the Zend gateway:
  Hermes Gateway → Hermes Adapter → Zend Gateway Contract → Event Spine

The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List, Optional

from spine import EventKind, append_event, get_events
from store import load_pairings, save_pairings, load_or_create_principal

# Hermes capability constants
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Store file for Hermes pairings
HERMES_STORE_FILE = "state/hermes-pairings.json"


def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records."""
    import os
    from pathlib import Path
    
    state_dir = os.environ.get("ZEND_STATE_DIR", str(Path(__file__).resolve().parents[2] / "state"))
    os.makedirs(state_dir, exist_ok=True)
    pairing_file = os.path.join(state_dir, 'hermes-pairings.json')
    
    if os.path.exists(pairing_file):
        with open(pairing_file, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    import os
    from pathlib import Path
    
    state_dir = os.environ.get("ZEND_STATE_DIR", str(Path(__file__).resolve().parents[2] / "state"))
    os.makedirs(state_dir, exist_ok=True)
    pairing_file = os.path.join(state_dir, 'hermes-pairings.json')
    
    with open(pairing_file, 'w') as f:
        json.dump(pairings, f, indent=2)


@dataclass
class HermesConnection:
    """Active Hermes connection with validated authority."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    authority_scope: str


def is_token_expired(token_data: dict) -> bool:
    """Check if an authority token has expired."""
    expires_at = token_data.get('token_expires_at')
    if not expires_at:
        return True
    
    try:
        expires_dt = datetime.fromisoformat(expires_at)
        return datetime.now(timezone.utc) > expires_dt
    except (ValueError, TypeError):
        return True


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: JSON string containing token data with hermes_id, 
                        principal_id, capabilities, and token_expires_at
        
    Returns:
        HermesConnection with validated capabilities
        
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
        PermissionError: If requested capabilities exceed Hermes scope
    """
    try:
        token_data = json.loads(authority_token)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("HERMES_INVALID_TOKEN: Authority token must be valid JSON")
    
    hermes_id = token_data.get('hermes_id')
    principal_id = token_data.get('principal_id')
    capabilities = token_data.get('capabilities', [])
    expires_at = token_data.get('token_expires_at')
    
    if not hermes_id:
        raise ValueError("HERMES_INVALID_TOKEN: hermes_id is required")
    
    if not principal_id:
        raise ValueError("HERMES_INVALID_TOKEN: principal_id is required")
    
    if not expires_at:
        raise ValueError("HERMES_INVALID_TOKEN: token_expires_at is required")
    
    # Check expiration
    try:
        expires_dt = datetime.fromisoformat(expires_at)
        if datetime.now(timezone.utc) > expires_dt:
            raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")
    except TypeError:
        raise ValueError("HERMES_INVALID_TOKEN: Invalid token_expires_at format")
    except ValueError:
        # Re-raise ValueError (includes HERMES_TOKEN_EXPIRED)
        raise
    
    # Validate requested capabilities are within Hermes scope
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise PermissionError(
                f"HERMES_UNAUTHORIZED: Capability '{cap}' is not in Hermes scope. "
                f"Allowed: {HERMES_CAPABILITIES}"
            )
    
    # Validate against stored pairing if exists
    pairings = _load_hermes_pairings()
    if hermes_id in pairings:
        stored = pairings[hermes_id]
        if stored.get('principal_id') != principal_id:
            raise ValueError("HERMES_INVALID_TOKEN: hermes_id does not match principal")
    
    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        authority_scope=','.join(capabilities)
    )


def pair_hermes(hermes_id: str, device_name: str, capabilities: Optional[List[str]] = None) -> dict:
    """
    Create a new Hermes pairing record.
    
    Args:
        hermes_id: Unique identifier for Hermes agent
        device_name: Descriptive name for the Hermes instance
        capabilities: List of capabilities (defaults to observe, summarize)
        
    Returns:
        Dict with pairing details
    """
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    # Idempotent pairing
    if hermes_id in pairings:
        return pairings[hermes_id]
    
    if capabilities is None:
        capabilities = HERMES_CAPABILITIES.copy()
    
    # Validate capabilities
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_INVALID_CAPABILITY: '{cap}' not in Hermes scope")
    
    expires_at = datetime.now(timezone.utc).isoformat()
    
    pairing = {
        'hermes_id': hermes_id,
        'device_name': device_name,
        'principal_id': principal.id,
        'capabilities': capabilities,
        'paired_at': datetime.now(timezone.utc).isoformat(),
        'token_expires_at': expires_at,
        'token_used': False
    }
    
    pairings[hermes_id] = pairing
    _save_hermes_pairings(pairings)
    
    # Append pairing event to spine
    append_event(
        EventKind.PAIRING_GRANTED,
        principal.id,
        {
            'device_name': device_name,
            'device_type': 'hermes',
            'capabilities': capabilities
        }
    )
    
    return pairing


def generate_authority_token(hermes_id: str) -> str:
    """
    Generate an authority token for a Hermes pairing.
    
    Args:
        hermes_id: Hermes pairing ID
        
    Returns:
        JSON string containing the authority token
    """
    pairings = _load_hermes_pairings()
    
    if hermes_id not in pairings:
        raise ValueError(f"HERMES_NOT_PAIRED: No pairing found for '{hermes_id}'")
    
    pairing = pairings[hermes_id]
    
    # Token valid for 24 hours
    expires_at = datetime.now(timezone.utc)
    from datetime import timedelta
    expires_at = (expires_at + timedelta(hours=24)).isoformat()
    
    token = {
        'hermes_id': hermes_id,
        'principal_id': pairing['principal_id'],
        'capabilities': pairing['capabilities'],
        'token_expires_at': expires_at,
        'token_id': str(uuid.uuid4())
    }
    
    return json.dumps(token)


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter. Requires observe capability.
    
    Args:
        connection: Validated HermesConnection
        
    Returns:
        Dict with miner status snapshot
        
    Raises:
        PermissionError: If connection lacks observe capability
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required to read status")
    
    # Import here to avoid circular dependency
    from daemon import miner
    
    return miner.get_snapshot()


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict:
    """
    Append a Hermes summary to the event spine. Requires summarize capability.
    
    Args:
        connection: Validated HermesConnection
        summary_text: The summary content to append
        authority_scope: Context for the summary (e.g., 'observe', 'control_receipt')
        
    Returns:
        Dict with append confirmation
        
    Raises:
        PermissionError: If connection lacks summarize capability
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required to append summaries")
    
    event = append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            'summary_text': summary_text,
            'authority_scope': authority_scope,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'hermes_id': connection.hermes_id
        }
    )
    
    return {
        'appended': True,
        'event_id': event.id,
        'kind': event.kind,
        'created_at': event.created_at
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see. Filters out user_message.
    
    Args:
        connection: Validated HermesConnection
        limit: Maximum number of events to return
        
    Returns:
        List of filtered events
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    # Filter to Hermes-readable events only
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    # Strip sensitive payload fields
    sanitized = []
    for event in filtered:
        sanitized.append({
            'id': event.id,
            'kind': event.kind,
            'principal_id': event.principal_id,
            'payload': _sanitize_payload(event.kind, event.payload),
            'created_at': event.created_at,
            'version': event.version
        })
    
    return sanitized[:limit]


def _sanitize_payload(kind: str, payload: dict) -> dict:
    """
    Strip fields from payload that Hermes shouldn't see.
    
    Args:
        kind: Event kind
        payload: Original payload
        
    Returns:
        Sanitized payload
    """
    # Hermes should not see user_message content - this is already filtered
    # but we sanitize anyway for defense in depth
    sanitized = payload.copy()
    
    # Remove any fields marked as sensitive
    sensitive_fields = ['user_id', 'recipient_id', 'memo_content', 'decrypted_content']
    for field in sensitive_fields:
        if field in sanitized:
            del sanitized[field]
    
    return sanitized


def verify_connection(connection: HermesConnection, required_capability: str) -> bool:
    """
    Verify a connection has the required capability.
    
    Args:
        connection: HermesConnection to verify
        required_capability: Capability to check for
        
    Returns:
        True if connection has required capability
    """
    return required_capability in connection.capabilities


def get_hermes_pairings() -> List[dict]:
    """Get all Hermes pairings."""
    return list(_load_hermes_pairings().values())


if __name__ == '__main__':
    # Test module constants
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
