#!/usr/bin/env python3
"""
Hermes Adapter — Zend capability boundary for Hermes AI agents.

The adapter enforces:
- Authority token validation (principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only; no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes should not see)

Architecture:
  Hermes Gateway → Hermes Adapter → Zend Gateway → Event Spine
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from spine import EventKind, append_event, get_events
from store import load_pairings, save_pairings


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Hermes is granted observe + summarize only.
HERMES_CAPABILITIES = ["observe", "summarize"]

# Event kinds Hermes may read from the spine.
HERMES_READABLE_EVENTS: list[EventKind] = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Maximum time-to-live for a Hermes authority token (24 hours).
HERMES_TOKEN_TTL_SECONDS = 86400


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """
    Represents an active Hermes session after a successful connect().

    Fields mirror the authority token payload.
    """
    hermes_id: str
    principal_id: str
    capabilities: list[str]  # e.g. ["observe", "summarize"]
    connected_at: str  # ISO 8601
    expires_at: str  # ISO 8601
    token_used: bool = False

    def is_expired(self) -> bool:
        """Check whether the authority token has expired."""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) > expires


@dataclass
class HermesPairing:
    """
    Persistent Hermes pairing record stored alongside device pairings.
    Hermes pairings are separate from device pairings: they use a different
    capability set (observe + summarize) and a different auth header scheme.
    """
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: list[str]
    paired_at: str
    token: str  # one-time pairing token
    token_expires_at: str
    token_used: bool = False

    def to_connection(self) -> HermesConnection:
        """Derive a HermesConnection from the pairing record."""
        return HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.principal_id,
            capabilities=self.capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
            expires_at=self.token_expires_at,
            token_used=self.token_used,
        )


# ---------------------------------------------------------------------------
# Store helpers
# ---------------------------------------------------------------------------

def _state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


_STATE_DIR = os.environ.get("ZEND_STATE_DIR", _state_dir())
os.makedirs(_STATE_DIR, exist_ok=True)

_HERMES_PAIRING_FILE = os.path.join(_STATE_DIR, "hermes-pairing-store.json")


def _load_hermes_pairings() -> dict:
    if os.path.exists(_HERMES_PAIRING_FILE):
        with open(_HERMES_PAIRING_FILE) as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    with open(_HERMES_PAIRING_FILE, "w") as f:
        json.dump(pairings, f, indent=2)


# ---------------------------------------------------------------------------
# Core adapter functions
# ---------------------------------------------------------------------------

def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create (or re-create) a Hermes pairing record with observe + summarize.

    Pairing is idempotent: calling again with the same hermes_id overwrites
    the existing record and issues a fresh token.

    Args:
        hermes_id:  Unique identifier for the Hermes agent.
        device_name: Human-readable label for the agent (e.g. "hermes-agent").

    Returns:
        The created HermesPairing record including the one-time pairing token.

    Raises:
        ValueError: If hermes_id is empty.
    """
    if not hermes_id:
        raise ValueError("hermes_id is required")

    # Load principal — Hermes pairs into the same principal as device clients.
    from store import load_or_create_principal
    principal = load_or_create_principal()

    pairings = _load_hermes_pairings()

    # Remove any prior pairing for this hermes_id (idempotent re-pair).
    pairings = {k: v for k, v in pairings.items()
                 if v.get("hermes_id") != hermes_id}

    now = datetime.now(timezone.utc)
    token = str(uuid.uuid4())
    expires = datetime.fromtimestamp(
        now.timestamp() + HERMES_TOKEN_TTL_SECONDS, tz=timezone.utc
    )

    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=list(HERMES_CAPABILITIES),
        paired_at=now.isoformat(),
        token=token,
        token_expires_at=expires.isoformat(),
        token_used=False,
    )

    pairings[pairing.id] = asdict(pairing)
    _save_hermes_pairings(pairings)

    # Emit a spine event so operators can audit Hermes pairings.
    append_event(
        EventKind.PAIRING_GRANTED,
        principal.id,
        {
            "device_name": device_name,
            "granted_capabilities": HERMES_CAPABILITIES,
            "agent_type": "hermes",
        },
    )

    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Return the pairing record for a Hermes agent, or None."""
    pairings = _load_hermes_pairings()
    for p in pairings.values():
        if p.get("hermes_id") == hermes_id:
            return HermesPairing(**p)
    return None


def connect(authority_token: str) -> HermesConnection:
    """
    Validate an authority token and establish a HermesConnection.

    Authority tokens are issued during Hermes pairing and encode the agent's
    identity, granted capabilities, and expiration time.

    Args:
        authority_token: A JSON-encoded string containing hermes_id,
                         principal_id, capabilities, and expires_at.

    Returns:
        A HermesConnection representing the active session.

    Raises:
        ValueError:  Token is malformed or missing required fields.
        PermissionError: Token is expired, used, or carries an invalid
                         capability set.
    """
    try:
        payload = json.loads(authority_token)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"HERMES_INVALID_TOKEN: malformed token — {exc}") from exc

    required = {"hermes_id", "principal_id", "capabilities", "expires_at"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(
            f"HERMES_INVALID_TOKEN: missing fields {sorted(missing)}"
        )

    hermes_id: str = payload["hermes_id"]
    principal_id: str = payload["principal_id"]
    capabilities: list = payload["capabilities"]
    expires_at: str = payload["expires_at"]

    # Verify Hermes capability subset.
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise PermissionError(
                f"HERMES_UNAUTHORIZED: capability '{cap}' is not permitted "
                f"for Hermes. Allowed: {HERMES_CAPABILITIES}"
            )

    # Verify token has not been used (one-time token).
    if payload.get("token_used"):
        raise PermissionError("HERMES_INVALID_TOKEN: token has already been used")

    # Verify token has not expired.
    try:
        expires_dt = datetime.fromisoformat(expires_at)
        if datetime.now(timezone.utc) > expires_dt:
            raise PermissionError("HERMES_INVALID_TOKEN: token has expired")
    except ValueError as exc:
        raise ValueError(
            f"HERMES_INVALID_TOKEN: invalid expires_at format — {exc}"
        ) from exc

    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=list(capabilities),
        connected_at=datetime.now(timezone.utc).isoformat(),
        expires_at=expires_at,
        token_used=False,
    )


def validate_connection(connection: HermesConnection) -> None:
    """
    Re-validate an active HermesConnection.

    Checks expiration on every request to support long-lived sessions.

    Raises:
        PermissionError: Connection has expired.
    """
    if connection.is_expired():
        raise PermissionError(
            "HERMES_CONNECTION_EXPIRED: please re-connect with a fresh token"
        )


def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.

    Requires the 'observe' capability. Status is obtained from the daemon's
    internal MinerSimulator instance via a direct call (in-process), which
    avoids an HTTP hop.

    Args:
        connection: An active HermesConnection.

    Returns:
        A miner snapshot dict with status, mode, hashrate_hs, etc.

    Raises:
        PermissionError: Connection lacks 'observe' capability or is expired.
    """
    validate_connection(connection)
    if "observe" not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: 'observe' capability required to read status"
        )

    # Import here to avoid circular imports at module load time.
    from daemon import miner

    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str,
) -> dict:
    """
    Append a Hermes summary event to the event spine.

    Requires the 'summarize' capability.

    Args:
        connection:     An active HermesConnection.
        summary_text:   Human-readable summary produced by Hermes.
        authority_scope: The capability under which Hermes generated the
                         summary (e.g. "observe").

    Returns:
        A dict with the appended event id.

    Raises:
        PermissionError: Connection lacks 'summarize' capability or is expired.
    """
    validate_connection(connection)
    if "summarize" not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: 'summarize' capability required to append "
            "summary"
        )

    if not summary_text or not summary_text.strip():
        raise ValueError("summary_text must be non-empty")

    event = append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            "summary_text": summary_text.strip(),
            "authority_scope": authority_scope,
            "hermes_id": connection.hermes_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "appended": True,
        "event_id": event.id,
        "kind": event.kind,
        "created_at": event.created_at,
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events from the spine that Hermes is permitted to read.

    Filters out 'user_message' events entirely, regardless of principal.
    Over-fetches to account for filtering, then truncates to the requested
    limit.

    Args:
        connection: An active HermesConnection.
        limit:      Maximum number of events to return (default 20).

    Returns:
        A list of SpineEvent dicts, most-recent-first, filtered to
        HERMES_READABLE_EVENTS.

    Raises:
        PermissionError: Connection is expired.
    """
    validate_connection(connection)

    all_events = get_events(limit=limit * 3)

    readable_kinds = {k.value for k in HERMES_READABLE_EVENTS}

    filtered = [
        e for e in all_events
        if e.kind in readable_kinds
    ]

    # Strip fields Hermes should not see (none currently, but extensible).
    return [
        {
            "id": e.id,
            "kind": e.kind,
            "payload": _strip_payload(e.kind, e.payload),
            "created_at": e.created_at,
        }
        for e in filtered
    ][:limit]


def _strip_payload(kind: str, payload: dict) -> dict:
    """
    Strip fields from a payload that Hermes should not see.

    Currently returns the payload unchanged; extensible for future fields.
    """
    # Reserved for future payload scrubbing rules.
    return payload


# ---------------------------------------------------------------------------
# Capability-checking decorators (optional helper for daemon endpoints)
# ---------------------------------------------------------------------------

def require_capability(capability: str):
    """Decorator factory: enforce a specific capability on a HermesConnection arg."""
    def decorator(fn):
        def wrapper(connection: HermesConnection, *args, **kwargs):
            validate_connection(connection)
            if capability not in connection.capabilities:
                raise PermissionError(
                    f"HERMES_UNAUTHORIZED: '{capability}' capability required"
                )
            return fn(connection, *args, **kwargs)
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper
    return decorator
