"""
Compatibility wrapper exposing Hermes adapter error types from the service root.
"""

from errors import (
    HermesCapabilityError,
    HermesConnectionError,
    HermesError,
    HermesUnauthorizedError,
)

__all__ = [
    "HermesCapabilityError",
    "HermesConnectionError",
    "HermesError",
    "HermesUnauthorizedError",
]
