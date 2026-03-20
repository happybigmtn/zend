"""
Importable Hermes adapter package facade for the hyphenated service directory.
"""

from .adapter import HermesAdapter
from .errors import (
    HermesCapabilityError,
    HermesConnectionError,
    HermesError,
    HermesUnauthorizedError,
)
from .models import (
    AuthorityToken,
    HermesCapability,
    HermesConnection,
    HermesSummary,
    MinerSnapshot,
    make_summary_text,
)
from .token import (
    create_hermes_token,
    mark_token_used,
    revoke_token,
    validate_token,
)

__all__ = [
    "AuthorityToken",
    "HermesAdapter",
    "HermesCapability",
    "HermesCapabilityError",
    "HermesConnection",
    "HermesConnectionError",
    "HermesError",
    "HermesSummary",
    "HermesUnauthorizedError",
    "MinerSnapshot",
    "create_hermes_token",
    "make_summary_text",
    "mark_token_used",
    "revoke_token",
    "validate_token",
]
