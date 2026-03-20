"""
Compatibility wrapper exposing the reviewed token.py module name.
"""

from auth_token import (
    create_hermes_token,
    mark_token_used,
    revoke_token,
    validate_token,
)

__all__ = [
    "create_hermes_token",
    "mark_token_used",
    "revoke_token",
    "validate_token",
]
