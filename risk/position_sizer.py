"""
risk/position_sizer.py
----------------------
Dynamic Position Sizing Engine for PhantomClaw v2.

Pure deterministic module. No side effects.
"""

from models.position_model import PositionSizingResult


def fixed_position_size(
    portfolio_value: float,
    price: float,
    fixed_quantity: int = 10,
) -> PositionSizingResult:
    """
    Fallback method that uses a fixed quantity.
    """
    quantity = max(1, fixed_quantity)
    capital_exposure = quantity * price

    return PositionSizingResult(
        quantity=quantity,
        risk_amount=0.0,
        stop_distance=0.0,
        atr=0.0,
        capital_exposure=capital_exposure,
        position_method="FIXED",
    )


def atr_position_size(
    portfolio_value: float,
    price: float,
    atr: float,
    risk_percent: float = 0.01,
    atr_multiplier: float = 2.0,
) -> PositionSizingResult:
    """
    Calculates position size dynamically based on ATR and portfolio risk.
    """
    if atr <= 0:
        return fixed_position_size(portfolio_value, price)

    risk_amount = portfolio_value * risk_percent
    stop_distance = atr * atr_multiplier

    if stop_distance <= 0:
        return fixed_position_size(portfolio_value, price)

    quantity = int(risk_amount / stop_distance)
    
    # Guarantee at least 1 share
    if quantity < 1:
        quantity = 1

    capital_exposure = quantity * price

    return PositionSizingResult(
        quantity=quantity,
        risk_amount=risk_amount,
        stop_distance=stop_distance,
        atr=atr,
        capital_exposure=capital_exposure,
        position_method="ATR",
    )


def calculate_position_size(
    portfolio_value: float,
    price: float,
    atr: float,
    method: str = "ATR",
) -> PositionSizingResult:
    """
    Dispatcher function for position sizing.
    """
    if method.upper() == "FIXED":
        return fixed_position_size(portfolio_value, price)
    
    # Default to ATR
    return atr_position_size(portfolio_value, price, atr)
