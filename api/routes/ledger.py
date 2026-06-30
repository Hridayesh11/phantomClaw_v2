from fastapi import APIRouter
from typing import Dict, Any

from database.db import get_all_execution_logs
from trading.analytics import PerformanceAnalytics
from trading.engine import get_trading_engine

router = APIRouter(
    prefix="/ledger",
    tags=["Ledger"],
)

@router.get("", response_model=Dict[str, Any])
async def get_ledger_and_analytics():
    """
    Returns all execution logs (Trade Ledger) and computed Performance Analytics.
    """
    logs = get_all_execution_logs()
    
    engine = get_trading_engine()
    initial_cash = engine.portfolio.initial_cash
    
    metrics = PerformanceAnalytics.compute_metrics(logs, initial_cash)
    
    return {
        "logs": logs,
        "metrics": metrics
    }
