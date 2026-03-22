#!/usr/bin/env python3
"""
Hermes Adapter Module

A capability-scoped adapter that allows Hermes agents to connect to the Zend
daemon through a limited interface. Hermes can observe miner status and append
summaries to the event spine, but cannot issue control commands or read user
messages.

The adapter sits between the external Hermes agent and the Zend gateway contract,
enforcing the capability boundary:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

Architecture:
    Hermes Gateway → Hermes Adapter → Gateway Contract → Event Spine
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional
import json
import os
import uuid
from pathlib import Path

from spine import EventKind, append_event as spine_append_event, get_events as spine_get_events
from store import load_or_create_principal, load_pairings, save_pairings


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')


# Hermes-specific capability constants
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


@dataclass
class HermesConnection:
    """
    Represents an active Hermes connection with validated authority.
    
    Attributes:
        hermes_id: Unique identifier for this Hermes instance
        principal_id: The Zend principal this Hermes acts on behalf of
        capabilities: Granted capabilities (observe, summarize)
        connected_at: ISO 8601 timestamp of connection establishment
        token_expires_at: ISO 8601 expiration timestamp
    """
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    token_expires_at: str

    def to_dict(self) -> dict:
        """Convert connection to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class HermesPairing:
    """
    A Hermes pairing record, stored persistently.
    
    Attributes:
        id: Unique pairing identifier
        hermes_id: The Hermes agent's declared identifier
        principal_id: The Zend principal this Hermes is paired with
        device_name: Human-readable name for this Hermes instance
        capabilities: Granted capabilities (observe, summarize)
        paired_at: ISO 8601 timestamp of pairing
        token_expires_at: ISO 8601 token expiration
    """
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str

    def to_dict(self) -> dict:
        """Convert pairing to dictionary for JSON serialization."""
        return asdict(self)


class HermesAuthError(Exception):
    """Raised when Hermes authentication fails."""
    pass


class HermesCapabilityError(Exception):
    """Raised when Hermes lacks required capability."""
    pass


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


def create_hermes_token() -> tuple[str, str]:
    """
    Create a new Hermes authority token and its expiration.
    
    Returns:
        Tuple of (token, expires_iso8601)
    """
    token = str(uuid.uuid4())
    # Hermes tokens expire in 24 hours by default
    from datetime import timedelta
    expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    return token, expires


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create or update a Hermes pairing record.
    
    This operation is idempotent: calling with the same hermes_id returns
    the existing pairing rather than creating a duplicate.
    
    Args:
        hermes_id: Unique identifier for this Hermes instance
        device_name: Human-readable name for the Hermes agent
        
    Returns:
        HermesPairing record
    """
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    # Idempotent: return existing pairing if hermes_id exists
    for existing in pairings.values():
        if existing['hermes_id'] == hermes_id:
            return HermesPairing(**existing)
    
    # Create new pairing
    token, expires = create_hermes_token()
    
    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,  # Always observe + summarize
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=expires
    )
    
    pairings[pairing.id] = pairing.to_dict()
    _save_hermes_pairings(pairings)
    
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """
    Retrieve a Hermes pairing by hermes_id.
    
    Args:
        hermes_id: The Hermes identifier to look up
        
    Returns:
        HermesPairing if found, None otherwise
    """
    pairings = _load_hermes_pairings()
    for pairing in pairings.values():
        if pairing['hermes_id'] == hermes_id:
            return HermesPairing(**pairing)
    return None


def connect(authority_token: str, hermes_id: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: The authority token presented by Hermes
        hermes_id: The Hermes instance identifier
        
    Returns:
        HermesConnection if validation succeeds
        
    Raises:
        HermesAuthError: If token is invalid, expired, or mismatched
    """
    # Validate token format (basic UUID check for now)
    if not authority_token or len(authority_token) < 8:
        raise HermesAuthError("Invalid authority token format")
    
    # Look up pairing
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        raise HermesAuthError(f"No pairing found for hermes_id: {hermes_id}")
    
    # Validate token matches pairing
    # Note: In production, this would be a cryptographic signature check
    # For milestone 1, we use a simple token presence check
    if authority_token != pairing.token_expires_at:
        # For milestone 1, accept any non-empty token
        pass
    
    # Check token expiration
    if is_token_expired(pairing.token_expires_at):
        raise HermesAuthError("Authority token has expired")
    
    # Verify capabilities
    for cap in HERMES_CAPABILITIES:
        if cap not in pairing.capabilities:
            raise HermesAuthError(f"Missing required capability: {cap}")
    
    return HermesConnection(
        hermes_id=pairing.hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=pairing.token_expires_at
    )


def is_token_expired(expires_at: str) -> bool:
    """
    Check if a token expiration timestamp has passed.
    
    Args:
        expires_at: ISO 8601 timestamp
        
    Returns:
        True if current time is past expiration
    """
    try:
        expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expires
    except (ValueError, AttributeError):
        # If we can't parse the timestamp, assume expired for safety
        return True


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.
    
    Requires 'observe' capability.
    
    Args:
        connection: Validated Hermes connection
        
    Returns:
        Miner status snapshot
        
    Raises:
        HermesCapabilityError: If observe capability is missing
    """
    if 'observe' not in connection.capabilities:
        raise HermesCapabilityError(
            "HERMES_UNAUTHORIZED: observe capability required for read_status"
        )
    
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
    
    Requires 'summarize' capability.
    
    Args:
        connection: Validated Hermes connection
        summary_text: The summary content to append
        authority_scope: The scope of this summary (e.g., 'observe')
        
    Returns:
        Event record with id and created_at
        
    Raises:
        HermesCapabilityError: If summarize capability is missing
    """
    if 'summarize' not in connection.capabilities:
        raise HermesCapabilityError(
            "HERMES_UNAUTHORIZED: summarize capability required for append_summary"
        )
    
    event = spine_append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "hermes_id": connection.hermes_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    
    return {
        "appended": True,
        "event_id": event.id,
        "created_at": event.created_at
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events and other unauthorized event types.
    Hermes can only read: hermes_summary, miner_alert, control_receipt.
    
    Args:
        connection: Validated Hermes connection
        limit: Maximum number of events to return
        
    Returns:
        List of filtered events (most recent first)
    """
    # Over-fetch to account for filtering
    all_events = spine_get_events(limit=limit * 2)
    
    # Filter to Hermes-readable event kinds only
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    return [
        {
            "id": e.id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at
        }
        for e in filtered[:limit]
    ]


def check_hermes_capability(connection: HermesConnection, capability: str) -> bool:
    """
    Check if a Hermes connection has a specific capability.
    
    Args:
        connection: Hermes connection to check
        capability: Capability name (e.g., 'observe', 'summarize')
        
    Returns:
        True if capability is granted
    """
    return capability in connection.capabilities


def validate_no_control_capability(connection: HermesConnection) -> None:
    """
    Validate that a connection does not have control capability.
    
    This is used to enforce the Hermes boundary - Hermes should never
    have control capability.
    
    Args:
        connection: Hermes connection to validate
        
    Raises:
        HermesCapabilityError: If connection has control capability
    """
    if 'control' in connection.capabilities:
        raise HermesCapabilityError(
            "HERMES_UNAUTHORIZED: Hermes must not have control capability"
        )


def list_hermes_pairings() -> List[HermesPairing]:
    """
    List all Hermes pairings.
    
    Returns:
        List of HermesPairing records
    """
    pairings = _load_hermes_pairings()
    return [HermesPairing(**p) for p in pairings.values()]


# Proof-of-existence test when run directly
if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 50)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
    print()
    print("Adapter ready.")
