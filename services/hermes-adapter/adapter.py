#!/usr/bin/env python3
"""
Hermes Adapter - Connects Hermes AI gateway to Zend native gateway.

Milestone 1 scope:
- Observe: read miner status
- Summarize: append summaries to event spine

No direct miner control, payout-target mutation, or inbox composition.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pathlib import Path


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


def _resolve_daemon_url() -> str:
    """Resolve the daemon URL from environment or defaults."""
    return os.environ.get('ZEND_DAEMON_URL', 'http://127.0.0.1:8080')


def _resolve_state_dir() -> str:
    """Resolve the state directory."""
    return os.environ.get('ZEND_STATE_DIR', str(Path(__file__).resolve().parents[2] / "state"))


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
        # Token format: device_name:capabilities:expires (base64 encoded JSON in production)
        # For milestone 1, we store pairings in the pairing store
        try:
            device_name, capabilities_raw = authority_token.split(':')
            capabilities = capabilities_raw.split(',')
        except ValueError:
            raise ValueError("Invalid authority token format")

        # Validate capabilities are allowed
        allowed = {c.value for c in HermesCapability}
        for cap in capabilities:
            if cap not in allowed:
                raise ValueError(f"Unsupported capability: {cap}")

        self._connection = HermesConnection(
            principal_id=self._load_principal_id(),
            device_name=device_name,
            capabilities=capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at="2099-01-01T00:00:00Z"  # milestone 1: no expiration
        )

        return self._connection

    def readStatus(self) -> MinerSnapshot:
        """
        Read current miner status (requires 'observe' capability).

        Returns cached snapshot from the daemon.
        """
        self._require_capability(HermesCapability.OBSERVE)

        url = f"{self._daemon_url}/status"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to read status: {e}")

        return MinerSnapshot(
            status=data['status'],
            mode=data['mode'],
            hashrate_hs=data['hashrate_hs'],
            temperature=data['temperature'],
            uptime_seconds=data['uptime_seconds'],
            freshness=data['freshness']
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
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "home-miner-daemon"))
        from store import load_or_create_principal
        return load_or_create_principal()
