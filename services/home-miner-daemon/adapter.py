#!/usr/bin/env python3
"""
Hermes Adapter for Zend Gateway.

Connects Hermes Gateway to Zend-native gateway contract using delegated authority.
Enforces capability boundaries: observe-only and summarize for milestone 1.1.
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

# Handle relative imports when running as script vs as module
try:
    from .spine import append_hermes_summary, get_events, EventKind
    from .store import load_or_create_principal, get_pairing_by_device
except ImportError:
    # Running as script - use absolute imports
    from spine import append_hermes_summary, get_events, EventKind
    from store import load_or_create_principal, get_pairing_by_device


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = None  # Lazily initialized


def _get_state_dir() -> str:
    global STATE_DIR
    if STATE_DIR is None:
        import os
        STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
    return STATE_DIR


class HermesCapability(str, Enum):
    OBSERVE = "observe"
    SUMMARIZE = "summarize"


class HermesAdapterError(Exception):
    """Base error for Hermes adapter."""
    pass


class InvalidTokenError(HermesAdapterError):
    """Token is malformed or invalid."""
    pass


class ExpiredTokenError(HermesAdapterError):
    """Token has expired."""
    pass


class UnauthorizedError(HermesAdapterError):
    """Capability not granted by token."""
    pass


@dataclass
class TokenClaims:
    principal_id: str
    capabilities: list
    expires_at: str
    issued_at: str

    @classmethod
    def from_token(cls, token: str) -> "TokenClaims":
        """
        Parse and validate a Hermes authority token.

        Token format (base64 JSON):
        {
            "principal_id": "...",
            "capabilities": ["observe", "summarize"],
            "expires_at": "ISO8601",
            "issued_at": "ISO8601"
        }
        """
        import base64
        import os

        state_dir = _get_state_dir()
        token_file = os.path.join(state_dir, 'hermes-tokens.json')

        if not os.path.exists(token_file):
            raise InvalidTokenError("Token not found in registry")

        with open(token_file, 'r') as f:
            tokens = json.load(f)

        if token not in tokens:
            raise InvalidTokenError("Token not recognized")

        claims = tokens[token]

        # Check expiration
        expires = datetime.fromisoformat(claims['expires_at'])
        if expires < datetime.now(timezone.utc):
            raise ExpiredTokenError(f"Token expired at {claims['expires_at']}")

        return cls(
            principal_id=claims['principal_id'],
            capabilities=claims['capabilities'],
            expires_at=claims['expires_at'],
            issued_at=claims['issued_at']
        )


@dataclass
class HermesConnection:
    connection_id: str
    claims: TokenClaims
    adapter: "HermesAdapter"
    created_at: str


class HermesAdapter:
    """
    Hermes adapter that connects to Zend gateway with delegated authority.

    Milestone 1.1 capabilities:
    - observe: read miner status
    - summarize: append summaries to event spine
    """

    def __init__(self, state_dir: str = None):
        global STATE_DIR
        if state_dir:
            STATE_DIR = state_dir
        self._connections: dict[str, HermesConnection] = {}

    def _validate_state_dir(self):
        """Ensure state directory is initialized."""
        _get_state_dir()

    def connect(self, authority_token: str) -> HermesConnection:
        """
        Connect to Zend gateway with delegated authority.

        Validates the token and returns a connection object that
        can be used for subsequent operations.
        """
        self._validate_state_dir()

        claims = TokenClaims.from_token(authority_token)

        connection_id = str(uuid.uuid4())
        connection = HermesConnection(
            connection_id=connection_id,
            claims=claims,
            adapter=self,
            created_at=datetime.now(timezone.utc).isoformat()
        )

        self._connections[connection_id] = connection
        return connection

    def disconnect(self, connection_id: str) -> bool:
        """Close a Hermes connection."""
        if connection_id in self._connections:
            del self._connections[connection_id]
            return True
        return False

    def get_connection(self, connection_id: str) -> Optional[HermesConnection]:
        """Get an existing connection by ID."""
        return self._connections.get(connection_id)

    def read_status(self, connection: HermesConnection) -> dict:
        """
        Read current miner status if observe capability is granted.

        Requires 'observe' capability in the connection's token.
        Raises: UnauthorizedError if observe not granted.
        """
        if HermesCapability.OBSERVE.value not in connection.claims.capabilities:
            raise UnauthorizedError(
                f"observe capability not granted. "
                f"Granted: {connection.claims.capabilities}"
            )

        # Import here to avoid circular dependency at module level
        try:
            from .daemon import miner
        except ImportError:
            from daemon import miner

        return miner.get_snapshot()

    def append_summary(
        self,
        connection: HermesConnection,
        summary_text: str
    ):
        """
        Append Hermes summary to event spine if summarize capability granted.

        Requires 'summarize' capability in the connection's token.
        Raises: UnauthorizedError if summarize not granted.
        """
        if HermesCapability.SUMMARIZE.value not in connection.claims.capabilities:
            raise UnauthorizedError(
                f"summarize capability not granted. "
                f"Granted: {connection.claims.capabilities}"
            )

        event = append_hermes_summary(
            summary_text=summary_text,
            authority_scope=connection.claims.capabilities,
            principal_id=connection.claims.principal_id
        )

        return event

    def get_scope(self, connection: HermesConnection) -> list[str]:
        """Return the capabilities granted by the authority token."""
        return list(connection.claims.capabilities)

    def get_hermes_events(self, connection: HermesConnection, limit: int = 50):
        """
        Get Hermes summary events from the event spine.

        Hermes can read:
        - hermes_summary (its own summaries)
        - miner_alert (alerts it may have generated)
        - control_receipt (recent actions)
        """
        if HermesCapability.OBSERVE.value not in connection.claims.capabilities:
            raise UnauthorizedError("observe capability required to read events")

        events = get_events(kind=EventKind.HERMES_SUMMARY, limit=limit)
        return events


def create_hermes_token(
    principal_id: str,
    capabilities: list,
    expires_at: str = None
) -> tuple[str, str]:
    """
    Create a new Hermes authority token for testing.

    Returns: (token, token_data)
    """
    import os
    import base64

    state_dir = _get_state_dir()
    os.makedirs(state_dir, exist_ok=True)

    token = str(uuid.uuid4())
    issued_at = datetime.now(timezone.utc).isoformat()

    if expires_at is None:
        # Default: 24 hours from now
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    token_data = {
        "principal_id": principal_id,
        "capabilities": capabilities,
        "issued_at": issued_at,
        "expires_at": expires_at
    }

    token_file = os.path.join(state_dir, 'hermes-tokens.json')
    tokens = {}

    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            tokens = json.load(f)

    tokens[token] = token_data

    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)

    # Return encoded token for convenience
    encoded = base64.b64encode(json.dumps(token_data).encode()).decode()

    return token, encoded
