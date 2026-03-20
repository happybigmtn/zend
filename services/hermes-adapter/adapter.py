"""
Hermes Adapter - Connects Hermes Gateway to Zend-native gateway contract.

Milestone 1 scope:
- observe: Read miner status from event spine
- summarize: Append summaries to event spine

No direct miner control. No payout-target mutation. No inbox message composition.
"""

import base64
import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_STATE_FILE = os.path.join(STATE_DIR, 'hermes-adapter-state.json')
SPINE_FILE = os.path.join(STATE_DIR, 'event-spine.jsonl')


class HermesCapability(str, Enum):
    """Hermes capabilities for milestone 1."""
    OBSERVE = "observe"
    SUMMARIZE = "summarize"


@dataclass
class MinerSnapshot:
    """Current miner status snapshot."""
    status: str  # 'running' | 'stopped' | 'offline' | 'error'
    mode: str    # 'paused' | 'balanced' | 'performance'
    hashrate_hs: float
    temperature: float
    uptime_seconds: int
    freshness: str  # ISO 8601


@dataclass
class HermesConnection:
    """Represents an active Hermes connection to the Zend gateway."""
    connection_id: str
    principal_id: str
    capabilities: list[HermesCapability]
    connected_at: str
    expires_at: Optional[str] = None


@dataclass
class HermesSummary:
    """A Hermes-generated summary for the event spine."""
    summary_text: str
    authority_scope: list[str]
    generated_at: str


class HermesAdapter:
    """
    Hermes Adapter connects Hermes Gateway to Zend-native gateway.

    Capability boundaries (enforced by adapter before relaying):
    - Milestone 1: observe (read status), summarize (append summaries)
    - No direct control commands
    - No payout-target mutation
    - No inbox message composition
    """

    def __init__(self, state_dir: str = STATE_DIR):
        self.state_dir = state_dir
        self.hermes_state_file = os.path.join(state_dir, 'hermes-adapter-state.json')
        self.spine_file = os.path.join(state_dir, 'event-spine.jsonl')
        self._connection: Optional[HermesConnection] = None

    def connect(self, authority_token: str) -> HermesConnection:
        """
        Connect to Zend gateway with delegated authority token.

        The authority token encodes principal ID, granted capabilities,
        and expiration. The adapter validates and stores the connection.
        """
        token_data = self._parse_authority_token(authority_token)
        principal_id = token_data["principal_id"]
        capabilities = self._normalize_capabilities(token_data.get("capabilities"))
        expires_at = self._validate_expiration(token_data.get("expires_at"))

        self._connection = HermesConnection(
            connection_id=str(uuid.uuid4()),
            principal_id=principal_id,
            capabilities=capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at
        )

        self._save_state()
        return self._connection

    def readStatus(self) -> Optional[MinerSnapshot]:
        """
        Read current miner status from event spine.

        Returns:
            MinerSnapshot if observe capability granted and status available
            None if no observe capability or no status found
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")

        if HermesCapability.OBSERVE not in self._connection.capabilities:
            raise PermissionError("observe capability not granted")

        return self._read_snapshot_from_spine()

    def appendSummary(self, summary: HermesSummary) -> str:
        """
        Append a Hermes summary to the event spine.

        Returns:
            Event ID of the appended summary

        Raises:
            PermissionError if summarize capability not granted
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")

        if HermesCapability.SUMMARIZE not in self._connection.capabilities:
            raise PermissionError("summarize capability not granted")

        # Append to event spine
        event = {
            "id": str(uuid.uuid4()),
            "principal_id": self._connection.principal_id,
            "kind": "hermes_summary",
            "payload": {
                "summary_text": summary.summary_text,
                "authority_scope": summary.authority_scope,
                "generated_at": summary.generated_at
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": 1
        }

        with open(self.spine_file, 'a') as f:
            f.write(json.dumps(event) + '\n')

        return event["id"]

    def getScope(self) -> list[HermesCapability]:
        """Get current authority scope from active connection."""
        if not self._connection:
            return []
        return self._connection.capabilities

    def isConnected(self) -> bool:
        """Check if adapter has an active connection."""
        return self._connection is not None

    def disconnect(self):
        """Close the active connection."""
        self._connection = None
        self._save_state()

    def _save_state(self):
        """Persist connection state to disk."""
        if self._connection:
            state = {
                "connection": asdict(self._connection),
                "saved_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            state = {"connection": None, "saved_at": datetime.now(timezone.utc).isoformat()}

        with open(self.hermes_state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _parse_authority_token(self, authority_token: str) -> dict:
        """Decode authority tokens from base64 JSON or raw JSON."""
        token = authority_token.strip()
        if not token:
            raise ValueError("authority token is required")

        parse_errors = []

        try:
            padding = "=" * (-len(token) % 4)
            decoded = base64.b64decode(token + padding).decode()
            token_data = json.loads(decoded)
            if isinstance(token_data, dict):
                return token_data
        except Exception as exc:  # pragma: no cover - best-effort decode path
            parse_errors.append(exc)

        try:
            token_data = json.loads(token)
        except json.JSONDecodeError as exc:
            parse_errors.append(exc)
        else:
            if isinstance(token_data, dict):
                return token_data

        raise ValueError("authority token must be base64-encoded JSON or raw JSON")

    def _normalize_capabilities(self, capabilities_raw: object) -> list[HermesCapability]:
        """Validate supported capabilities declared by the authority token."""
        if not isinstance(capabilities_raw, list):
            raise ValueError("authority token missing capabilities list")

        capabilities = []
        unsupported = []
        for capability in capabilities_raw:
            try:
                capabilities.append(HermesCapability(capability))
            except ValueError:
                unsupported.append(capability)

        if unsupported:
            joined = ", ".join(str(capability) for capability in unsupported)
            raise ValueError(f"authority token includes unsupported capability: {joined}")

        if not capabilities:
            raise ValueError("authority token grants no supported capabilities")

        return capabilities

    def _validate_expiration(self, expires_at: object) -> Optional[str]:
        """Reject expired authority tokens and normalize timestamp formatting."""
        if expires_at in (None, ""):
            return None

        if not isinstance(expires_at, str):
            raise ValueError("authority token expiration must be an ISO 8601 string or null")

        normalized = expires_at.replace("Z", "+00:00")
        try:
            expires = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("authority token expiration must be valid ISO 8601") from exc

        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if expires <= datetime.now(timezone.utc):
            raise ValueError("authority token has expired")

        return expires.isoformat()

    def _read_snapshot_from_spine(self) -> Optional[MinerSnapshot]:
        """
        Reconstruct a coarse miner snapshot from accepted control receipts.

        Milestone 1 Hermes observe access is limited to event-spine state, so we
        derive the latest known status/mode from control receipts for the active
        principal rather than calling the miner daemon directly.
        """
        if not os.path.exists(self.spine_file):
            return None

        status = "stopped"
        mode = "paused"
        freshness = None
        found_receipt = False

        with open(self.spine_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("kind") != "control_receipt":
                    continue

                if event.get("principal_id") != self._connection.principal_id:
                    continue

                payload = event.get("payload") or {}
                if payload.get("status") != "accepted":
                    continue

                command = payload.get("command")
                if command == "start":
                    status = "running"
                elif command == "stop":
                    status = "stopped"
                elif command == "set_mode" and payload.get("mode") in {
                    "paused",
                    "balanced",
                    "performance",
                }:
                    mode = payload["mode"]

                freshness = event.get("created_at") or freshness
                found_receipt = True

        if not found_receipt:
            return None

        hashrate_hs = 0.0
        if status == "running":
            if mode == "balanced":
                hashrate_hs = 50000.0
            elif mode == "performance":
                hashrate_hs = 150000.0

        return MinerSnapshot(
            status=status,
            mode=mode,
            hashrate_hs=hashrate_hs,
            temperature=45.0,
            uptime_seconds=0,
            freshness=freshness or datetime.now(timezone.utc).isoformat()
        )

    @classmethod
    def from_state(cls, state_dir: str = STATE_DIR) -> "HermesAdapter":
        """Restore adapter from saved state."""
        adapter = cls(state_dir=state_dir)
        state_file = os.path.join(state_dir, 'hermes-adapter-state.json')

        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                if state.get("connection"):
                    conn_data = state["connection"]
                    adapter._connection = HermesConnection(
                        connection_id=conn_data["connection_id"],
                        principal_id=conn_data["principal_id"],
                        capabilities=[HermesCapability(c) for c in conn_data["capabilities"]],
                        connected_at=conn_data["connected_at"],
                        expires_at=conn_data.get("expires_at")
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        return adapter
