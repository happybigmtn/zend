#!/usr/bin/env python3
"""
Hermes Adapter Module

Enables an AI agent (Hermes) to connect to the Zend daemon with scoped
capabilities. Hermes can observe miner status and append summaries to the
event spine, but cannot issue control commands or read user messages.

The adapter is a capability boundary, not a deployment boundary. It enforces
scope by filtering requests before they reach the gateway contract.
"""

import base64
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')


# Hermes capability constants
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read
# Note: These are EventKind enum values, imported at runtime from spine
HERMES_READABLE_EVENT_KINDS = [
    'hermes_summary',
    'miner_alert',
    'control_receipt',
]


@dataclass
class HermesConnection:
    """Represents an active Hermes connection with scoped capabilities."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str


@dataclass
class HermesPairing:
    """Hermes pairing record stored in the pairing store."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str
    authority_token: str
    token_used: bool = False


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


def _generate_authority_token(hermes_id: str, principal_id: str, capabilities: List[str]) -> str:
    """Generate an authority token encoding Hermes identity and capabilities.
    
    The token is a base64-encoded JSON object for milestone 1.
    Production would use JWT or similar signed token.
    """
    payload = {
        'hermes_id': hermes_id,
        'principal_id': principal_id,
        'capabilities': capabilities,
        'issued_at': datetime.now(timezone.utc).isoformat(),
        'expires_at': datetime.now(timezone.utc).isoformat(),
    }
    # Simple base64 encoding for milestone 1 (not cryptographically signed)
    token_bytes = json.dumps(payload).encode('utf-8')
    return base64.b64encode(token_bytes).decode('ascii')


def _decode_authority_token(token: str) -> dict:
    """Decode and validate an authority token.
    
    Returns the decoded payload or raises ValueError.
    """
    try:
        token_bytes = base64.b64decode(token.encode('ascii'))
        payload = json.loads(token_bytes.decode('utf-8'))
        
        # Validate required fields
        required_fields = ['hermes_id', 'principal_id', 'capabilities', 'expires_at']
        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Token missing required field: {field}")
        
        return payload
    except Exception as e:
        raise ValueError(f"Invalid token format: {e}")


def _is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired.
    
    For milestone 1, tokens are valid for a short period. In production,
    this would be a proper JWT with cryptographic verification.
    """
    try:
        expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        # Allow for small clock differences (1 minute grace period)
        grace_period = expires_dt.timestamp() - now.timestamp()
        return grace_period < -60  # Expired if more than 60 seconds ago
        
    except Exception:
        # If we can't parse, assume expired for safety
        return True


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """Create or update a Hermes pairing record with observe+summarize capabilities.
    
    This operation is idempotent: pairing the same hermes_id again updates
    the existing record with a new token.
    
    Args:
        hermes_id: Unique Hermes agent identifier
        device_name: Human-readable name for the Hermes instance
        
    Returns:
        HermesPairing record with authority token
    """
    # Import here to avoid circular imports
    from store import load_or_create_principal
    
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    # Generate new authority token
    expires = datetime.now(timezone.utc).isoformat()
    authority_token = _generate_authority_token(hermes_id, principal.id, HERMES_CAPABILITIES)
    
    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES.copy(),
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=expires,
        authority_token=authority_token,
        token_used=False
    )
    
    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    return pairing


def get_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    return None


def connect(authority_token: str) -> HermesConnection:
    """Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: Base64-encoded authority token from pairing
        
    Returns:
        HermesConnection object if token is valid
        
    Raises:
        ValueError: If token is invalid or malformed
        PermissionError: If token lacks Hermes capabilities
    """
    # Decode and validate token structure
    payload = _decode_authority_token(authority_token)
    
    # Check for Hermes-specific capabilities
    capabilities = payload.get('capabilities', [])
    
    # Verify this is a Hermes token (has at least Hermes capabilities)
    has_hermes_caps = all(cap in HERMES_CAPABILITIES for cap in capabilities)
    if not has_hermes_caps or not capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: Token lacks Hermes capabilities. "
            f"Expected: {HERMES_CAPABILITIES}, Got: {capabilities}"
        )
    
    # Check token expiration
    expires_at = payload.get('expires_at', '')
    if _is_token_expired(expires_at):
        raise ValueError("HERMES_AUTH_EXPIRED: Authority token has expired")
    
    return HermesConnection(
        hermes_id=payload['hermes_id'],
        principal_id=payload['principal_id'],
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat()
    )


def read_status(connection: HermesConnection) -> dict:
    """Read miner status through adapter.
    
    Requires 'observe' capability in the connection.
    
    Args:
        connection: Active HermesConnection
        
    Returns:
        Miner status snapshot dict
        
    Raises:
        PermissionError: If connection lacks observe capability
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: observe capability required for read_status"
        )
    
    # Import here to avoid circular imports and use daemon's miner instance
    # In production, this would be an internal RPC or direct module access
    try:
        from daemon import miner
        return miner.get_snapshot()
    except ImportError:
        # Fallback for standalone testing
        return {
            'status': 'unknown',
            'mode': 'paused',
            'hashrate_hs': 0,
            'temperature': 0,
            'uptime_seconds': 0,
            'freshness': datetime.now(timezone.utc).isoformat()
        }


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict:
    """Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability in the connection.
    
    Args:
        connection: Active HermesConnection
        summary_text: The summary content
        authority_scope: The scope of the observation (e.g., 'observe')
        
    Returns:
        Dict with appended status and event_id
        
    Raises:
        PermissionError: If connection lacks summarize capability
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: summarize capability required for append_summary"
        )
    
    # Import here to avoid circular imports
    from spine import append_hermes_summary
    
    event = append_hermes_summary(
        summary_text=summary_text,
        authority_scope=[authority_scope],
        principal_id=connection.principal_id
    )
    
    return {
        'appended': True,
        'event_id': event.id
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """Return events Hermes is allowed to see.
    
    Filters out user_message events to enforce privacy boundary.
    
    Args:
        connection: Active HermesConnection
        limit: Maximum number of events to return
        
    Returns:
        List of filtered SpineEvent objects
    """
    # Import here to avoid circular imports
    from spine import get_events
    
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    # Filter to Hermes-readable events only
    filtered = [
        event for event in all_events
        if event.kind in HERMES_READABLE_EVENT_KINDS
    ]
    
    return filtered[:limit]


def validate_connection_auth(hermes_id: str) -> Optional[HermesConnection]:
    """Validate a Hermes connection by hermes_id.
    
    Used by daemon endpoints that receive 'Authorization: Hermes <hermes_id>' headers.
    
    Args:
        hermes_id: The Hermes ID from the Authorization header
        
    Returns:
        HermesConnection if pairing exists, None otherwise
    """
    pairing = get_pairing(hermes_id)
    if not pairing:
        return None
    
    return HermesConnection(
        hermes_id=pairing.hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=pairing.paired_at  # Use paired_at as connected_at for stored connections
    )


# Module-level proof for testing
if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {HERMES_READABLE_EVENT_KINDS}")
    
    # Test token generation/decoding
    test_token = _generate_authority_token(
        'test-hermes-001',
        'principal-001',
        HERMES_CAPABILITIES
    )
    print(f"\nTest token: {test_token[:50]}...")
    
    decoded = _decode_authority_token(test_token)
    print(f"Decoded: hermes_id={decoded['hermes_id']}, caps={decoded['capabilities']}")
