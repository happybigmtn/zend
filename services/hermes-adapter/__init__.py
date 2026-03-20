"""
Hermes Adapter Service

This module provides the Zend-native adapter that connects Hermes Gateway
to the Zend gateway contract through delegated authority.

Usage:
    from adapter import HermesAdapter

    adapter = HermesAdapter("/path/to/state.json")
    scope = adapter.get_scope()
    connection = adapter.connect(authority_token)
    snapshot = adapter.read_status()
    adapter.append_summary(summary)
"""

from .adapter import (
    HermesAdapter,
    HermesCapability,
    HermesConnection,
    HermesSummary,
    MinerSnapshot,
)

__all__ = [
    "HermesAdapter",
    "HermesCapability",
    "HermesConnection",
    "HermesSummary",
    "MinerSnapshot",
]