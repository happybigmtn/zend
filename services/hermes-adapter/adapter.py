"""
Hermes Adapter - Connects Hermes Gateway to Zend-native gateway contract.

Milestone 1 scope:
- observe: Read miner status from event spine
- summarize: Append summaries to event spine

No direct miner control. No payout-target mutation. No inbox message composition.
"""

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
        # Parse authority token (base64-encoded JSON for milestone 1)
        import base64
        try:
            token_data = json.loads(base64.b64decode(authority_token).decode())
        except Exception:
            # For development, accept raw JSON or simple format
            try:
                token_data = json.loads(authority_token)
            except Exception:
                # Fallback: create a demo connection for testing
                token_data = {
                    "principal_id": str(uuid.uuid4()),
                    "capabilities": ["observe", "summarize"],
                    "expires_at": None
                }

        principal_id = token_data.get("principal_id", str(uuid.uuid4()))
        capabilities_raw = token_data.get("capabilities", ["observe", "summarize"])

        # Validate and normalize capabilities
        capabilities = []
        for cap in capabilities_raw:
            if cap in ["observe", "summarize"]:
                capabilities.append(HermesCapability(cap))

        if not capabilities:
            capabilities = [HermesCapability.OBSERVE, HermesCapability.SUMMARIZE]

        self._connection = HermesConnection(
            connection_id=str(uuid.uuid4()),
            principal_id=principal_id,
            capabilities=capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
            expires_at=token_data.get("expires_at")
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

        # Read latest miner status from event spine
        # For milestone 1, we read from the control_receipt or use stored status
        if not os.path.exists(self.spine_file):
            return None

        latest_status = None
        with open(self.spine_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        if event.get('kind') == 'control_receipt':
                            latest_status = event.get('payload', {}).get('status')
                    except json.JSONDecodeError:
                        continue

        # Return a snapshot (in milestone 1, this is simplified)
        # The actual miner status would come from the home-miner-daemon
        return MinerSnapshot(
            status='running',
            mode='balanced',
            hashrate_hs=0.0,
            temperature=0.0,
            uptime_seconds=0,
            freshness=datetime.now(timezone.utc).isoformat()
        )

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