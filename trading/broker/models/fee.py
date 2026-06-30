"""
trading/broker/models/fee.py
----------------------------
Implementations of BaseFeeModel using the Strategy Pattern.
"""

from trading.interfaces import BaseFeeModel


class PercentageFeeModel(BaseFeeModel):
    """
    Calculates fee as a percentage of total trade value.
    Example: 0.001 (0.1%) of trade value.
    """
    def __init__(self, percentage: float):
        if percentage < 0:
            raise ValueError("Fee percentage cannot be negative.")
        self.percentage = percentage

    def calculate_fee(self, price: float, quantity: int) -> float:
        trade_value = price * quantity
        return trade_value * self.percentage


class FlatFeeModel(BaseFeeModel):
    """
    Calculates a flat fixed fee per order regardless of size.
    Example: 10.0 (Rs 10) per trade.
    """
    def __init__(self, flat_fee: float):
        if flat_fee < 0:
            raise ValueError("Flat fee cannot be negative.")
        self.flat_fee = flat_fee

    def calculate_fee(self, price: float, quantity: int) -> float:
        return self.flat_fee


class ZeroFeeModel(BaseFeeModel):
    """No fees applied."""
    
    def calculate_fee(self, price: float, quantity: int) -> float:
        return 0.0
