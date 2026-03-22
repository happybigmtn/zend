#!/usr/bin/env python3
"""
Hermes Adapter Module

Provides a capability-scoped adapter for Hermes AI agents to interact with
the Zend daemon. Hermes can observe miner status and append summaries to
the event spine, but cannot issue control commands or read user messages.

The adapter enforces:
- Authority token validation with principal_id, hermes_id, capabilities, expiration
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

# Resolve relative imports from daemon context
import sys
_daemon_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_daemon_dir))

import spine
import store


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')


class HermesCapability(str, Enum):
    """Hermes capabilities - independent from gateway observe/control."""
    OBSERVE = "observe"
    SUMMARIZE = "summarize"


# Hermes capability set for milestone 1
HERMES_CAPABILITIES = [c.value for c in HermesCapability]

# Events Hermes is allowed to read from the spine
HERMES_READABLE_EVENTS = [
    spine.EventKind.HERMES_SUMMARY,
    spine.EventKind.MINER_ALERT,
    spine.EventKind.CONTROL_RECEIPT,
]


@dataclass
class HermesConnection:
    """A live Hermes connection with validated authority."""
    hermes_id: str
    principal_id: str
    capabilities: list[str]
    connected_at: str
    token_expires_at: str

    def has_capability(self, cap: str) -> bool:
        """Check if connection has a specific capability."""
        return cap in self.capabilities


@dataclass
class HermesPairing:
    """Hermes pairing record stored in the daemon."""
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: list[str]
    paired_at: str
    token: str
    token_expires_at: str


def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records from store."""
    if os.path.exists(HERMES_PAIRING_FILE):
        with open(HERMES_PAIRING_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records to store."""
    with open(HERMES_PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def _is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    return datetime.now(timezone.utc) > expires


def _validate_authority_token(token: str) -> dict:
    """
    Validate an authority token and return its claims.
    
    Token format: JSON with hermes_id, principal_id, capabilities, expires_at
    For milestone 1, tokens are stored as simple JSON files.
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
    """
    # Try to find token in pairing store
    pairings = _load_hermes_pairings()
    
    for pairing_id, pairing_data in pairings.items():
        if pairing_data.get('token') == token:
            if _is_token_expired(pairing_data['token_expires_at']):
                raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")
            
            # Validate capabilities
            caps = pairing_data.get('capabilities', [])
            for cap in caps:
                if cap not in HERMES_CAPABILITIES:
                    raise ValueError(f"HERMES_INVALID_CAPABILITY: '{cap}' is not a valid Hermes capability")
            
            # Control capability is explicitly disallowed for Hermes
            if 'control' in caps:
                raise ValueError("HERMES_UNAUTHORIZED: Hermes cannot have 'control' capability")
            
            return pairing_data
    
    raise ValueError("HERMES_INVALID_TOKEN: Authority token not found")


def pair_hermes(hermes_id: str, device_name: str, requested_capabilities: Optional[list[str]] = None) -> HermesPairing:
    """
    Create a new Hermes pairing record.
    
    Idempotent: If hermes_id already exists, returns existing pairing.
    Default capabilities are observe + summarize.
    
    Args:
        hermes_id: Unique identifier for the Hermes agent
        device_name: Human-readable name for this Hermes instance
        requested_capabilities: Override default capabilities (not recommended)
    
    Returns:
        HermesPairing record with token for initial connection
    """
    principal = store.load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    # Idempotent: return existing pairing if hermes_id exists
    for existing in pairings.values():
        if existing['hermes_id'] == hermes_id:
            return HermesPairing(**existing)
    
    # Create new pairing with observe + summarize
    capabilities = requested_capabilities or HERMES_CAPABILITIES.copy()
    
    # Ensure no control capability (defensive)
    if 'control' in capabilities:
        capabilities.remove('control')
    
    token = str(uuid.uuid4())
    # Token expires in 24 hours
    from datetime import timedelta
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    
    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=capabilities,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token=token,
        token_expires_at=expires_at
    )
    
    pairings[pairing.id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    # Append pairing event to spine
    spine.append_pairing_granted(
        device_name,
        capabilities,
        principal.id
    )
    
    return pairing


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: Token issued during Hermes pairing
    
    Returns:
        HermesConnection with validated capabilities
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities
    """
    token_claims = _validate_authority_token(authority_token)
    
    return HermesConnection(
        hermes_id=token_claims['hermes_id'],
        principal_id=token_claims['principal_id'],
        capabilities=token_claims['capabilities'],
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=token_claims['token_expires_at']
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability. Delegates to daemon's internal status endpoint.
    
    Args:
        connection: Validated Hermes connection
    
    Returns:
        Miner status snapshot
    
    Raises:
        PermissionError: If observe capability is not granted
    """
    if HermesCapability.OBSERVE.value not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import here to avoid circular dependency
    from daemon import miner
    
    return miner.get_snapshot()


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str = "observe") -> spine.SpineEvent:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability. Creates a hermes_summary event.
    
    Args:
        connection: Validated Hermes connection
        summary_text: The summary content to record
        authority_scope: Scope of authority used (observe, summarize, or both)
    
    Returns:
        The appended SpineEvent
    
    Raises:
        PermissionError: If summarize capability is not granted
    """
    if HermesCapability.SUMMARIZE.value not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    # Append to spine with hermes_summary kind
    event = spine.append_hermes_summary(
        summary_text=summary_text,
        authority_scope=authority_scope,
        principal_id=connection.principal_id
    )
    
    return event


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list[dict]:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events and any event kinds not in HERMES_READABLE_EVENTS.
    Over-fetches to account for filtering overhead.
    
    Args:
        connection: Validated Hermes connection
        limit: Maximum number of events to return
    
    Returns:
        List of event dicts suitable for Hermes consumption
    """
    # Over-fetch to account for filtered events
    all_events = spine.get_events(limit=limit * 3)
    
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [
        e for e in all_events 
        if e.kind in readable_kinds
    ]
    
    # Transform events for Hermes consumption
    result = []
    for event in filtered[:limit]:
        result.append({
            "id": event.id,
            "kind": event.kind,
            "payload": _transform_payload_for_hermes(event.kind, event.payload),
            "created_at": event.created_at
        })
    
    return result


def _transform_payload_for_hermes(kind: str, payload: dict) -> dict:
    """
    Transform payload to strip fields Hermes shouldn't see.
    
    For milestone 1, this is a pass-through but the function exists
    for future expansion where we might redact sensitive fields.
    """
    # Current: pass through unchanged
    # Future: strip encrypted_content from user_message, redact addresses, etc.
    return payload.copy()


def get_hermes_status(connection: HermesConnection) -> dict:
    """
    Get Hermes connection status and capabilities.
    
    Returns a summary of the Hermes connection state for the Agent tab.
    """
    return {
        "hermes_id": connection.hermes_id,
        "principal_id": connection.principal_id,
        "capabilities": connection.capabilities,
        "connected_at": connection.connected_at,
        "status": "connected"
    }


def get_hermes_pairings() -> list[dict]:
    """List all Hermes pairings."""
    pairings = _load_hermes_pairings()
    return [
        {
            "id": p['id'],
            "hermes_id": p['hermes_id'],
            "device_name": p['device_name'],
            "capabilities": p['capabilities'],
            "paired_at": p['paired_at']
        }
        for p in pairings.values()
    ]
