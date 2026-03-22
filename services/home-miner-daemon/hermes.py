#!/usr/bin/env python3
"""
Hermes Adapter Module

Provides a capability-scoped interface for Hermes AI agents to connect to the
Zend gateway. Hermes can observe miner status and append summaries, but cannot
issue control commands or read user messages.

The adapter sits between the external Hermes agent and the Zend gateway contract:

    Hermes Gateway → Zend Hermes Adapter → Event Spine

This module implements:
- Authority token validation
- Capability checking (observe + summarize only)
- Event filtering (block user_message events)
- Connection state management
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Import from sibling modules
from spine import EventKind, append_event, get_events, SpineEvent
from store import load_pairings, save_pairings, load_or_create_principal

# Re-export EventKind for convenience
__all__ = [
    'HermesConnection',
    'HermesCapabilityError',
    'HermesAuthenticationError',
    'connect',
    'read_status',
    'append_summary',
    'get_filtered_events',
    'HERMES_CAPABILITIES',
    'HERMES_READABLE_EVENTS',
    'pair_hermes',
    'get_hermes_pairing',
]


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[1] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Hermes capabilities are independent from gateway capabilities.
# Hermes can observe and summarize, but NOT control.
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read from the spine.
# NOTE: user_message is explicitly excluded.
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


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


class HermesAuthenticationError(Exception):
    """Raised when Hermes authentication fails."""
    pass


class HermesCapabilityError(Exception):
    """Raised when Hermes lacks required capability."""
    pass


# ---------------------------------------------------------------------------
# Hermes Pairing Store
# ---------------------------------------------------------------------------

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


def pair_hermes(hermes_id: str, device_name: str = None) -> dict:
    """
    Create or update a Hermes pairing record with observe+summarize capabilities.

    This operation is idempotent: pairing the same hermes_id again updates
    the existing record.

    Args:
        hermes_id: Unique identifier for the Hermes agent
        device_name: Human-readable name for the Hermes agent (optional)

    Returns:
        dict with hermes_id, capabilities, paired_at
    """
    pairings = _load_hermes_pairings()

    if device_name is None:
        device_name = f"hermes-{hermes_id}"

    now = datetime.now(timezone.utc).isoformat()

    if hermes_id in pairings:
        # Idempotent re-pairing: update timestamp
        pairings[hermes_id]['paired_at'] = now
        pairings[hermes_id]['device_name'] = device_name
    else:
        # New pairing
        pairings[hermes_id] = {
            'hermes_id': hermes_id,
            'device_name': device_name,
            'capabilities': HERMES_CAPABILITIES.copy(),
            'paired_at': now,
        }

    _save_hermes_pairings(pairings)
    return pairings[hermes_id]


def get_hermes_pairing(hermes_id: str) -> Optional[dict]:
    """Get a Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    return pairings.get(hermes_id)


def get_hermes_pairings() -> List[dict]:
    """Get all Hermes pairing records."""
    pairings = _load_hermes_pairings()
    return list(pairings.values())


# ---------------------------------------------------------------------------
# Authority Token
# ---------------------------------------------------------------------------

def _generate_authority_token(hermes_id: str, principal_id: str) -> dict:
    """
    Generate an authority token for Hermes connection.

    The token encodes the principal, hermes_id, granted capabilities,
    and expiration time.
    """
    token_id = str(uuid.uuid4())
    issued_at = datetime.now(timezone.utc)

    # Token expires in 24 hours
    from datetime import timedelta
    expires_at = issued_at + timedelta(hours=24)

    return {
        'token_id': token_id,
        'hermes_id': hermes_id,
        'principal_id': principal_id,
        'capabilities': HERMES_CAPABILITIES.copy(),
        'issued_at': issued_at.isoformat(),
        'expires_at': expires_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Core Adapter Functions
# ---------------------------------------------------------------------------

def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.

    Args:
        authority_token: JSON-encoded authority token string

    Returns:
        HermesConnection instance

    Raises:
        HermesAuthenticationError: If token is invalid or expired
    """
    try:
        token_data = json.loads(authority_token)
    except json.JSONDecodeError:
        raise HermesAuthenticationError("Invalid authority token format")

    # Validate required fields
    required_fields = ['hermes_id', 'principal_id', 'capabilities', 'expires_at']
    for field in required_fields:
        if field not in token_data:
            raise HermesAuthenticationError(f"Missing required field: {field}")

    # Check expiration
    try:
        expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
        if expires_at < datetime.now(timezone.utc):
            raise HermesAuthenticationError("Authority token has expired")
    except (ValueError, TypeError):
        raise HermesAuthenticationError("Invalid token expiration format")

    # Validate capabilities
    token_caps = set(token_data.get('capabilities', []))
    required_caps = set(HERMES_CAPABILITIES)

    # Hermes must have at least observe capability to connect
    if 'observe' not in token_caps:
        raise HermesAuthenticationError("Authority token must include 'observe' capability")

    # Check that Hermes is NOT requesting control capability (which is invalid for Hermes)
    control_caps = token_caps - required_caps
    if control_caps:
        raise HermesCapabilityError(
            f"Hermes cannot have control capabilities: {list(control_caps)}"
        )

    # Verify the hermes_id exists in pairing store
    pairing = get_hermes_pairing(token_data['hermes_id'])
    if not pairing:
        raise HermesAuthenticationError(
            f"Hermes '{token_data['hermes_id']}' is not paired with Zend"
        )

    return HermesConnection(
        hermes_id=token_data['hermes_id'],
        principal_id=token_data['principal_id'],
        capabilities=token_data['capabilities'],
        connected_at=datetime.now(timezone.utc).isoformat(),
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through the adapter.

    Requires 'observe' capability.

    Args:
        connection: Active Hermes connection

    Returns:
        dict with miner status snapshot

    Raises:
        HermesCapabilityError: If observe capability is missing
    """
    if 'observe' not in connection.capabilities:
        raise HermesCapabilityError(
            "HERMES_UNAUTHORIZED: observe capability required"
        )

    # Import here to avoid circular dependency
    from daemon import miner

    snapshot = miner.get_snapshot()
    return {
        'hermes_id': connection.hermes_id,
        'status': snapshot['status'],
        'mode': snapshot['mode'],
        'hashrate_hs': snapshot['hashrate_hs'],
        'temperature': snapshot['temperature'],
        'uptime_seconds': snapshot['uptime_seconds'],
        'freshness': snapshot['freshness'],
    }


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str = 'observe'
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.

    Requires 'summarize' capability.

    Args:
        connection: Active Hermes connection
        summary_text: The summary text to append
        authority_scope: The scope of the authority (default: 'observe')

    Returns:
        SpineEvent that was appended

    Raises:
        HermesCapabilityError: If summarize capability is missing
    """
    if 'summarize' not in connection.capabilities:
        raise HermesCapabilityError(
            "HERMES_UNAUTHORIZED: summarize capability required"
        )

    if not summary_text or not summary_text.strip():
        raise ValueError("summary_text cannot be empty")

    # Import here to avoid circular dependency
    from spine import append_hermes_summary

    event = append_hermes_summary(
        summary_text=summary_text.strip(),
        authority_scope=[authority_scope],
        principal_id=connection.principal_id,
    )

    return event


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Get events Hermes is allowed to see.

    Filters out user_message events that Hermes should not access.

    Args:
        connection: Active Hermes connection
        limit: Maximum number of events to return

    Returns:
        List of SpineEvent objects that Hermes can read
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)

    # Filter to only Hermes-readable event kinds
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]

    return filtered[:limit]


def validate_control_attempt(connection: HermesConnection) -> bool:
    """
    Validate whether Hermes is attempting to use control capability.

    Hermes should NEVER be able to control the miner.

    Args:
        connection: Active Hermes connection

    Returns:
        True if Hermes has control (should never happen)

    Raises:
        HermesCapabilityError: Always raised with clear rejection message
    """
    raise HermesCapabilityError(
        "HERMES_UNAUTHORIZED: Hermes does not have control capability. "
        "Control commands are not permitted for Hermes agents."
    )


# ---------------------------------------------------------------------------
# CLI Helpers
# ---------------------------------------------------------------------------

def create_hermes_token(hermes_id: str) -> str:
    """
    Create a new authority token for a paired Hermes agent.

    Returns a JSON string that can be passed directly to the daemon.
    This is a convenience function for testing and development.
    Production systems should implement proper token issuance.
    """
    principal = load_or_create_principal()
    pairing = get_hermes_pairing(hermes_id)

    if not pairing:
        raise ValueError(f"Hermes '{hermes_id}' is not paired. Call pair_hermes() first.")

    # Generate token and return as JSON string
    token = _generate_authority_token(hermes_id, principal.id)
    return json.dumps(token)


# ---------------------------------------------------------------------------
# Module Proof
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Hermes Adapter Module")
    print("=" * 50)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
    print()
    print("Available functions:")
    for name, func in [
        ('connect', 'Establish Hermes connection with authority token'),
        ('read_status', 'Read miner status (requires observe)'),
        ('append_summary', 'Append summary to spine (requires summarize)'),
        ('get_filtered_events', 'Get filtered events (no user_message)'),
        ('pair_hermes', 'Create Hermes pairing record'),
        ('create_hermes_token', 'Generate authority token for Hermes'),
    ]:
        print(f"  - {name}: {func}")
