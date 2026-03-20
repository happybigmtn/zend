"""
Hermes Adapter - Connects Hermes Gateway to Zend gateway contract.

Enforces capability boundaries: only observe and summarize in milestone 1.
No direct miner control, no payout mutation, no inbox message composition.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Import from sibling modules (home-miner-daemon)
_DAEMON_DIR = Path(__file__).resolve().parents[1] / "home-miner-daemon"
sys.path.insert(0, str(_DAEMON_DIR))

from errors import (
    HermesError,
    HermesUnauthorizedError,
    HermesCapabilityError,
    HermesConnectionError,
)
from models import (
    AuthorityToken,
    HermesCapability,
    HermesConnection,
    HermesSummary,
    MinerSnapshot,
    make_summary_text,
)
from auth_token import validate_token, mark_token_used


class HermesAdapter:
    """
    Zend-native adapter for Hermes Gateway.

    Connects to Zend gateway contract using delegated authority.
    Enforces capability boundaries: observe and summarize only.

    Usage:
        adapter = HermesAdapter()
        conn = adapter.connect(authority_token="...")
        status = adapter.readStatus()
        adapter.appendSummary(HermesSummary(...))
        scope = adapter.getScope()
    """

    def __init__(self, daemon_host: str = "127.0.0.1", daemon_port: int = 8080):
        """
        Initialize Hermes adapter.

        Args:
            daemon_host: Zend gateway host (default: 127.0.0.1)
            daemon_port: Zend gateway port (default: 8080)
        """
        self._daemon_host = daemon_host
        self._daemon_port = daemon_port
        self._connection: Optional[HermesConnection] = None
        self._token: Optional[AuthorityToken] = None

    def connect(self, authority_token: str) -> HermesConnection:
        """
        Connect to Zend gateway with delegated authority.

        Validates token and establishes connection if authorized.
        Marks token as used to prevent replay attacks.

        Args:
            authority_token: Token issued by Zend gateway during pairing

        Returns:
            HermesConnection with principal_id and capabilities

        Raises:
            HermesUnauthorizedError: If token is invalid, expired, or replayed
            HermesConnectionError: If cannot reach Zend gateway
        """
        try:
            token = validate_token(authority_token)
        except HermesUnauthorizedError:
            raise
        except Exception as e:
            raise HermesConnectionError(f"Failed to validate token: {e}")

        # Mark token used to prevent replay
        mark_token_used(authority_token)

        # Create connection
        self._connection = HermesConnection(
            principal_id=token.principal_id,
            capabilities=token.capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
            expires_at=token.expires_at,
        )
        self._token = token

        return self._connection

    def readStatus(self) -> MinerSnapshot:
        """
        Read current miner status if observe capability granted.

        Returns:
            MinerSnapshot with current miner state and freshness timestamp

        Raises:
            HermesCapabilityError: If observe capability not granted
            HermesConnectionError: If not connected or daemon unreachable
        """
        self._check_connected()
        self._check_capability("observe")

        try:
            import json
            from urllib.request import urlopen
            from urllib.error import URLError

            url = f"http://{self._daemon_host}:{self._daemon_port}/status"
            with urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                return MinerSnapshot(
                    status=data.get("status", "unknown"),
                    mode=data.get("mode", "unknown"),
                    hashrate_hs=data.get("hashrate_hs", 0),
                    temperature=data.get("temperature", 0.0),
                    uptime_seconds=data.get("uptime_seconds", 0),
                    freshness=data.get("freshness", datetime.now(timezone.utc).isoformat()),
                )
        except URLError as e:
            raise HermesConnectionError(f"Cannot reach daemon at {self._daemon_host}:{self._daemon_port}: {e}")
        except Exception as e:
            raise HermesConnectionError(f"Failed to read status: {e}")

    def appendSummary(self, summary: HermesSummary) -> None:
        """
        Append summary to event spine if summarize capability granted.

        Args:
            summary: HermesSummary to append

        Raises:
            HermesCapabilityError: If summarize capability not granted
            HermesConnectionError: If not connected or spine append fails
        """
        self._check_connected()
        self._check_capability("summarize")

        try:
            # Import spine from sibling module
            from spine import append_hermes_summary

            event = append_hermes_summary(
                summary_text=summary.summary_text,
                authority_scope=summary.authority_scope,
                principal_id=self._connection.principal_id,
            )
            return event
        except Exception as e:
            raise HermesConnectionError(f"Failed to append summary to spine: {e}")

    def getScope(self) -> list[HermesCapability]:
        """
        Get current granted authority scope.

        Returns:
            List of granted capabilities (observe, summarize)

        Raises:
            HermesConnectionError: If not connected
        """
        self._check_connected()
        return list(self._connection.capabilities)

    def isConnected(self) -> bool:
        """Check if adapter has an active connection."""
        return self._connection is not None

    def disconnect(self) -> None:
        """Close the current connection."""
        self._connection = None
        self._token = None

    def _check_connected(self):
        """Raise error if not connected."""
        if self._connection is None:
            raise HermesConnectionError("Not connected. Call connect() first.")

    def _check_capability(self, capability: HermesCapability):
        """
        Raise error if capability not in scope.

        Args:
            capability: Required capability

        Raises:
            HermesCapabilityError: If capability not granted
        """
        if capability not in self._connection.capabilities:
            raise HermesCapabilityError(
                f"Capability '{capability}' not in scope. "
                f"Granted capabilities: {self._connection.capabilities}"
            )