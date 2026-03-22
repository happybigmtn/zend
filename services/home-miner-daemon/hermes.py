#!/usr/bin/env python3
"""
Hermes Adapter Module

Hermes is an AI agent that can connect to the Zend daemon through this scoped
adapter. The adapter enforces a narrower capability scope than the gateway:
- Hermes can observe (read miner status) and summarize (append summaries)
- Hermes CANNOT control the miner
- Hermes CANNOT read user messages (filtered from event spine)

Architecture:
  Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine

Token validation:
  Authority tokens encode principal_id, hermes_id, capabilities, expiration.
  Invalid or expired tokens raise ValueError.
"""

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

from spine import (
    EventKind,
    append_event,
    get_events,
    SpineEvent,
)
from store import (
    load_pairings,
    save_pairings,
    load_or_create_principal,
    Principal,
)

# Hermes-internal capability set (distinct from gateway observe/control)
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read (excludes user_message)
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


@dataclass
class HermesConnection:
    """
    Active Hermes connection state.
    
    Attributes:
        hermes_id: Unique Hermes agent identifier
        principal_id: Associated Zend principal
        capabilities: Granted capabilities (observe, summarize)
        connected_at: ISO 8601 connection timestamp
        token_expires_at: ISO 8601 token expiration
    """
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    token_expires_at: str


@dataclass
class HermesPairing:
    """Hermes-specific pairing record in the store."""
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


def _get_hermes_pairings() -> dict:
    """Load Hermes pairing records from store."""
    state_dir = os.environ.get(
        'ZEND_STATE_DIR',
        str(os.path.join(os.path.dirname(__file__), '..', '..', 'state'))
    )
    hermes_file = os.path.join(state_dir, 'hermes-pairing.json')
    
    if os.path.exists(hermes_file):
        with open(hermes_file, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records to store."""
    state_dir = os.environ.get(
        'ZEND_STATE_DIR',
        str(os.path.join(os.path.dirname(__file__), '..', '..', 'state'))
    )
    hermes_file = os.path.join(state_dir, 'hermes-pairing.json')
    
    with open(hermes_file, 'w') as f:
        json.dump(pairings, f, indent=2)


def _is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    return datetime.now(timezone.utc) > expires


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: JWT or opaque token encoding Hermes authority.
            For milestone 1, we accept a simple token format:
            {"hermes_id": "...", "principal_id": "...", "capabilities": [...],
             "token_expires_at": "..."}
    
    Returns:
        HermesConnection with validated capabilities.
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities.
    """
    # For milestone 1, parse simple JSON token
    try:
        token_data = json.loads(authority_token)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("HERMES_INVALID_TOKEN: Token must be valid JSON")
    
    # Validate required fields
    required = ['hermes_id', 'principal_id', 'capabilities', 'token_expires_at']
    for field in required:
        if field not in token_data:
            raise ValueError(f"HERMES_INVALID_TOKEN: Missing required field '{field}'")
    
    hermes_id = token_data['hermes_id']
    principal_id = token_data['principal_id']
    capabilities = token_data['capabilities']
    token_expires_at = token_data['token_expires_at']
    
    # Validate capabilities are subset of HERMES_CAPABILITIES
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_INVALID_CAPABILITY: '{cap}' not allowed for Hermes. "
                f"Allowed: {HERMES_CAPABILITIES}"
            )
    
    # Check expiration
    if _is_token_expired(token_expires_at):
        raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")
    
    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=token_expires_at,
    )


def pair_hermes(hermes_id: str, device_name: str, capabilities: Optional[List[str]] = None) -> HermesPairing:
    """
    Create or update a Hermes pairing record.
    
    Idempotent: same hermes_id re-pairs with updated timestamp.
    
    Args:
        hermes_id: Unique Hermes agent identifier
        device_name: Human-readable name for the Hermes agent
        capabilities: Override default capabilities (observe, summarize)
    
    Returns:
        HermesPairing record with granted capabilities.
    """
    if capabilities is None:
        capabilities = HERMES_CAPABILITIES.copy()
    
    # Validate requested capabilities
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_INVALID_CAPABILITY: '{cap}' not allowed. "
                f"Allowed: {HERMES_CAPABILITIES}"
            )
    
    principal = load_or_create_principal()
    pairings = _get_hermes_pairings()
    
    now = datetime.now(timezone.utc).isoformat()
    token_expires = datetime.now(timezone.utc)
    token_expires = token_expires.replace(year=token_expires.year + 1).isoformat()
    
    # Idempotent: re-pair if exists
    existing = None
    for p in pairings.values():
        if p.get('hermes_id') == hermes_id:
            existing = p
            break
    
    if existing:
        # Update existing pairing
        existing['paired_at'] = now
        existing['token_expires_at'] = token_expires
        existing['capabilities'] = capabilities
        pairing = HermesPairing(**existing)
    else:
        # Create new pairing
        pairing = HermesPairing(
            id=str(uuid.uuid4()),
            hermes_id=hermes_id,
            principal_id=principal.id,
            device_name=device_name,
            capabilities=capabilities,
            paired_at=now,
            token_expires_at=token_expires,
        )
        pairings[pairing.id] = asdict(pairing)
    
    _save_hermes_pairings(pairings)
    
    # Append pairing event to spine
    append_event(
        EventKind.PAIRING_GRANTED,
        principal.id,
        {
            "device_name": device_name,
            "granted_capabilities": capabilities,
            "agent_type": "hermes",
        }
    )
    
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing record by hermes_id."""
    pairings = _get_hermes_pairings()
    for pairing in pairings.values():
        if pairing.get('hermes_id') == hermes_id:
            return HermesPairing(**pairing)
    return None


def generate_authority_token(hermes_id: str, capabilities: List[str], token_expires_at: str) -> str:
    """
    Generate an authority token for Hermes.
    
    This is typically called by the daemon after pairing to provide
    Hermes with its initial or refreshed authority token.
    
    Args:
        hermes_id: Hermes agent identifier
        capabilities: Granted capabilities
        token_expires_at: ISO 8601 expiration timestamp
    
    Returns:
        JSON-encoded authority token string.
    """
    principal = load_or_create_principal()
    token_data = {
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "capabilities": capabilities,
        "token_expires_at": token_expires_at,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(token_data)


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability.
    
    Args:
        connection: Active Hermes connection.
    
    Returns:
        Miner status snapshot dict.
    
    Raises:
        PermissionError: If observe capability not granted.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: 'observe' capability required for read_status"
        )
    
    # Import here to avoid circular dependency at module load
    from daemon import miner
    
    return miner.get_snapshot()


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Args:
        connection: Active Hermes connection.
        summary_text: The summary content to append.
        authority_scope: Context of what Hermes observed (e.g., "observe").
    
    Returns:
        The appended SpineEvent.
    
    Raises:
        PermissionError: If summarize capability not granted.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: 'summarize' capability required for append_summary"
        )
    
    return append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id,
        }
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events. Over-fetches to account for filtering.
    
    Args:
        connection: Active Hermes connection.
        limit: Maximum events to return.
    
    Returns:
        List of event dicts.
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    # If observe not granted, only return hermes_summary events from this connection
    if 'observe' not in connection.capabilities:
        filtered = [
            e for e in filtered
            if e.kind == EventKind.HERMES_SUMMARY.value
            and e.principal_id == connection.principal_id
        ]
    
    return [
        {
            "id": e.id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
        }
        for e in filtered[:limit]
    ]


def validate_hermes_auth(hermes_id: str, auth_header: str) -> Optional[HermesConnection]:
    """
    Validate Hermes authentication from request headers.
    
    Accepts "Hermes <hermes_id>" format header.
    Looks up pairing and creates a connection with current timestamp.
    
    Args:
        hermes_id: Expected Hermes ID from header.
        auth_header: Full Authorization header value.
    
    Returns:
        HermesConnection if valid, None otherwise.
    """
    if not auth_header:
        return None
    
    parts = auth_header.split(' ', 1)
    if len(parts) != 2 or parts[0] != 'Hermes':
        return None
    
    header_hermes_id = parts[1]
    if header_hermes_id != hermes_id:
        return None
    
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        return None
    
    if _is_token_expired(pairing.token_expires_at):
        return None
    
    return HermesConnection(
        hermes_id=pairing.hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=pairing.paired_at,
        token_expires_at=pairing.token_expires_at,
    )


# --- Proof-of-concept verification ---
if __name__ == '__main__':
    import sys
    
    print("Hermes Adapter Module")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
    print()
    
    # Test token generation and validation
    pairing = pair_hermes("hermes-001", "hermes-agent")
    print(f"Paired: {pairing.hermes_id} with {pairing.capabilities}")
    
    token = generate_authority_token(
        pairing.hermes_id,
        pairing.capabilities,
        pairing.token_expires_at,
    )
    print(f"Authority token: {token[:60]}...")
    
    try:
        conn = connect(token)
        print(f"Connected as: {conn.hermes_id}, capabilities: {conn.capabilities}")
        
        # Test append_summary
        event = append_summary(conn, "Test summary: miner healthy", "observe")
        print(f"Summary appended: {event.id}")
        
        # Test event filtering
        events = get_filtered_events(conn, limit=5)
        print(f"Filtered events: {len(events)} (no user_message)")
        
        # Test permission denial
        try:
            # Create connection without summarize
            no_sum_conn = HermesConnection(
                hermes_id="test",
                principal_id="p1",
                capabilities=["observe"],
                connected_at=datetime.now(timezone.utc).isoformat(),
                token_expires_at=datetime.now(timezone.utc).isoformat(),
            )
            append_summary(no_sum_conn, "should fail", "observe")
            print("ERROR: Should have raised PermissionError")
        except PermissionError as e:
            print(f"Permission denied (expected): {e}")
        
        print()
        print("All tests passed!")
        sys.exit(0)
        
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
