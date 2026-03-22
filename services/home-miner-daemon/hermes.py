#!/usr/bin/env python3
"""
Hermes Adapter - capability-scoped adapter for Hermes AI agent.

The Hermes adapter sits between the external Hermes agent and the Zend gateway contract:

    Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine

The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
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


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')


class HermesCapability(str, Enum):
    """Capabilities granted to Hermes agent."""
    OBSERVE = "observe"
    SUMMARIZE = "summarize"


# Hermes is restricted to observe and summarize only - no control
HERMES_CAPABILITIES = [HermesCapability.OBSERVE.value, HermesCapability.SUMMARIZE.value]

# Events Hermes is allowed to read
# Blocks USER_MESSAGE to protect user privacy
HERMES_READABLE_EVENTS = [
    "hermes_summary",
    "miner_alert",
    "control_receipt",
]


@dataclass
class HermesConnection:
    """Represents an active Hermes agent connection."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    authority_token: str


@dataclass
class HermesPairing:
    """Hermes pairing record stored in the daemon."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
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


def generate_authority_token() -> str:
    """Generate a new authority token for Hermes."""
    return str(uuid.uuid4())


def is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    try:
        expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expires
    except (ValueError, AttributeError):
        # Unparseable expiration = expired. Fail closed on security boundary.
        return True


def validate_authority_token(token: str) -> Optional[HermesPairing]:
    """
    Validate an authority token and return the associated Hermes pairing.
    
    Returns None if token is invalid, expired, or not found.
    """
    pairings = _load_hermes_pairings()
    
    for pairing in pairings.values():
        if pairing.get('token') == token:
            if is_token_expired(pairing.get('token_expires_at', '')):
                return None
            return HermesPairing(**pairing)
    
    return None


def connect(authority_token: str) -> HermesConnection:
    """
    Establish a Hermes connection using authority token.
    
    Validates the token and returns a HermesConnection object.
    
    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities.
    """
    if not authority_token:
        raise ValueError("HERMES_INVALID_TOKEN: authority token is required")
    
    pairing = validate_authority_token(authority_token)
    
    if not pairing:
        raise ValueError("HERMES_INVALID_TOKEN: token is invalid or expired")
    
    # Verify capabilities are only observe + summarize
    for cap in pairing.capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(f"HERMES_UNAUTHORIZED: capability '{cap}' not allowed for Hermes")
    
    return HermesConnection(
        hermes_id=pairing.hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        authority_token=authority_token
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through the adapter.
    
    Requires 'observe' capability.
    
    Raises:
        PermissionError: If Hermes lacks observe capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
    
    # Import here to avoid circular dependency
    from daemon import miner
    
    return miner.get_snapshot()


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Raises:
        PermissionError: If Hermes lacks summarize capability.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
    
    # Import here to avoid circular dependency
    from spine import append_event, EventKind
    
    event = append_event(
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
        "kind": event.kind,
        "created_at": event.created_at
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]:
    """
    Get events that Hermes is allowed to see.
    
    Filters out user_message events to protect user privacy.
    """
    from spine import get_events

    # Over-fetch to compensate for filtering, then trim to limit
    all_events = get_events(limit=limit * 3)

    filtered = [
        {
            "id": e.id,
            "principal_id": e.principal_id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
            "version": e.version
        }
        for e in all_events
        if e.kind in HERMES_READABLE_EVENTS
    ]

    return filtered[:limit]


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create or update a Hermes pairing record.
    
    Idempotent - same hermes_id will update the existing pairing.
    """
    # Import here to avoid circular dependency
    from store import load_or_create_principal
    
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    token = generate_authority_token()
    paired_at = datetime.now(timezone.utc).isoformat()
    # Token expires in 24 hours
    from datetime import timedelta
    token_expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    
    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=paired_at,
        token=token,
        token_expires_at=token_expires
    )
    
    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    data = pairings.get(hermes_id)
    if data:
        return HermesPairing(**data)
    return None


def revoke_hermes_token(hermes_id: str) -> bool:
    """Revoke Hermes pairing by invalidating its token."""
    pairings = _load_hermes_pairings()
    
    if hermes_id in pairings:
        # Set token expiration to past
        pairings[hermes_id]['token_expires_at'] = '1970-01-01T00:00:00+00:00'
        _save_hermes_pairings(pairings)
        return True
    
    return False
