"""
trading/broker/models/slippage.py
---------------------------------
Implementations of BaseSlippageModel using the Strategy Pattern.
"""

from trading.interfaces import BaseSlippageModel
from trading.models import OrderSide


class PercentageSlippageModel(BaseSlippageModel):
    """
    Simulates market slippage as a percentage of the quoted price.
    Worsens the execution price for the trader:
    - Buys execute HIGHER than the quoted price.
    - Sells execute LOWER than the quoted price.
    
    Example: 0.0005 (0.05%) slippage on a $100 buy makes the fill price $100.05.
    """
    def __init__(self, percentage: float):
        if percentage < 0:
            raise ValueError("Slippage percentage cannot be negative.")
        self.percentage = percentage

    def apply_slippage(self, price: float, quantity: int, side: str) -> float:
        slippage_amount = price * self.percentage
        
        if side == OrderSide.BUY:
            return price + slippage_amount
        elif side == OrderSide.SELL:
            return price - slippage_amount
        else:
            return price


class ZeroSlippageModel(BaseSlippageModel):
    """No slippage applied (perfect fills)."""
    
    def apply_slippage(self, price: float, quantity: int, side: str) -> float:
        return price
