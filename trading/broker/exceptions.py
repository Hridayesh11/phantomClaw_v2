"""
trading/broker/exceptions.py
----------------------------
Broker-specific exceptions.
"""

class OrderExecutionError(Exception):
    """Base class for order execution failures."""
    pass

class InsufficientFundsError(OrderExecutionError):
    """Raised when buying power is insufficient for an order."""
    pass

class InsufficientSharesError(OrderExecutionError):
    """Raised when attempting to sell more shares than owned."""
    pass

class InvalidOrderError(OrderExecutionError):
    """Raised when an order is malformed or invalid."""
    pass
