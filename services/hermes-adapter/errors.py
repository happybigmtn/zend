"""
Hermes Adapter error types.
"""


class HermesError(Exception):
    """Base error for Hermes adapter."""


class HermesUnauthorizedError(HermesError):
    """Raised when authority token is invalid or expired."""


class HermesCapabilityError(HermesError):
    """Raised when action requires capability not in scope."""


class HermesConnectionError(HermesError):
    """Raised when cannot connect to Zend gateway."""