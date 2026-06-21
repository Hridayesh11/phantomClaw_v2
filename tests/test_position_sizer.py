"""
tests/test_position_sizer.py
----------------------------
Deterministic tests for the Phase 10 Dynamic Position Sizing Engine.
"""

import pytest

from models.position_model import PositionSizingResult
from risk.position_sizer import atr_position_size, calculate_position_size, fixed_position_size


def test_low_atr_larger_quantity():
    # Low ATR (0.5)
    res_low = atr_position_size(
        portfolio_value=100_000, price=150.0, atr=0.5, risk_percent=0.01, atr_multiplier=2.0
    )
    # Risk amount = 1000
    # Stop distance = 0.5 * 2 = 1.0
    # Quantity = 1000 / 1.0 = 1000
    assert res_low.quantity == 1000
    assert res_low.position_method == "ATR"

def test_high_atr_smaller_quantity():
    # High ATR (5.0)
    res_high = atr_position_size(
        portfolio_value=100_000, price=150.0, atr=5.0, risk_percent=0.01, atr_multiplier=2.0
    )
    # Stop distance = 5.0 * 2 = 10.0
    # Quantity = 1000 / 10.0 = 100
    assert res_high.quantity == 100
    assert res_high.position_method == "ATR"

def test_atr_zero_fallback():
    # ATR = 0
    res = atr_position_size(
        portfolio_value=100_000, price=150.0, atr=0.0, risk_percent=0.01, atr_multiplier=2.0
    )
    assert res.position_method == "FIXED"
    assert res.quantity == 10

def test_atr_negative_fallback():
    # Negative ATR
    res = atr_position_size(
        portfolio_value=100_000, price=150.0, atr=-1.5, risk_percent=0.01, atr_multiplier=2.0
    )
    assert res.position_method == "FIXED"
    assert res.quantity == 10

def test_tiny_portfolio_minimum_quantity():
    # Tiny portfolio -> risk_amount very small -> quantity < 1 -> clamped to 1
    res = atr_position_size(
        portfolio_value=100, price=150.0, atr=2.0, risk_percent=0.01, atr_multiplier=2.0
    )
    # Risk = 1. Stop dist = 4. Qty = 1/4 = 0. Clamped to 1.
    assert res.quantity == 1
    assert res.capital_exposure == 150.0

def test_large_portfolio_no_overflow():
    res = atr_position_size(
        portfolio_value=1_000_000_000, price=150.0, atr=1.0, risk_percent=0.01, atr_multiplier=2.0
    )
    # Risk = 10,000,000. Stop dist = 2.0. Qty = 5,000,000.
    assert res.quantity == 5_000_000
    assert res.capital_exposure == 750_000_000.0

def test_capital_exposure_positive():
    res = atr_position_size(
        portfolio_value=100_000, price=150.0, atr=1.0
    )
    assert res.capital_exposure > 0

def test_dispatcher_calculate_position_size():
    # Default is ATR
    res_atr = calculate_position_size(100_000, 150.0, 1.0)
    assert res_atr.position_method == "ATR"
    
    # FIXED method
    res_fixed = calculate_position_size(100_000, 150.0, 1.0, method="FIXED")
    assert res_fixed.position_method == "FIXED"
    assert res_fixed.quantity == 10

def test_position_sizing_result_model_validation():
    # Test valid
    model = PositionSizingResult(
        quantity=5,
        risk_amount=100.0,
        stop_distance=2.5,
        atr=1.2,
        capital_exposure=750.0,
        position_method="ATR",
    )
    assert model.quantity == 5
    
    # Test invalid quantity
    with pytest.raises(ValueError):
        PositionSizingResult(
            quantity=0,
            risk_amount=100.0,
            stop_distance=2.5,
            atr=1.2,
            capital_exposure=750.0,
            position_method="ATR",
        )
