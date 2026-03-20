"""
Hermes Adapter - Connects Hermes Gateway to Zend-native gateway contract.

This adapter provides observe and summarize capabilities for milestone 1:
- observe: Read miner status from the event spine
- summarize: Append summaries to the event spine

The adapter enforces capability boundaries before relaying any request.
"""

from .adapter import HermesAdapter, HermesCapability, MinerSnapshot

__all__ = ["HermesAdapter", "HermesCapability", "MinerSnapshot"]