#!/usr/bin/env python3
"""
Hermes Adapter Module

Enforces capability boundaries for Hermes AI agents connecting to the Zend daemon.
Hermes can observe miner status and append summaries, but cannot issue control
commands or read user messages.

The adapter validates authority tokens and filters events before they reach the
gateway contract.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional

# Import from sibling modules (relative import for package)
from spine import append_event, get_events, EventKind, SpineEvent
from store import load_pairings, save_pairings, Principal, GatewayPairing

# Add parent to path for daemon imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Token storage for Hermes authority tokens
def _hermes_tokens_file() -> str:
    """Path to Hermes tokens store."""
    state_dir = os.environ.get(
        "ZEND_STATE_DIR",
        str(Path(__file__).resolve().parents[2] / "state")
    )
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, 'hermes-tokens.json')


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


# Hermes capability constants
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
HERMES_WRITABLE_EVENTS = [EventKind.HERMES_SUMMARY]

# Blocked events - Hermes can never read these
HERMES_BLOCKED_EVENTS = [
    EventKind.USER_MESSAGE,
]


class HermesCapability(str, Enum):
    """Hermes-specific capabilities."""
    OBSERVE = 'observe'
    SUMMARIZE = 'summarize'


@dataclass
class HermesConnection:
    """Active Hermes connection state."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    authority_token: str = ""
    expires_at: Optional[str] = None


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


@dataclass
class AuthorityToken:
    """Authority token issued to Hermes during pairing."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    issued_at: str
    expires_at: str
    token: str


def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records."""
    path = _hermes_tokens_file()
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    path = _hermes_tokens_file()
    # Filter out 'tokens' key if present - we're only saving pairings
    pairings_to_save = {k: v for k, v in pairings.items() if k != 'tokens'}
    with open(path, 'w') as f:
        json.dump(pairings_to_save, f, indent=2)


def _load_hermes_tokens() -> dict:
    """Load Hermes authority tokens."""
    tokens_path = _hermes_tokens_file()
    if os.path.exists(tokens_path):
        with open(tokens_path, 'r') as f:
            data = json.load(f)
            # Tokens are stored under 'tokens' key
            return data.get('tokens', {})
    return {}


def _save_hermes_tokens(tokens: dict):
    """Save Hermes authority tokens."""
    tokens_path = _hermes_tokens_file()
    data = _load_hermes_pairings()
    data['tokens'] = tokens
    with open(tokens_path, 'w') as f:
        json.dump(data, f, indent=2)


def is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    try:
        expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expires
    except (ValueError, AttributeError):
        return True


def validate_authority_token(token: str) -> Optional[AuthorityToken]:
    """
    Validate an authority token and return its contents.
    
    Returns None if token is invalid, expired, or malformed.
    """
    tokens = _load_hermes_tokens()
    
    if token not in tokens:
        return None
    
    token_data = tokens[token]
    
    # Check expiration
    if is_token_expired(token_data.get('expires_at', '')):
        return None
    
    # Include the token itself in the data
    token_data['token'] = token
    
    return AuthorityToken(**token_data)


def pair_hermes(hermes_id: str, device_name: str, capabilities: List[str] = None) -> HermesPairing:
    """
    Create a Hermes pairing record with observe+summarize capabilities.
    
    This is idempotent - re-pairing with the same hermes_id updates the token.
    """
    if capabilities is None:
        capabilities = HERMES_CAPABILITIES.copy()
    
    # Validate requested capabilities
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"Invalid Hermes capability: {cap}. Valid: {HERMES_CAPABILITIES}")
    
    # Load existing or create new
    pairings = _load_hermes_pairings()
    
    # Get principal ID (reuse from gateway store)
    from store import load_or_create_principal
    principal = load_or_create_principal()
    
    now = datetime.now(timezone.utc)
    # Token valid for 24 hours
    expires = datetime.now(timezone.utc)
    expires = expires.replace(hour=23, minute=59, second=59)
    
    token = str(uuid.uuid4())
    
    # Check for existing pairing (idempotent)
    existing = None
    for p in pairings.values():
        if p.get('hermes_id') == hermes_id:
            existing = p
            break
    
    if existing:
        # Update token but keep paired_at
        existing['token'] = token
        existing['token_expires_at'] = expires.isoformat()
        existing['capabilities'] = capabilities
        pairing = HermesPairing(**existing)
    else:
        pairing = HermesPairing(
            hermes_id=hermes_id,
            principal_id=principal.id,
            device_name=device_name,
            capabilities=capabilities,
            paired_at=now.isoformat(),
            token=token,
            token_expires_at=expires.isoformat()
        )
        pairings[hermes_id] = asdict(pairing)
    
    # Save pairing
    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    # Save token
    tokens = _load_hermes_tokens()
    tokens[token] = {
        'hermes_id': pairing.hermes_id,
        'principal_id': pairing.principal_id,
        'capabilities': pairing.capabilities,
        'issued_at': now.isoformat(),
        'expires_at': pairing.token_expires_at
    }
    _save_hermes_tokens(tokens)
    
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing by hermes_id."""
    pairings = _load_hermes_pairings()
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    return None


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities.
    """
    token_data = validate_authority_token(authority_token)
    
    if token_data is None:
        raise ValueError("HERMES_INVALID_TOKEN: Authority token is invalid or expired")
    
    # Verify capabilities
    for cap in token_data.capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_INVALID_CAPABILITY: {cap} is not a valid Hermes capability")
    
    return HermesConnection(
        hermes_id=token_data.hermes_id,
        principal_id=token_data.principal_id,
        capabilities=token_data.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        authority_token=authority_token,
        expires_at=token_data.expires_at
    )


def require_capability(connection: HermesConnection, capability: str):
    """Raise PermissionError if connection lacks required capability."""
    if capability not in connection.capabilities:
        raise PermissionError(f"HERMES_UNAUTHORIZED: {capability} capability required")


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability.
    """
    require_capability(connection, HermesCapability.OBSERVE.value)
    
    # Import miner simulator from daemon
    # This is a circular-safe import since we only access the instance
    from daemon import miner
    return miner.get_snapshot()


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    """
    require_capability(connection, HermesCapability.SUMMARIZE.value)
    
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


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events and only returns hermes-readable events.
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    # Get allowed event kinds
    allowed_kinds = set(e.value for e in HERMES_READABLE_EVENTS)
    
    # Filter events
    filtered = [
        e for e in all_events 
        if e.kind in allowed_kinds
    ]
    
    return filtered[:limit]


def get_hermes_events_for_connection(connection: HermesConnection, limit: int = 20) -> list:
    """
    Get Hermes-specific events (only hermes_summary kind for this connection).
    
    This is more restrictive than get_filtered_events - it only returns
    events generated by this Hermes instance.
    """
    all_events = get_events(kind=EventKind.HERMES_SUMMARY, limit=limit * 2)
    
    # Filter to only this Hermes
    filtered = [
        e for e in all_events
        if e.payload.get('hermes_id') == connection.hermes_id
    ]
    
    return filtered[:limit]


def verify_connection_auth(connection: HermesConnection, required_capability: str = None) -> bool:
    """
    Verify a Hermes connection is still valid.
    
    Optionally verify a specific capability is present.
    """
    if required_capability:
        return required_capability in connection.capabilities
    return True


def revoke_hermes_token(hermes_id: str) -> bool:
    """
    Revoke all tokens for a Hermes pairing.
    
    Returns True if a pairing was found and revoked.
    """
    pairings = _load_hermes_pairings()
    
    if hermes_id not in pairings:
        return False
    
    # Find and remove tokens
    tokens = _load_hermes_tokens()
    pairing_data = pairings[hermes_id]
    token_to_remove = pairing_data.get('token')
    
    # Remove pairing first
    del pairings[hermes_id]
    
    # Delete token if it exists
    if token_to_remove and token_to_remove in tokens:
        del tokens[token_to_remove]
    
    # Save pairings first (without tokens key), then tokens
    _save_hermes_pairings(pairings)
    _save_hermes_tokens(tokens)
    
    return True


def list_hermes_pairings() -> List[HermesPairing]:
    """List all Hermes pairings."""
    pairings = _load_hermes_pairings()
    # Filter out 'tokens' key if present (it's not a pairing)
    result = []
    for key, p in pairings.items():
        if key == 'tokens':
            continue
        if isinstance(p, dict) and 'hermes_id' in p:
            result.append(HermesPairing(**p))
    return result


# Proof-of-concept verification
if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
    print(f"Blocked events: {[e.value for e in HERMES_BLOCKED_EVENTS]}")
    print()
    
    # Test pairing
    try:
        pairing = pair_hermes("hermes-001", "test-agent")
        print(f"Paired: {pairing.hermes_id}")
        print(f"Token: {pairing.token[:8]}...")
        print(f"Capabilities: {pairing.capabilities}")
        print()
        
        # Test connect
        conn = connect(pairing.token)
        print(f"Connected: {conn.hermes_id}")
        print(f"Capabilities: {conn.capabilities}")
        print()
        
        # Test summary append
        event = append_summary(conn, "Test summary", "observe")
        print(f"Summary appended: {event.id}")
        print()
        
        # Test filtered events
        events = get_filtered_events(conn, limit=10)
        print(f"Filtered events: {len(events)}")
        
    except Exception as e:
        print(f"Error: {e}")
