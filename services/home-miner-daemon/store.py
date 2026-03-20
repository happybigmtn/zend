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
PAIRING_TOKEN_TTL_DAYS = int(os.environ.get("ZEND_PAIRING_TOKEN_TTL_DAYS", "30"))


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
    auth_token: str = ""
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


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _pairing_needs_token_refresh(pairing: dict) -> bool:
    token = pairing.get("auth_token")
    expires = pairing.get("token_expires_at")
    paired_at = pairing.get("paired_at")
    if not token or not expires:
        return True

    try:
        expires_at = _parse_timestamp(expires)
        paired_at_dt = _parse_timestamp(paired_at) if paired_at else None
    except ValueError:
        return True

    return paired_at_dt is not None and expires_at <= paired_at_dt


def _normalize_pairing_record(pairing: dict) -> tuple[dict, bool]:
    normalized = dict(pairing)
    changed = False

    if "token_used" not in normalized:
        normalized["token_used"] = False
        changed = True

    if _pairing_needs_token_refresh(normalized):
        token, expires = create_pairing_token()
        normalized["auth_token"] = token
        normalized["token_expires_at"] = expires
        changed = True

    return normalized, changed


def load_pairings() -> dict:
    """Load all pairing records."""
    if os.path.exists(PAIRING_FILE):
        with open(PAIRING_FILE, 'r') as f:
            pairings = json.load(f)
        normalized_pairings = {}
        changed = False
        for pairing_id, pairing in pairings.items():
            normalized, record_changed = _normalize_pairing_record(pairing)
            normalized_pairings[pairing_id] = normalized
            changed = changed or record_changed
        if changed:
            save_pairings(normalized_pairings)
        return normalized_pairings
    return {}


def save_pairings(pairings: dict):
    """Save pairing records."""
    with open(PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def create_pairing_token() -> tuple[str, str]:
    """Create a new pairing token and its expiration."""
    token = str(uuid.uuid4())
    expires = (_now_utc() + timedelta(days=PAIRING_TOKEN_TTL_DAYS)).isoformat()
    return token, expires


def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create a new pairing record for a client."""
    principal = load_or_create_principal()
    pairings = load_pairings()

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
        capabilities=capabilities,
        paired_at=_now_utc().isoformat(),
        token_expires_at=expires,
        auth_token=token,
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


def get_pairing_by_token(auth_token: str) -> Optional[GatewayPairing]:
    """Get pairing record by bearer token."""
    pairings = load_pairings()
    for pairing in pairings.values():
        if pairing.get("auth_token") == auth_token:
            return GatewayPairing(**pairing)
    return None


def pairing_token_expired(pairing: GatewayPairing) -> bool:
    """Check whether a pairing's bearer token is expired."""
    try:
        return _parse_timestamp(pairing.token_expires_at) <= _now_utc()
    except ValueError:
        return True


def has_capability(device_name: str, capability: str) -> bool:
    """Check if device has specific capability."""
    pairing = get_pairing_by_device(device_name)
    if not pairing:
        return False
    return capability in pairing.capabilities or (
        capability == "observe" and "control" in pairing.capabilities
    )


def list_devices() -> list:
    """List all paired devices."""
    pairings = load_pairings()
    return [GatewayPairing(**p) for p in pairings.values()]
