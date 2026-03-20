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
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass, asdict

# State directory
STATE_DIR = os.environ.get('ZEND_STATE_DIR', 'state')
os.makedirs(STATE_DIR, exist_ok=True)

PRINCIPAL_FILE = os.path.join(STATE_DIR, 'principal.json')
PAIRING_FILE = os.path.join(STATE_DIR, 'pairing-store.json')
ALLOWED_GATEWAY_CAPABILITIES = ("observe", "control")


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


def normalize_capabilities(capabilities: list[str]) -> list[str]:
    """Validate and normalize a milestone 1 capability set."""
    normalized = []
    for capability in capabilities:
        value = capability.strip()
        if not value:
            continue
        if value not in ALLOWED_GATEWAY_CAPABILITIES:
            allowed = ", ".join(ALLOWED_GATEWAY_CAPABILITIES)
            raise ValueError(
                f"Unsupported capability '{value}'. Allowed values: {allowed}"
            )
        if value not in normalized:
            normalized.append(value)

    if not normalized:
        raise ValueError("At least one gateway capability is required")

    return [
        capability
        for capability in ALLOWED_GATEWAY_CAPABILITIES
        if capability in normalized
    ]


def create_pairing_token() -> tuple[str, str]:
    """Create a new pairing token and its expiration."""
    token = str(uuid.uuid4())
    expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    return token, expires


def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create a new pairing record for a client."""
    device_name = device_name.strip()
    if not device_name:
        raise ValueError("Device name is required")

    principal = load_or_create_principal()
    pairings = load_pairings()
    normalized_capabilities = normalize_capabilities(capabilities)

    # Check for duplicate device name
    for existing in pairings.values():
        if existing['device_name'] == device_name:
            raise ValueError(f"Device '{device_name}' already paired")

    # Create pairing token
    token, expires = create_pairing_token()

    pairing = GatewayPairing(
        id=str(uuid.uuid4()),
        principal_id=principal.id,
        device_name=device_name,
        capabilities=normalized_capabilities,
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
