"""
portfolio/optimizer.py
----------------------
Portfolio Optimization Engine for PhantomClaw v2.

Determines safe position sizes, Kelly sizing, and portfolio-level risk.
Pure deterministic logic.
"""

from models.portfolio_model import PortfolioOptimizationResult


def max_portfolio_risk_check(
    current_portfolio_risk_percent: float,
    new_position_risk_percent: float,
    max_portfolio_risk_percent: float = 5.0,
) -> bool:
    """
    Reject trade if total portfolio risk would exceed the maximum allowed.
    """
    return (current_portfolio_risk_percent + new_position_risk_percent) <= max_portfolio_risk_percent


def max_position_exposure_check(
    position_value: float,
    portfolio_value: float,
    max_position_exposure_percent: float = 20.0,
) -> bool:
    """
    Reject oversized positions that exceed a given percentage of total portfolio value.
    """
    if portfolio_value <= 0:
        return False
    exposure_percent = (position_value / portfolio_value) * 100.0
    return exposure_percent <= max_position_exposure_percent


def conservative_kelly_fraction(
    win_rate: float,
    reward_risk_ratio: float,
) -> float:
    """
    Calculate half-Kelly fraction for conservative bet sizing.
    """
    if reward_risk_ratio <= 0:
        return 0.0

    kelly = win_rate - ((1.0 - win_rate) / reward_risk_ratio)
    
    # Clamp to [0, 1]
    kelly = max(0.0, min(1.0, kelly))
    
    # Return Half Kelly
    return kelly * 0.5


def apply_kelly_adjustment(
    quantity: int,
    kelly_fraction: float,
) -> int:
    """
    Adjust the position quantity using the calculated Kelly fraction.
    Guarantees the quantity never drops below 1 if the original quantity was >= 1.
    """
    adjusted = int(quantity * kelly_fraction)
    return max(1, adjusted)


def optimize_position(
    portfolio_value: float,
    current_portfolio_risk_percent: float,
    position_value: float,
    position_risk_percent: float,
    quantity: int,
    win_rate: float = 0.55,
    reward_risk_ratio: float = 2.0,
) -> PortfolioOptimizationResult:
    """
    Main dispatcher for portfolio optimization. Evaluates portfolio limits and adjusts
    sizing using the Kelly criterion.
    """
    capital_exposure_percent = 0.0
    if portfolio_value > 0:
        capital_exposure_percent = (position_value / portfolio_value) * 100.0

    # 1. Max Portfolio Risk Check
    if not max_portfolio_risk_check(current_portfolio_risk_percent, position_risk_percent):
        return PortfolioOptimizationResult(
            allowed_trade=False,
            adjusted_quantity=0,
            portfolio_risk_percent=current_portfolio_risk_percent,
            position_risk_percent=position_risk_percent,
            capital_exposure_percent=capital_exposure_percent,
            optimization_reason="Exceeds maximum portfolio risk limit.",
            optimization_method="MAX_RISK",
        )

    # 2. Max Position Exposure Check
    if not max_position_exposure_check(position_value, portfolio_value):
        return PortfolioOptimizationResult(
            allowed_trade=False,
            adjusted_quantity=0,
            portfolio_risk_percent=current_portfolio_risk_percent,
            position_risk_percent=position_risk_percent,
            capital_exposure_percent=capital_exposure_percent,
            optimization_reason="Exceeds maximum position exposure limit (20%).",
            optimization_method="MAX_EXPOSURE",
        )

    # 3. Kelly Sizing
    kelly_frac = conservative_kelly_fraction(win_rate, reward_risk_ratio)
    adjusted_qty = apply_kelly_adjustment(quantity, kelly_frac)

    # Re-calculate capital exposure after Kelly
    if quantity > 0 and portfolio_value > 0:
        new_position_value = position_value * (adjusted_qty / quantity)
        capital_exposure_percent = (new_position_value / portfolio_value) * 100.0

    return PortfolioOptimizationResult(
        allowed_trade=True,
        adjusted_quantity=adjusted_qty,
        portfolio_risk_percent=current_portfolio_risk_percent,
        position_risk_percent=position_risk_percent,
        capital_exposure_percent=capital_exposure_percent,
        optimization_reason="Trade allowed and sized via Half-Kelly criterion.",
        optimization_method="KELLY",
    )
