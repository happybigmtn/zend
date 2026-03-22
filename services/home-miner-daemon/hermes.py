#!/usr/bin/env python3
"""
Hermes Adapter - Capability-scoped interface for the Hermes AI agent.

The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

Architecture:
    Hermes Gateway → Hermes Adapter → Event Spine
                      ↑
                      THIS MODULE
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

# These imports are relative to the daemon directory
from spine import EventKind, append_event, get_events, SpineEvent
from store import load_pairings, save_pairings, load_or_create_principal


# Hermes is limited to observe and summarize capabilities
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read (excludes user_message)
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


@dataclass
class HermesConnection:
    """Active Hermes connection state."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str
    token_expires_at: str


@dataclass
class HermesPairing:
    """Hermes pairing record stored in the pairing store."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]  # ['observe', 'summarize']
    paired_at: str
    token: str
    token_expires_at: str


def _load_hermes_pairings() -> dict:
    """Load Hermes pairings from the store."""
    all_pairings = load_pairings()
    hermes_pairings = {}

    for pairing_id, pairing_data in all_pairings.items():
        # Hermes pairings are marked with a 'hermes_id' field
        if 'hermes_id' in pairing_data:
            hermes_pairings[pairing_data['hermes_id']] = pairing_data

    return hermes_pairings


def _save_hermes_pairing(pairing: HermesPairing):
    """Save Hermes pairing to the store."""
    all_pairings = load_pairings()

    # Store with both pairing_id and hermes_id keys for lookup flexibility
    pairing_dict = asdict(pairing)
    all_pairings[pairing.id] = pairing_dict

    save_pairings(all_pairings)


def _generate_authority_token() -> tuple[str, str]:
    """Generate a new authority token and expiration time.

    Returns:
        tuple: (token, expires_at_iso)
    """
    token = str(uuid.uuid4())
    # Set expiration to 1 hour from now to avoid microsecond edge cases
    from datetime import timedelta
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    return token, expires_at


def _is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    try:
        expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        # Use >= to handle edge case where expires_at == now
        return datetime.now(timezone.utc) >= expires_dt
    except (ValueError, TypeError):
        return True  # Invalid format treated as expired


def connect(authority_token: str) -> HermesConnection:
    """Validate authority token and establish Hermes connection.

    Args:
        authority_token: The authority token issued during Hermes pairing.

    Returns:
        HermesConnection: Active connection state.

    Raises:
        ValueError: If token is invalid, expired, or has wrong capabilities.
    """
    # Find pairing by token
    all_pairings = load_pairings()
    pairing_data = None
    pairing_id = None

    for pid, pdata in all_pairings.items():
        if pdata.get('token') == authority_token and 'hermes_id' in pdata:
            pairing_data = pdata
            pairing_id = pid
            break

    if not pairing_data:
        raise ValueError("HERMES_INVALID_TOKEN: Authority token not found")

    # Check expiration
    if _is_token_expired(pairing_data.get('token_expires_at', '')):
        raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")

    # Verify capabilities are subset of allowed Hermes capabilities
    granted = set(pairing_data.get('capabilities', []))
    allowed = set(HERMES_CAPABILITIES)
    if not granted.issubset(allowed):
        invalid = granted - allowed
        raise ValueError(f"HERMES_INVALID_CAPABILITY: {list(invalid)} not allowed for Hermes")

    return HermesConnection(
        hermes_id=pairing_data['hermes_id'],
        principal_id=pairing_data['principal_id'],
        capabilities=pairing_data['capabilities'],
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=pairing_data['token_expires_at']
    )


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """Create a new Hermes pairing with observe + summarize capabilities.

    This is idempotent - re-pairing the same hermes_id updates the token.

    Args:
        hermes_id: Unique identifier for the Hermes agent.
        device_name: Human-readable name for this Hermes instance.

    Returns:
        HermesPairing: The new or updated pairing record.
    """
    principal = load_or_create_principal()
    all_pairings = load_pairings()

    token, expires = _generate_authority_token()

    # Check for existing Hermes pairing
    existing_pairing_id = None
    for pid, pdata in all_pairings.items():
        if pdata.get('hermes_id') == hermes_id:
            existing_pairing_id = pid
            break

    if existing_pairing_id:
        # Re-pair: update token
        existing = all_pairings[existing_pairing_id]
        existing['token'] = token
        existing['token_expires_at'] = expires
        existing['device_name'] = device_name
        pairing = HermesPairing(
            hermes_id=existing['hermes_id'],
            principal_id=existing['principal_id'],
            device_name=existing['device_name'],
            capabilities=existing['capabilities'],
            paired_at=existing['paired_at'],
            token=token,
            token_expires_at=expires
        )
        all_pairings[existing_pairing_id] = asdict(pairing)
    else:
        # New pairing
        pairing = HermesPairing(
            hermes_id=hermes_id,
            principal_id=principal.id,
            device_name=device_name,
            capabilities=HERMES_CAPABILITIES,  # Always observe + summarize
            paired_at=datetime.now(timezone.utc).isoformat(),
            token=token,
            token_expires_at=expires
        )
        all_pairings[pairing.hermes_id] = asdict(pairing)

    save_pairings(all_pairings)

    # Append pairing event to spine
    append_event(
        EventKind.PAIRING_GRANTED,
        principal.id,
        {
            "device_name": device_name,
            "device_type": "hermes",
            "granted_capabilities": HERMES_CAPABILITIES
        }
    )

    return pairing


def read_status(connection: HermesConnection) -> dict:
    """Read miner status through adapter. Requires observe capability.

    Args:
        connection: Active Hermes connection.

    Returns:
        dict: Miner status snapshot.

    Raises:
        PermissionError: If observe capability is not granted.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required for read_status")

    # Import here to avoid circular dependency at module load
    from daemon import miner

    return miner.get_snapshot()


def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent:
    """Append a Hermes summary to the event spine. Requires summarize capability.

    Args:
        connection: Active Hermes connection.
        summary_text: The summary content generated by Hermes.
        authority_scope: The scope of this summary (e.g., 'observe', 'observe+summarize').

    Returns:
        SpineEvent: The appended event.

    Raises:
        PermissionError: If summarize capability is not granted.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required for append_summary")

    event = append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id
        }
    )

    return event


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]:
    """Return events Hermes is allowed to see. Filters out user_message.

    Args:
        connection: Active Hermes connection.
        limit: Maximum number of events to return.

    Returns:
        List[SpineEvent]: Filtered events visible to Hermes.
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)

    # Filter to allowed event kinds
    allowed_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in allowed_kinds]

    # Strip sensitive payload fields
    for event in filtered:
        event.payload = _strip_sensitive_fields(event.payload, event.kind)

    return filtered[:limit]


def _strip_sensitive_fields(payload: dict, event_kind: str) -> dict:
    """Strip fields from payload that Hermes shouldn't see.

    Args:
        payload: Original event payload.
        event_kind: The kind of event.

    Returns:
        dict: Payload with sensitive fields removed.
    """
    # Start with a copy
    stripped = dict(payload)

    # Remove fields based on event kind
    sensitive_fields = {
        EventKind.PAIRING_GRANTED.value: ['token', 'secret'],
        EventKind.CONTROL_RECEIPT.value: ['receipt_id'],  # Keep command/status but not IDs
        EventKind.USER_MESSAGE.value: ['content', 'sender'],  # Hermes shouldn't see user messages
    }

    for kind, fields in sensitive_fields.items():
        if event_kind == kind:
            for field in fields:
                stripped.pop(field, None)

    return stripped


def verify_authority(connection: HermesConnection, required_capability: str) -> bool:
    """Verify that a connection has a specific capability.

    Args:
        connection: Active Hermes connection.
        required_capability: The capability to check for.

    Returns:
        bool: True if the capability is granted.
    """
    return required_capability in connection.capabilities


def check_control_attempt(hermes_id: str) -> dict:
    """Check and log a control attempt from Hermes (which should be rejected).

    This is called when Hermes attempts to use a control endpoint.
    The adapter logs the attempt but always rejects it.

    Args:
        hermes_id: The Hermes ID attempting control.

    Returns:
        dict: Rejection response with reason.
    """
    return {
        "authorized": False,
        "error": "HERMES_UNAUTHORIZED",
        "message": "Hermes agent does not have control capability",
        "hermes_id": hermes_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
