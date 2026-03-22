#!/usr/bin/env python3
"""
Hermes Adapter Module

Provides a scoped capability boundary for Hermes AI agents to interact
with the Zend daemon. Hermes agents can observe miner status and
append summaries to the event spine, but cannot issue control commands
or read user messages.

The adapter enforces:
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

# Import from spine module - note: this will be imported after spine is defined
# In practice, these are imported at module level in daemon.py
# We use late binding to avoid circular imports

HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read (excludes USER_MESSAGE)
HERMES_READABLE_EVENTS = [
    'hermes_summary',
    'miner_alert',
    'control_receipt',
]


@dataclass
class HermesConnection:
    """Represents an active Hermes agent connection."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str

    def has_capability(self, capability: str) -> bool:
        """Check if connection has a specific capability."""
        return capability in self.capabilities

    def to_dict(self) -> dict:
        """Serialize connection to dict for JSON responses."""
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at,
        }


@dataclass
class HermesPairing:
    """Represents a Hermes pairing record."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token: str
    token_expires_at: str

    def to_dict(self) -> dict:
        """Serialize pairing to dict for JSON responses."""
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "device_name": self.device_name,
            "capabilities": self.capabilities,
            "paired_at": self.paired_at,
            "token_expires_at": self.token_expires_at,
        }


def _get_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


def _get_hermes_store_path() -> str:
    """Get path to Hermes pairing store."""
    state_dir = _get_state_dir()
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, 'hermes-pairings.json')


def _load_hermes_pairings() -> dict:
    """Load all Hermes pairing records."""
    store_path = _get_hermes_store_path()
    if os.path.exists(store_path):
        with open(store_path, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    store_path = _get_hermes_store_path()
    with open(store_path, 'w') as f:
        json.dump(pairings, f, indent=2)


def _parse_token(token: str) -> dict:
    """
    Parse and validate an authority token.
    
    Authority token format: base64-encoded JSON containing:
    - hermes_id: unique Hermes identifier
    - principal_id: Zend principal identifier  
    - capabilities: list of granted capabilities
    - expires_at: ISO timestamp of expiration
    
    Returns parsed token dict or raises ValueError.
    """
    try:
        import base64
        # Decode base64 token
        decoded = base64.b64decode(token).decode('utf-8')
        token_data = json.loads(decoded)
        
        # Validate required fields
        required = ['hermes_id', 'principal_id', 'capabilities', 'expires_at']
        for field in required:
            if field not in token_data:
                raise ValueError(f"Token missing required field: {field}")
        
        # Validate capabilities are subset of HERMES_CAPABILITIES
        for cap in token_data['capabilities']:
            if cap not in HERMES_CAPABILITIES:
                raise ValueError(f"Invalid capability in token: {cap}")
        
        return token_data
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Invalid token format: {e}")


def _is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    try:
        expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expires
    except ValueError:
        # If we can't parse, assume expired for safety
        return True


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: Base64-encoded JSON authority token
        
    Returns:
        HermesConnection object if token is valid
        
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
    """
    # Parse and validate token
    token_data = _parse_token(authority_token)
    
    # Check expiration
    if _is_token_expired(token_data['expires_at']):
        raise ValueError("HERMES_UNAUTHORIZED: Authority token has expired")
    
    # Verify capabilities
    for cap in token_data['capabilities']:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_UNAUTHORIZED: Invalid capability '{cap}' for Hermes")
    
    # Create connection
    return HermesConnection(
        hermes_id=token_data['hermes_id'],
        principal_id=token_data['principal_id'],
        capabilities=token_data['capabilities'],
        connected_at=datetime.now(timezone.utc).isoformat(),
    )


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create or update a Hermes pairing record.
    
    This is idempotent - calling with the same hermes_id returns the existing
    pairing with a refreshed token.
    
    Args:
        hermes_id: Unique Hermes identifier
        device_name: Human-readable name for the Hermes agent
        
    Returns:
        HermesPairing object
    """
    import base64
    
    # Load existing pairings
    pairings = _load_hermes_pairings()
    
    # Check for existing pairing (idempotent)
    if hermes_id in pairings:
        existing = HermesPairing(**pairings[hermes_id])
        # Refresh token
        existing.token = str(uuid.uuid4())
        existing.token_expires_at = datetime.now(timezone.utc).isoformat()
        pairings[hermes_id] = existing.__dict__
        _save_hermes_pairings(pairings)
        return existing
    
    # Create new pairing with observe + summarize capabilities
    principal_id = _get_or_create_principal_id()
    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal_id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES.copy(),
        paired_at=datetime.now(timezone.utc).isoformat(),
        token=str(uuid.uuid4()),
        token_expires_at=datetime.now(timezone.utc).isoformat(),
    )
    
    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    return pairing


def _get_or_create_principal_id() -> str:
    """Get or create the principal ID for Hermes pairings."""
    state_dir = _get_state_dir()
    os.makedirs(state_dir, exist_ok=True)
    principal_file = os.path.join(state_dir, 'principal.json')
    
    if os.path.exists(principal_file):
        with open(principal_file, 'r') as f:
            data = json.load(f)
            return data.get('id', str(uuid.uuid4()))
    
    return str(uuid.uuid4())


def get_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get a Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    return None


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability. Delegates to daemon's internal
    status endpoint.
    
    Args:
        connection: Active Hermes connection
        
    Returns:
        Miner status dict
        
    Raises:
        PermissionError: If connection lacks observe capability
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import here to avoid circular dependency
    from daemon import miner
    
    # Get miner status
    status = miner.get_snapshot()
    
    # Transform payload - strip sensitive fields Hermes shouldn't see
    return {
        "status": status.get("status"),
        "mode": status.get("mode"),
        "hashrate_hs": status.get("hashrate_hs"),
        "temperature": status.get("temperature"),
        "uptime_seconds": status.get("uptime_seconds"),
        "freshness": status.get("freshness"),
        "hermes_id": connection.hermes_id,
        "capabilities": connection.capabilities,
    }


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Args:
        connection: Active Hermes connection
        summary_text: The summary text to append
        authority_scope: The scope of the summary (e.g., "observe")
        
    Returns:
        Dict with appended status
        
    Raises:
        PermissionError: If connection lacks summarize capability
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    # Import here to avoid circular dependency
    from spine import append_hermes_summary, EventKind
    
    # Append to spine
    event = append_hermes_summary(
        summary_text=summary_text,
        authority_scope=[authority_scope],
        principal_id=connection.principal_id,
    )
    
    return {
        "appended": True,
        "event_id": event.id,
        "hermes_id": connection.hermes_id,
        "kind": event.kind,
        "created_at": event.created_at,
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events that Hermes should not access.
    
    Args:
        connection: Active Hermes connection
        limit: Maximum number of events to return
        
    Returns:
        List of filtered events
    """
    # Import here to avoid circular dependency
    from spine import get_events, EventKind
    
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    # Filter to Hermes-readable events only
    filtered = [
        e for e in all_events
        if e.kind in HERMES_READABLE_EVENTS
    ][:limit]
    
    # Transform events - strip sensitive payload fields
    return [
        {
            "id": e.id,
            "kind": e.kind,
            "payload": _strip_sensitive_fields(e.payload, e.kind),
            "created_at": e.created_at,
        }
        for e in filtered
    ]


def _strip_sensitive_fields(payload: dict, kind: str) -> dict:
    """
    Strip sensitive fields from event payload for Hermes visibility.
    
    Hermes should not see full user message content or sensitive
    control parameters.
    """
    # Start with copy
    clean = payload.copy()
    
    # Strip full message content from control receipts
    if kind == 'control_receipt':
        # Keep receipt metadata but strip sensitive params
        safe_fields = ['command', 'status', 'receipt_id', 'mode']
        clean = {k: v for k, v in clean.items() if k in safe_fields}
    
    return clean


def generate_authority_token(hermes_id: str, principal_id: str, 
                              capabilities: List[str], 
                              expires_in_hours: int = 24) -> str:
    """
    Generate an authority token for Hermes connection.
    
    This is a helper for testing and pairing flows.
    In production, token issuance would go through plan 006 (token auth).
    
    Args:
        hermes_id: Unique Hermes identifier
        principal_id: Zend principal identifier
        capabilities: List of capabilities (observe, summarize)
        expires_in_hours: Token validity in hours
        
    Returns:
        Base64-encoded authority token
    """
    import base64
    
    expires_at = datetime.now(timezone.utc).timestamp() + (expires_in_hours * 3600)
    expires_at_iso = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
    
    token_data = {
        "hermes_id": hermes_id,
        "principal_id": principal_id,
        "capabilities": capabilities,
        "expires_at": expires_at_iso,
    }
    
    json_str = json.dumps(token_data)
    return base64.b64encode(json_str.encode()).decode()


# Module-level proof
if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {HERMES_READABLE_EVENTS}")
    print()
    
    # Test token generation
    token = generate_authority_token(
        hermes_id="hermes-001",
        principal_id="test-principal",
        capabilities=HERMES_CAPABILITIES,
        expires_in_hours=24
    )
    print(f"Test token: {token[:50]}...")
    print()
    
    # Test connection with valid token
    try:
        conn = connect(token)
        print(f"Connection established: {conn.hermes_id}")
        print(f"Capabilities: {conn.capabilities}")
    except ValueError as e:
        print(f"Connection failed: {e}")
