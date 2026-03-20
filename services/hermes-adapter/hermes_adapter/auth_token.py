"""
Compatibility wrapper exposing authority-token helpers from the service root.
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
