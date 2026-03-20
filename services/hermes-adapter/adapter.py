#!/usr/bin/env python3
"""
Hermes Adapter - Connects Hermes AI gateway to Zend native gateway.

Milestone 1 scope:
- Observe: read miner status
- Summarize: append summaries to event spine

No direct miner control, payout-target mutation, or inbox composition.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pathlib import Path
import sys


class HermesCapability(str, Enum):
    OBSERVE = "observe"
    SUMMARIZE = "summarize"


@dataclass
class MinerSnapshot:
    """Current miner status snapshot."""
    status: str
    mode: str
    hashrate_hs: int
    temperature: float
    uptime_seconds: int
    freshness: str


@dataclass
class HermesSummary:
    """A Hermes-generated summary for the event spine."""
    summary_text: str
    authority_scope: list[str]


@dataclass
class HermesConnection:
    """Active Hermes connection to Zend gateway."""
    principal_id: str
    device_name: str
    capabilities: list[str]
    connected_at: str
    token_expires_at: str


@dataclass
class HermesAuthorityGrant:
    """Validated delegated authority token payload."""
    principal_id: str
    device_name: str
    capabilities: list[str]
    expires_at: str


def _resolve_daemon_url() -> str:
    """Resolve the daemon URL from environment or defaults."""
    return os.environ.get('ZEND_DAEMON_URL', 'http://127.0.0.1:8080')


def _resolve_state_dir() -> str:
    """Resolve the state directory."""
    return os.environ.get('ZEND_STATE_DIR', str(Path(__file__).resolve().parents[2] / "state"))


def _parse_authority_expiry(expires_at: str) -> datetime:
    """Parse authority token expiry in ISO 8601 format."""
    normalized = expires_at.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_contract_value(value: object) -> str:
    """Normalize enum-like values back to the contract's lower-case strings."""
    if isinstance(value, Enum):
        return str(value.value)

    text = str(value)
    if "." in text:
        return text.rsplit(".", 1)[-1].lower()
    return text


def _decode_authority_token(authority_token: str) -> HermesAuthorityGrant:
    """Decode and validate the delegated authority token payload."""
    try:
        padding = "=" * (-len(authority_token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(f"{authority_token}{padding}".encode()))
    except (binascii.Error, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid authority token encoding") from exc

    if not isinstance(payload, dict):
        raise ValueError("Authority token payload must decode to an object")

    required_fields = {"principal_id", "device_name", "capabilities", "expires_at"}
    missing = sorted(required_fields - set(payload))
    if missing:
        raise ValueError(f"Authority token missing required fields: {', '.join(missing)}")

    principal_id = payload["principal_id"]
    device_name = payload["device_name"]
    capabilities = payload["capabilities"]
    expires_at = payload["expires_at"]

    if not isinstance(principal_id, str) or not principal_id:
        raise ValueError("Authority token principal_id must be a non-empty string")
    if not isinstance(device_name, str) or not device_name:
        raise ValueError("Authority token device_name must be a non-empty string")
    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError("Authority token capabilities must be a non-empty list")
    if not isinstance(expires_at, str) or not expires_at:
        raise ValueError("Authority token expires_at must be a non-empty string")

    allowed_capabilities = {capability.value for capability in HermesCapability}
    normalized_capabilities = []
    for capability in capabilities:
        if not isinstance(capability, str):
            raise ValueError("Authority token capabilities must be strings")
        if capability not in allowed_capabilities:
            raise ValueError(f"Unsupported capability: {capability}")
        normalized_capabilities.append(capability)

    parsed_expiry = _parse_authority_expiry(expires_at)
    if parsed_expiry <= datetime.now(timezone.utc):
        raise ValueError("Authority token has expired")

    return HermesAuthorityGrant(
        principal_id=principal_id,
        device_name=device_name,
        capabilities=normalized_capabilities,
        expires_at=parsed_expiry.isoformat(),
    )


class HermesAdapter:
    """
    Zend gateway adapter for Hermes AI gateway.

    Connects using delegated authority and provides:
    - observe: read miner status
    - summarize: append summaries to event spine
    """

    def __init__(self):
        self._connection: Optional[HermesConnection] = None
        self._daemon_url = _resolve_daemon_url()
        self._state_dir = _resolve_state_dir()

    def connect(self, authority_token: str) -> HermesConnection:
        """
        Connect to Zend gateway using authority token.

        The authority token encodes principal, capabilities, and expiration.
        For milestone 1, tokens are issued during the pairing flow.
        """
        grant = _decode_authority_token(authority_token)
        local_principal_id = self._load_principal_id()
        if grant.principal_id != local_principal_id:
            raise ValueError("Authority token principal does not match local principal")

        self._connection = HermesConnection(
            principal_id=grant.principal_id,
            device_name=grant.device_name,
            capabilities=grant.capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=grant.expires_at,
        )

        return self._connection

    def readStatus(self) -> MinerSnapshot:
        """
        Read current miner status (requires 'observe' capability).

        Returns cached snapshot from the daemon.
        """
        self._require_capability(HermesCapability.OBSERVE)

        data = self._read_status_payload()

        return MinerSnapshot(
            status=_normalize_contract_value(data['status']),
            mode=_normalize_contract_value(data['mode']),
            hashrate_hs=int(data['hashrate_hs']),
            temperature=float(data['temperature']),
            uptime_seconds=int(data['uptime_seconds']),
            freshness=str(data['freshness'])
        )

    def appendSummary(self, summary: HermesSummary) -> None:
        """
        Append summary to event spine (requires 'summarize' capability).

        Writes a hermes_summary event to the append-only journal.
        """
        self._require_capability(HermesCapability.SUMMARIZE)

        # Import spine dynamically to avoid circular deps
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "home-miner-daemon"))
        from spine import append_hermes_summary

        principal = self._load_or_create_principal()
        append_hermes_summary(
            summary.summary_text,
            summary.authority_scope,
            principal.id
        )

    def getScope(self) -> list[str]:
        """Get current authority scope (capabilities)."""
        if not self._connection:
            return []
        return self._connection.capabilities.copy()

    def _read_status_payload(self) -> dict:
        """Read status from the configured daemon transport."""
        if self._daemon_url == "inproc://home-miner-daemon":
            return self._read_status_inproc()

        url = f"{self._daemon_url}/status"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to read status: {e}")

    def _read_status_inproc(self) -> dict:
        """Load the daemon module directly for sandbox-safe bootstrap proof."""
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "home-miner-daemon"))
        import daemon as home_miner_daemon

        return home_miner_daemon.miner.get_snapshot()

    def _require_capability(self, capability: HermesCapability) -> None:
        """Enforce capability boundary before relaying any request."""
        if not self._connection:
            raise RuntimeError("Not connected - call connect() first")
        if capability.value not in self._connection.capabilities:
            raise RuntimeError(
                f"Capability '{capability.value}' not granted. "
                f"Current scope: {self._connection.capabilities}"
            )

    def _load_principal_id(self) -> str:
        """Load principal ID from state."""
        principal_file = os.path.join(self._state_dir, 'principal.json')
        if os.path.exists(principal_file):
            with open(principal_file, 'r') as f:
                data = json.load(f)
                return data['id']
        # Create if not exists (same logic as home-miner-daemon)
        principal_id = self._load_or_create_principal().id
        return principal_id

    def _load_or_create_principal(self):
        """Load or create principal (used internally)."""
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "home-miner-daemon"))
        from store import load_or_create_principal
        return load_or_create_principal()
