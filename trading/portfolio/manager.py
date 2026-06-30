"""
trading/portfolio/manager.py
----------------------------
Central source of truth for account state.
Manages cash balance, active positions, and portfolio constraints.
Decoupled from execution; updates happen strictly via TradeFills.
"""

import logging
from typing import Dict, List, Optional

from trading.models import OrderSide, TradeFill
from trading.portfolio.position import Position

logger = logging.getLogger(__name__)


class PortfolioManager:
    """
    Manages the aggregate state of the paper trading account.
    Designed as an in-memory singleton for Phase 5.
    """
    
    def __init__(self, initial_cash: float = 100_000.0):
        self.initial_cash: float = initial_cash
        self.cash: float = initial_cash
        self.positions: Dict[str, Position] = {}
        
    def apply_fill(self, fill: TradeFill) -> None:
        """
        Process an execution event from the broker.
        Updates cash balances and delegates position math.
        """
        symbol = fill.symbol
        
        # 1. Update Cash
        if fill.side == OrderSide.BUY:
            # Buying deducts cash (cost of shares + fees)
            cost = (fill.price * fill.quantity) + fill.fees
            self.cash -= cost
        else:
            # Selling adds cash (revenue from shares - fees)
            revenue = (fill.price * fill.quantity) - fill.fees
            self.cash += revenue
            
        # 2. Update Position
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
            
        position = self.positions[symbol]
        position.apply_fill(fill.side, fill.quantity, fill.price)
        
        # Optional cleanup: remove closed positions from active dict
        if position.quantity == 0:
            # We keep it for Realized PnL records in a real system, 
            # but for a simple active registry, it can remain with quantity 0.
            pass
            
        logger.info(
            "Portfolio updated | %s %s | Cash: %.2f | Qty: %d",
            fill.side.value, symbol, self.cash, position.quantity
        )

    def get_buying_power(self) -> float:
        """Return available cash. Can be expanded for margin lending."""
        return self.cash
        
    def get_position(self, symbol: str) -> Optional[Position]:
        """Return the active position for a symbol, if any."""
        pos = self.positions.get(symbol)
        if pos and pos.quantity > 0:
            return pos
        return None

    def get_all_positions(self) -> List[Position]:
        """Return all open positions."""
        return [p for p in self.positions.values() if p.quantity > 0]

    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate total account equity: Cash + Sum(Position Value).
        Requires a dictionary mapping symbols to their current market price.
        """
        total_equity = self.cash
        
        for symbol, pos in self.positions.items():
            if pos.quantity > 0:
                price = current_prices.get(symbol, pos.average_entry_price)
                total_equity += (pos.quantity * price)
                
        return total_equity
        
    def reset(self) -> None:
        """Reset the portfolio to its initial state. Useful for testing."""
        self.cash = self.initial_cash
        self.positions.clear()
