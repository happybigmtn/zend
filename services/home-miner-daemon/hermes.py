#!/usr/bin/env python3
"""
Hermes Adapter Module

Enforces capability boundaries for Hermes AI agent connections:
- Hermes can observe miner status
- Hermes can append summaries to the event spine
- Hermes CANNOT issue control commands
- Hermes CANNOT read user_message events

The adapter validates authority tokens and filters events before
they reach the gateway contract.
"""

import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

from spine import append_event, get_events, EventKind
from store import load_or_create_principal, load_pairings, save_pairings, get_pairing_by_device


# Hermes capabilities are observe and summarize (no control)
HERMES_CAPABILITIES = ['observe', 'summarize']

# Hermes can read these events from the spine
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


@dataclass
class HermesConnection:
    """Represents an active Hermes connection with scoped capabilities."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str

    def to_dict(self) -> dict:
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at,
            "capabilities_label": "Hermes Adapter (observe + summarize)",
        }


def _validate_authority_token(authority_token: str) -> dict:
    """
    Validate authority token structure and extract claims.
    
    Token format: hermes_id|principal_id|capabilities|expiry_iso
    
    Raises ValueError if token is malformed or expired.
    """
    if not authority_token:
        raise ValueError("HERMES_INVALID_TOKEN: Empty authority token")
    
    parts = authority_token.split('|')
    if len(parts) != 4:
        raise ValueError("HERMES_INVALID_TOKEN: Malformed token structure")
    
    hermes_id, principal_id, capabilities_str, expiry_str = parts
    
    # Validate capabilities
    token_caps = capabilities_str.split(',')
    for cap in token_caps:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_INVALID_CAPABILITY: {cap} not in allowed set")
    
    # Validate expiration
    try:
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if expiry < datetime.now(timezone.utc):
            raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")
    except ValueError as e:
        if "expired" in str(e).lower():
            raise
        raise ValueError(f"HERMES_INVALID_TOKEN: Invalid expiry format: {e}")
    
    return {
        "hermes_id": hermes_id,
        "principal_id": principal_id,
        "capabilities": token_caps,
        "expires_at": expiry_str,
    }


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: Encoded token with hermes_id, principal_id, 
                        capabilities, and expiration.
    
    Returns:
        HermesConnection with validated capabilities.
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities.
    """
    claims = _validate_authority_token(authority_token)
    
    return HermesConnection(
        hermes_id=claims["hermes_id"],
        principal_id=claims["principal_id"],
        capabilities=claims["capabilities"],
        connected_at=datetime.now(timezone.utc).isoformat(),
    )


def pair_hermes(hermes_id: str, device_name: Optional[str] = None) -> HermesConnection:
    """
    Create a new Hermes pairing record with observe+summarize capabilities.
    
    This is idempotent - re-pairing with same hermes_id returns existing.
    
    Args:
        hermes_id: Unique identifier for the Hermes agent.
        device_name: Optional device name for the pairing record.
    
    Returns:
        HermesConnection with observe and summarize capabilities.
    """
    # Reject hermes_id containing the token delimiter to prevent token format corruption
    if '|' in hermes_id:
        raise ValueError("HERMES_INVALID_ID: hermes_id must not contain '|'")

    principal = load_or_create_principal()
    pairings = load_pairings()

    # Check for existing pairing
    for pairing_id, existing in pairings.items():
        if existing.get('hermes_id') == hermes_id:
            # Check if stored token is still valid; regenerate if expired
            try:
                expires_at = datetime.fromisoformat(
                    existing.get('token_expires_at', '').replace('Z', '+00:00')
                )
                if expires_at < datetime.now(timezone.utc):
                    # Token expired — regenerate
                    from datetime import timedelta
                    new_expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                    caps_str = ','.join(HERMES_CAPABILITIES)
                    new_token = f"{hermes_id}|{existing['principal_id']}|{caps_str}|{new_expires}"
                    existing['authority_token'] = new_token
                    existing['token_expires_at'] = new_expires
                    pairings[pairing_id] = existing
                    save_pairings(pairings)
            except (KeyError, ValueError):
                pass

            return HermesConnection(
                hermes_id=hermes_id,
                principal_id=existing['principal_id'],
                capabilities=existing.get('capabilities', HERMES_CAPABILITIES),
                connected_at=existing.get('paired_at', datetime.now(timezone.utc).isoformat()),
            )
    
    # Create new pairing
    pairing_id = str(uuid.uuid4())
    paired_at = datetime.now(timezone.utc).isoformat()
    
    # Token expires in 30 days
    expires_at = datetime.now(timezone.utc)
    from datetime import timedelta
    expires_at = (expires_at + timedelta(days=30)).isoformat()
    
    # Build authority token for storage
    capabilities_str = ','.join(HERMES_CAPABILITIES)
    authority_token = f"{hermes_id}|{principal.id}|{capabilities_str}|{expires_at}"
    
    pairing = {
        "id": pairing_id,
        "hermes_id": hermes_id,
        "device_name": device_name or f"hermes-{hermes_id}",
        "principal_id": principal.id,
        "capabilities": HERMES_CAPABILITIES,
        "paired_at": paired_at,
        "token_expires_at": expires_at,
        "authority_token": authority_token,
        "token_used": False,
    }
    
    pairings[pairing_id] = pairing
    save_pairings(pairings)
    
    # Append pairing event
    append_event(
        EventKind.PAIRING_REQUESTED,
        principal.id,
        {
            "device_name": device_name or f"hermes-{hermes_id}",
            "requested_capabilities": HERMES_CAPABILITIES,
            "agent_type": "hermes",
        }
    )
    
    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal.id,
        capabilities=HERMES_CAPABILITIES,
        connected_at=paired_at,
    )


def get_authority_token(hermes_id: str) -> Optional[str]:
    """Get stored authority token for Hermes pairing."""
    pairings = load_pairings()
    for pairing in pairings.values():
        if pairing.get('hermes_id') == hermes_id:
            return pairing.get('authority_token')
    return None


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through the adapter.
    
    Requires 'observe' capability.
    
    Args:
        connection: Active HermesConnection.
    
    Returns:
        MinerSnapshot dict with status, mode, hashrate, etc.
    
    Raises:
        PermissionError: If Hermes lacks observe capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import here to avoid circular dependency
    from daemon import miner
    
    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: Optional[List[str]] = None
) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Args:
        connection: Active HermesConnection.
        summary_text: The summary content to append.
        authority_scope: Optional scope description (defaults to connection caps).
    
    Returns:
        Event dict with id and metadata.
    
    Raises:
        PermissionError: If Hermes lacks summarize capability.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    scope = authority_scope or connection.capabilities
    
    event = append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            "summary_text": summary_text,
            "authority_scope": scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id,
        }
    )
    
    return {
        "appended": True,
        "event_id": event.id,
        "kind": event.kind,
        "created_at": event.created_at,
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.

    This filters out user_message events - Hermes cannot read user messages.

    Args:
        connection: Active HermesConnection.
        limit: Maximum events to return.

    Returns:
        List of SpineEvent dicts (filtered).

    Raises:
        PermissionError: If Hermes lacks observe capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    
    filtered = [
        {
            "id": e.id,
            "principal_id": e.principal_id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
            "version": e.version,
        }
        for e in all_events
        if e.kind in readable_kinds
    ]
    
    return filtered[:limit]


def check_capability(connection: HermesConnection, capability: str) -> bool:
    """Check if Hermes connection has a specific capability."""
    return capability in connection.capabilities


def validate_connection(connection: HermesConnection) -> bool:
    """
    Validate that a HermesConnection is still valid.
    
    Checks that the pairing record exists and is not expired.
    """
    pairings = load_pairings()
    
    for pairing in pairings.values():
        if pairing.get('hermes_id') == connection.hermes_id:
            try:
                expires_at = datetime.fromisoformat(
                    pairing['token_expires_at'].replace('Z', '+00:00')
                )
                return expires_at > datetime.now(timezone.utc)
            except (KeyError, ValueError):
                return False
    
    return False


# CLI-friendly helpers

def generate_token(hermes_id: str, principal_id: str, days_valid: int = 30) -> str:
    """Generate a new authority token for Hermes."""
    from datetime import timedelta
    
    capabilities_str = ','.join(HERMES_CAPABILITIES)
    expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
    
    return f"{hermes_id}|{principal_id}|{capabilities_str}|{expires_at.isoformat()}"


# Proof of concept test
if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
    print()
    
    # Test token generation and validation
    principal_id = str(uuid.uuid4())
    token = generate_token("hermes-001", principal_id)
    print(f"Generated token: {token[:50]}...")
    
    claims = _validate_authority_token(token)
    print(f"Validated claims: hermes_id={claims['hermes_id']}, capabilities={claims['capabilities']}")
    
    # Test connection
    conn = connect(token)
    print(f"Connection: {conn.hermes_id} with capabilities {conn.capabilities}")
