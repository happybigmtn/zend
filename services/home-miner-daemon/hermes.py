#!/usr/bin/env python3
"""
Hermes Adapter - Zend capability boundary for Hermes agent connections.

The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

This module is the capability boundary between the external Hermes agent
and the Zend gateway contract. It runs in-process to avoid network hop
complexity.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional

# Add service to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spine import append_event, get_events, EventKind
from store import load_pairings, save_pairings


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')


# Hermes-specific capability scope
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read from the spine
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Block these events from Hermes reads
HERMES_BLOCKED_EVENTS = [
    EventKind.USER_MESSAGE,
]


@dataclass
class HermesConnection:
    """Represents an active Hermes connection with delegated authority."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str


@dataclass
class HermesPairing:
    """Hermes pairing record stored in the daemon."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token: str
    token_expires_at: str


@dataclass
class AuthorityToken:
    """Authority token issued during Hermes pairing."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    issued_at: str
    expires_at: str


def _load_hermes_pairings() -> dict:
    """Load all Hermes pairing records."""
    if os.path.exists(HERMES_PAIRING_FILE):
        with open(HERMES_PAIRING_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    with open(HERMES_PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create or update a Hermes pairing record.
    
    Idempotent: if hermes_id already exists, returns existing pairing.
    Hermes always gets observe + summarize capabilities.
    """
    pairings = _load_hermes_pairings()
    
    # Check for existing pairing (idempotent)
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    
    # Load principal for principal_id
    from store import load_or_create_principal
    principal = load_or_create_principal()
    
    now = datetime.now(timezone.utc)
    
    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES.copy(),
        paired_at=now.isoformat(),
        token=str(uuid.uuid4()),
        token_expires_at=(now + timedelta(days=365)).isoformat(),
    )
    
    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    # Append pairing event to spine
    append_event(
        EventKind.PAIRING_GRANTED,
        principal.id,
        {
            "device_name": device_name,
            "device_type": "hermes",
            "granted_capabilities": pairing.capabilities,
        }
    )
    
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    return None


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    The authority token is expected to be a JSON-encoded AuthorityToken.
    In milestone 1, this is a simplified token format.
    
    Raises:
        ValueError: if token is invalid, expired, or malformed
        PermissionError: if token has wrong capabilities for Hermes
    """
    try:
        # Parse authority token (expected format: JSON)
        token_data = json.loads(authority_token)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("HERMES_AUTH_FAILED: Invalid authority token format")
    
    # Validate required fields
    required_fields = ['hermes_id', 'principal_id', 'capabilities', 'expires_at']
    for field in required_fields:
        if field not in token_data:
            raise ValueError(f"HERMES_AUTH_FAILED: Missing required field: {field}")
    
    # Check expiration
    try:
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now(timezone.utc) > expires_at:
            raise PermissionError("HERMES_AUTH_FAILED: Authority token has expired")
    except ValueError:
        raise ValueError("HERMES_AUTH_FAILED: Invalid expiration format")
    
    # Validate capabilities - Hermes must only have observe + summarize
    capabilities = token_data.get('capabilities', [])
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise PermissionError(
                f"HERMES_UNAUTHORIZED: Capability '{cap}' not allowed for Hermes"
            )
    
    # Block control capability explicitly
    if 'control' in capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: Hermes cannot have control capability"
        )
    
    # Verify pairing exists
    pairing = get_hermes_pairing(token_data['hermes_id'])
    if not pairing:
        raise PermissionError("HERMES_AUTH_FAILED: Hermes not paired with this gateway")
    
    # Verify principal matches
    if pairing.principal_id != token_data['principal_id']:
        raise PermissionError("HERMES_AUTH_FAILED: Principal mismatch")
    
    return HermesConnection(
        hermes_id=token_data['hermes_id'],
        principal_id=token_data['principal_id'],
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
    )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through the adapter.
    
    Requires 'observe' capability.
    
    Raises:
        PermissionError: if observe capability is not granted
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: observe capability required for status read"
        )
    
    # Import here to avoid circular import
    from daemon import miner
    
    # Get miner snapshot (this is the same contract a real miner would use)
    snapshot = miner.get_snapshot()
    
    # Strip any fields Hermes shouldn't see in the future
    # For milestone 1, we return the full snapshot
    return {
        "status": snapshot.get("status"),
        "mode": snapshot.get("mode"),
        "hashrate_hs": snapshot.get("hashrate_hs"),
        "temperature": snapshot.get("temperature"),
        "uptime_seconds": snapshot.get("uptime_seconds"),
        "freshness": snapshot.get("freshness"),
        "source": "hermes_adapter",
    }


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str
) -> dict:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Args:
        connection: The validated Hermes connection
        summary_text: The summary text to append
        authority_scope: The scope of this summary (e.g., 'observe')
    
    Returns:
        The appended event
    
    Raises:
        PermissionError: if summarize capability is not granted
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: summarize capability required for summary append"
        )
    
    # Append to event spine
    event = append_event(
        EventKind.HERMES_SUMMARY,
        connection.principal_id,
        {
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "hermes_id": connection.hermes_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    
    return {
        "appended": True,
        "event_id": event.id,
        "principal_id": connection.principal_id,
        "timestamp": event.created_at,
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events Hermes is allowed to see.
    
    Filters out user_message events and other blocked events.
    Hermes can see: hermes_summary, miner_alert, control_receipt
    
    Args:
        connection: The validated Hermes connection
        limit: Maximum number of events to return
    
    Returns:
        List of filtered events
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 3)
    
    # Build allowed kinds list
    allowed_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    
    # Filter events
    filtered = [
        {
            "id": e.id,
            "kind": e.kind,
            "principal_id": e.principal_id,
            "payload": e.payload,
            "created_at": e.created_at,
        }
        for e in all_events
        if e.kind in allowed_kinds
    ]
    
    return filtered[:limit]


def validate_control_attempt(connection: HermesConnection) -> bool:
    """
    Validate whether a control command should be allowed.
    
    Hermes can NEVER issue control commands.
    
    Returns:
        False (always blocks control)
    """
    return False


def generate_authority_token(hermes_id: str, principal_id: str) -> str:
    """
    Generate an authority token for a paired Hermes.
    
    This is used during the Hermes pairing flow to issue
    the initial authority token.
    
    Returns:
        JSON-encoded authority token string
    """
    now = datetime.now(timezone.utc)
    token = AuthorityToken(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=HERMES_CAPABILITIES.copy(),
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=365)).isoformat(),
    )
    return json.dumps(asdict(token))
