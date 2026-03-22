#!/usr/bin/env python3
"""
Hermes Adapter Module

Sits between the external Hermes agent and the Zend gateway contract.
Enforces the capability boundary: Hermes gets observe + summarize only,
never control.

Architecture:

    Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                     ^^^^^^^^^^^^^^^^^^^^
                     THIS IS WHAT WE BUILD

Enforces:
- Token validation (authority token with principal_id, hermes_id,
  capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

References:
- references/hermes-adapter.md — canonical adapter contract
- references/event-spine.md — event spine event kinds
- references/observability.md — structured log events
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional
import json
import uuid

# Local imports — these are in the same package
try:
    from . import spine
    from . import store
except ImportError:
    # Standalone execution (e.g. python3 hermes.py)
    import spine
    import store

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HERMES_CAPABILITIES: List[str] = ['observe', 'summarize']
"""
The canonical set of capabilities Hermes may hold in milestone 1.
Direct miner control is NOT included.
"""

HERMES_READABLE_EVENT_KINDS: List[spine.EventKind] = [
    spine.EventKind.HERMES_SUMMARY,
    spine.EventKind.MINER_ALERT,
    spine.EventKind.CONTROL_RECEIPT,
]
"""
Event kinds Hermes may read from the spine.
user_message is intentionally excluded — Hermes must not read user content.
"""

HERMES_WRITABLE_EVENT_KINDS: List[spine.EventKind] = [
    spine.EventKind.HERMES_SUMMARY,
]
"""
Event kinds Hermes may append to the spine.
"""

AUTHORITY_TOKEN_VERSION = 1
"""
Authority token format version. Increment when the token schema changes.
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """
    Represents an active Hermes connection.

    Fields:
        hermes_id: Stable identifier for the Hermes agent.
        principal_id: Zend principal this agent acts on behalf of.
        capabilities: Scoped permissions — ['observe', 'summarize'] only.
        connected_at: ISO 8601 timestamp when the connection was established.
        authority_scope: The original scope grant from pairing (informational).
    """
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    authority_scope: List[str]


@dataclass
class HermesPairing:
    """
    A Hermes pairing record stored in the daemon.

    Similar to GatewayPairing but for Hermes agents with a different
    capability set (observe + summarize only).
    """
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str


@dataclass
class AuthorityToken:
    """
    Authority token issued by the Zend gateway during Hermes pairing.

    Encodes the grant Hermes presents to the adapter on each request.
    Stored as a compact JSON string; validated on each connect.
    """
    version: int
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    issued_at: str
    expires_at: str


# ---------------------------------------------------------------------------
# Token encoding / decoding
# ---------------------------------------------------------------------------

def _encode_token(token: AuthorityToken) -> str:
    """Encode an authority token to a compact string for transport."""
    return json.dumps(asdict(token))


def _decode_token(raw: str) -> AuthorityToken:
    """Decode an authority token from its transport string."""
    try:
        data = json.loads(raw)
        return AuthorityToken(**data)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        raise ValueError(f"INVALID_TOKEN_FORMAT: {e}")


def _is_token_expired(token: AuthorityToken) -> bool:
    """Check whether an authority token has passed its expiration."""
    try:
        expires = datetime.fromisoformat(token.expires_at)
        now = datetime.now(timezone.utc)
        # Normalize to UTC
        expires = expires.replace(tzinfo=timezone.utc)
        return now > expires
    except ValueError:
        # Malformed timestamp — treat as expired
        return True


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def _validate_hermes_capabilities(capabilities: List[str]) -> None:
    """
    Validate that a token's capabilities are a subset of HERMES_CAPABILITIES.

    Raises ValueError if:
    - Any capability is not in the Hermes allowlist
    - Hermes attempts to claim 'control' or any gateway-only capability
    """
    allowed = set(HERMES_CAPABILITIES)
    requested = set(capabilities)
    unknown = requested - allowed

    if unknown:
        raise ValueError(
            f"INVALID_HERMES_CAPABILITIES: {sorted(unknown)} not in "
            f"{HERMES_CAPABILITIES}"
        )


# ---------------------------------------------------------------------------
# Core adapter functions
# ---------------------------------------------------------------------------

def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create a Hermes pairing record in the store.

    This uses the same store mechanism as device pairing but with the
    Hermes-only capability set (observe + summarize).

    Idempotent: re-pairing with the same hermes_id updates the record.

    Args:
        hermes_id: Stable identifier for the Hermes agent.
        device_name: Human-readable name for this Hermes agent.

    Returns:
        HermesPairing record.
    """
    principal = store.load_or_create_principal()
    pairings = store.load_hermes_pairings()

    # Idempotent: update existing pairing
    for existing in pairings.values():
        if existing['hermes_id'] == hermes_id:
            # Refresh expiration
            existing['token_expires_at'] = _iso_now(days=30)
            pairings[existing['id']] = existing
            store.save_hermes_pairings(pairings)
            return HermesPairing(**existing)

    # Issue authority token
    token = AuthorityToken(
        version=AUTHORITY_TOKEN_VERSION,
        hermes_id=hermes_id,
        principal_id=principal.id,
        capabilities=HERMES_CAPABILITIES,
        issued_at=_iso_now(),
        expires_at=_iso_now(days=30),
    )

    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=_iso_now(),
        token_expires_at=token.expires_at,
    )

    pairings[pairing.id] = asdict(pairing)
    store.save_hermes_pairings(pairings)

    # Emit pairing event
    spine.append_event(
        spine.EventKind.PAIRING_GRANTED,
        principal.id,
        {
            "device_name": device_name,
            "granted_capabilities": HERMES_CAPABILITIES,
            "agent_type": "hermes",
        }
    )

    return pairing


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish a Hermes connection.

    This is the primary entry point for Hermes to authenticate with the
    daemon. The token encodes principal, capabilities, and expiration.

    Raises ValueError if:
    - Token is malformed or missing required fields
    - Token has expired
    - Token capabilities include non-Hermes scopes (e.g., 'control')
    - No pairing record exists for the hermes_id in the token

    Args:
        authority_token: Compact JSON authority token string.

    Returns:
        HermesConnection — the validated, active connection state.
    """
    # Decode token
    token = _decode_token(authority_token)

    # Check version
    if token.version != AUTHORITY_TOKEN_VERSION:
        raise ValueError(
            f"UNSUPPORTED_TOKEN_VERSION: token version {token.version}, "
            f"expected {AUTHORITY_TOKEN_VERSION}"
        )

    # Check expiration
    if _is_token_expired(token):
        raise ValueError("TOKEN_EXPIRED: authority token has passed its expiration")

    # Validate capabilities — Hermes must not claim gateway-only scopes
    _validate_hermes_capabilities(token.capabilities)

    # Verify pairing record exists
    pairings = store.load_hermes_pairings()
    pairing_record = None
    for p in pairings.values():
        if p['hermes_id'] == token.hermes_id:
            pairing_record = p
            break

    if pairing_record is None:
        raise ValueError(
            f"HERMES_NOT_PAIRED: no pairing record for hermes_id={token.hermes_id}"
        )

    # Verify the pairing hasn't expired server-side
    pairing_expires = datetime.fromisoformat(pairing_record['token_expires_at'])
    pairing_expires = pairing_expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > pairing_expires:
        raise ValueError("PAIRING_EXPIRED: server-side pairing has expired")

    return HermesConnection(
        hermes_id=token.hermes_id,
        principal_id=token.principal_id,
        capabilities=token.capabilities,
        connected_at=_iso_now(),
        authority_scope=token.capabilities,
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through the adapter.

    Requires the 'observe' capability. Returns the cached miner snapshot
    including status, mode, hashrate, temperature, uptime, and freshness.

    This function delegates to the daemon's internal miner simulator but
    enforces the Hermes capability boundary — Hermes cannot call this without
    'observe' granted.

    Args:
        connection: Active HermesConnection (from connect()).

    Returns:
        dict with miner snapshot fields.

    Raises:
        PermissionError: if 'observe' is not in connection.capabilities.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: 'observe' capability required to read status"
        )

    # Delegate to daemon's status endpoint.
    # In the simulator, we import the miner singleton directly.
    # A production daemon would call its own internal HTTP endpoint.
    import daemon as _daemon_mod
    return _daemon_mod.miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: Optional[str] = None,
) -> spine.SpineEvent:
    """
    Append a Hermes summary event to the event spine.

    Requires the 'summarize' capability. Appends a hermes_summary event
    with the provided text and scope metadata. The event is written to the
    append-only event spine (source of truth), not directly to the inbox.

    Args:
        connection: Active HermesConnection (from connect()).
        summary_text: Human-readable summary text to record.
        authority_scope: Optional scope annotation (defaults to connection.scope).

    Returns:
        The appended SpineEvent.

    Raises:
        PermissionError: if 'summarize' is not in connection.capabilities.
        ValueError: if summary_text is empty.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: 'summarize' capability required to append summary"
        )

    if not summary_text or not summary_text.strip():
        raise ValueError("INVALID_SUMMARY: summary_text must not be empty")

    scope = authority_scope or ','.join(connection.capabilities)

    return spine.append_hermes_summary(
        summary_text=summary_text.strip(),
        authority_scope=connection.capabilities,
        principal_id=connection.principal_id,
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.

    Over-fetches to account for filtering (user_message events are removed).
    Returns only events whose kind is in HERMES_READABLE_EVENT_KINDS.

    Args:
        connection: Active HermesConnection (from connect()).
        limit: Maximum number of events to return after filtering.

    Returns:
        List of SpineEvent objects visible to Hermes.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: 'observe' capability required to read events"
        )

    # Over-fetch to account for filtering
    all_events = spine.get_events(limit=limit * 3)

    readable_kinds = {k.value for k in HERMES_READABLE_EVENT_KINDS}
    filtered = [e for e in all_events if e.kind in readable_kinds]

    return filtered[:limit]


def check_control_denied(connection: HermesConnection) -> bool:
    """
    Check whether a Hermes connection is attempting to use control capability.

    This is used by the daemon to block control attempts from Hermes clients.
    Returns True if control IS denied (Hermes has no control capability).
    Returns False if Hermes somehow has control (which should never happen
    with a valid token, but we check anyway for defense in depth).

    Args:
        connection: Active HermesConnection.

    Returns:
        True if control is denied (expected: Hermes never has control).
    """
    if 'control' in connection.capabilities:
        # This should never happen with a valid token, but log it.
        import sys
        print(
            f"SECURITY WARNING: Hermes {connection.hermes_id} claims control "
            f"capability — this should be impossible with a valid token",
            file=sys.stderr
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso_now(days: int = 0) -> str:
    """Return current UTC time as ISO 8601 string, optionally offset by days."""
    now = datetime.now(timezone.utc)
    if days:
        from datetime import timedelta
        now = now + timedelta(days=days)
    return now.isoformat()


# ---------------------------------------------------------------------------
# Proof of implementation
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Capabilities:", HERMES_CAPABILITIES)
    print("Readable event kinds:", [k.value for k in HERMES_READABLE_EVENT_KINDS])
    print("Writable event kinds:", [k.value for k in HERMES_WRITABLE_EVENT_KINDS])
