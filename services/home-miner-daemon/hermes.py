#!/usr/bin/env python3
"""
Hermes Adapter Module

Adapter between external Hermes AI agent and the Zend gateway contract.
Enforces capability boundaries: Hermes can observe and summarize, but cannot control.

The adapter validates authority tokens and filters events before relaying
requests to the event spine.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from spine import (
    append_event,
    append_hermes_summary,
    get_events,
    EventKind,
    SpineEvent,
)
from store import (
    get_pairing_by_device,
    list_devices,
    load_pairings,
    save_pairings,
    load_or_create_principal,
)

# Hermes capabilities - observe and summarize only, no control
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read from the spine
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


@dataclass
class HermesConnection:
    """Active Hermes connection with validated authority."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    token_expires_at: str


@dataclass
class HermesPairing:
    """Hermes pairing record in the store."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


def _is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    try:
        expires = datetime.fromisoformat(expires_at)
        return datetime.now(timezone.utc) > expires
    except (ValueError, TypeError):
        return True


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.

    The authority token is a JSON string encoding:
    - hermes_id: the Hermes agent identifier
    - principal_id: the Zend principal
    - capabilities: list of granted capabilities
    - expires_at: ISO timestamp of expiration

    Raises ValueError if token is invalid, expired, or has wrong capabilities.
    """
    try:
        token_data = json.loads(authority_token)
    except json.JSONDecodeError:
        raise ValueError("HERMES_INVALID_TOKEN: Authority token must be valid JSON")

    # Extract token fields
    hermes_id = token_data.get('hermes_id')
    principal_id = token_data.get('principal_id')
    capabilities = token_data.get('capabilities', [])
    expires_at = token_data.get('expires_at', '')

    # Validate required fields
    if not hermes_id:
        raise ValueError("HERMES_INVALID_TOKEN: hermes_id is required")
    if not principal_id:
        raise ValueError("HERMES_INVALID_TOKEN: principal_id is required")

    # Validate capabilities - must be observe and/or summarize only
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_UNAUTHORIZED: Capability '{cap}' not permitted for Hermes. "
                f"Allowed: {HERMES_CAPABILITIES}"
            )

    # Check expiration
    if _is_token_expired(expires_at):
        raise ValueError("HERMES_TOKEN_EXPIRED: Authority token has expired")

    # Validate that a pairing exists for this hermes_id
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        raise ValueError("HERMES_NOT_PAIRED: Hermes agent not registered with gateway")

    # Token must match stored pairing principal
    if pairing.principal_id != principal_id:
        raise ValueError("HERMES_INVALID_TOKEN: Principal ID mismatch")

    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=expires_at,
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.

    Requires 'observe' capability in the connection.
    Returns the current miner snapshot from the daemon.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: observe capability required for read_status"
        )

    # Import here to avoid circular dependency
    from daemon import miner

    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.

    Requires 'summarize' capability in the connection.
    Returns the created SpineEvent.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: summarize capability required for append_summary"
        )

    if not summary_text:
        raise ValueError("HERMES_INVALID: summary_text cannot be empty")

    return append_hermes_summary(
        summary_text=summary_text,
        authority_scope=[authority_scope] if authority_scope else connection.capabilities,
        principal_id=connection.principal_id,
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]:
    """
    Return events Hermes is allowed to see.

    Filters out user_message events. Only returns:
    - hermes_summary
    - miner_alert
    - control_receipt

    Requires 'observe' capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: observe capability required for get_filtered_events"
        )

    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)

    # Filter to readable event kinds
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]

    return filtered[:limit]


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create a Hermes pairing record with observe+summarize capabilities.

    Idempotent: if hermes_id already paired, returns existing pairing.
    """
    pairings = load_pairings()

    # Check for existing pairing (idempotent)
    for existing in pairings.values():
        if existing.get('hermes_id') == hermes_id:
            return HermesPairing(
                hermes_id=existing['hermes_id'],
                principal_id=existing['principal_id'],
                device_name=existing['device_name'],
                capabilities=existing['capabilities'],
                paired_at=existing['paired_at'],
                token_expires_at=existing['token_expires_at'],
            )

    # Create new pairing
    principal = load_or_create_principal()
    token_expires = _get_default_expiration()

    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES.copy(),
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=token_expires,
    )

    # Store with hermes_id as key for easy lookup
    pairings[f"hermes:{hermes_id}"] = {
        "hermes_id": pairing.hermes_id,
        "principal_id": pairing.principal_id,
        "device_name": pairing.device_name,
        "capabilities": pairing.capabilities,
        "paired_at": pairing.paired_at,
        "token_expires_at": pairing.token_expires_at,
    }
    save_pairings(pairings)

    # Append pairing events
    append_event(
        EventKind.PAIRING_REQUESTED,
        principal.id,
        {
            "device_name": device_name,
            "requested_capabilities": HERMES_CAPABILITIES,
            "agent_type": "hermes",
        }
    )
    append_event(
        EventKind.PAIRING_GRANTED,
        principal.id,
        {
            "device_name": device_name,
            "granted_capabilities": HERMES_CAPABILITIES,
            "agent_type": "hermes",
        }
    )

    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing record by hermes_id."""
    pairings = load_pairings()
    key = f"hermes:{hermes_id}"

    if key in pairings:
        data = pairings[key]
        return HermesPairing(
            hermes_id=data['hermes_id'],
            principal_id=data['principal_id'],
            device_name=data['device_name'],
            capabilities=data['capabilities'],
            paired_at=data['paired_at'],
            token_expires_at=data['token_expires_at'],
        )
    return None


def issue_authority_token(hermes_id: str) -> str:
    """
    Issue a new authority token for a paired Hermes agent.

    Returns a JSON string token that can be used to connect.
    """
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        raise ValueError(f"HERMES_NOT_PAIRED: No pairing found for {hermes_id}")

    token_data = {
        "hermes_id": hermes_id,
        "principal_id": pairing.principal_id,
        "capabilities": pairing.capabilities,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": _get_default_expiration(),
    }

    return json.dumps(token_data)


def _get_default_expiration() -> str:
    """Get default token expiration (30 days from now)."""
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()


def list_hermes_pairings() -> List[HermesPairing]:
    """List all Hermes pairings."""
    pairings = load_pairings()
    result = []

    for key, data in pairings.items():
        if key.startswith("hermes:"):
            result.append(HermesPairing(
                hermes_id=data['hermes_id'],
                principal_id=data['principal_id'],
                device_name=data['device_name'],
                capabilities=data['capabilities'],
                paired_at=data['paired_at'],
                token_expires_at=data['token_expires_at'],
            ))

    return result
