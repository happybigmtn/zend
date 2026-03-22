#!/usr/bin/env python3
"""
Hermes Adapter Module

Enforces capability boundaries between the Hermes AI agent and the Zend gateway.
Hermes can observe miner status and append summaries, but cannot issue control
commands or read user messages.

This adapter sits between the external Hermes agent and the Zend gateway contract:
  Hermes Gateway → Hermes Adapter → Zend Gateway Contract → Event Spine
"""

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

# These imports rely on sibling modules being in the same package
from store import (
    load_pairings,
    save_pairings,
    load_or_create_principal,
    Principal,
)
from spine import (
    EventKind,
    SpineEvent,
    get_events as spine_get_events,
    append_event,
    append_hermes_summary,
)

# Hermes capability constants
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Blocked event kinds for Hermes (user cannot see these)
HERMES_BLOCKED_EVENTS = [EventKind.USER_MESSAGE]


@dataclass
class HermesConnection:
    """Represents an active Hermes connection with validated authority."""
    hermes_id: str
    principal_id: str
    capabilities: list[str]
    connected_at: str

    def has_capability(self, cap: str) -> bool:
        """Check if connection has a specific capability."""
        return cap in self.capabilities

    def to_dict(self) -> dict:
        """Serialize connection state for API responses."""
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at,
            "connected": True
        }


class HermesCapabilityError(Exception):
    """Raised when Hermes lacks required capability."""
    def __init__(self, required_capability: str, action: str):
        self.required_capability = required_capability
        self.action = action
        super().__init__(f"HERMES_UNAUTHORIZED: {action} requires '{required_capability}' capability")


class HermesTokenError(Exception):
    """Raised when authority token validation fails."""
    pass


@dataclass
class HermesPairing:
    """Hermes pairing record stored persistently."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: list[str]
    paired_at: str
    token: str
    token_expires_at: str


def _get_hermes_pairings() -> dict:
    """Load Hermes pairing records from store."""
    pairings_file = _get_hermes_pairings_file()
    if pairings_file.exists():
        with open(pairings_file, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records to store."""
    pairings_file = _get_hermes_pairings_file()
    pairings_file.parent.mkdir(parents=True, exist_ok=True)
    with open(pairings_file, 'w') as f:
        json.dump(pairings, f, indent=2)


def _get_hermes_pairings_file():
    """Get path to Hermes pairings file."""
    from pathlib import Path
    state_dir = os.environ.get('ZEND_STATE_DIR')
    if state_dir:
        return Path(state_dir) / 'hermes-pairings.json'
    # Default to sibling of principal.json
    return Path(__file__).resolve().parents[1].parent / 'state' / 'hermes-pairings.json'


import os  # Moved here to avoid circular import issues


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create a Hermes pairing record with observe + summarize capabilities.
    Idempotent: returns existing pairing if hermes_id already exists.
    """
    pairings = _get_hermes_pairings()

    # Idempotent: return existing pairing
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])

    principal = load_or_create_principal()

    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES.copy(),
        paired_at=datetime.now(timezone.utc).isoformat(),
        token=str(uuid.uuid4()),
        token_expires_at=datetime.now(timezone.utc).isoformat(),  # No expiration for MVP
    )

    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)

    return pairing


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.

    Args:
        authority_token: Token issued during Hermes pairing.
                        Format: "Hermes <hermes_id>:<token>"

    Returns:
        HermesConnection with validated capabilities.

    Raises:
        HermesTokenError: If token is invalid, expired, or malformed.
    """
    if not authority_token:
        raise HermesTokenError("Authority token is required")

    # Parse token format: "Hermes <hermes_id>:<token>"
    parts = authority_token.split(' ', 1)
    if len(parts) != 2 or parts[0] != 'Hermes':
        raise HermesTokenError("Invalid token format. Expected: 'Hermes <hermes_id>:<token>'")

    hermes_id_part = parts[1]
    if ':' in hermes_id_part:
        hermes_id, token = hermes_id_part.split(':', 1)
    else:
        # For MVP, accept just the hermes_id as token
        hermes_id = hermes_id_part
        token = hermes_id_part

    # Validate pairing exists
    pairings = _get_hermes_pairings()
    if hermes_id not in pairings:
        raise HermesTokenError(f"Unknown Hermes ID: {hermes_id}")

    pairing_data = pairings[hermes_id]

    # Validate token matches
    if pairing_data.get('token') != token:
        raise HermesTokenError("Token validation failed")

    # Validate capabilities (must be observe + summarize only)
    capabilities = pairing_data.get('capabilities', [])
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise HermesTokenError(f"Unsupported capability: {cap}")

    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=pairing_data['principal_id'],
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat()
    )


def read_status(connection: HermesConnection, miner) -> dict:
    """
    Read miner status through adapter.

    Args:
        connection: Validated Hermes connection.
        miner: MinerSimulator instance providing status.

    Returns:
        Miner status snapshot.

    Raises:
        HermesCapabilityError: If connection lacks 'observe' capability.
    """
    if 'observe' not in connection.capabilities:
        raise HermesCapabilityError('observe', 'read_status')

    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.

    Args:
        connection: Validated Hermes connection.
        summary_text: The summary content to append.
        authority_scope: The scope of the summary (e.g., 'observe').

    Returns:
        The appended SpineEvent.

    Raises:
        HermesCapabilityError: If connection lacks 'summarize' capability.
    """
    if 'summarize' not in connection.capabilities:
        raise HermesCapabilityError('summarize', 'append_summary')

    return append_hermes_summary(
        summary_text=summary_text,
        authority_scope=[authority_scope] if authority_scope else ['observe'],
        principal_id=connection.principal_id
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list[dict]:
    """
    Return events Hermes is allowed to see.

    Filters out user_message events and returns only:
    - hermes_summary
    - miner_alert
    - control_receipt

    Args:
        connection: Validated Hermes connection.
        limit: Maximum number of events to return.

    Returns:
        List of filtered event dictionaries.
    """
    # Over-fetch to account for filtering
    all_events = spine_get_events(limit=limit * 2)

    # Filter to readable event kinds
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]

    # Convert to dicts for JSON serialization
    return [
        {
            "id": e.id,
            "principal_id": e.principal_id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
            "version": e.version
        }
        for e in filtered[:limit]
    ]


def verify_control_denied(connection: HermesConnection) -> bool:
    """
    Verify that Hermes connection cannot perform control actions.

    This is a convenience method for testing and validation.

    Args:
        connection: Hermes connection to verify.

    Returns:
        True if Hermes lacks control capability (correctly denied).
    """
    return 'control' not in connection.capabilities


# Convenience function to validate Hermes auth header
def parse_hermes_auth_header(auth_header: str) -> str:
    """
    Parse Authorization header for Hermes authentication.

    Expected format: "Hermes <hermes_id>"

    Returns:
        The hermes_id from the header.

    Raises:
        HermesTokenError: If header is missing or malformed.
    """
    if not auth_header:
        raise HermesTokenError("Authorization header required")

    parts = auth_header.split(' ', 1)
    if len(parts) != 2 or parts[0] != 'Hermes':
        raise HermesTokenError("Invalid Authorization format. Expected: 'Hermes <hermes_id>'")

    return parts[1]


if __name__ == '__main__':
    # Self-test
    print("Hermes Adapter Module")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {[e.value for e in HERMES_READABLE_EVENTS]}")
    print(f"Blocked events: {[e.value for e in HERMES_BLOCKED_EVENTS]}")
    print()
    print("Module loaded successfully.")
