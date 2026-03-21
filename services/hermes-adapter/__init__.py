"""Public exports for the Hermes adapter slice."""

try:
    from .adapter import (
        HermesAdapter,
        HermesCapability,
        HermesConnection,
        HermesSummary,
        MinerSnapshot,
    )
except ImportError:
    from adapter import (
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
