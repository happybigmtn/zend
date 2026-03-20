#!/usr/bin/env python3
"""
Authority token handling for Hermes adapter.

The authority token is issued by the Zend gateway during Hermes pairing.
It encodes: principal ID, granted capabilities, and expiration time.
"""

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_TOKEN_FILE = os.path.join(STATE_DIR, "hermes-authority-token.json")


@dataclass
class AuthorityToken:
    """Decoded authority token data."""
    principal_id: str
    capabilities: list[str]  # observe | summarize
    issued_at: str
    expires_at: str

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expires


def encode_authority_token(
    principal_id: str,
    capabilities: list[str],
    expires_at: Optional[str] = None,
) -> str:
    """
    Encode authority token as base64 JSON.

    This is a simplified encoding for milestone 1.
    Real deployment would use proper cryptographic signing.
    """
    if expires_at is None:
        # Default 24-hour expiration
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    payload = {
        "principal_id": principal_id,
        "capabilities": capabilities,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
    }

    data = base64.b64encode(json.dumps(payload).encode()).decode()
    return data


def decode_authority_token(token: str) -> AuthorityToken:
    """
    Decode and validate authority token.

    Raises ValueError if token is malformed.
    """
    try:
        payload = json.loads(base64.b64decode(token.encode()).decode())
    except Exception as e:
        raise ValueError(f"Invalid authority token: {e}")

    required = ["principal_id", "capabilities", "issued_at", "expires_at"]
    for field in required:
        if field not in payload:
            raise ValueError(f"Missing required field in token: {field}")

    return AuthorityToken(
        principal_id=payload["principal_id"],
        capabilities=payload["capabilities"],
        issued_at=payload["issued_at"],
        expires_at=payload["expires_at"],
    )


def load_hermes_token() -> Optional[str]:
    """Load existing Hermes authority token from state."""
    if os.path.exists(HERMES_TOKEN_FILE):
        with open(HERMES_TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None


def save_hermes_token(token: str):
    """Save Hermes authority token to state."""
    with open(HERMES_TOKEN_FILE, "w") as f:
        f.write(token)
