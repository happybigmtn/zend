"""
Zend Hermes Adapter Service

Connects Hermes Gateway to the Zend-native gateway contract through
delegated authority. Enforces capability boundaries.
"""

from .adapter import HermesAdapter, HermesConnection, HermesCapability, get_adapter

__all__ = ["HermesAdapter", "HermesConnection", "HermesCapability", "get_adapter"]