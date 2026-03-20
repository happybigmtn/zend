"""
Hermes Adapter Service

Provides the HermesAdapter interface for connecting Hermes Gateway
to the Zend-native gateway contract with delegated authority.
"""

from .adapter import HermesAdapter, HermesConnection, MinerSnapshot, HermesSummary
from .adapter import HermesCapability, CapabilityError

__all__ = [
    "HermesAdapter",
    "HermesConnection",
    "MinerSnapshot",
    "HermesSummary",
    "HermesCapability",
    "CapabilityError",
]