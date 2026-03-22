#!/usr/bin/env python3
"""
Gateway pairing and principal store.

Manages:
- PrincipalId creation and storage
- Gateway pairing records
- Capability-scoped permissions
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

PRINCIPAL_FILE = os.path.join(STATE_DIR, 'principal.json')
PAIRING_FILE = os.path.join(STATE_DIR, 'pairing-store.json')


@dataclass
class Principal:
    """Zend principal identity."""
    id: str
    created_at: str
    name: str


@dataclass
class GatewayPairing:
    """Paired gateway client record."""
    id: str
    principal_id: str
    device_name: str
    capabilities: list
    paired_at: str
    token_expires_at: str
    token_used: bool = False


def load_or_create_principal() -> Principal:
    """Load existing principal or create new one."""
    if os.path.exists(PRINCIPAL_FILE):
        with open(PRINCIPAL_FILE, 'r') as f:
            data = json.load(f)
            return Principal(**data)

    # Create new principal
    principal = Principal(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
        name="Zend Home"
    )

    with open(PRINCIPAL_FILE, 'w') as f:
        json.dump(asdict(principal), f, indent=2)

    return principal


def load_pairings() -> dict:
    """Load all pairing records."""
    if os.path.exists(PAIRING_FILE):
        with open(PAIRING_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_pairings(pairings: dict):
    """Save pairing records."""
    with open(PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def create_pairing_token() -> tuple[str, str]:
    """Create a new pairing token and its expiration (24h from now)."""
    token = str(uuid.uuid4())
    expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    return token, expires


def is_token_expired(pairing: GatewayPairing) -> bool:
    """Check if a pairing token has expired."""
    expires_at = datetime.fromisoformat(pairing.token_expires_at)
    return datetime.now(timezone.utc) > expires_at


def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create or refresh a pairing record for a client.

    Idempotent: re-pairing an existing device_name refreshes the token
    and updates capabilities rather than raising an error.
    """
    principal = load_or_create_principal()
    pairings = load_pairings()

    # Re-pair existing device: refresh token and capabilities
    for pairing_id, existing in pairings.items():
        if existing['device_name'] == device_name:
            token, expires = create_pairing_token()
            existing['capabilities'] = capabilities
            existing['token_expires_at'] = expires
            existing['token_used'] = False
            save_pairings(pairings)
            return GatewayPairing(**existing)

    # New device pairing
    token, expires = create_pairing_token()

    pairing = GatewayPairing(
        id=str(uuid.uuid4()),
        principal_id=principal.id,
        device_name=device_name,
        capabilities=capabilities,
        paired_at=datetime.now(timezone.utc).isoformat(),
        token_expires_at=expires,
        token_used=False
    )

    pairings[pairing.id] = asdict(pairing)
    save_pairings(pairings)

    return pairing


def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]:
    """Get pairing record by device name."""
    pairings = load_pairings()
    for pairing in pairings.values():
        if pairing['device_name'] == device_name:
            return GatewayPairing(**pairing)
    return None


def has_capability(device_name: str, capability: str) -> bool:
    """Check if device has specific capability."""
    pairing = get_pairing_by_device(device_name)
    if not pairing:
        return False
    return capability in pairing.capabilities


def list_devices() -> list:
    """List all paired devices."""
    pairings = load_pairings()
    return [GatewayPairing(**p) for p in pairings.values()]
