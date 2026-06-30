"""
tests/test_trading_broker.py
----------------------------
Unit tests for the trading broker subsystem.
"""

import pytest
from trading.broker.exceptions import InsufficientFundsError, InsufficientSharesError, InvalidOrderError
from trading.broker.models.fee import FlatFeeModel, PercentageFeeModel, ZeroFeeModel
from trading.broker.models.slippage import PercentageSlippageModel, ZeroSlippageModel
from trading.broker.paper_broker import PaperBroker
from trading.models import Order, OrderSide, OrderType, OrderStatus
from trading.portfolio.manager import PortfolioManager


def test_fee_models():
    flat = FlatFeeModel(flat_fee=5.0)
    assert flat.calculate_fee(100.0, 10) == 5.0
    
    pct = PercentageFeeModel(percentage=0.01) # 1%
    assert pct.calculate_fee(100.0, 10) == 10.0 # 1000 * 0.01
    
    zero = ZeroFeeModel()
    assert zero.calculate_fee(100.0, 10) == 0.0


def test_slippage_models():
    slip = PercentageSlippageModel(percentage=0.01) # 1%
    
    # Buy slippage adds to price
    buy_price = slip.apply_slippage(100.0, 10, OrderSide.BUY)
    assert buy_price == 101.0
    
    # Sell slippage subtracts from price
    sell_price = slip.apply_slippage(100.0, 10, OrderSide.SELL)
    assert sell_price == 99.0


def test_paper_broker_successful_buy():
    portfolio = PortfolioManager(initial_cash=1000.0)
    broker = PaperBroker(
        portfolio_manager=portfolio,
        fee_model=ZeroFeeModel(),
        slippage_model=ZeroSlippageModel()
    )
    
    order = Order(symbol="AAPL", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=5)
    fill = broker.submit_order(order, current_price=100.0)
    
    assert fill is not None
    assert fill.symbol == "AAPL"
    assert fill.quantity == 5
    assert fill.price == 100.0
    
    assert order.status == OrderStatus.FILLED
    assert order.filled_price == 100.0


def test_paper_broker_insufficient_funds():
    portfolio = PortfolioManager(initial_cash=400.0)
    broker = PaperBroker(
        portfolio_manager=portfolio,
        fee_model=ZeroFeeModel(),
        slippage_model=ZeroSlippageModel()
    )
    
    order = Order(symbol="AAPL", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=5)
    
    with pytest.raises(InsufficientFundsError):
        broker.submit_order(order, current_price=100.0)
        
    assert order.status == OrderStatus.REJECTED


def test_paper_broker_insufficient_shares():
    portfolio = PortfolioManager(initial_cash=1000.0)
    broker = PaperBroker(
        portfolio_manager=portfolio,
        fee_model=ZeroFeeModel(),
        slippage_model=ZeroSlippageModel()
    )
    
    # Try to sell shares we don't own
    order = Order(symbol="AAPL", side=OrderSide.SELL, order_type=OrderType.MARKET, quantity=5)
    
    with pytest.raises(InsufficientSharesError):
        broker.submit_order(order, current_price=100.0)
        
    assert order.status == OrderStatus.REJECTED
