"""
Hermes Adapter Service

Provides the HermesAdapter interface for connecting Hermes Gateway
to the Zend-native gateway contract with delegated authority.
"""

from importlib import import_module

__all__ = [
    "HermesAdapter",
    "HermesConnection",
    "MinerSnapshot",
    "HermesSummary",
    "HermesCapability",
    "CapabilityError",
    "issue_authority_token",
]


def __getattr__(name: str):
    if name in __all__:
        module = import_module(".adapter", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
