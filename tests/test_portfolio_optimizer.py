"""
tests/test_portfolio_optimizer.py
---------------------------------
Deterministic tests for the Phase 11 Portfolio Optimization Engine.
"""

import pytest

from models.portfolio_model import PortfolioOptimizationResult
from portfolio.optimizer import (
    apply_kelly_adjustment,
    conservative_kelly_fraction,
    max_portfolio_risk_check,
    max_position_exposure_check,
    optimize_position,
)


def test_risk_overflow_rejected():
    res = optimize_position(
        portfolio_value=100_000,
        current_portfolio_risk_percent=4.0,
        position_value=20_000,
        position_risk_percent=1.5,
        quantity=100,
    )
    # Total risk 5.5% > 5.0%
    assert not res.allowed_trade
    assert res.adjusted_quantity == 0
    assert res.optimization_method == "MAX_RISK"

def test_safe_portfolio_allowed():
    res = optimize_position(
        portfolio_value=100_000,
        current_portfolio_risk_percent=2.0,
        position_value=10_000,
        position_risk_percent=1.0,
        quantity=100,
        win_rate=0.6,
        reward_risk_ratio=2.0
    )
    # Total risk 3.0% <= 5.0%, Exposure 10% <= 20%
    assert res.allowed_trade
    assert res.optimization_method == "KELLY"
    # Kelly fraction: 0.6 - (0.4 / 2.0) = 0.6 - 0.2 = 0.4. Half-Kelly = 0.2
    # Qty = 100 * 0.2 = 20
    assert res.adjusted_quantity == 20

def test_exposure_greater_than_20_rejected():
    res = optimize_position(
        portfolio_value=100_000,
        current_portfolio_risk_percent=1.0,
        position_value=25_000,  # 25% exposure
        position_risk_percent=1.0,
        quantity=100,
    )
    assert not res.allowed_trade
    assert res.adjusted_quantity == 0
    assert res.optimization_method == "MAX_EXPOSURE"

def test_kelly_fraction_between_0_and_1():
    # Negative expectation
    frac1 = conservative_kelly_fraction(win_rate=0.3, reward_risk_ratio=1.0)
    assert frac1 == 0.0
    
    # 100% win rate
    frac2 = conservative_kelly_fraction(win_rate=1.0, reward_risk_ratio=5.0)
    assert 0.0 <= frac2 <= 1.0
    assert frac2 == 0.5  # Half of 1.0

def test_quantity_adjustment_never_below_1():
    adj = apply_kelly_adjustment(quantity=2, kelly_fraction=0.1)
    # 2 * 0.1 = 0.2, int() = 0 -> max(1, 0) -> 1
    assert adj == 1

def test_large_portfolio_no_overflow():
    res = optimize_position(
        portfolio_value=1_000_000_000,
        current_portfolio_risk_percent=1.0,
        position_value=10_000_000,
        position_risk_percent=1.0,
        quantity=100_000,
        win_rate=0.55,
        reward_risk_ratio=2.0
    )
    assert res.allowed_trade
    assert res.adjusted_quantity > 0
    assert res.capital_exposure_percent == 1.0 * (res.adjusted_quantity / 100_000)

def test_small_portfolio_behaves_correctly():
    res = optimize_position(
        portfolio_value=100,
        current_portfolio_risk_percent=1.0,
        position_value=10,
        position_risk_percent=1.0,
        quantity=1,
    )
    assert res.allowed_trade
    assert res.adjusted_quantity == 1
    assert res.capital_exposure_percent == 10.0

def test_optimization_result_model_validation():
    # Valid
    model = PortfolioOptimizationResult(
        allowed_trade=True,
        adjusted_quantity=50,
        portfolio_risk_percent=3.0,
        position_risk_percent=1.0,
        capital_exposure_percent=15.0,
        optimization_reason="Test reason",
        optimization_method="KELLY"
    )
    assert model.allowed_trade
    assert model.correlation_penalty == 0.0
    assert model.sector_penalty == 0.0
