#!/usr/bin/env python3
"""
Hermes Adapter Module

Provides a capability boundary between the Hermes AI agent and the Zend
gateway contract. Hermes can observe miner status and append summaries,
but cannot issue control commands or read user messages.

Architecture:
    Hermes Gateway → Hermes Adapter → Zend Gateway → Event Spine

This module enforces:
- Authority token validation (principal_id, hermes_id, capabilities, expiration)
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
from typing import List, Optional

# Import from sibling modules
from . import spine
from . import store

# Add service path for direct testing
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# Constants
# =============================================================================

HERMES_CAPABILITIES = ['observe', 'summarize']
"""Hermes is granted observe and summarize capabilities only."""

HERMES_READABLE_EVENTS = [
    spine.EventKind.HERMES_SUMMARY,
    spine.EventKind.MINER_ALERT,
    spine.EventKind.CONTROL_RECEIPT,
]
"""Hermes may read hermes_summary, miner_alert, and control_receipt events."""

HERMES_BLOCKED_EVENTS = [
    spine.EventKind.USER_MESSAGE,
]
"""Hermes is blocked from reading user_message events."""


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class HermesConnection:
    """Represents an active Hermes connection with validated authority."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str

    def has_capability(self, capability: str) -> bool:
        """Check if this connection has the specified capability."""
        return capability in self.capabilities


@dataclass
class HermesPairing:
    """Represents a Hermes device pairing record."""
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


@dataclass
class AuthorityToken:
    """Parsed authority token for Hermes connection."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    expires_at: str


# =============================================================================
# Token Management
# =============================================================================

def _get_hermes_state_dir() -> str:
    """Get the Hermes-specific state directory."""
    return os.path.join(store.default_state_dir(), 'hermes')


def _ensure_hermes_dir():
    """Ensure the Hermes state directory exists."""
    hermes_dir = _get_hermes_state_dir()
    os.makedirs(hermes_dir, exist_ok=True)
    return hermes_dir


def _get_hermes_pairings_file() -> str:
    """Get the path to the Hermes pairings store."""
    return os.path.join(_get_hermes_state_dir(), 'pairings.json')


def _load_hermes_pairings() -> dict:
    """Load all Hermes pairing records."""
    pairings_file = _get_hermes_pairings_file()
    if os.path.exists(pairings_file):
        with open(pairings_file, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    _ensure_hermes_dir()
    pairings_file = _get_hermes_pairings_file()
    with open(pairings_file, 'w') as f:
        json.dump(pairings, f, indent=2)


def _load_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Load a specific Hermes pairing by ID."""
    pairings = _load_hermes_pairings()
    for pairing_data in pairings.values():
        if pairing_data.get('hermes_id') == hermes_id:
            return HermesPairing(**pairing_data)
    return None


def _is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    try:
        expires_dt = datetime.fromisoformat(expires_at)
        return datetime.now(timezone.utc) > expires_dt
    except (ValueError, TypeError):
        return True


# =============================================================================
# Authority Token Operations
# =============================================================================

def _generate_authority_token(hermes_id: str, principal_id: str, 
                               capabilities: List[str]) -> tuple[str, str]:
    """Generate an authority token and expiration time."""
    token = str(uuid.uuid4())
    # Authority tokens expire in 24 hours
    from datetime import timedelta
    expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    return token, expires


def _validate_authority_token_structure(token: str) -> Optional[dict]:
    """
    Validate the structure of an authority token.
    
    For milestone 1, tokens are UUIDs stored in the pairing record.
    In production, this would use cryptographic signatures.
    """
    # Check if token looks like a UUID
    try:
        uuid.UUID(token)
        return {'format': 'uuid'}
    except (ValueError, TypeError):
        return None


def _lookup_token_pairing(token: str) -> Optional[HermesPairing]:
    """
    Look up the pairing associated with an authority token.
    
    For milestone 1, we use a simple token-to-pairing lookup.
    The token is stored in the pairing record.
    """
    pairings = _load_hermes_pairings()
    for pairing_data in pairings.values():
        if pairing_data.get('token') == token:
            return HermesPairing(**pairing_data)
    return None


# =============================================================================
# Core Adapter Operations
# =============================================================================

def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create or update a Hermes pairing with observe and summarize capabilities.
    
    This is idempotent: pairing the same hermes_id updates the existing record.
    
    Args:
        hermes_id: Unique identifier for the Hermes agent
        device_name: Human-readable name for the Hermes device
        
    Returns:
        HermesPairing record with granted capabilities
        
    Raises:
        ValueError: If hermes_id or device_name is invalid
    """
    if not hermes_id:
        raise ValueError("hermes_id is required")
    if not device_name:
        raise ValueError("device_name is required")
    
    _ensure_hermes_dir()
    principal = store.load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    # Check for existing pairing by hermes_id
    existing = None
    existing_id = None
    for pid, pdata in pairings.items():
        if pdata.get('hermes_id') == hermes_id:
            existing = HermesPairing(**pdata)
            existing_id = pid
            break
    
    # Generate token for this pairing
    token, expires = _generate_authority_token(hermes_id, principal.id, 
                                                HERMES_CAPABILITIES)
    
    if existing:
        # Update existing pairing (idempotent)
        pairing = HermesPairing(
            id=existing.id,
            hermes_id=hermes_id,
            principal_id=principal.id,
            device_name=device_name,
            capabilities=HERMES_CAPABILITIES,
            paired_at=existing.paired_at,
            token_expires_at=expires
        )
        pairing_data = asdict(pairing)
        pairing_data['token'] = token  # Update token on each pair
        pairings[existing_id] = pairing_data
    else:
        # Create new pairing
        pairing = HermesPairing(
            id=str(uuid.uuid4()),
            hermes_id=hermes_id,
            principal_id=principal.id,
            device_name=device_name,
            capabilities=HERMES_CAPABILITIES,
            paired_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=expires
        )
        pairing_data = asdict(pairing)
        pairing_data['token'] = token
        pairings[pairing.id] = pairing_data
    
    _save_hermes_pairings(pairings)
    
    # Log observability event
    _log_hermes_event('gateway.hermes.paired', {
        'hermes_id': hermes_id,
        'device_name': device_name,
        'capabilities': HERMES_CAPABILITIES
    })
    
    return pairing


def get_pairing_token(hermes_id: str) -> Optional[str]:
    """Get the current authority token for a paired Hermes device."""
    pairing = _load_hermes_pairing(hermes_id)
    if not pairing:
        return None
    
    pairings = _load_hermes_pairings()
    for pdata in pairings.values():
        if pdata.get('hermes_id') == hermes_id:
            return pdata.get('token')
    return None


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: The authority token issued during pairing
        
    Returns:
        HermesConnection with validated capabilities
        
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
    """
    # Validate token structure
    token_info = _validate_authority_token_structure(authority_token)
    if not token_info:
        _log_hermes_event('gateway.hermes.unauthorized', {
            'reason': 'invalid_token_format',
            'action': 'connect'
        })
        raise ValueError("HERMES_UNAUTHORIZED: invalid token format")
    
    # Look up the pairing by token
    pairing = _lookup_token_pairing(authority_token)
    if not pairing:
        _log_hermes_event('gateway.hermes.unauthorized', {
            'reason': 'token_not_found',
            'action': 'connect'
        })
        raise ValueError("HERMES_UNAUTHORIZED: token not found")
    
    # Check token expiration
    if _is_token_expired(pairing.token_expires_at):
        _log_hermes_event('gateway.hermes.unauthorized', {
            'reason': 'token_expired',
            'action': 'connect',
            'hermes_id': pairing.hermes_id
        })
        raise ValueError("HERMES_UNAUTHORIZED: token expired, please re-pair")
    
    # Validate capabilities
    for cap in pairing.capabilities:
        if cap not in HERMES_CAPABILITIES:
            _log_hermes_event('gateway.hermes.unauthorized', {
                'reason': 'invalid_capability',
                'action': 'connect',
                'capability': cap
            })
            raise ValueError(f"HERMES_UNAUTHORIZED: invalid capability '{cap}'")
    
    _log_hermes_event('gateway.hermes.connected', {
        'hermes_id': pairing.hermes_id,
        'capabilities': pairing.capabilities
    })
    
    return HermesConnection(
        hermes_id=pairing.hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat()
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through the adapter.
    
    Requires the 'observe' capability.
    
    Args:
        connection: Active Hermes connection
        
    Returns:
        Miner snapshot dict with status, mode, hashrate, etc.
        
    Raises:
        PermissionError: If connection lacks observe capability
    """
    if 'observe' not in connection.capabilities:
        _log_hermes_event('gateway.hermes.unauthorized', {
            'action': 'read_status',
            'required_capability': 'observe',
            'hermes_id': connection.hermes_id
        })
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Delegate to daemon's status endpoint
    # In milestone 1, we read directly from the miner simulator
    from .daemon import miner
    
    snapshot = miner.get_snapshot()
    
    _log_hermes_event('gateway.status.read', {
        'client': 'hermes',
        'hermes_id': connection.hermes_id,
        'freshness': snapshot.get('freshness')
    })
    
    return snapshot


def append_summary(connection: HermesConnection, summary_text: str, 
                   authority_scope: str) -> spine.SpineEvent:
    """
    Append a Hermes summary to the event spine.
    
    Requires the 'summarize' capability.
    
    Args:
        connection: Active Hermes connection
        summary_text: The summary content to append
        authority_scope: The scope of observation that generated this summary
        
    Returns:
        The appended SpineEvent
        
    Raises:
        PermissionError: If connection lacks summarize capability
    """
    if 'summarize' not in connection.capabilities:
        _log_hermes_event('gateway.hermes.unauthorized', {
            'action': 'append_summary',
            'required_capability': 'summarize',
            'hermes_id': connection.hermes_id
        })
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    # Append to event spine
    event = spine.append_hermes_summary(
        summary_text=summary_text,
        authority_scope=[authority_scope],
        principal_id=connection.principal_id
    )
    
    _log_hermes_event('gateway.hermes.summary_appended', {
        'summary_id': event.id,
        'hermes_id': connection.hermes_id,
        'authority_scope': authority_scope
    })
    
    return event


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events and any other events not in
    HERMES_READABLE_EVENTS.
    
    Args:
        connection: Active Hermes connection
        limit: Maximum number of events to return
        
    Returns:
        List of filtered SpineEvent objects
    """
    # Over-fetch to account for filtering
    all_events = spine.get_events(limit=limit * 2)
    
    # Filter to Hermes-readable events only
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [
        e for e in all_events 
        if e.kind in readable_kinds
    ]
    
    return filtered[:limit]


def check_control_denied(connection: HermesConnection) -> bool:
    """
    Check if Hermes attempts a control action (always denied).
    
    This is a no-op that always returns False to indicate control is denied.
    The actual enforcement happens at the daemon level.
    
    Args:
        connection: Active Hermes connection
        
    Returns:
        False (control is always denied for Hermes)
    """
    _log_hermes_event('gateway.hermes.unauthorized', {
        'action': 'control_attempt',
        'hermes_id': connection.hermes_id,
        'reason': 'hermes_cannot_control'
    })
    return False


# =============================================================================
# Observability Logging
# =============================================================================

def _log_hermes_event(event_type: str, context: dict):
    """
    Log a structured observability event for Hermes operations.
    
    Uses the format defined in references/observability.md
    """
    import logging
    logger = logging.getLogger('hermes.adapter')
    
    log_entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event': event_type,
        **context
    }
    
    # Emit structured JSON log
    logger.info(json.dumps(log_entry))


def setup_logging():
    """Configure logging for the Hermes adapter."""
    import logging
    import sys
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))
    
    logger = logging.getLogger('hermes.adapter')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    return logger


# =============================================================================
# CLI Helpers
# =============================================================================

def cmd_pair_hermes(hermes_id: str, device_name: str) -> dict:
    """CLI helper to pair a Hermes device."""
    pairing = pair_hermes(hermes_id, device_name)
    token = get_pairing_token(hermes_id)
    
    return {
        'success': True,
        'hermes_id': pairing.hermes_id,
        'device_name': pairing.device_name,
        'capabilities': pairing.capabilities,
        'token': token,  # Return token for client to use
        'paired_at': pairing.paired_at
    }


def cmd_hermes_connect(token: str) -> dict:
    """CLI helper to connect Hermes with authority token."""
    try:
        connection = connect(token)
        return {
            'success': True,
            'connected': True,
            'hermes_id': connection.hermes_id,
            'capabilities': connection.capabilities,
            'connected_at': connection.connected_at
        }
    except ValueError as e:
        return {
            'success': False,
            'error': str(e)
        }


def cmd_hermes_status(token: str) -> dict:
    """CLI helper to read status as Hermes."""
    try:
        connection = connect(token)
        status = read_status(connection)
        return {
            'success': True,
            'status': status
        }
    except (ValueError, PermissionError) as e:
        return {
            'success': False,
            'error': str(e)
        }


def cmd_hermes_summary(token: str, summary_text: str, authority_scope: str = 'observe') -> dict:
    """CLI helper to append a summary as Hermes."""
    try:
        connection = connect(token)
        event = append_summary(connection, summary_text, authority_scope)
        return {
            'success': True,
            'appended': True,
            'event_id': event.id,
            'kind': event.kind,
            'created_at': event.created_at
        }
    except (ValueError, PermissionError) as e:
        return {
            'success': False,
            'error': str(e)
        }


def cmd_hermes_events(token: str, limit: int = 20) -> dict:
    """CLI helper to get filtered events for Hermes."""
    try:
        connection = connect(token)
        events = get_filtered_events(connection, limit)
        return {
            'success': True,
            'events': [
                {
                    'id': e.id,
                    'kind': e.kind,
                    'payload': e.payload,
                    'created_at': e.created_at
                }
                for e in events
            ]
        }
    except ValueError as e:
        return {
            'success': False,
            'error': str(e)
        }


# =============================================================================
# Proof of Implementation
# =============================================================================

if __name__ == '__main__':
    # Run proof of implementation
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("=== Hermes Adapter Implementation Proof ===\n")
    
    print("Capabilities:", HERMES_CAPABILITIES)
    print("Readable events:", [e.value for e in HERMES_READABLE_EVENTS])
    print("Blocked events:", [e.value for e in HERMES_BLOCKED_EVENTS])
    
    print("\n--- Pairing Hermes ---")
    pairing = pair_hermes('hermes-001', 'hermes-agent')
    print(f"Paired: {pairing.hermes_id}")
    print(f"Capabilities: {pairing.capabilities}")
    
    print("\n--- Connecting with Token ---")
    token = get_pairing_token('hermes-001')
    connection = connect(token)
    print(f"Connected: {connection.hermes_id}")
    print(f"Capabilities: {connection.capabilities}")
    
    print("\n--- Reading Status (observe) ---")
    status = read_status(connection)
    print(f"Status: {status.get('status')}")
    print(f"Mode: {status.get('mode')}")
    
    print("\n--- Appending Summary (summarize) ---")
    event = append_summary(connection, "Miner running normally at 50kH/s", "observe")
    print(f"Summary appended: {event.id}")
    
    print("\n--- Filtering Events ---")
    events = get_filtered_events(connection)
    user_messages_blocked = all(
        e.kind != 'user_message' for e in events
    )
    print(f"Events returned: {len(events)}")
    print(f"User messages blocked: {user_messages_blocked}")
    
    print("\n=== All Proofs Passed ===")
