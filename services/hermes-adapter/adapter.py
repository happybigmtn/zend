"""
Hermes adapter for milestone 1 delegated gateway access.

The adapter keeps Hermes on a Zend-owned contract surface and enforces the
milestone 1 boundary: observe miner state and append summaries only.
"""

from __future__ import annotations

import base64
import binascii
import importlib.util
import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


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

    def __init__(
        self,
        state_file: str,
        event_spine_appender: Optional[Callable[[str, List[str], str], Any]] = None,
    ):
        self.state_file = state_file
        self._event_spine_appender = event_spine_appender
        self._state = self._load_state()

    def _state_dir(self) -> str:
        return os.path.dirname(self.state_file) or "."

    def _default_state(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "adapter_id": "hermes-adapter-001",
            "authority_scope": [cap.value for cap in HermesCapability],
            "connected": False,
            "connected_at": None,
            "connected_principal_id": None,
            "connection_expires_at": None,
            "last_summary_ts": None,
        }

    def _load_state(self) -> Dict[str, Any]:
        os.makedirs(self._state_dir(), exist_ok=True)
        state = self._default_state()
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as handle:
                loaded_state = json.load(handle)
            if not isinstance(loaded_state, dict):
                raise ValueError("Hermes adapter state must be a JSON object")
            state.update(loaded_state)
        return state

    def _save_state(self) -> None:
        os.makedirs(self._state_dir(), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)

    def _require_connection(self) -> None:
        if not self._state.get("connected", False):
            raise PermissionError("adapter not connected")
        expiration = self._state.get("connection_expires_at")
        if not isinstance(expiration, (int, float)):
            raise PermissionError("adapter connection missing expiration")
        if time.time() > float(expiration):
            self.disconnect()
            raise PermissionError("authority token has expired")

    def _connected_principal_id(self) -> str:
        principal_id = self._state.get("connected_principal_id")
        if not isinstance(principal_id, str) or not principal_id:
            raise PermissionError("adapter connection missing principal")
        return principal_id

    def _scope_values(self) -> List[str]:
        return [cap.value for cap in self.get_scope()]

    def _resolve_event_spine_appender(self) -> Callable[[str, List[str], str], Any]:
        if self._event_spine_appender is not None:
            return self._event_spine_appender

        spine_path = Path(__file__).resolve().parents[1] / "home-miner-daemon" / "spine.py"
        spec = importlib.util.spec_from_file_location("zend_home_miner_spine", spine_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load event spine appender from {spine_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        appender = getattr(module, "append_hermes_summary", None)
        if appender is None:
            raise RuntimeError("Event spine module does not expose append_hermes_summary")
        return appender

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
        self._state["connected_principal_id"] = decoded["principal_id"]
        self._state["connection_expires_at"] = decoded["expiration"]
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
        if summary.principal_id != self._connected_principal_id():
            raise PermissionError("summary principal does not match connected principal")
        if not isinstance(summary.capabilities, list):
            raise ValueError("summary capabilities must be a list")

        granted_scope = self._scope_values()
        unexpected_capabilities = sorted(set(summary.capabilities) - set(granted_scope))
        if unexpected_capabilities:
            raise PermissionError("summary capabilities exceed granted scope")

        event = self._resolve_event_spine_appender()(
            summary.text,
            granted_scope,
            summary.principal_id,
        )
        created_at = getattr(event, "created_at", None)
        if not isinstance(created_at, str) or not created_at:
            raise RuntimeError("event spine append did not return a created_at timestamp")
        self._state["last_summary_ts"] = created_at
        self._save_state()

    def disconnect(self) -> None:
        self._state["connected"] = False
        self._state["connected_at"] = None
        self._state["connected_principal_id"] = None
        self._state["connection_expires_at"] = None
        self._save_state()
