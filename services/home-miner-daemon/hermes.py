#!/usr/bin/env python3
"""
Hermes Adapter Module

Enforces the capability boundary between an external Hermes agent and the Zend
gateway. Hermes can only observe miner status and append summaries — it cannot
issue control commands or read user messages.

The adapter lives in-process with the daemon. It is a capability boundary, not
a deployment boundary.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional
import json
import uuid

from spine import EventKind, append_event, get_events
import store


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HERMES_CAPABILITIES: List[str] = ['observe', 'summarize']
"""Hermes may only receive observe and summarize — never control."""

HERMES_READABLE_EVENTS: List[EventKind] = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
"""Hermes may read its own summaries, miner alerts, and control receipts.
user_message and pairing events are explicitly excluded."""

HERMES_WRITABLE_EVENTS: List[EventKind] = [
    EventKind.HERMES_SUMMARY,
]
"""Hermes may only write hermes_summary to the spine."""

CONTROL_PATHS: List[str] = [
    '/miner/start',
    '/miner/stop',
    '/miner/set_mode',
]
"""HTTP paths that represent control operations. Hermes must be rejected."""


# ---------------------------------------------------------------------------
# Connection State
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """Represents an active Hermes session validated by authority token."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str        # ISO 8601

    def has_capability(self, cap: str) -> bool:
        return cap in self.capabilities


# ---------------------------------------------------------------------------
# Store helpers (Hermes-specific pairing)
# ---------------------------------------------------------------------------

HERMES_PAIRING_FILE = store.STATE_DIR + '/hermes-pairing-store.json'


def _load_hermes_pairings() -> dict:
    import os as _os
    if _os.path.exists(HERMES_PAIRING_FILE):
        with open(HERMES_PAIRING_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict) -> None:
    with open(HERMES_PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)



# ---------------------------------------------------------------------------
# connect — authority token validation
# ---------------------------------------------------------------------------

def connect(authority_token: str) -> HermesConnection:
    """
    Validate an authority token and establish a Hermes connection.

    The authority token format is a compact JSON object:
        {"hermes_id": "...", "principal_id": "...", "capabilities": [...],
         "expires_at": "..."}

    Raises:
        ValueError — token is malformed or missing required fields
        PermissionError — token is expired or lacks Hermes capabilities
    """
    # ── Decode ──────────────────────────────────────────────────────────────
    try:
        payload = json.loads(authority_token)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("HERMES_AUTH_INVALID: authority token is not valid JSON")

    hermes_id: Optional[str] = payload.get('hermes_id')
    principal_id: Optional[str] = payload.get('principal_id')
    capabilities: List[str] = payload.get('capabilities', [])
    expires_at_str: Optional[str] = payload.get('expires_at')

    if not hermes_id:
        raise ValueError("HERMES_AUTH_INVALID: hermes_id is required")
    if not principal_id:
        raise ValueError("HERMES_AUTH_INVALID: principal_id is required")
    if not isinstance(capabilities, list):
        raise ValueError("HERMES_AUTH_INVALID: capabilities must be a list")

    # ── Expiration check ───────────────────────────────────────────────────
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
        except ValueError:
            raise ValueError("HERMES_AUTH_INVALID: expires_at is not a valid ISO timestamp")
        if datetime.now(timezone.utc) > expires_at:
            raise PermissionError("HERMES_TOKEN_EXPIRED")

    # ── Capability check ───────────────────────────────────────────────────
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise PermissionError(
                f"HERMES_UNAUTHORIZED_CAPABILITY: '{cap}' is not in "
                f"the Hermes allowlist {HERMES_CAPABILITIES}"
            )

    # Require at least one Hermes capability
    if not any(cap in HERMES_CAPABILITIES for cap in capabilities):
        raise PermissionError(
            f"HERMES_UNAUTHORIZED: no Hermes capabilities granted. "
            f"Granted: {capabilities}. Allowed: {HERMES_CAPABILITIES}"
        )

    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# connect_from_pairing — connect using stored Hermes pairing record
# ---------------------------------------------------------------------------

def connect_from_pairing(hermes_id: str) -> HermesConnection:
    """
    Connect a Hermes agent using a previously stored pairing record.

    Raises:
        ValueError — no pairing record found for hermes_id
    """
    pairings = _load_hermes_pairings()
    record = pairings.get(hermes_id)

    if not record:
        raise ValueError(f"HERMES_PAIRING_NOT_FOUND: no pairing record for '{hermes_id}'")

    # Derive an authority token payload from the stored record
    authority_payload = json.dumps({
        'hermes_id': hermes_id,
        'principal_id': record['principal_id'],
        'capabilities': record['capabilities'],
        'expires_at': record.get('token_expires_at', ''),
    })
    return connect(authority_payload)


# ---------------------------------------------------------------------------
# pair_hermes — create or update a Hermes pairing record
# ---------------------------------------------------------------------------

def pair_hermes(hermes_id: str, device_name: str) -> dict:
    """
    Create or update (idempotent) a Hermes pairing record with
    observe + summarize capabilities.

    Returns the pairing record dict.
    """
    pairings = _load_hermes_pairings()
    principal = store.load_or_create_principal()

    # Token expires 30 days from now
    from datetime import timedelta
    token_expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    record = {
        'id': str(uuid.uuid4()),
        'hermes_id': hermes_id,
        'device_name': device_name,
        'principal_id': principal.id,
        'capabilities': HERMES_CAPABILITIES.copy(),
        'paired_at': datetime.now(timezone.utc).isoformat(),
        'token_expires_at': token_expires_at,
    }

    pairings[hermes_id] = record
    _save_hermes_pairings(pairings)

    return record


def get_hermes_pairing(hermes_id: str) -> Optional[dict]:
    """Return the pairing record for hermes_id, or None."""
    pairings = _load_hermes_pairings()
    return pairings.get(hermes_id)


def list_hermes_pairings() -> List[dict]:
    """Return all Hermes pairing records."""
    return list(_load_hermes_pairings().values())


# ---------------------------------------------------------------------------
# read_status — requires 'observe' capability
# ---------------------------------------------------------------------------

def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.

    Requires the 'observe' capability.

    Raises:
        PermissionError — observe not granted
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required for read_status")

    # Import here to avoid circular import at module level
    from daemon import miner

    return miner.get_snapshot()


# ---------------------------------------------------------------------------
# append_summary — requires 'summarize' capability
# ---------------------------------------------------------------------------

def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: Optional[List[str]] = None,
) -> dict:
    """
    Append a Hermes summary to the event spine.

    Requires the 'summarize' capability.

    Args:
        connection: Active Hermes connection.
        summary_text: The summary text generated by Hermes.
        authority_scope: List of Hermes capabilities exercised for this summary.
                        Defaults to ['summarize'].

    Returns:
        dict with the appended event id and timestamp.

    Raises:
        PermissionError — summarize not granted
        ValueError — summary_text is empty
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: summarize capability required for append_summary"
        )

    if not summary_text or not summary_text.strip():
        raise ValueError("HERMES_INVALID: summary_text must not be empty")

    scope = authority_scope or ['summarize']

    event = append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            'summary_text': summary_text.strip(),
            'authority_scope': scope,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'hermes_id': connection.hermes_id,
        },
    )

    return {
        'appended': True,
        'event_id': event.id,
        'kind': event.kind,
        'created_at': event.created_at,
    }


# ---------------------------------------------------------------------------
# get_filtered_events — Hermes-readable subset of the event spine
# ---------------------------------------------------------------------------

def get_filtered_events(
    connection: HermesConnection,
    limit: int = 20,
) -> List[dict]:
    """
    Return events Hermes is permitted to read.

    Filters out user_message and pairing events. Returns the most recent
    HERMES_READABLE_EVENTS first.

    Does NOT require any capability (read-only listing is always allowed
    for paired Hermes sessions).
    """
    all_events = get_events(limit=limit * 3)

    allowed_kinds = {e.value for e in HERMES_READABLE_EVENTS}

    filtered = [
        {
            'id': e.id,
            'kind': e.kind,
            'payload': e.payload,
            'created_at': e.created_at,
            'principal_id': e.principal_id,
        }
        for e in all_events
        if e.kind in allowed_kinds
    ]

    return filtered[:limit]


# ---------------------------------------------------------------------------
# can_control — check if Hermes attempted a control path
# ---------------------------------------------------------------------------

def is_control_path(path: str) -> bool:
    """Return True if the HTTP path represents a control operation Hermes cannot use."""
    return path in CONTROL_PATHS


# ---------------------------------------------------------------------------
# Bootstrap proof
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Capabilities:', HERMES_CAPABILITIES)
    print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
    print('Writable events:', [e.value for e in HERMES_WRITABLE_EVENTS])
