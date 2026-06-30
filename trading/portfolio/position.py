"""
trading/portfolio/position.py
-----------------------------
Tracks the state of a single holding in the portfolio.
"""

from typing import Optional
from pydantic import BaseModel, Field

from trading.models import OrderSide


class Position(BaseModel):
    """
    Represents an open holding for a single symbol.
    Provides mathematical methods to handle fills and compute PnL.
    """
    symbol: str
    quantity: int = Field(default=0, description="Current number of shares held")
    average_entry_price: float = Field(default=0.0, description="Volume-weighted average entry price")
    realized_pnl: float = Field(default=0.0, description="Cumulative realized PnL from closed portions")

    def apply_fill(self, side: OrderSide, fill_quantity: int, fill_price: float) -> None:
        """
        Update position math based on a new trade fill.
        Currently assumes Long-only trading (no short selling).
        """
        if fill_quantity <= 0:
            raise ValueError("Fill quantity must be positive.")

        if side == OrderSide.BUY:
            # Long Buy: Increase quantity, compute new volume-weighted average price (VWAP)
            total_cost = (self.quantity * self.average_entry_price) + (fill_quantity * fill_price)
            self.quantity += fill_quantity
            self.average_entry_price = total_cost / self.quantity

        elif side == OrderSide.SELL:
            # Long Sell: Decrease quantity, realize PnL
            if fill_quantity > self.quantity:
                raise ValueError(
                    f"Cannot sell {fill_quantity} shares of {self.symbol}. Only {self.quantity} owned."
                )
            
            # PnL = (Sell Price - Average Entry Price) * Quantity
            trade_pnl = (fill_price - self.average_entry_price) * fill_quantity
            self.realized_pnl += trade_pnl
            
            self.quantity -= fill_quantity
            
            # Reset entry price if position is fully closed
            if self.quantity == 0:
                self.average_entry_price = 0.0

    def get_unrealized_pnl(self, current_market_price: Optional[float]) -> float:
        """
        Calculate unrealized PnL based on a current market price.
        Returns 0.0 if quantity is 0 or market price is unknown.
        """
        if self.quantity == 0 or current_market_price is None:
            return 0.0
            
        return (current_market_price - self.average_entry_price) * self.quantity
