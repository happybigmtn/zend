#!/usr/bin/env python3
"""
Hermes Adapter

Implements the HermesAdapter interface for milestone 1:
- observe: read miner status from the daemon
- summarize: append summaries to the event spine

Does NOT implement control (milestone 1 boundary).
"""

import json
import os
import sys
import urllib.request
import urllib.error
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


# Resolve paths relative to this file's location
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


STATE_DIR = os.environ.get("ZEND_STATE_DIR", str(_repo_root() / "state"))
DAEMON_URL = os.environ.get("ZEND_DAEMON_URL", "http://127.0.0.1:8080")

sys.path.insert(0, str(_repo_root() / "services" / "home-miner-daemon"))


class HermesCapability(str, Enum):
    OBSERVE = "observe"
    SUMMARIZE = "summarize"


class CapabilityError(Exception):
    """Raised when a Hermes operation lacks the required capability."""
    pass


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
    """A Hermes-generated summary to append to the event spine."""
    summary_text: str
    authority_scope: list[str]
    generated_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class HermesConnection:
    """
    An active Hermes connection with validated authority.

    Returned by HermesAdapter.connect(). Encapsulates the
    granted capability scope for this session.
    """

    def __init__(self, principal_id: str, capabilities: list[HermesCapability]):
        self.principal_id = principal_id
        self.capabilities = capabilities

    def has_capability(self, cap: HermesCapability) -> bool:
        return cap in self.capabilities

    def validate_capability(self, cap: HermesCapability):
        """Raise CapabilityError if the connection lacks the given capability."""
        if not self.has_capability(cap):
            raise CapabilityError(
                f"Operation requires '{cap.value}' capability; "
                f"granted: {[c.value for c in self.capabilities]}"
            )


class HermesAdapter:
    """
    Zend-native adapter that connects Hermes Gateway to the home-miner daemon.

    Milestone 1 scope:
    - observe: read miner status via daemon HTTP API
    - summarize: append summaries to the event spine

    Out of scope (milestone 1 boundaries):
    - control: direct miner commands (not granted to Hermes)
    - inbox message composition
    - payout-target mutation
    """

    def __init__(self, daemon_url: str = DAEMON_URL, state_dir: str = STATE_DIR):
        self.daemon_url = daemon_url
        self.state_dir = state_dir
        self._connection: Optional[HermesConnection] = None

    # -------------------------------------------------------------------------
    # Authority token management
    # -------------------------------------------------------------------------

    def connect(self, authority_token: str) -> HermesConnection:
        """
        Connect to the Zend gateway using a delegated authority token.

        The authority token encodes the principal ID and granted capabilities.
        For milestone 1, Hermes receives 'observe' and/or 'summarize' tokens.

        Returns a HermesConnection with validated scope.
        Raises ValueError if the token is invalid or expired.
        """
        principal_id, capabilities = self._validate_token(authority_token)
        self._connection = HermesConnection(principal_id, capabilities)
        return self._connection

    def get_scope(self) -> list[HermesCapability]:
        """Return the current granted capability scope."""
        if self._connection is None:
            return []
        return self._connection.capabilities

    # -------------------------------------------------------------------------
    # Observe capability
    # -------------------------------------------------------------------------

    def read_status(self) -> MinerSnapshot:
        """
        Read the current miner status snapshot.

        Requires 'observe' capability.

        Returns a MinerSnapshot with current miner state.
        Raises CapabilityError if observe is not granted.
        """
        self._require_connection()
        self._connection.validate_capability(HermesCapability.OBSERVE)

        try:
            url = f"{self.daemon_url}/status"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())

            return MinerSnapshot(
                status=data["status"],
                mode=data["mode"],
                hashrate_hs=data["hashrate_hs"],
                temperature=data["temperature"],
                uptime_seconds=data["uptime_seconds"],
                freshness=data["freshness"],
            )
        except urllib.error.URLError as e:
            raise RuntimeError(f"Daemon unavailable: {e}") from e

    # -------------------------------------------------------------------------
    # Summarize capability
    # -------------------------------------------------------------------------

    def append_summary(self, summary: HermesSummary) -> str:
        """
        Append a Hermes summary to the event spine.

        Requires 'summarize' capability.

        Returns the event ID of the appended summary.
        Raises CapabilityError if summarize is not granted.
        """
        self._require_connection()
        self._connection.validate_capability(HermesCapability.SUMMARIZE)

        from store import load_or_create_principal
        from spine import append_hermes_summary

        principal = load_or_create_principal()

        event = append_hermes_summary(
            summary_text=summary.summary_text,
            authority_scope=summary.authority_scope,
            principal_id=principal.id,
        )
        return event.id

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _require_connection(self):
        if self._connection is None:
            raise RuntimeError(
                "Not connected. Call connect(authority_token) first."
            )

    def _validate_token(self, token: str) -> tuple[str, list[HermesCapability]]:
        """
        Validate an authority token and return (principal_id, capabilities).

        Token format for milestone 1: base64(json({
          "principal_id": "<uuid>",
          "capabilities": ["observe", "summarize"],
          "expires_at": "<iso8601>"
        }))

        Returns (principal_id, capabilities).
        Raises ValueError if invalid.
        """
        import base64

        try:
            decoded = base64.b64decode(token).decode()
            payload = json.loads(decoded)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid authority token: {e}") from e

        principal_id = payload.get("principal_id")
        if not principal_id:
            raise ValueError("Token missing principal_id")

        capabilities_raw = payload.get("capabilities", [])
        capabilities = []
        for cap in capabilities_raw:
            try:
                capabilities.append(HermesCapability(cap))
            except ValueError:
                raise ValueError(f"Unknown capability in token: {cap}") from None

        expires_at = payload.get("expires_at")
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires_dt:
                raise ValueError("Authority token has expired")

        return principal_id, capabilities


def create_hermes_token(
    principal_id: str,
    capabilities: list[HermesCapability],
    expires_at: Optional[str] = None,
) -> str:
    """
    Create an authority token for Hermes (utility function for testing).

    In production, tokens are issued by the Zend gateway pairing flow.
    """
    import base64

    if expires_at is None:
        expires_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "principal_id": principal_id,
        "capabilities": [c.value for c in capabilities],
        "expires_at": expires_at,
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


# -------------------------------------------------------------------------
# CLI entry point
# -------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Hermes Adapter CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status command
    status = subparsers.add_parser("status", help="Read miner status via adapter")
    status.add_argument("--token", required=True, help="Authority token (base64)")

    # summarize command
    summarize = subparsers.add_parser("summarize", help="Append a Hermes summary")
    summarize.add_argument("--token", required=True, help="Authority token (base64)")
    summarize.add_argument("--text", required=True, help="Summary text")

    # scope command
    scope = subparsers.add_parser("scope", help="Show current capability scope")
    scope.add_argument("--token", required=True, help="Authority token (base64)")

    args = parser.parse_args()
    adapter = HermesAdapter()

    try:
        if args.command == "status":
            adapter.connect(args.token)
            snap = adapter.read_status()
            print(json.dumps(asdict(snap), indent=2))

        elif args.command == "summarize":
            adapter.connect(args.token)
            summary = HermesSummary(
                summary_text=args.text,
                authority_scope=[c.value for c in adapter.get_scope()],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
            event_id = adapter.append_summary(summary)
            print(json.dumps({"event_id": event_id}, indent=2))

        elif args.command == "scope":
            adapter.connect(args.token)
            caps = adapter.get_scope()
            print(json.dumps({"capabilities": [c.value for c in caps]}, indent=2))

    except CapabilityError as e:
        print(json.dumps({"error": "capability_denied", "message": str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": type(e).__name__, "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
