"""
trading/engine.py
-----------------
Orchestrator for the trading subsystem.
Bridges the AI pipeline (ExecutionController) to the Execution mechanisms (Brokers).
"""

import logging
from typing import Optional

from models.trade_model import ExecutionDecision, TradeRecommendation
from trading.broker.models.fee import PercentageFeeModel
from trading.broker.models.slippage import PercentageSlippageModel
from trading.broker.paper_broker import PaperBroker
from trading.interfaces import BaseBroker
from trading.ledger import TradeLedger
from trading.models import Order, OrderSide, OrderType, TradeFill
from trading.portfolio.manager import PortfolioManager
from utils.config import config

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    Coordinates the flow of orders from the AI pipeline to the broker,
    updates the portfolio state, and persists trades to the ledger.
    """
    
    def __init__(self, broker: Optional[BaseBroker] = None):
        # Initialize internal state managers
        self.portfolio = PortfolioManager(initial_cash=100_000.0)
        self.ledger = TradeLedger()
        
        # Inject the active broker, defaulting to PaperBroker for Phase 5
        if broker is None:
            # Note: Fee and slippage percentages could be driven by config.
            # Using defaults: 0.1% fee, 0.05% slippage
            fee_pct = getattr(config, "PAPER_BROKERAGE_FEE_PCT", 0.001)
            slip_pct = getattr(config, "PAPER_SLIPPAGE_PCT", 0.0005)
            
            self.broker = PaperBroker(
                portfolio_manager=self.portfolio,
                fee_model=PercentageFeeModel(percentage=fee_pct),
                slippage_model=PercentageSlippageModel(percentage=slip_pct)
            )
        else:
            self.broker = broker

    def execute_signal(
        self, 
        recommendation: TradeRecommendation, 
        decision: ExecutionDecision, 
        current_price: float
    ) -> Optional[TradeFill]:
        """
        Process a final AI trade recommendation.
        If the ExecutionController decided to EXECUTE, route it to the broker.
        """
        if decision.decision != "EXECUTE" or recommendation.quantity <= 0:
            logger.info(
                "TradingEngine: Signal ignored. Decision: %s, Qty: %d",
                decision.decision, recommendation.quantity
            )
            return None

        # 1. Map TradeRecommendation to an Order
        try:
            side = OrderSide(recommendation.action.upper())
        except ValueError:
            logger.warning("Invalid trade action for order: %s", recommendation.action)
            return None

        order = Order(
            symbol=recommendation.symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=recommendation.quantity
        )

        # 2. Submit to Broker
        try:
            fill = self.broker.submit_order(order, current_price)
        except Exception as exc:
            logger.error("Broker execution failed: %s", exc)
            return None

        # 3. Process Fill (if synchronously returned, like in PaperBroker)
        if fill:
            # 3a. Update Portfolio (Cash & Positions)
            self.portfolio.apply_fill(fill)
            
            # 3b. Record to Database Ledger
            try:
                self.ledger.record_trade(fill)
            except Exception as db_exc:
                logger.error("Failed to persist TradeFill to ledger: %s", db_exc)

            return fill
            
        return None

# Singleton instance
_trading_engine: Optional[TradingEngine] = None

def get_trading_engine() -> TradingEngine:
    """Returns a singleton TradingEngine to persist state across FastAPI requests."""
    global _trading_engine
    if _trading_engine is None:
        _trading_engine = TradingEngine()
    return _trading_engine
