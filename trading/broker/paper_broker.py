"""
trading/broker/paper_broker.py
------------------------------
Simulated broker implementation for paper trading.
Adheres to the BaseBroker interface.
"""

import logging
from typing import Dict, Optional
from uuid import uuid4

from trading.broker.exceptions import InsufficientFundsError, InsufficientSharesError, InvalidOrderError
from trading.interfaces import BaseBroker, BaseFeeModel, BaseSlippageModel
from trading.models import Order, OrderSide, OrderStatus, TradeFill
from trading.portfolio.manager import PortfolioManager

logger = logging.getLogger(__name__)


class PaperBroker(BaseBroker):
    """
    Simulates a live broker environment.
    Evaluates orders against a PortfolioManager for margin constraints,
    applies slippage and fees, and returns synchronous TradeFills.
    """
    
    def __init__(
        self, 
        portfolio_manager: PortfolioManager,
        fee_model: BaseFeeModel,
        slippage_model: BaseSlippageModel
    ):
        self.portfolio = portfolio_manager
        self.fee_model = fee_model
        self.slippage_model = slippage_model
        
    def submit_order(self, order: Order, current_price: float) -> Optional[TradeFill]:
        """
        Execute an order synchronously for paper trading.
        """
        logger.info("Broker received order: %s %d %s (Type: %s)", order.side.value, order.quantity, order.symbol, order.order_type.value)
        
        # Phase 5: Only supporting Market orders for immediate execution for now.
        # Limit/Stop orders would require a pending queue evaluated on every tick.
        if order.order_type != "MARKET":
            logger.warning("PaperBroker currently only simulates MARKET orders. Marking as REJECTED.")
            order.status = OrderStatus.REJECTED
            order.reject_reason = f"Unsupported order type: {order.order_type.value}"
            return None
            
        if order.quantity <= 0:
            raise InvalidOrderError("Order quantity must be positive.")

        # 1. Apply Slippage to find actual execution price
        fill_price = self.slippage_model.apply_slippage(
            price=current_price,
            quantity=order.quantity,
            side=order.side
        )
        
        # 2. Calculate Fees
        fees = self.fee_model.calculate_fee(
            price=fill_price,
            quantity=order.quantity
        )
        
        # 3. Validate against Portfolio Constraints
        if order.side == OrderSide.BUY:
            total_cost = (fill_price * order.quantity) + fees
            if total_cost > self.portfolio.get_buying_power():
                order.status = OrderStatus.REJECTED
                order.reject_reason = "Insufficient funds"
                raise InsufficientFundsError(
                    f"Cost {total_cost:.2f} exceeds buying power {self.portfolio.get_buying_power():.2f}"
                )
                
        elif order.side == OrderSide.SELL:
            pos = self.portfolio.get_position(order.symbol)
            owned_qty = pos.quantity if pos else 0
            if order.quantity > owned_qty:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "Insufficient shares"
                raise InsufficientSharesError(
                    f"Attempted to sell {order.quantity} shares of {order.symbol}, but only own {owned_qty}."
                )

        # 4. Generate TradeFill
        fill = TradeFill(
            fill_id=uuid4(),
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            fees=fees,
            slippage=abs(fill_price - current_price)
        )
        
        # Update Order metadata
        from datetime import datetime
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.utcnow()
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.fees_paid = fees
        
        logger.info("Broker executed fill: %s %d %s @ %.2f (Fees: %.2f)", fill.side.value, fill.quantity, fill.symbol, fill.price, fill.fees)
        
        return fill

    def cancel_order(self, order_id: str) -> bool:
        """Paper broker currently executes instantly, so cancel is a no-op."""
        logger.warning("Cancel order requested for %s, but paper orders execute instantly.", order_id)
        return False

    def get_cash_balance(self) -> float:
        """Return the available cash balance by proxying the portfolio."""
        return self.portfolio.get_buying_power()

    def get_positions(self) -> Dict[str, int]:
        """Return a mapping of symbol -> quantity for all open positions."""
        return {pos.symbol: pos.quantity for pos in self.portfolio.get_all_positions()}
