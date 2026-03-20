#!/usr/bin/env python3
"""
Hermes Adapter — Connects Hermes Gateway to Zend gateway contract.

Enforces capability scoping: observe (read status) and summarize (append summaries).
Direct miner control is NOT permitted in milestone 1.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class HermesCapability(str, Enum):
    """Hermes capabilities in milestone 1."""
    OBSERVE = "observe"
    SUMMARIZE = "summarize"


@dataclass
class MinerSnapshot:
    """Miner status snapshot."""
    status: str  # running | stopped | offline | error
    mode: str  # paused | balanced | performance
    hashrate_hs: int
    temperature: float
    uptime_seconds: int
    freshness: str  # ISO 8601


@dataclass
class HermesSummary:
    """A Hermes-generated summary for the event spine."""
    summary_text: str
    authority_scope: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HermesConnection:
    """Active Hermes connection with delegated authority."""
    connection_id: str
    principal_id: str
    capabilities: list[HermesCapability]
    connected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None


class HermesAdapter:
    """
    Zend-native adapter for Hermes Gateway.

    Enforces capability boundaries before relaying any request.
    Milestone 1: observe-only + summarize (no direct control).
    """

    def __init__(self, gateway_url: str = "http://127.0.0.1:8080"):
        self._gateway_url = gateway_url
        self._connection: Optional[HermesConnection] = None

    def connect(self, authority_token: str) -> HermesConnection:
        """
        Connect to Zend gateway using delegated authority token.

        The token encodes principal ID, granted capabilities, and expiration.
        Raises ValueError if token is invalid or expired.
        """
        from authority import decode_authority_token

        auth = decode_authority_token(authority_token)

        if auth.is_expired:
            raise ValueError("Authority token has expired")

        self._connection = HermesConnection(
            connection_id=str(uuid.uuid4()),
            principal_id=auth.principal_id,
            capabilities=[HermesCapability(c) for c in auth.capabilities],
            connected_at=datetime.now(timezone.utc).isoformat(),
            expires_at=auth.expires_at,
        )
        return self._connection

    def disconnect(self):
        """Close the active Hermes connection."""
        self._connection = None

    def get_scope(self) -> list[HermesCapability]:
        """Return the current authority scope for this connection."""
        if not self._connection:
            return []
        return self._connection.capabilities

    def readStatus(self) -> MinerSnapshot:
        """
        Read current miner status (requires 'observe' capability).

        Raises PermissionError if observe capability not granted.
        """
        self._require_capability(HermesCapability.OBSERVE)

        import json
        import urllib.request

        url = f"{self._gateway_url}/status"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())

        return MinerSnapshot(
            status=data["status"],
            mode=data["mode"],
            hashrate_hs=data["hashrate_hs"],
            temperature=data["temperature"],
            uptime_seconds=data["uptime_seconds"],
            freshness=data["freshness"],
        )

    def appendSummary(self, summary: HermesSummary) -> None:
        """
        Append a Hermes summary to the event spine (requires 'summarize' capability).

        Raises PermissionError if summarize capability not granted.
        """
        self._require_capability(HermesCapability.SUMMARIZE)

        import sys
        import os

        # Add daemon to path for spine access
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "home-miner-daemon"))
        from spine import append_hermes_summary

        append_hermes_summary(
            summary_text=summary.summary_text,
            authority_scope=summary.authority_scope,
            principal_id=self._connection.principal_id,
        )

    def _require_capability(self, capability: HermesCapability):
        """Enforce capability boundary. Raises PermissionError if not granted."""
        if not self._connection:
            raise PermissionError("Not connected to Zend gateway")

        if capability not in self._connection.capabilities:
            raise PermissionError(
                f"Capability '{capability.value}' not granted. "
                f"Granted: {[c.value for c in self._connection.capabilities]}"
            )
