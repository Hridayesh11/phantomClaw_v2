"""
api/routes/history.py
---------------------
Trade history endpoint for PhantomClaw v3.

Returns historical trade log entries by delegating to the existing
database layer (database.db.get_recent_trades).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, status

from api.schemas.responses import TradeHistoryEntry, TradeHistoryResponse
from database.db import get_recent_trades

logger = logging.getLogger(__name__)

router = APIRouter(tags=["History"])


@router.get(
    "/history",
    response_model=TradeHistoryResponse,
    summary="Retrieve historical trade log entries",
    description=(
        "Return the most recent trade analysis records from the SQLite database, "
        "ordered newest-first. Supports pagination via the `limit` query parameter."
    ),
    responses={
        200: {"description": "Trade history retrieved successfully"},
    },
)
async def get_trade_history(
    limit: int = Query(
        default=20,
        ge=1,
        le=200,
        description="Maximum number of records to return",
    ),
) -> TradeHistoryResponse:
    """Return historical trades from the database layer."""
    raw_trades: list[dict] = get_recent_trades(limit=limit)

    trades = [TradeHistoryEntry(**trade) for trade in raw_trades]

    logger.debug("History: returning %d trade(s) (limit=%d)", len(trades), limit)

    return TradeHistoryResponse(
        count=len(trades),
        trades=trades,
    )
