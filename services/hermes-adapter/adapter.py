"""
Hermes adapter for milestone 1 delegated gateway access.

The adapter keeps Hermes on a Zend-owned contract surface and enforces the
milestone 1 boundary: observe miner state and append summaries only.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class HermesCapability(Enum):
    """Capabilities Hermes may receive in milestone 1."""

    OBSERVE = "observe"
    SUMMARIZE = "summarize"


@dataclass
class MinerSnapshot:
    """Cached miner state served through the adapter surface."""

    status: str
    mode: str
    freshness: str
    health: str = "unknown"


@dataclass
class HermesSummary:
    """Summary payload Hermes appends through Zend."""

    id: str
    text: str
    capabilities: List[str]
    principal_id: str
    timestamp: str


@dataclass
class HermesConnection:
    """Active delegated connection details."""

    connected: bool
    authority_scope: List[HermesCapability]
    connected_at: Optional[str] = None


class HermesAdapter:
    """
    Zend-native adapter that mediates Hermes access to the gateway contract.

    Milestone 1 grants:
    - observe: read status
    - summarize: append summaries
    """

    def __init__(self, state_file: str):
        self.state_file = state_file
        self._state = self._load_state()

    def _state_dir(self) -> str:
        return os.path.dirname(self.state_file) or "."

    def _load_state(self) -> Dict[str, Any]:
        os.makedirs(self._state_dir(), exist_ok=True)
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as handle:
                return json.load(handle)

        return {
            "version": 1,
            "adapter_id": "hermes-adapter-001",
            "authority_scope": [cap.value for cap in HermesCapability],
            "connected": False,
            "connected_at": None,
            "last_summary_ts": None,
        }

    def _save_state(self) -> None:
        os.makedirs(self._state_dir(), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)

    def _require_connection(self) -> None:
        if not self._state.get("connected", False):
            raise PermissionError("adapter not connected")

    def _parse_authority_token(self, authority_token: str) -> Dict[str, Any]:
        if not authority_token:
            raise ValueError("Authority token is required")

        try:
            payload = base64.b64decode(authority_token.encode("utf-8"), validate=True)
            decoded = json.loads(payload.decode("utf-8"))
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError("Invalid authority token format") from exc

        if not isinstance(decoded, dict):
            raise ValueError("Invalid authority token format")

        principal_id = decoded.get("principal_id")
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ValueError("Invalid token: missing principal_id")

        capabilities = decoded.get("capabilities")
        if not isinstance(capabilities, list):
            raise ValueError("Invalid token: missing capabilities")

        valid_capabilities = {cap.value for cap in HermesCapability}
        normalized_capabilities: List[str] = []
        for capability in capabilities:
            if capability not in valid_capabilities:
                raise ValueError(f"Unknown capability: {capability}")
            normalized_capabilities.append(capability)

        expiration = decoded.get("expiration")
        if not isinstance(expiration, (int, float)):
            raise ValueError("Invalid token: missing expiration")
        if time.time() > float(expiration):
            raise ValueError("Authority token has expired")

        return {
            "principal_id": principal_id.strip(),
            "capabilities": normalized_capabilities,
            "expiration": float(expiration),
        }

    def get_scope(self) -> List[HermesCapability]:
        scope = self._state.get("authority_scope", [])
        return [HermesCapability(capability) for capability in scope]

    def connect(self, authority_token: str) -> HermesConnection:
        decoded = self._parse_authority_token(authority_token)

        self._state["connected"] = True
        self._state["authority_scope"] = decoded["capabilities"]
        self._state["connected_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._save_state()

        return HermesConnection(
            connected=True,
            authority_scope=self.get_scope(),
            connected_at=self._state["connected_at"],
        )

    def read_status(self) -> MinerSnapshot:
        self._require_connection()
        if HermesCapability.OBSERVE not in self.get_scope():
            raise PermissionError("observe capability not granted")

        return MinerSnapshot(
            status="running",
            mode="balanced",
            freshness=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            health="healthy",
        )

    def append_summary(self, summary: HermesSummary) -> None:
        self._require_connection()
        if HermesCapability.SUMMARIZE not in self.get_scope():
            raise PermissionError("summarize capability not granted")

        self._state["last_summary_ts"] = summary.timestamp
        self._save_state()

    def disconnect(self) -> None:
        self._state["connected"] = False
        self._state["connected_at"] = None
        self._save_state()
