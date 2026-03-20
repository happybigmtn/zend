"""
Authority token validation for Hermes adapter.

Tokens are issued by the Zend gateway during Hermes pairing flow.
They encode principal ID, granted capabilities, and expiration.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from errors import HermesUnauthorizedError
from models import AuthorityToken, HermesCapability


def _get_tokens_path() -> str:
    """Resolve path to tokens store."""
    state_dir = os.environ.get(
        "ZEND_STATE_DIR",
        str(Path(__file__).resolve().parents[2] / "state")
    )
    return os.path.join(state_dir, "hermes-tokens.json")


def _load_tokens() -> dict:
    """Load token store."""
    path = _get_tokens_path()
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def _save_tokens(tokens: dict):
    """Save token store."""
    path = _get_tokens_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(tokens, f, indent=2)


def validate_token(token_str: str) -> AuthorityToken:
    """
    Validate an authority token.

    Checks:
    1. Token exists in store
    2. Token is not expired
    3. Token has not been replayed (used flag)

    Returns decoded AuthorityToken if valid.
    Raises HermesUnauthorizedError if invalid.
    """
    tokens = _load_tokens()

    if token_str not in tokens:
        raise HermesUnauthorizedError(f"Token not found: {token_str[:8]}...")

    data = tokens[token_str]
    token = AuthorityToken(**data)

    # Check expiration
    expires = datetime.fromisoformat(token.expires_at)
    if datetime.now(timezone.utc) > expires:
        raise HermesUnauthorizedError(f"Token expired at {token.expires_at}")

    # Check for replay
    if token.used:
        raise HermesUnauthorizedError("Token has already been used (replay attack)")

    return token


def mark_token_used(token_str: str):
    """Mark a token as used to prevent replay."""
    tokens = _load_tokens()
    if token_str in tokens:
        tokens[token_str]["used"] = True
        _save_tokens(tokens)


def create_hermes_token(
    principal_id: str,
    capabilities: list[HermesCapability],
    ttl_seconds: int = 3600
) -> tuple[str, AuthorityToken]:
    """
    Create a new Hermes authority token.

    This is called by the gateway during Hermes pairing flow.
    Returns (token_string, AuthorityToken).
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=ttl_seconds)

    token = AuthorityToken(
        principal_id=principal_id,
        capabilities=capabilities,
        issued_at=now.isoformat(),
        expires_at=expires.isoformat(),
        token_id=str(uuid.uuid4()),
        used=False,
    )

    token_str = str(uuid.uuid4())
    tokens = _load_tokens()
    tokens[token_str] = {
        "principal_id": token.principal_id,
        "capabilities": token.capabilities,
        "issued_at": token.issued_at,
        "expires_at": token.expires_at,
        "token_id": token.token_id,
        "used": token.used,
    }
    _save_tokens(tokens)

    return token_str, token


def revoke_token(token_str: str):
    """Revoke a token by marking it used."""
    mark_token_used(token_str)