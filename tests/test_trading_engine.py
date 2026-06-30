"""
tests/test_trading_engine.py
----------------------------
Unit tests for the TradingEngine orchestrator.
"""

from unittest.mock import MagicMock
from models.trade_model import ExecutionDecision, TradeRecommendation
from trading.engine import TradingEngine
from trading.models import OrderSide


def test_trading_engine_ignores_non_execute():
    engine = TradingEngine()
    
    recommendation = TradeRecommendation(
        symbol="AAPL", action="HOLD", quantity=0, confidence=0.5, reason="Testing"
    )
    decision = ExecutionDecision(decision="HOLD", rationale="Test")
    
    fill = engine.execute_signal(recommendation, decision, 150.0)
    assert fill is None


def test_trading_engine_executes_valid_signal():
    engine = TradingEngine()
    # Mock ledger to avoid DB writes during this pure test
    engine.ledger.record_trade = MagicMock()
    
    recommendation = TradeRecommendation(
        symbol="AAPL", action="BUY", quantity=2, confidence=0.9, reason="Testing"
    )
    decision = ExecutionDecision(decision="EXECUTE", rationale="Test")
    
    fill = engine.execute_signal(recommendation, decision, 100.0)
    
    assert fill is not None
    assert fill.symbol == "AAPL"
    assert fill.side == OrderSide.BUY
    assert fill.quantity == 2
    
    # Verify the portfolio was updated
    assert engine.portfolio.get_position("AAPL").quantity == 2
    
    # Verify ledger was called
    engine.ledger.record_trade.assert_called_once_with(fill)
