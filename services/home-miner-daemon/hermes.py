#!/usr/bin/env python3
"""
Hermes Adapter for Zend Home Miner Daemon.

The Hermes adapter sits between external Hermes agents and the Zend gateway contract.
It enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

Architecture:
    Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                     ^^^^^^^^^^^^^^^^^^^^
                     THIS IS WHAT WE BUILD

Authority tokens are issued during Hermes pairing and encode:
- principal_id: the Zend principal this Hermes reports to
- hermes_id: unique identifier for this Hermes instance
- capabilities: ['observe', 'summarize'] (scope is narrower than gateway)
- expiration: ISO 8601 timestamp when token expires
"""

import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Resolve paths relative to this module
_HERMES_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _HERMES_DIR.parents[1]


def _default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(_ROOT_DIR / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", _default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_STORE_FILE = os.path.join(STATE_DIR, 'hermes-store.json')
HERMES_TOKEN_FILE = os.path.join(STATE_DIR, 'hermes-tokens.json')


# Hermes-specific capabilities (narrower than gateway capabilities)
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    'hermes_summary',
    'miner_alert',
    'control_receipt',
]
# Events Hermes CANNOT read
HERMES_BLOCKED_EVENTS = [
    'user_message',  # Blocked: Hermes must not see user messages
]


@dataclass
class HermesConnection:
    """
    Represents an active Hermes connection session.

    Attributes:
        hermes_id: Unique identifier for this Hermes instance
        principal_id: The Zend principal this Hermes reports to
        capabilities: Granted capabilities (subset of HERMES_CAPABILITIES)
        connected_at: ISO 8601 timestamp of connection establishment
        last_seen: ISO 8601 timestamp of last activity
    """
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    last_seen: str = ""

    def __post_init__(self):
        if not self.last_seen:
            self.last_seen = self.connected_at

    def is_capable(self, capability: str) -> bool:
        """Check if this connection has the given capability."""
        return capability in self.capabilities


@dataclass
class HermesPairing:
    """
    A Hermes pairing record, stored persistently.
    
    Attributes:
        hermes_id: Unique identifier for this Hermes instance
        device_name: Human-readable name for this Hermes
        principal_id: The Zend principal this Hermes belongs to
        capabilities: Granted capabilities
        paired_at: ISO 8601 timestamp of pairing
        token_expires_at: ISO 8601 timestamp of token expiration
    """
    hermes_id: str
    device_name: str
    principal_id: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


@dataclass
class AuthorityToken:
    """
    An authority token issued to Hermes during pairing.
    
    Encodes the connection scope Hermes operates within.
    """
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    issued_at: str
    expires_at: str

    def is_expired(self) -> bool:
        """Check if this token has expired."""
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) > expiry
        except (ValueError, TypeError):
            return True  # Treat malformed dates as expired for safety


def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records from store."""
    if os.path.exists(HERMES_STORE_FILE):
        with open(HERMES_STORE_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records to store."""
    with open(HERMES_STORE_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def _load_hermes_tokens() -> dict:
    """Load Hermes authority tokens from store."""
    if os.path.exists(HERMES_TOKEN_FILE):
        with open(HERMES_TOKEN_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_tokens(tokens: dict):
    """Save Hermes authority tokens to store."""
    with open(HERMES_TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)


def pair_hermes(hermes_id: str, device_name: str, principal_id: str) -> HermesPairing:
    """
    Create a new Hermes pairing record.
    
    Hermes pairings are idempotent: if a Hermes with the same hermes_id
    is already paired, returns the existing pairing.
    
    Args:
        hermes_id: Unique identifier for this Hermes instance
        device_name: Human-readable name for display
        principal_id: The Zend principal this Hermes belongs to
        
    Returns:
        HermesPairing record
    """
    pairings = _load_hermes_pairings()
    
    # Idempotent: return existing pairing if Hermes already paired
    if hermes_id in pairings:
        p = pairings[hermes_id]
        return HermesPairing(
            hermes_id=p['hermes_id'],
            device_name=p['device_name'],
            principal_id=p['principal_id'],
            capabilities=p['capabilities'],
            paired_at=p['paired_at'],
            token_expires_at=p['token_expires_at']
        )
    
    now = datetime.now(timezone.utc)
    
    # Token expires in 30 days by default
    from datetime import timedelta
    expires = now + timedelta(days=30)
    
    pairing = HermesPairing(
        hermes_id=hermes_id,
        device_name=device_name,
        principal_id=principal_id,
        capabilities=HERMES_CAPABILITIES,  # Always grant full Hermes scope
        paired_at=now.isoformat(),
        token_expires_at=expires.isoformat()
    )
    
    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    return pairing


def issue_authority_token(hermes_id: str) -> AuthorityToken:
    """
    Issue a new authority token for a paired Hermes.
    
    The token encodes the connection scope Hermes operates within.
    
    Args:
        hermes_id: The Hermes to issue a token for
        
    Returns:
        AuthorityToken for this Hermes
        
    Raises:
        ValueError: If Hermes is not paired
    """
    pairings = _load_hermes_pairings()
    
    if hermes_id not in pairings:
        raise ValueError(f"Hermes '{hermes_id}' is not paired")
    
    pairing_data = pairings[hermes_id]
    now = datetime.now(timezone.utc)
    
    # Parse expiry from pairing
    try:
        expires_at = datetime.fromisoformat(pairing_data['token_expires_at'])
    except (ValueError, KeyError):
        from datetime import timedelta
        expires_at = now + timedelta(days=30)
    
    token = AuthorityToken(
        hermes_id=hermes_id,
        principal_id=pairing_data['principal_id'],
        capabilities=pairing_data['capabilities'],
        issued_at=now.isoformat(),
        expires_at=expires_at.isoformat()
    )
    
    # Store the token
    tokens = _load_hermes_tokens()
    tokens[hermes_id] = asdict(token)
    _save_hermes_tokens(tokens)
    
    return token


def validate_authority_token(token_data: dict) -> AuthorityToken:
    """
    Validate an authority token from raw token data.
    
    Args:
        token_data: Dictionary containing token fields
        
    Returns:
        AuthorityToken if valid
        
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
    """
    if not token_data:
        raise ValueError("HERMES_INVALID_TOKEN: Empty token")
    
    required_fields = ['hermes_id', 'principal_id', 'capabilities', 'expires_at']
    for field in required_fields:
        if field not in token_data:
            raise ValueError(f"HERMES_INVALID_TOKEN: Missing required field '{field}'")
    
    token = AuthorityToken(
        hermes_id=token_data['hermes_id'],
        principal_id=token_data['principal_id'],
        capabilities=token_data['capabilities'],
        issued_at=token_data.get('issued_at', ''),
        expires_at=token_data['expires_at']
    )
    
    # Check expiration
    if token.is_expired():
        raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")
    
    # Validate capabilities (Hermes can only have observe + summarize)
    for cap in token.capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_INVALID_CAPABILITY: '{cap}' not allowed for Hermes")
    
    # Ensure Hermes never gets control capability
    if 'control' in token.capabilities:
        raise ValueError("HERMES_INVALID_CAPABILITY: Hermes cannot have 'control' capability")
    
    return token


def connect(authority_token_data: dict) -> HermesConnection:
    """
    Connect to the Zend gateway as a Hermes agent.
    
    Validates the authority token and establishes a connection session.
    
    Args:
        authority_token_data: Raw token data from the client
        
    Returns:
        HermesConnection representing the active session
        
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
    """
    token = validate_authority_token(authority_token_data)
    
    now = datetime.now(timezone.utc).isoformat()
    
    return HermesConnection(
        hermes_id=token.hermes_id,
        principal_id=token.principal_id,
        capabilities=token.capabilities,
        connected_at=now,
        last_seen=now
    )


def reconnect_with_token(hermes_id: str) -> HermesConnection:
    """
    Reconnect using stored token for a paired Hermes.
    
    Args:
        hermes_id: The Hermes to reconnect
        
    Returns:
        HermesConnection representing the session
        
    Raises:
        ValueError: If Hermes is not paired or token is invalid
    """
    tokens = _load_hermes_tokens()
    
    if hermes_id not in tokens:
        # Issue a new token if none exists
        token = issue_authority_token(hermes_id)
    else:
        token_data = tokens[hermes_id]
        
        # Validate and check expiration
        if token_data.get('expires_at'):
            try:
                expiry = datetime.fromisoformat(token_data['expires_at'])
                if datetime.now(timezone.utc) > expiry:
                    # Token expired, issue new one
                    token = issue_authority_token(hermes_id)
                else:
                    token = validate_authority_token(token_data)
            except (ValueError, TypeError):
                token = issue_authority_token(hermes_id)
        else:
            token = issue_authority_token(hermes_id)
    
    now = datetime.now(timezone.utc).isoformat()
    
    return HermesConnection(
        hermes_id=token.hermes_id,
        principal_id=token.principal_id,
        capabilities=token.capabilities,
        connected_at=now,
        last_seen=now
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.
    
    Requires the 'observe' capability.
    
    Args:
        connection: Active Hermes connection
        
    Returns:
        MinerSnapshot dict
        
    Raises:
        PermissionError: If connection lacks 'observe' capability
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import miner from daemon to get status
    # This avoids circular imports by importing inside the function
    import sys
    from pathlib import Path
    
    daemon_path = Path(__file__).parent / "daemon.py"
    if daemon_path.exists():
        # Import the miner simulator from daemon
        sys.path.insert(0, str(Path(__file__).parent))
        try:
            from daemon import miner
            return miner.get_snapshot()
        except (ImportError, AttributeError):
            pass
    
    # Fallback: return a minimal status if daemon isn't importable
    return {
        "status": "unknown",
        "mode": "paused",
        "hashrate_hs": 0,
        "temperature": 0,
        "uptime_seconds": 0,
        "freshness": datetime.now(timezone.utc).isoformat()
    }


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires the 'summarize' capability.
    
    Args:
        connection: Active Hermes connection
        summary_text: The summary text to append
        authority_scope: The scope of observation (e.g., 'observe')
        
    Returns:
        Dict with append result
        
    Raises:
        PermissionError: If connection lacks 'summarize' capability
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    # Import spine and append the event
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from spine import append_hermes_summary, append_event, EventKind
        
        event = append_hermes_summary(
            summary_text=summary_text,
            authority_scope=[authority_scope],
            principal_id=connection.principal_id
        )
        
        return {
            "appended": True,
            "event_id": event.id,
            "kind": event.kind,
            "created_at": event.created_at
        }
    except ImportError:
        return {
            "appended": False,
            "error": "spine_not_available"
        }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Get events that Hermes is allowed to see.
    
    This filters out user_message events and returns only events
    that Hermes has permission to read.
    
    Args:
        connection: Active Hermes connection
        limit: Maximum number of events to return
        
    Returns:
        List of filtered SpineEvents
    """
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        from spine import get_events
        
        # Over-fetch to account for filtering
        all_events = get_events(limit=limit * 2)
        
        # Filter to allowed event kinds
        filtered = []
        for event in all_events:
            if event.kind in HERMES_READABLE_EVENTS:
                # Strip any sensitive payload fields Hermes shouldn't see
                filtered_event = {
                    "id": event.id,
                    "principal_id": event.principal_id,
                    "kind": event.kind,
                    "created_at": event.created_at,
                    # Include payload but don't expose sensitive fields
                    "payload": _strip_sensitive_payload(event.kind, event.payload)
                }
                filtered.append(filtered_event)
                
                if len(filtered) >= limit:
                    break
        
        return filtered
        
    except ImportError:
        return []


def _strip_sensitive_payload(kind: str, payload: dict) -> dict:
    """
    Strip sensitive fields from event payloads that Hermes shouldn't see.
    
    Args:
        kind: Event kind
        payload: Original payload
        
    Returns:
        Sanitized payload
    """
    if kind == 'user_message':
        # Hermes should never see user messages, but this is a safety measure
        return {"_redacted": "hermes_blocked"}
    
    # For other events, return as-is (they're Hermes-readable by design)
    return payload


def get_hermes_connection_info(connection: HermesConnection) -> dict:
    """
    Get connection information for a Hermes connection.
    
    Args:
        connection: Active Hermes connection
        
    Returns:
        Dict with connection metadata
    """
    return {
        "hermes_id": connection.hermes_id,
        "principal_id": connection.principal_id,
        "capabilities": connection.capabilities,
        "connected_at": connection.connected_at,
        "last_seen": connection.last_seen,
        "can_observe": connection.is_capable('observe'),
        "can_summarize": connection.is_capable('summarize'),
        "can_control": connection.is_capable('control')
    }


def list_hermes_pairings() -> List[HermesPairing]:
    """
    List all Hermes pairings.
    
    Returns:
        List of HermesPairing records
    """
    pairings = _load_hermes_pairings()
    return [
        HermesPairing(**p) for p in pairings.values()
    ]
