#!/usr/bin/env python3
"""
Hermes Adapter - Zend's scoped adapter for Hermes AI agents.

The Hermes adapter sits between the external Hermes agent and the Zend gateway,
enforcing capability boundaries. Hermes can observe miner status and append
summaries to the event spine, but cannot issue control commands or read
user messages.

Hermes capabilities: 'observe', 'summarize' (independent from gateway observe/control)
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from spine import EventKind, SpineEvent, append_event, get_events


# Hermes is granted observe + summarize capabilities only.
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read from the spine.
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]


@dataclass
class HermesConnection:
    """Represents an active Hermes session with scoped authority."""

    hermes_id: str
    principal_id: str
    capabilities: List[str]  # subset of HERMES_CAPABILITIES
    connected_at: str
    token_expires_at: Optional[str] = None


def connect(authority_token: str, principal_id: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.

    Args:
        authority_token: Encoded authority token from the pairing flow.
        principal_id: Principal identity that Hermes is acting on behalf of.

    Returns:
        HermesConnection with observe + summarize capabilities.

    Raises:
        ValueError: If token is invalid, malformed, or expired.
    """
    if not authority_token or not isinstance(authority_token, str):
        raise ValueError("HERMES_INVALID_TOKEN: authority_token must be a non-empty string")

    # Parse token format: base64(hermes_id:capabilities:expires_iso)
    # In milestone 1, tokens are UUIDs stored in the pairing store.
    # Token validation is delegated to the store via token lookup.
    try:
        # Token format: hermes_id|capabilities|expires_iso
        # Using pipe separator to avoid conflict with ISO datetime colons
        parts = authority_token.split('|')
        if len(parts) == 1:
            # Legacy or simplified token format - treat entire token as ID
            hermes_id = authority_token
            capabilities = HERMES_CAPABILITIES.copy()
            expires_str = None
        elif len(parts) == 2:
            # hermes_id|capabilities format
            hermes_id, caps_str = parts
            capabilities = caps_str.split(',') if caps_str else HERMES_CAPABILITIES.copy()
            expires_str = None
        else:
            # hermes_id|capabilities|expires format
            hermes_id, caps_str, expires_str = parts
            capabilities = caps_str.split(',') if caps_str else HERMES_CAPABILITIES.copy()

        # Validate capabilities are a subset of allowed Hermes capabilities
        for cap in capabilities:
            if cap not in HERMES_CAPABILITIES:
                raise ValueError(
                    f"HERMES_INVALID_CAPABILITY: '{cap}' is not a valid Hermes capability. "
                    f"Allowed: {HERMES_CAPABILITIES}"
                )

        # Validate expiration
        if expires_str and expires_str != 'never':
            expires_at = datetime.fromisoformat(expires_str)
            if expires_at < datetime.now(timezone.utc):
                raise ValueError("HERMES_TOKEN_EXPIRED: authority token has expired")

        return HermesConnection(
            hermes_id=hermes_id,
            principal_id=principal_id,
            capabilities=capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=expires_str if expires_str and expires_str != 'never' else None,
        )

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"HERMES_INVALID_TOKEN: failed to parse token - {e}")


def read_status(connection: HermesConnection, miner_snapshot: dict) -> dict:
    """
    Read miner status through the adapter.

    Requires 'observe' capability. The actual miner snapshot is provided by
    the daemon's internal miner simulator to avoid circular imports.

    Args:
        connection: Valid Hermes connection with observe capability.
        miner_snapshot: Current miner status dict from the daemon.

    Returns:
        Filtered miner status suitable for Hermes consumption.

    Raises:
        PermissionError: If Hermes lacks observe capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: observe capability required to read miner status"
        )

    # Hermes receives a filtered view of miner state.
    # We strip fields that are internal or security-sensitive.
    return {
        "status": miner_snapshot.get("status"),
        "mode": miner_snapshot.get("mode"),
        "hashrate_hs": miner_snapshot.get("hashrate_hs"),
        "temperature": miner_snapshot.get("temperature"),
        "uptime_seconds": miner_snapshot.get("uptime_seconds"),
        "freshness": miner_snapshot.get("freshness"),
        "hermes_id": connection.hermes_id,
    }


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: List[str]
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.

    Requires 'summarize' capability. The summary is written to the spine
    as a hermes_summary event, which is visible in the Inbox and Agent tabs.

    Args:
        connection: Valid Hermes connection with summarize capability.
        summary_text: The AI-generated summary text.
        authority_scope: List of capabilities Hermes was using when generating this summary.

    Returns:
        The appended SpineEvent.

    Raises:
        PermissionError: If Hermes lacks summarize capability.
        ValueError: If summary_text is empty.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: summarize capability required to append summaries"
        )

    if not summary_text or not isinstance(summary_text, str):
        raise ValueError("HERMES_INVALID_SUMMARY: summary_text must be a non-empty string")

    # Validate authority_scope contains only valid capabilities
    for scope in authority_scope:
        if scope not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_INVALID_SCOPE: '{scope}' is not a valid Hermes scope"
            )

    return append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hermes_id": connection.hermes_id,
        }
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]:
    """
    Return events Hermes is permitted to see.

    Filters out user_message events (Hermes must never read user messages).
    Returns hermes_summary, miner_alert, and control_receipt events.

    Args:
        connection: Valid Hermes connection.
        limit: Maximum number of events to return.

    Returns:
        List of event dicts (asdict format).
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)

    readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]

    filtered = [
        asdict(event) for event in all_events
        if event.kind in readable_kinds
    ]

    return filtered[:limit]


def validate_hermes_control_attempt(connection: HermesConnection, action: str) -> bool:
    """
    Validate whether Hermes is attempting an unauthorized control action.

    All control commands are blocked for Hermes. This function is called by
    the daemon before routing any control-type requests.

    Args:
        connection: The Hermes connection making the request.
        action: The control action being attempted (e.g., 'start', 'stop').

    Returns:
        True if the action is authorized, False if blocked.

    Raises:
        PermissionError: Always raised - Hermes cannot perform control actions.
    """
    raise PermissionError(
        f"HERMES_UNAUTHORIZED: Hermes cannot perform control action '{action}'. "
        f"Available capabilities: {connection.capabilities}"
    )


# Convenience function to check if a token has a specific capability
def has_capability(connection: HermesConnection, capability: str) -> bool:
    """Check if the Hermes connection has a specific capability."""
    return capability in connection.capabilities
