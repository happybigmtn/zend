#!/usr/bin/env python3
"""
Hermes Adapter Module

Implements the Zend Hermes adapter that provides Hermes AI agents with
a capability-scoped interface to the Zend home miner daemon.

Hermes can:
- Observe miner status (read-only)
- Append summaries to the event spine

Hermes CANNOT:
- Issue control commands (start, stop, set_mode)
- Read user_message events
- Access gateway control capabilities

Architecture:
  Hermes Gateway → Hermes Adapter → Gateway Contract → Event Spine
"""

import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

from spine import EventKind, append_event, get_events
from store import load_pairings, save_pairings, load_or_create_principal


# Hermes capability constants
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_CAPABILITY_OBSERVE = 'observe'
HERMES_CAPABILITY_SUMMARIZE = 'summarize'

# Events Hermes is allowed to read (blocks user_message)
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Events Hermes is NOT allowed to read
HERMES_BLOCKED_EVENTS = [
    EventKind.USER_MESSAGE,
]


@dataclass
class HermesConnection:
    """Represents an active Hermes connection session."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str

    def has_capability(self, capability: str) -> bool:
        """Check if connection has a specific capability."""
        return capability in self.capabilities

    def can_observe(self) -> bool:
        """Check if connection can observe miner status."""
        return self.has_capability(HERMES_CAPABILITY_OBSERVE)

    def can_summarize(self) -> bool:
        """Check if connection can append summaries."""
        return self.has_capability(HERMES_CAPABILITY_SUMMARIZE)

    def to_dict(self) -> dict:
        """Serialize connection state for API responses."""
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at,
        }


class HermesAuthError(ValueError):
    """Raised when Hermes authentication fails."""
    pass


class HermesCapabilityError(PermissionError):
    """Raised when Hermes lacks required capability."""
    pass


def _validate_hermes_id(hermes_id: str) -> bool:
    """Validate hermes_id format."""
    if not hermes_id or len(hermes_id) < 3:
        return False
    # Basic format check: alphanumeric with hyphens allowed
    return all(c.isalnum() or c in '-_' for c in hermes_id)


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.

    The authority token is expected to be a JSON payload containing:
    - hermes_id: The Hermes agent identifier
    - principal_id: The Zend principal this Hermes is acting on behalf of
    - capabilities: List of granted capabilities (should be subset of HERMES_CAPABILITIES)
    - expires_at: ISO timestamp of token expiration

    Args:
        authority_token: Base64-encoded JSON authority token from Hermes

    Returns:
        HermesConnection instance for the established session

    Raises:
        HermesAuthError: If token is invalid, expired, or has wrong capabilities
    """
    import json
    import base64

    if not authority_token:
        raise HermesAuthError("HERMES_AUTH_FAILED: empty authority token")

    try:
        # Decode authority token (Base64-encoded JSON)
        token_data = json.loads(base64.b64decode(authority_token).decode('utf-8'))
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        raise HermesAuthError("HERMES_AUTH_FAILED: invalid token encoding")

    # Extract and validate fields
    hermes_id = token_data.get('hermes_id')
    principal_id = token_data.get('principal_id')
    capabilities = token_data.get('capabilities', [])
    expires_at = token_data.get('expires_at')

    if not hermes_id:
        raise HermesAuthError("HERMES_AUTH_FAILED: missing hermes_id")
    if not principal_id:
        raise HermesAuthError("HERMES_AUTH_FAILED: missing principal_id")
    if not _validate_hermes_id(hermes_id):
        raise HermesAuthError("HERMES_AUTH_FAILED: invalid hermes_id format")

    # Validate capabilities (must be subset of HERMES_CAPABILITIES)
    invalid_caps = set(capabilities) - set(HERMES_CAPABILITIES)
    if invalid_caps:
        raise HermesAuthError(f"HERMES_AUTH_FAILED: invalid capabilities: {invalid_caps}")

    # Validate required capabilities are present
    if not capabilities:
        raise HermesAuthError("HERMES_AUTH_FAILED: no capabilities granted")

    # Check expiration
    if expires_at:
        try:
            expiry_str = expires_at.replace('Z', '+00:00')
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now(timezone.utc) > expiry:
                raise HermesAuthError("HERMES_AUTH_FAILED: authority token expired")
        except HermesAuthError:
            raise  # Re-raise HermesAuthError
        except ValueError:
            raise HermesAuthError("HERMES_AUTH_FAILED: invalid expires_at format")

    # Create connection
    connection = HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
    )

    return connection


def pair_hermes(hermes_id: str, device_name: str = None) -> dict:
    """
    Create or update a Hermes pairing record.

    Hermes pairing is idempotent - re-pairing with same hermes_id updates the record.

    Args:
        hermes_id: The Hermes agent identifier
        device_name: Optional friendly name for the Hermes agent

    Returns:
        dict with pairing details
    """
    if not _validate_hermes_id(hermes_id):
        raise ValueError(f"Invalid hermes_id format: {hermes_id}")

    principal = load_or_create_principal()
    pairings = load_pairings()

    # Generate token and expiration
    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc).isoformat()

    # Create or update pairing record
    pairing_record = {
        "id": str(uuid.uuid4()),
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "device_name": device_name or f"hermes-{hermes_id}",
        "capabilities": HERMES_CAPABILITIES.copy(),
        "paired_at": datetime.now(timezone.utc).isoformat(),
        "token_expires_at": expires_at,
        "token_used": False,
    }

    # Store by hermes_id for easy lookup
    pairings[f"hermes:{hermes_id}"] = pairing_record
    save_pairings(pairings)

    # Return authority token for the new pairing
    import base64
    import json
    token_payload = {
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "capabilities": HERMES_CAPABILITIES,
        "expires_at": expires_at,
    }
    authority_token = base64.b64encode(json.dumps(token_payload).encode()).decode()

    return {
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "capabilities": HERMES_CAPABILITIES,
        "paired_at": pairing_record["paired_at"],
        "authority_token": authority_token,
    }


def get_hermes_pairing(hermes_id: str) -> Optional[dict]:
    """Get Hermes pairing record by hermes_id."""
    pairings = load_pairings()
    key = f"hermes:{hermes_id}"
    return pairings.get(key)


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter. Requires observe capability.

    Args:
        connection: Active HermesConnection

    Returns:
        dict with miner status snapshot

    Raises:
        HermesCapabilityError: If observe capability is not granted
    """
    if not connection.can_observe():
        raise HermesCapabilityError("HERMES_UNAUTHORIZED: observe capability required")

    # Import here to avoid circular dependency
    from daemon import miner

    # Get status snapshot from miner simulator
    snapshot = miner.get_snapshot()

    return {
        "status": snapshot.get("status"),
        "mode": snapshot.get("mode"),
        "hashrate_hs": snapshot.get("hashrate_hs"),
        "temperature": snapshot.get("temperature"),
        "uptime_seconds": snapshot.get("uptime_seconds"),
        "freshness": snapshot.get("freshness"),
        "observed_by": connection.hermes_id,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: List[str]) -> dict:
    """
    Append a Hermes summary to the event spine. Requires summarize capability.

    Args:
        connection: Active HermesConnection
        summary_text: The summary content to append
        authority_scope: List of scopes used to generate this summary (e.g., ['observe'])

    Returns:
        dict with event details

    Raises:
        HermesCapabilityError: If summarize capability is not granted
    """
    if not connection.can_summarize():
        raise HermesCapabilityError("HERMES_UNAUTHORIZED: summarize capability required")

    if not summary_text or len(summary_text.strip()) == 0:
        raise ValueError("summary_text cannot be empty")

    # Append to event spine
    event = append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text.strip(),
            "authority_scope": authority_scope,
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


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]:
    """
    Return events Hermes is allowed to see. Filters out user_message and other blocked events.

    Args:
        connection: Active HermesConnection
        limit: Maximum number of events to return

    Returns:
        List of event dicts that Hermes can access
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)

    # Filter to only Hermes-readable events
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]

    # Return most recent first, limited
    filtered.reverse()
    return [
        {
            "id": e.id,
            "kind": e.kind,
            "payload": e.payload,
            "created_at": e.created_at,
        }
        for e in filtered[:limit]
    ]


def verify_control_attempt(connection: HermesConnection) -> bool:
    """
    Verify that a control attempt should be blocked.

    This is used by the daemon to reject control commands from Hermes.

    Args:
        connection: HermesConnection attempting the operation

    Returns:
        True if control is allowed, raises HermesCapabilityError if not
    """
    # Hermes should NEVER have control capability
    if connection.has_capability('control'):
        # Log security event - this shouldn't happen
        import logging
        logging.warning(
            f"SECURITY: Hermes {connection.hermes_id} attempted to use control capability"
        )
        raise HermesCapabilityError(
            "HERMES_UNAUTHORIZED: Hermes agents cannot have control capability"
        )

    # Control is not allowed
    raise HermesCapabilityError(
        "HERMES_UNAUTHORIZED: Hermes agents cannot issue control commands"
    )


def get_capabilities() -> dict:
    """Return Hermes adapter capability manifest."""
    return {
        "adapter": "hermes",
        "version": "1.0.0",
        "capabilities": HERMES_CAPABILITIES,
        "readable_events": [e.value for e in HERMES_READABLE_EVENTS],
        "blocked_events": [e.value for e in HERMES_BLOCKED_EVENTS],
    }
