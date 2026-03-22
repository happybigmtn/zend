#!/usr/bin/env python3
"""
Hermes Adapter Module

Enforces capability boundaries between Hermes AI agent and the Zend gateway.
Hermes can observe and summarize but cannot issue control commands.

The adapter validates authority tokens and filters event access to ensure
Hermes never inherits gateway control capability.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional

# Import from spine module
from spine import EventKind, append_event, get_events, SpineEvent


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_STORE_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')

# Hermes can only have these capabilities - no control!
HERMES_CAPABILITIES = ['observe', 'summarize']

# Hermes can only read these event kinds - never user_message
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
    authority_scope: str  # 'observe' or 'observe+summarize'


@dataclass
class HermesPairing:
    """Hermes pairing record in the store."""
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token: str
    token_expires_at: str


class HermesError(Exception):
    """Base exception for Hermes adapter errors."""
    pass


class HermesUnauthorizedError(HermesError):
    """Raised when Hermes lacks required capability."""
    pass


class HermesTokenExpiredError(HermesError):
    """Raised when Hermes authority token has expired."""
    pass


class HermesInvalidTokenError(HermesError):
    """Raised when Hermes authority token is invalid."""
    pass


def _load_hermes_pairings() -> dict:
    """Load Hermes pairing records from store."""
    if os.path.exists(HERMES_STORE_FILE):
        with open(HERMES_STORE_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records to store."""
    with open(HERMES_STORE_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def pair_hermes(hermes_id: str, device_name: str = None) -> HermesPairing:
    """
    Create a new Hermes pairing with observe+summarize capabilities.
    
    Idempotent: if hermes_id already exists, returns existing pairing.
    """
    # Load or create principal
    from store import load_or_create_principal, PAIRING_FILE, PRINCIPAL_FILE
    
    principal_id = None
    if os.path.exists(PRINCIPAL_FILE):
        with open(PRINCIPAL_FILE, 'r') as f:
            data = json.load(f)
            principal_id = data.get('id')
    
    if not principal_id:
        from store import load_or_create_principal as _create
        principal = _create()
        principal_id = principal.id
    
    pairings = _load_hermes_pairings()
    
    # Return existing if idempotent re-pair
    if hermes_id in pairings:
        data = pairings[hermes_id]
        return HermesPairing(
            hermes_id=data['hermes_id'],
            principal_id=data['principal_id'],
            device_name=data['device_name'],
            capabilities=data['capabilities'],
            paired_at=data['paired_at'],
            token=data['token'],
            token_expires_at=data['token_expires_at']
        )
    
    # Create new pairing
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()
    
    pairing = HermesPairing(
        hermes_id=hermes_id,
        principal_id=principal_id,
        device_name=device_name or f"hermes-{hermes_id}",
        capabilities=HERMES_CAPABILITIES,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token=token,
        token_expires_at=expires
    )
    
    pairings[hermes_id] = asdict(pairing)
    _save_hermes_pairings(pairings)
    
    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    
    if hermes_id not in pairings:
        return None
    
    data = pairings[hermes_id]
    return HermesPairing(
        hermes_id=data['hermes_id'],
        principal_id=data['principal_id'],
        device_name=data['device_name'],
        capabilities=data['capabilities'],
        paired_at=data['paired_at'],
        token=data['token'],
        token_expires_at=data['token_expires_at']
    )


def connect(authority_token: str, hermes_id: str = None) -> HermesConnection:
    """
    Validate authority token and establish Hermes connection.
    
    Args:
        authority_token: Token issued during Hermes pairing
        hermes_id: Hermes identifier (extracted from Authorization header if not provided)
    
    Returns:
        HermesConnection with validated capabilities
    
    Raises:
        HermesInvalidTokenError: Token is malformed or doesn't match pairing
        HermesTokenExpiredError: Token has expired
        HermesUnauthorizedError: Token doesn't have Hermes capabilities
    """
    # Load pairing by token or hermes_id
    pairings = _load_hermes_pairings()
    pairing_data = None
    
    # Find by token
    for pid, pdata in pairings.items():
        if pdata.get('token') == authority_token:
            pairing_data = pdata
            break
    
    # Fallback: find by hermes_id
    if not pairing_data and hermes_id and hermes_id in pairings:
        pairing_data = pairings[hermes_id]
    
    if not pairing_data:
        raise HermesInvalidTokenError("Invalid authority token: no matching pairing found")
    
    # Validate token hasn't expired (in production, tokens would have proper expiry)
    # For milestone 1, tokens don't expire - this is a placeholder for future
    expires_at = pairing_data.get('token_expires_at')
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expiry:
                raise HermesTokenExpiredError("Authority token has expired")
        except ValueError:
            pass  # Malformed expiry, allow for now
    
    # Validate capabilities - must be Hermes capabilities only
    capabilities = pairing_data.get('capabilities', [])
    for cap in capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise HermesUnauthorizedError(
                f"Hermes cannot have capability '{cap}' - only {HERMES_CAPABILITIES} allowed"
            )
    
    # Determine authority scope
    if 'summarize' in capabilities and 'observe' in capabilities:
        scope = 'observe+summarize'
    elif 'observe' in capabilities:
        scope = 'observe'
    else:
        scope = 'none'
    
    return HermesConnection(
        hermes_id=pairing_data['hermes_id'],
        principal_id=pairing_data['principal_id'],
        capabilities=capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        authority_scope=scope
    )


def require_capability(connection: HermesConnection, capability: str):
    """
    Verify connection has required capability.
    
    Raises HermesUnauthorizedError if missing.
    """
    if capability not in connection.capabilities:
        raise HermesUnauthorizedError(
            f"HERMES_UNAUTHORIZED: {capability} capability required"
        )


def read_status(connection: HermesConnection) -> dict:
    """
    Read miner status through adapter.
    
    Requires 'observe' capability.
    
    Returns:
        Miner status snapshot (status, mode, hashrate, temperature, uptime)
    
    Raises:
        HermesUnauthorizedError: If Hermes lacks observe capability
    """
    require_capability(connection, 'observe')
    
    # Import miner simulator from daemon
    # In production, this would be a proper RPC call
    from daemon import miner
    
    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str = None
) -> SpineEvent:
    """
    Append a Hermes summary to the event spine.
    
    Requires 'summarize' capability.
    
    Args:
        connection: Validated Hermes connection
        summary_text: The summary content
        authority_scope: Optional scope descriptor (defaults to connection.authority_scope)
    
    Returns:
        The appended SpineEvent
    
    Raises:
        HermesUnauthorizedError: If Hermes lacks summarize capability
    """
    require_capability(connection, 'summarize')
    
    scope = authority_scope or connection.authority_scope
    
    return append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={
            "summary_text": summary_text,
            "authority_scope": [scope] if isinstance(scope, str) else scope,
            "hermes_id": connection.hermes_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]:
    """
    Return events Hermes is allowed to see.
    
    Always filters out user_message events.
    
    Args:
        connection: Validated Hermes connection
        limit: Maximum events to return (before filtering)
    
    Returns:
        List of SpineEvents visible to Hermes
    """
    # Over-fetch to account for filtering
    all_events = get_events(limit=limit * 2)
    
    # Filter to Hermes-readable event kinds
    readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
    filtered = [e for e in all_events if e.kind in readable_kinds]
    
    return filtered[:limit]


def is_hermes_request(headers: dict) -> bool:
    """Check if request is a Hermes request (Authorization header starts with 'Hermes')."""
    auth = headers.get('Authorization', '')
    return auth.startswith('Hermes ')


def extract_hermes_id(headers: dict) -> Optional[str]:
    """Extract hermes_id from Hermes Authorization header."""
    auth = headers.get('Authorization', '')
    if auth.startswith('Hermes '):
        return auth[7:].strip()
    return None


def validate_hermes_auth(headers: dict, authority_token: str = None) -> HermesConnection:
    """
    Validate Hermes authorization from request headers.
    
    Expects: Authorization: Hermes <hermes_id>
    
    Returns:
        HermesConnection if valid
    
    Raises:
        HermesUnauthorizedError: If auth is missing or invalid
    """
    hermes_id = extract_hermes_id(headers)
    if not hermes_id:
        raise HermesUnauthorizedError("Missing Hermes authorization header")
    
    # In milestone 1, we use hermes_id directly as authority
    # Future: validate authority_token JWT
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        raise HermesUnauthorizedError(f"Unknown Hermes ID: {hermes_id}")
    
    return connect(authority_token or pairing.token, hermes_id)


# Export for external use
__all__ = [
    'HermesConnection',
    'HermesPairing',
    'HermesError',
    'HermesUnauthorizedError',
    'HermesTokenExpiredError',
    'HermesInvalidTokenError',
    'HERMES_CAPABILITIES',
    'HERMES_READABLE_EVENTS',
    'pair_hermes',
    'get_hermes_pairing',
    'connect',
    'read_status',
    'append_summary',
    'get_filtered_events',
    'is_hermes_request',
    'extract_hermes_id',
    'validate_hermes_auth',
]
