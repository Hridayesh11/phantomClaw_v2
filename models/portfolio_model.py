"""
models/portfolio_model.py
-------------------------
Pydantic model for Phase 11 Portfolio Optimization Engine.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PortfolioOptimizationResult(BaseModel):
    """
    Result of the portfolio-level risk management and optimization.
    """

    allowed_trade: bool = Field(..., description="Whether the trade passes portfolio risk limits")
    adjusted_quantity: int = Field(..., description="The final trade quantity after Kelly sizing and risk limits")
    portfolio_risk_percent: float = Field(..., description="Total portfolio risk percent before this trade")
    position_risk_percent: float = Field(..., description="Risk percent added by this specific position")
    capital_exposure_percent: float = Field(..., description="Percentage of portfolio capital exposed")
    
    # Future-ready placeholders
    correlation_penalty: float = Field(0.0, description="Penalty for correlating assets (future use)")
    sector_penalty: float = Field(0.0, description="Penalty for sector concentration (future use)")
    
    optimization_reason: str = Field(..., description="Reason for adjustment or rejection")
    optimization_method: str = Field(..., description="Method applied (e.g. KELLY, MAX_RISK, MAX_EXPOSURE)")
