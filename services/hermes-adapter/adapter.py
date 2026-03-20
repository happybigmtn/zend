#!/usr/bin/env python3
"""
Zend Hermes Adapter

Connects Hermes Gateway to the Zend-native gateway contract through
delegated authority. Enforces capability boundaries.

Authority scope for milestone 1:
- observe: read miner status
- summarize: append summaries to event spine

Direct miner control through Hermes is NOT part of milestone 1.
"""

import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

# Add home-miner-daemon to path for shared modules
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "services" / "home-miner-daemon"))

from store import load_or_create_principal
from spine import append_hermes_summary, get_events, EventKind


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())


class HermesCapability(str, Enum):
    OBSERVE = "observe"
    SUMMARIZE = "summarize"


@dataclass
class HermesConnection:
    """Active Hermes connection with delegated authority."""
    connection_id: str
    principal_id: str
    capabilities: list
    connected_at: str
    expires_at: str


@dataclass
class HermesAdapter:
    """
    Zend Hermes Adapter implementing the delegated authority interface.

    Enforces milestone 1 boundaries:
    - No direct control commands
    - No payout-target mutation
    - No inbox message composition
    - Read-only access to user messages
    """

    def __init__(self):
        self._connection: Optional[HermesConnection] = None
        self._principal: Optional[dict] = None

    def connect(self, authority_token: str) -> HermesConnection:
        """
        Connect to Zend gateway with delegated authority.

        In milestone 1, authority_token is a simple principal identifier.
        Real token validation (JWT, signature verification) is deferred.
        """
        if not authority_token:
            raise ValueError("authority_token is required")

        # Load or create principal for Hermes
        principal = load_or_create_principal()
        self._principal = asdict(principal)

        # Milestone 1: Hermes starts with observe + summarize capabilities
        capabilities = [HermesCapability.OBSERVE.value, HermesCapability.SUMMARIZE.value]

        # Create connection record
        self._connection = HermesConnection(
            connection_id=str(uuid.uuid4()),
            principal_id=principal.id,
            capabilities=capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
            expires_at=datetime.now(timezone.utc).isoformat(),  # No expiry in milestone 1
        )

        return self._connection

    def read_status(self) -> dict:
        """
        Read current miner status (requires observe capability).

        Returns cached snapshot from the home-miner-daemon via the event spine.
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")

        if HermesCapability.OBSERVE.value not in self._connection.capabilities:
            raise PermissionError("observe capability not granted")

        # Get latest control receipt as proxy for miner status
        # In a real implementation, this would query the daemon directly
        events = get_events(EventKind.CONTROL_RECEIPT, limit=1)
        if events:
            latest = events[0]
            return {
                "status": "ok",
                "mode": latest.payload.get("mode", "unknown"),
                "last_command": latest.payload.get("command", "none"),
                "principal_id": self._connection.principal_id,
            }

        return {
            "status": "ok",
            "mode": "paused",
            "last_command": "none",
            "principal_id": self._connection.principal_id,
        }

    def readStatus(self) -> dict:
        """Compatibility alias for the approved adapter contract."""
        return self.read_status()

    def append_summary(self, summary_text: str) -> dict:
        """
        Append a summary to the event spine (requires summarize capability).

        In milestone 1, Hermes can only write hermes_summary events.
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")

        if HermesCapability.SUMMARIZE.value not in self._connection.capabilities:
            raise PermissionError("summarize capability not granted")

        if not summary_text:
            raise ValueError("summary_text is required")

        event = append_hermes_summary(
            summary_text=summary_text,
            authority_scope=self._connection.capabilities,
            principal_id=self._connection.principal_id,
        )

        return {
            "event_id": event.id,
            "kind": event.kind,
            "created_at": event.created_at,
        }

    def appendSummary(self, summary_text: str) -> dict:
        """Compatibility alias for the approved adapter contract."""
        return self.append_summary(summary_text)

    def get_scope(self) -> list:
        """Get the current authority scope."""
        if not self._connection:
            return []
        return self._connection.capabilities

    def getScope(self) -> list:
        """Compatibility alias for the approved adapter contract."""
        return self.get_scope()

    @property
    def is_connected(self) -> bool:
        """Check if adapter has an active connection."""
        return self._connection is not None


# Singleton adapter instance for CLI use
_adapter: Optional[HermesAdapter] = None


def get_adapter() -> HermesAdapter:
    """Get or create the singleton adapter instance."""
    global _adapter
    if _adapter is None:
        _adapter = HermesAdapter()
    return _adapter


def main():
    """CLI entry point for Hermes adapter."""
    import argparse

    parser = argparse.ArgumentParser(description="Zend Hermes Adapter")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # connect command
    connect_parser = subparsers.add_parser("connect", help="Connect with delegated authority")
    connect_parser.add_argument("--token", required=True, help="Authority token")

    # status command
    status_parser = subparsers.add_parser("status", help="Read miner status (requires observe)")

    # summary command
    summary_parser = subparsers.add_parser("summary", help="Append Hermes summary")
    summary_parser.add_argument("--text", required=True, help="Summary text")

    # scope command
    scope_parser = subparsers.add_parser("scope", help="Show current authority scope")

    args = parser.parse_args()

    adapter = get_adapter()

    if args.command == "connect":
        conn = adapter.connect(args.token)
        print(f"Connected: {conn.connection_id}")
        print(f"Principal: {conn.principal_id}")
        print(f"Capabilities: {', '.join(conn.capabilities)}")

    elif args.command == "status":
        status = adapter.read_status()
        print(json.dumps(status, indent=2))

    elif args.command == "summary":
        result = adapter.append_summary(args.text)
        print(f"Summary appended: {result['event_id']}")

    elif args.command == "scope":
        scope = adapter.get_scope()
        if scope:
            print(f"Authority scope: {', '.join(scope)}")
        else:
            print("Not connected")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
