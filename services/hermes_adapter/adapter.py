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
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
import base64


# Resolve paths relative to this file's location
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


STATE_DIR = os.environ.get("ZEND_STATE_DIR", str(_repo_root() / "state"))
DAEMON_URL = os.environ.get("ZEND_DAEMON_URL", "http://127.0.0.1:8080")
DEFAULT_HERMES_DEVICE = "hermes-gateway"
DEFAULT_AUTHORITY_TOKEN_PATH = Path(STATE_DIR) / f"{DEFAULT_HERMES_DEVICE}.authority-token"
DEFAULT_TOKEN_TTL = timedelta(hours=1)

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

    def __init__(
        self,
        principal_id: str,
        device_name: str,
        pairing_id: str,
        capabilities: list[HermesCapability],
    ):
        self.principal_id = principal_id
        self.device_name = device_name
        self.pairing_id = pairing_id
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
        principal_id, device_name, pairing_id, capabilities = self._validate_token(
            authority_token
        )
        self._connection = HermesConnection(
            principal_id=principal_id,
            device_name=device_name,
            pairing_id=pairing_id,
            capabilities=capabilities,
        )
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

        from spine import append_hermes_summary

        event = append_hermes_summary(
            summary_text=summary.summary_text,
            authority_scope=summary.authority_scope,
            principal_id=self._connection.principal_id,
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

    def _validate_token(
        self, token: str
    ) -> tuple[str, str, str, list[HermesCapability]]:
        """
        Validate an authority token and return store-backed pairing details.

        Token format for milestone 1: base64(json({
          "pairing_id": "<uuid>",
          "principal_id": "<uuid>",
          "device_name": "hermes-gateway",
          "capabilities": ["observe", "summarize"],
          "expires_at": "<iso8601>"
        }))

        Returns (principal_id, device_name, pairing_id, capabilities).
        Raises ValueError if invalid.
        """
        from store import load_or_create_principal, load_pairings

        try:
            decoded = base64.b64decode(token).decode()
            payload = json.loads(decoded)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid authority token: {e}") from e

        pairing_id = payload.get("pairing_id")
        if not pairing_id:
            raise ValueError("Token missing pairing_id")

        principal_id = payload.get("principal_id")
        if not principal_id:
            raise ValueError("Token missing principal_id")

        device_name = payload.get("device_name")
        if not device_name:
            raise ValueError("Token missing device_name")

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
        else:
            raise ValueError("Token missing expires_at")

        principal = load_or_create_principal()
        if principal.id != principal_id:
            raise ValueError("Token principal_id does not match local principal")

        pairings = load_pairings()
        pairing = pairings.get(pairing_id)
        if pairing is None:
            raise ValueError("Token references unknown pairing")

        if pairing.get("principal_id") != principal_id:
            raise ValueError("Token principal_id does not match stored pairing")

        if pairing.get("device_name") != device_name:
            raise ValueError("Token device_name does not match stored pairing")

        granted_capabilities = set(pairing.get("capabilities", []))
        for capability in capabilities:
            if capability.value not in granted_capabilities:
                raise ValueError(
                    f"Token capability '{capability.value}' not granted to {device_name}"
                )

        return principal_id, device_name, pairing_id, capabilities


def issue_authority_token(
    device_name: str = DEFAULT_HERMES_DEVICE,
    capabilities: Optional[list[str | HermesCapability]] = None,
    expires_at: Optional[str] = None,
) -> str:
    """
    Issue a delegated Hermes authority token from the stored pairing record.

    The token scope must be a subset of the paired Hermes capabilities.
    """
    from store import get_pairing_by_device, load_or_create_principal

    pairing = get_pairing_by_device(device_name)
    if pairing is None:
        raise ValueError(f"Hermes device '{device_name}' is not paired")

    principal = load_or_create_principal()
    if pairing.principal_id != principal.id:
        raise ValueError("Stored Hermes pairing does not belong to the local principal")

    granted_capabilities: list[HermesCapability] = []
    for capability in pairing.capabilities:
        try:
            granted_capabilities.append(HermesCapability(capability))
        except ValueError as exc:
            raise ValueError(
                f"Stored Hermes capability is not supported by this slice: {capability}"
            ) from exc

    granted_values = {capability.value for capability in granted_capabilities}
    requested_capabilities: list[HermesCapability] = []
    raw_capabilities = capabilities or [capability.value for capability in granted_capabilities]
    for capability in raw_capabilities:
        normalized = capability.value if isinstance(capability, HermesCapability) else capability
        enum_value = HermesCapability(normalized)
        if enum_value.value not in granted_values:
            raise ValueError(
                f"Requested capability '{enum_value.value}' is not granted to {device_name}"
            )
        requested_capabilities.append(enum_value)

    if expires_at is None:
        expires_at = (datetime.now(timezone.utc) + DEFAULT_TOKEN_TTL).isoformat()

    payload = {
        "pairing_id": pairing.id,
        "principal_id": principal.id,
        "device_name": pairing.device_name,
        "capabilities": [capability.value for capability in requested_capabilities],
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

    # issue-token command
    issue_token = subparsers.add_parser(
        "issue-token", help="Issue a delegated Hermes authority token"
    )
    issue_token.add_argument(
        "--device",
        default=DEFAULT_HERMES_DEVICE,
        help="Paired Hermes device name",
    )
    issue_token.add_argument(
        "--capabilities",
        help="Comma-separated subset of granted capabilities",
    )

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

        elif args.command == "issue-token":
            requested_capabilities = None
            if args.capabilities:
                requested_capabilities = [
                    capability.strip()
                    for capability in args.capabilities.split(",")
                    if capability.strip()
                ]
            token = issue_authority_token(
                device_name=args.device,
                capabilities=requested_capabilities,
            )
            print(
                json.dumps(
                    {
                        "device_name": args.device,
                        "token": token,
                    },
                    indent=2,
                )
            )

    except CapabilityError as e:
        print(json.dumps({"error": "capability_denied", "message": str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": type(e).__name__, "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
