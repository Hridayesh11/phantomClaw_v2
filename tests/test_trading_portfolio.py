"""
tests/test_trading_portfolio.py
-------------------------------
Unit tests for the trading portfolio subsystem.
"""

import pytest
from trading.models import OrderSide, TradeFill
from trading.portfolio.position import Position
from trading.portfolio.manager import PortfolioManager
from uuid import uuid4
from datetime import datetime


def test_position_math_long_buy():
    pos = Position(symbol="AAPL")
    pos.apply_fill(OrderSide.BUY, 10, 100.0)
    assert pos.quantity == 10
    assert pos.average_entry_price == 100.0
    
    # Average up
    pos.apply_fill(OrderSide.BUY, 10, 110.0)
    assert pos.quantity == 20
    assert pos.average_entry_price == 105.0


def test_position_math_long_sell():
    pos = Position(symbol="AAPL")
    pos.apply_fill(OrderSide.BUY, 10, 100.0)
    
    # Partial sell
    pos.apply_fill(OrderSide.SELL, 5, 120.0)
    assert pos.quantity == 5
    assert pos.average_entry_price == 100.0
    assert pos.realized_pnl == 100.0  # (120 - 100) * 5
    
    # Full close
    pos.apply_fill(OrderSide.SELL, 5, 90.0)
    assert pos.quantity == 0
    assert pos.average_entry_price == 0.0
    assert pos.realized_pnl == 50.0   # 100 + ((90 - 100) * 5)


def test_position_sell_insufficient():
    pos = Position(symbol="AAPL")
    pos.apply_fill(OrderSide.BUY, 10, 100.0)
    with pytest.raises(ValueError, match="Cannot sell"):
        pos.apply_fill(OrderSide.SELL, 15, 100.0)


def test_portfolio_manager_cash_and_positions():
    mgr = PortfolioManager(initial_cash=1000.0)
    
    fill1 = TradeFill(
        order_id=uuid4(), symbol="TSLA", side=OrderSide.BUY,
        quantity=2, price=200.0, fees=5.0
    )
    
    mgr.apply_fill(fill1)
    
    assert mgr.get_buying_power() == 595.0  # 1000 - 400 - 5
    
    pos = mgr.get_position("TSLA")
    assert pos is not None
    assert pos.quantity == 2
    assert pos.average_entry_price == 200.0
    
    fill2 = TradeFill(
        order_id=uuid4(), symbol="TSLA", side=OrderSide.SELL,
        quantity=1, price=250.0, fees=5.0
    )
    
    mgr.apply_fill(fill2)
    assert mgr.get_buying_power() == 840.0  # 595 + 250 - 5
    assert mgr.get_position("TSLA").quantity == 1
    
    # Total portfolio value
    # Cash = 840.0, TSLA qty = 1. Market price 300. Total = 1140.0
    assert mgr.get_portfolio_value({"TSLA": 300.0}) == 1140.0
