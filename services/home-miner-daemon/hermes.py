#!/usr/bin/env python3
"""
Zend Hermes Adapter

Enforces capability boundaries between Hermes AI agents and the Zend gateway.
Hermes can observe miner status and append summaries, but cannot issue control
commands or read user messages.

Architecture:
    Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
"""

import json
import os
import uuid
import jwt
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional

# Resolve paths relative to this module
_module_dir = Path(__file__).resolve().parents[0]
DAEMON_DIR = _module_dir
ROOT_DIR = _module_dir.parents[0] if _module_dir.name == 'home-miner-daemon' else _module_dir

import sys
sys.path.insert(0, str(DAEMON_DIR))

from spine import EventKind, append_event, get_events, SpineEvent
from store import load_pairings, save_pairings, load_or_create_principal, GatewayPairing

# Hermes-specific capability set (narrower than gateway capabilities)
HERMES_CAPABILITIES = ['observe', 'summarize']

# Events Hermes is allowed to read (filtered from spine)
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

# Hermes-specific JWT secret (separate from device auth)
# In production, this would be derived from a secure key management system
HERMES_JWT_SECRET = os.environ.get('ZEND_HERMES_JWT_SECRET', 'hermes-adapter-secret-key-milestone1')


class HermesError(Exception):
    """Base exception for Hermes adapter errors."""
    pass


class HermesUnauthorizedError(HermesError):
    """Raised when Hermes lacks required capability."""
    pass


class HermesTokenError(HermesError):
    """Raised when authority token is invalid or expired."""
    pass


class HermesCapabilityError(HermesError):
    """Raised when token requests capabilities Hermes cannot have."""
    pass


@dataclass
class HermesConnection:
    """Active Hermes connection with validated authority."""
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    expires_at: str

    def has_capability(self, capability: str) -> bool:
        """Check if connection has specific capability."""
        return capability in self.capabilities

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {
            "hermes_id": self.hermes_id,
            "principal_id": self.principal_id,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at,
            "expires_at": self.expires_at
        }


@dataclass
class HermesPairing:
    """Hermes-specific pairing record."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str
    is_active: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _default_state_dir() -> str:
    """Resolve the state directory for Hermes pairing records."""
    # Use parent of daemon dir (repo root) / state
    return str(ROOT_DIR / "state")


def _get_hermes_pairings_path() -> str:
    """Path to Hermes pairing store."""
    state_dir = os.environ.get('ZEND_STATE_DIR', _default_state_dir())
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, 'hermes-pairings.json')


def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records."""
    path = _get_hermes_pairings_path()
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    path = _get_hermes_pairings_path()
    with open(path, 'w') as f:
        json.dump(pairings, f, indent=2)


def pair_hermes(hermes_id: str, device_name: str, capabilities: Optional[List[str]] = None) -> HermesPairing:
    """
    Create or update a Hermes pairing record.
    
    Hermes pairings always use observe+summarize capabilities (Hermes cannot
    have gateway 'control' capability).
    
    Idempotent: calling with same hermes_id updates the existing pairing.
    """
    if capabilities is None:
        capabilities = HERMES_CAPABILITIES.copy()
    
    # Validate requested capabilities are a subset of Hermes allowed set
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise HermesCapabilityError(
                f"'{cap}' is not a valid Hermes capability. "
                f"Hermes capabilities are: {HERMES_CAPABILITIES}"
            )
    
    principal = load_or_create_principal()
    pairings = _load_hermes_pairings()
    
    # Idempotent pairing (re-pair if exists)
    paired_at = datetime.now(timezone.utc).isoformat()
    expires_at = datetime.now(timezone.utc)
    expires_at = expires_at.replace(year=expires_at.year + 1).isoformat()  # 1 year validity
    
    pairing_data = {
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "device_name": device_name,
        "capabilities": capabilities,
        "paired_at": paired_at,
        "token_expires_at": expires_at,
        "is_active": True
    }
    
    pairings[hermes_id] = pairing_data
    _save_hermes_pairings(pairings)
    
    return HermesPairing(**pairing_data)


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing by ID."""
    pairings = _load_hermes_pairings()
    if hermes_id in pairings:
        return HermesPairing(**pairings[hermes_id])
    return None


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Token format (JWT):
        - hermes_id: unique agent identifier
        - principal_id: associated principal
        - capabilities: list of granted capabilities
        - exp: expiration timestamp
    
    Raises:
        HermesTokenError: if token is invalid or expired
        HermesCapabilityError: if token requests non-Hermes capabilities
    """
    try:
        # Decode and validate JWT
        payload = jwt.decode(
            authority_token,
            HERMES_JWT_SECRET,
            algorithms=['HS256']
        )
    except jwt.ExpiredSignatureError:
        raise HermesTokenError("Authority token has expired")
    except jwt.InvalidTokenError as e:
        raise HermesTokenError(f"Invalid authority token: {e}")
    
    # Extract token fields
    hermes_id = payload.get('hermes_id')
    principal_id = payload.get('principal_id')
    capabilities = payload.get('capabilities', [])
    exp = payload.get('exp')
    
    if not hermes_id:
        raise HermesTokenError("Token missing hermes_id")
    if not principal_id:
        raise HermesTokenError("Token missing principal_id")
    
    # Validate capabilities are Hermes-allowed
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise HermesCapabilityError(
                f"Token requests '{cap}' which Hermes cannot hold. "
                f"Hermes capabilities are: {HERMES_CAPABILITIES}"
            )
    
    # Validate against stored pairing
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        raise HermesUnauthorizedError(f"No pairing found for Hermes '{hermes_id}'")
    
    if not pairing.is_active:
        raise HermesUnauthorizedError(f"Hermes '{hermes_id}' pairing is inactive")
    
    # Build connection
    connected_at = datetime.now(timezone.utc).isoformat()
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat() if exp else None
    
    return HermesConnection(
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        connected_at=connected_at,
        expires_at=expires_at or pairing.token_expires_at
    )


def generate_authority_token(hermes_id: str, capabilities: Optional[List[str]] = None) -> str:
    """
    Generate an authority token for Hermes.
    
    This is used during the pairing flow to issue Hermes its access token.
    """
    principal = load_or_create_principal()
    pairing = get_hermes_pairing(hermes_id)
    
    if not pairing:
        raise HermesError(f"No pairing found for '{hermes_id}'. Pair first with /hermes/pair")
    
    if capabilities is None:
        capabilities = pairing.capabilities
    
    # Token expires in 24 hours (shorter than pairing validity)
    exp = datetime.now(timezone.utc).timestamp() + (24 * 60 * 60)
    
    payload = {
        'hermes_id': hermes_id,
        'principal_id': principal.id,
        'capabilities': capabilities,
        'iat': datetime.now(timezone.utc).timestamp(),
        'exp': exp
    }
    
    return jwt.encode(payload, HERMES_JWT_SECRET, algorithm='HS256')


def read_status(connection: HermesConnection, miner_get_snapshot=None) -> dict:
    """
    Read current miner status through adapter.
    
    Requires 'observe' capability.
    
    Args:
        connection: Validated Hermes connection
        miner_get_snapshot: Function to get miner snapshot (daemon.miner.get_snapshot)
    
    Returns:
        MinerSnapshot dict
    """
    if 'observe' not in connection.capabilities:
        raise HermesUnauthorizedError(
            "HERMES_UNAUTHORIZED: observe capability required for read_status"
        )
    
    if miner_get_snapshot is None:
        # Import and use daemon's miner if available
        try:
            from daemon import miner
            return miner.get_snapshot()
        except ImportError:
            raise HermesError("Miner not available in adapter context")
    
    return miner_get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: Optional[List[str]] = None
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Args:
        connection: Validated Hermes connection
        summary_text: The summary content
        authority_scope: Scope of the authority (defaults to connection capabilities)
    
    Returns:
        The created SpineEvent
    """
    if 'summarize' not in connection.capabilities:
        raise HermesUnauthorizedError(
            "HERMES_UNAUTHORIZED: summarize capability required for append_summary"
        )
    
    if authority_scope is None:
        authority_scope = connection.capabilities
    
    return append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]:
    """
    Get events Hermes is allowed to see.
    
    Filters out user_message events and returns only Hermes-readable events.
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 3)
    
    # Filter to Hermes-readable event kinds
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    return filtered[:limit]


def verify_control_blocked(connection: HermesConnection) -> bool:
    """
    Verify that control capability is blocked for this Hermes connection.
    
    Returns True if control IS blocked (correct behavior).
    Raises HermesUnauthorizedError if control capability is present.
    """
    if 'control' in connection.capabilities:
        raise HermesUnauthorizedError(
            "HERMES_SECURITY_VIOLATION: Hermes cannot hold 'control' capability"
        )
    return True


# Observable constants for validation
def get_capabilities() -> List[str]:
    """Return Hermes capability set."""
    return HERMES_CAPABILITIES.copy()


def get_readable_events() -> List[str]:
    """Return event kinds Hermes can read."""
    return [e.value for e in HERMES_READABLE_EVENTS]
