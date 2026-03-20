"""
Zend Hermes Adapter

Connects Hermes Gateway to the Zend-native gateway contract using delegated authority.
Keeps Zend future-proof and prevents Hermes from becoming the internal skeleton.
"""

from .adapter import HermesAdapter, HermesConnection
from .errors import (
    HermesError,
    HermesUnauthorizedError,
    HermesCapabilityError,
    HermesConnectionError,
)
from .models import HermesSummary, MinerSnapshot

__all__ = [
    "HermesAdapter",
    "HermesConnection",
    "HermesError",
    "HermesUnauthorizedError",
    "HermesCapabilityError",
    "HermesConnectionError",
    "HermesSummary",
    "MinerSnapshot",
]