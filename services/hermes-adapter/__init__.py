"""
Zend Hermes Adapter

Connects Hermes Gateway to the Zend-native gateway contract using delegated
authority. Enforces capability boundaries (observe/summarize only) before
relaying any request.

Milestone 1 scope:
- observe: read miner status
- summarize: append summaries to event spine
"""

from .adapter import HermesAdapter, HermesCapability, HermesConnection
from .authority import AuthorityToken, decode_authority_token

__all__ = [
    "HermesAdapter",
    "HermesCapability",
    "HermesConnection",
    "AuthorityToken",
    "decode_authority_token",
]