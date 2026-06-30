"""
api/routes/portfolio.py
-----------------------
Provides read-only access to the current PortfolioManager state.
"""

from fastapi import APIRouter
from typing import List, Dict, Any

from trading.engine import get_trading_engine
from api.schemas.responses import RootResponse

router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"],
)

@router.get("", response_model=Dict[str, Any])
async def get_portfolio_state():
    """
    Returns the current cash balance and open positions.
    """
    engine = get_trading_engine()
    portfolio = engine.portfolio
    
    positions = []
    for pos in portfolio.get_all_positions():
        positions.append({
            "symbol": pos.symbol,
            "quantity": pos.quantity,
            "average_entry_price": pos.average_entry_price,
            "realized_pnl": pos.realized_pnl
        })
        
    return {
        "cash": portfolio.cash,
        "initial_cash": portfolio.initial_cash,
        "positions": positions
    }
