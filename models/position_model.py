"""
models/position_model.py
------------------------
Pydantic model for Phase 10 Dynamic Position Sizing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PositionSizingResult(BaseModel):
    """
    Result of the dynamic position sizing calculation.
    """

    quantity: int = Field(..., description="Suggested trade quantity (must be >= 1)", ge=1)
    risk_amount: float = Field(..., description="Calculated risk amount in base currency")
    stop_distance: float = Field(..., description="Distance to stop loss in price terms")
    atr: float = Field(..., description="ATR value used for sizing")
    capital_exposure: float = Field(..., description="Total capital exposed in this position")
    position_method: str = Field(..., description="Method used for calculation (e.g. 'ATR' or 'FIXED')")
