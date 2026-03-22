#!/usr/bin/env python3
"""
Hermes Adapter Module

Sits between the external Hermes AI agent and the Zend event spine.
Enforces capability boundaries: Hermes can observe and summarize, but cannot
issue control commands or read user messages.

Architecture:
    Hermes Gateway → Zend Hermes Adapter → Event Spine

Hermes Capabilities (milestone 1):
    - observe: Read miner status
    - summarize: Append summaries to event spine

Hermes CANNOT:
    - Issue control commands (start/stop/mining mode)
    - Read user_message events
    - Access inbox messages
"""

import json
import os
import sys
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Import from sibling modules (support both module and standalone execution)
try:
    from . import spine
    from . import store
except ImportError:
    # Standalone execution (for testing)
    import spine
    import store


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    spine.EventKind.HERMES_SUMMARY,
    spine.EventKind.MINER_ALERT,
    spine.EventKind.CONTROL_RECEIPT,
]

# Token file for storing Hermes authority tokens
def _get_token_file() -> str:
    state_dir = os.environ.get(
        'ZEND_STATE_DIR',
        str(Path(__file__).resolve().parents[2] / 'state')
    )
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, 'hermes-tokens.json')


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """Represents an active Hermes connection session."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    token_expires_at: str


@dataclass
class HermesPairing:
    """Represents a Hermes pairing record."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


@dataclass
class AuthorityToken:
    """Decoded authority token payload."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    issued_at: str
    expires_at: str


# ---------------------------------------------------------------------------
# Token Management
# ---------------------------------------------------------------------------

def _load_tokens() -> dict:
    """Load Hermes tokens from storage."""
    token_file = _get_token_file()
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            return json.load(f)
    return {}


def _save_tokens(tokens: dict) -> None:
    """Save Hermes tokens to storage."""
    token_file = _get_token_file()
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)


def _is_token_expired(token: AuthorityToken) -> bool:
    """Check if a token has expired."""
    expires = datetime.fromisoformat(token.expires_at.replace('Z', '+00:00'))
    return datetime.now(timezone.utc) > expires


def _generate_token(hermes_id: str, principal_id: str, capabilities: List[str]) -> tuple[str, str]:
    """Generate a new authority token for Hermes."""
    token_id = str(uuid.uuid4())
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at.astimezone(timezone.utc)
    # Token valid for 24 hours
    from datetime import timedelta
    expires_at = (issued_at + timedelta(hours=24)).isoformat()
    issued_at_str = issued_at.isoformat()
    
    tokens = _load_tokens()
    tokens[token_id] = {
        'hermes_id': hermes_id,
        'principal_id': principal_id,
        'capabilities': capabilities,
        'issued_at': issued_at_str,
        'expires_at': expires_at
    }
    _save_tokens(tokens)
    
    return token_id, expires_at


def _validate_token(token_id: str) -> AuthorityToken:
    """Validate a token and return its payload.
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities.
    """
    tokens = _load_tokens()
    
    if token_id not in tokens:
        raise ValueError("HERMES_INVALID_TOKEN: Token not found")
    
    token_data = tokens[token_id]
    token = AuthorityToken(**token_data)
    
    # Check expiration
    if _is_token_expired(token):
        raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")
    
    # Check capabilities
    for cap in token.capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_INVALID_CAPABILITY: {cap} is not a valid Hermes capability")
    
    return token


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------

def pair_hermes(hermes_id: str, device_name: Optional[str] = None) -> HermesPairing:
    """Create a Hermes pairing record.
    
    This is idempotent: if hermes_id already exists, returns existing pairing.
    
    Args:
        hermes_id: Unique identifier for Hermes agent
        device_name: Optional friendly name for the device
    
    Returns:
        HermesPairing record with observe+summarize capabilities
    """
    principal = store.load_or_create_principal()
    
    # Check for existing pairing
    existing = _get_pairing(hermes_id)
    if existing:
        return existing
    
    # Create new pairing
    device_name = device_name or f"hermes-{hermes_id}"
    
    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=datetime.now(timezone.utc).isoformat()
    )
    
    # Store pairing
    _save_pairing(pairing)
    
    # Generate initial token
    token_id, expires_at = _generate_token(hermes_id, principal.id, HERMES_CAPABILITIES)
    pairing.token_expires_at = expires_at
    
    # Append pairing event
    spine.append_event(
        spine.EventKind.PAIRING_GRANTED,
        principal.id,
        {
            'device_name': device_name,
            'device_type': 'hermes',
            'granted_capabilities': HERMES_CAPABILITIES
        }
    )
    
    return pairing


def _get_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get existing Hermes pairing."""
    pairings = _load_pairings()
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    return None


def _save_pairing(pairing: HermesPairing) -> None:
    """Save Hermes pairing record."""
    pairings = _load_pairings()
    pairings[pairing.hermes_id] = asdict(pairing)
    _save_pairings(pairings)


def _load_pairings() -> dict:
    """Load Hermes pairings from storage."""
    state_dir = os.environ.get(
        'ZEND_STATE_DIR',
        str(Path(__file__).resolve().parents[2] / 'state')
    )
    os.makedirs(state_dir, exist_ok=True)
    pairing_file = os.path.join(state_dir, 'hermes-pairings.json')
    
    if os.path.exists(pairing_file):
        with open(pairing_file, 'r') as f:
            return json.load(f)
    return {}


def _save_pairings(pairings: dict) -> None:
    """Save Hermes pairings to storage."""
    state_dir = os.environ.get(
        'ZEND_STATE_DIR',
        str(Path(__file__).resolve().parents[2] / 'state')
    )
    os.makedirs(state_dir, exist_ok=True)
    pairing_file = os.path.join(state_dir, 'hermes-pairings.json')
    
    with open(pairing_file, 'w') as f:
        json.dump(pairings, f, indent=2)


# ---------------------------------------------------------------------------
# Connection Management
# ---------------------------------------------------------------------------

def connect(authority_token: str) -> HermesConnection:
    """Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: Token issued during Hermes pairing
    
    Returns:
        HermesConnection object with session details
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
    """
    # Validate the token
    token = _validate_token(authority_token)
    
    # Create connection
    connection = HermesConnection(
        hermes_id=token.hermes_id,
        principal_id=token.principal_id,
        capabilities=token.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=token.expires_at
    )
    
    return connection


def get_connection_status(hermes_id: str) -> Optional[dict]:
    """Get Hermes connection status.
    
    Returns connection info if Hermes is paired, None otherwise.
    """
    pairing = _get_pairing(hermes_id)
    if not pairing:
        return None
    
    return {
        'hermes_id': pairing.hermes_id,
        'device_name': pairing.device_name,
        'capabilities': pairing.capabilities,
        'paired_at': pairing.paired_at,
        'connected': True,
        'status': 'active'
    }


# ---------------------------------------------------------------------------
# Hermes Operations
# ---------------------------------------------------------------------------

def read_status(connection: HermesConnection) -> dict:
    """Read miner status through adapter.
    
    Requires 'observe' capability. This delegates to the daemon's
    internal miner simulator.
    
    Args:
        connection: Active Hermes connection
    
    Returns:
        Miner status snapshot dict
    
    Raises:
        PermissionError: If observe capability is not granted
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import miner simulator from daemon
    # Note: In production, this would be an internal API call
    try:
        from .daemon import miner
    except ImportError:
        import daemon as daemon_module
        miner = daemon_module.miner
    
    snapshot = miner.get_snapshot()
    
    # Transform for Hermes (strip sensitive fields)
    return {
        'status': snapshot.get('status'),
        'mode': snapshot.get('mode'),
        'hashrate_hs': snapshot.get('hashrate_hs'),
        'temperature': snapshot.get('temperature'),
        'uptime_seconds': snapshot.get('uptime_seconds'),
        'freshness': snapshot.get('freshness'),
        'capabilities': ['observe', 'summarize'],  # Hermes scope
        'connection_id': connection.hermes_id
    }


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str
) -> spine.SpineEvent:
    """Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability. This appends a hermes_summary
    event that will appear in the operations inbox.
    
    Args:
        connection: Active Hermes connection
        summary_text: The summary content
        authority_scope: The scope of the summary (e.g., 'observe')
    
    Returns:
        SpineEvent that was appended
    
    Raises:
        PermissionError: If summarize capability is not granted
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    if not summary_text or not summary_text.strip():
        raise ValueError("HERMES_INVALID_INPUT: summary_text cannot be empty")
    
    event = spine.append_event(
        spine.EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            'summary_text': summary_text.strip(),
            'authority_scope': authority_scope,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'hermes_id': connection.hermes_id
        }
    )
    
    return event


def get_filtered_events(
    connection: HermesConnection,
    limit: int = 20
) -> List[spine.SpineEvent]:
    """Return events Hermes is allowed to see.
    
    Filters out user_message events and returns only events
    from the HERMES_READABLE_EVENTS list.
    
    Args:
        connection: Active Hermes connection
        limit: Maximum number of events to return
    
    Returns:
        List of filtered SpineEvent objects
    """
    # Over-fetch to account for filtering
    all_events = spine.get_events(limit=limit * 2)
    
    # Filter to readable event kinds
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    return filtered[:limit]


def can_control(connection: HermesConnection) -> bool:
    """Check if Hermes connection has control capability.
    
    Always returns False for Hermes - this is a boundary enforcement
    helper to make control rejection explicit.
    """
    return 'control' in connection.capabilities


# ---------------------------------------------------------------------------
# Proof of Implementation
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
