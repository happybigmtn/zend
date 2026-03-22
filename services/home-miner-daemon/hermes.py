#!/usr/bin/env python3
"""
Hermes Adapter - Capability-scoped adapter for Hermes AI agents.

The Hermes adapter sits between external Hermes agents and the Zend gateway contract,
enforcing a strict capability boundary:
- Hermes can observe miner status and read filtered events
- Hermes can append summaries to the event spine
- Hermes CANNOT issue control commands or read user messages

This module is intentionally scoped to Hermes capabilities (observe + summarize)
which are independent from the gateway's observe + control.
"""

import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

from spine import EventKind, append_event, get_events, SpineEvent, append_hermes_summary
from store import load_or_create_principal, load_pairings, save_pairings


# Hermes capability set (independent from gateway capabilities)
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read
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
            "status": "connected"
        }


@dataclass
class HermesPairing:
    """Hermes pairing record with Hermes-specific capabilities."""
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


def _is_token_expired(expires_at: str) -> bool:
    """Check if a token has expired."""
    try:
        expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expires
    except (ValueError, AttributeError):
        return True


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.

    The authority token encodes:
    - hermes_id: The Hermes agent's identifier
    - principal_id: The user's principal
    - capabilities: Granted capabilities (observe + summarize)
    - expires_at: Token expiration time

    Raises:
        ValueError: If token is invalid or expired
        PermissionError: If token lacks Hermes capabilities
    """
    if not authority_token:
        raise ValueError("HERMES_INVALID: authority token is required")

    # Parse token (format: hermes_id:principal_id:capabilities:expires_at encoded as UUID-like)
    # For milestone 1, we use a simplified token format
    # In production, this would be a signed JWT or similar
    try:
        # Token format: hermes_id|principal_id|capabilities|expires_at
        parts = authority_token.split('|')
        if len(parts) != 4:
            raise ValueError("HERMES_INVALID: malformed authority token")

        hermes_id, principal_id, caps_str, expires_at = parts
        capabilities = caps_str.split(',')

        # Validate expiration
        if _is_token_expired(expires_at):
            raise ValueError("HERMES_EXPIRED: authority token has expired")

        # Validate capabilities contain Hermes scope
        missing = set(HERMES_CAPABILITIES) - set(capabilities)
        if missing:
            raise PermissionError(
                f"HERMES_UNAUTHORIZED: missing capabilities {list(missing)}"
            )

        # Validate no control capability (Hermes should never have gateway control)
        if 'control' in capabilities:
            raise PermissionError(
                "HERMES_UNAUTHORIZED: Hermes cannot have control capability"
            )

        return HermesConnection(
            hermes_id=hermes_id,
            principal_id=principal_id,
            capabilities=capabilities,
            connected_at=datetime.now(timezone.utc).isoformat()
        )

    except ValueError as e:
        # Re-raise with context
        raise ValueError(f"HERMES_INVALID: {str(e)}")


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.

    Requires 'observe' capability. Delegates to the daemon's internal status.

    Raises:
        PermissionError: If Hermes lacks observe capability
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

    # Import here to avoid circular dependency
    from daemon import miner

    snapshot = miner.get_snapshot()
    return {
        "source": "hermes_adapter",
        "hermes_id": connection.hermes_id,
        **snapshot
    }


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.

    Requires 'summarize' capability. Creates a hermes_summary event.

    Args:
        connection: Active Hermes connection
        summary_text: The summary content
        authority_scope: The scope of this summary (e.g., 'observe')

    Returns:
        The created SpineEvent

    Raises:
        PermissionError: If Hermes lacks summarize capability
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")

    if not summary_text:
        raise ValueError("HERMES_INVALID: summary_text is required")

    event = append_hermes_summary(
        summary_text=summary_text,
        authority_scope=[authority_scope] if authority_scope else ['observe'],
        principal_id=connection.principal_id
    )

    return event


def get_filtered_events(
    connection: HermesConnection,
    limit: int = 20
) -> List[SpineEvent]:
    """
    Return events Hermes is allowed to see.

    This filters out user_message events and other unauthorized content.
    Hermes can only see: hermes_summary, miner_alert, control_receipt

    Args:
        connection: Active Hermes connection
        limit: Maximum events to return

    Returns:
        List of filtered SpineEvents
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)

    # Filter to Hermes-readable event kinds
    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]

    return filtered[:limit]


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create or update a Hermes pairing record.

    Hermes pairings use observe + summarize capabilities by default.
    This is idempotent: same hermes_id re-pairs with updated timestamp.

    Args:
        hermes_id: Unique Hermes agent identifier
        device_name: Human-readable name for the agent

    Returns:
        The HermesPairing record
    """
    principal = load_or_create_principal()
    pairings = load_pairings()

    # Find existing Hermes pairing or create new
    pairing_key = None
    for key, pairing in pairings.items():
        if pairing.get('hermes_id') == hermes_id:
            pairing_key = key
            break

    now = datetime.now(timezone.utc)
    expires = datetime(
        now.year + 1, now.month, now.day, now.hour, now.minute, now.second,
        tzinfo=timezone.utc
    ).isoformat()

    pairing_data = {
        "id": pairing_key or str(uuid.uuid4()),
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "device_name": device_name,
        "capabilities": HERMES_CAPABILITIES,
        "paired_at": now.isoformat(),
        "token_expires_at": expires
    }

    pairings[pairing_data["id"]] = pairing_data
    save_pairings(pairings)

    return HermesPairing(**pairing_data)


def generate_hermes_token(hermes_id: str) -> tuple[str, str]:
    """
    Generate an authority token for Hermes.

    Returns:
        Tuple of (token, expires_at)
    """
    principal = load_or_create_principal()
    expires = datetime(
        2027, 12, 31, 23, 59, 59,
        tzinfo=timezone.utc
    ).isoformat()

    # Token format: hermes_id|principal_id|capabilities|expires_at
    capabilities = ','.join(HERMES_CAPABILITIES)
    token = f"{hermes_id}|{principal.id}|{capabilities}|{expires}"

    return token, expires


def get_hermes_status(connection: HermesConnection) -> dict:
    """
    Get Hermes connection status including recent summaries.

    Combines connection info with recent Hermes-specific events.
    """
    recent_events = get_filtered_events(connection, limit=5)

    return {
        "connection": connection.to_dict(),
        "recent_summaries": [
            {
                "id": e.id,
                "summary_text": e.payload.get("summary_text"),
                "generated_at": e.payload.get("generated_at")
            }
            for e in recent_events if e.kind == EventKind.HERMES_SUMMARY.value
        ],
        "capabilities": HERMES_CAPABILITIES,
        "readable_events": [k.value for k in HERMES_READABLE_EVENTS]
    }


# Proof-of-existence for the adapter
if __name__ == '__main__':
    print("Capabilities:", HERMES_CAPABILITIES)
    print("Readable events:", [e.value for e in HERMES_READABLE_EVENTS])
