"""
trading/interfaces.py
---------------------
Abstract Base Classes for the trading engine.
Enforces SOLID principles and allows hot-swapping simulated components
with live components (e.g. PaperBroker -> UpstoxBroker).
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from trading.models import Order, TradeFill


class BaseFeeModel(ABC):
    """Strategy interface for calculating brokerage fees."""
    
    @abstractmethod
    def calculate_fee(self, price: float, quantity: int) -> float:
        """Returns the fee amount for a given execution."""
        pass


class BaseSlippageModel(ABC):
    """Strategy interface for simulating market slippage."""
    
    @abstractmethod
    def apply_slippage(self, price: float, quantity: int, side: str) -> float:
        """Returns the actual fill price after slippage is applied."""
        pass


class BaseBroker(ABC):
    """
    Interface for a broker execution gateway.
    Can be implemented as a PaperBroker or a LiveBroker (Upstox, Alpaca, etc).
    """

    @abstractmethod
    def submit_order(self, order: Order, current_price: float) -> Optional[TradeFill]:
        """
        Submit an order for execution.
        For paper trading, execution is synchronous and returns a TradeFill or None.
        For live trading, this might return None immediately and trigger async events later.
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open pending order."""
        pass

    @abstractmethod
    def get_cash_balance(self) -> float:
        """Return the available cash balance."""
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, int]:
        """Return a mapping of symbol -> quantity for all open positions."""
        pass
