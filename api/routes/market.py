"""
api/routes/market.py
--------------------
Market data endpoint for PhantomClaw v3.

Fetches live OHLCV data and technical indicators for a given symbol.
Reuses existing modules:
  - market.market_data  (fetch_market_data, get_latest_price, validate_symbol)
  - market.indicators   (get_indicator_summary)
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial

from fastapi import APIRouter, HTTPException, Path, status

from api.schemas.responses import MarketSnapshotResponse
from market.indicators import get_indicator_summary
from market.market_data import fetch_market_data, get_latest_price, validate_symbol

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Market"])


@router.get(
    "/market/{symbol}",
    response_model=MarketSnapshotResponse,
    summary="Fetch live market data and technical indicators",
    description=(
        "Retrieve the latest price snapshot and computed technical indicators "
        "(RSI, EMA20, EMA50, MACD, ATR) for the given symbol."
    ),
    responses={
        200: {"description": "Market snapshot with indicators"},
        404: {"description": "No market data available for the symbol"},
        422: {"description": "Invalid symbol format"},
    },
)
async def get_market_data(
    symbol: str = Path(
        ...,
        min_length=1,
        max_length=20,
        description="Ticker symbol (e.g. 'AAPL', 'RELIANCE')",
        examples=["AAPL", "RELIANCE"],
    ),
) -> MarketSnapshotResponse:
    """Return current price, OHLC, volume, and technical indicators for a symbol."""
    clean_symbol = validate_symbol(symbol)

    loop = asyncio.get_running_loop()

    # Fetch OHLCV data in a thread to avoid blocking the event loop
    df = await loop.run_in_executor(
        None, partial(fetch_market_data, clean_symbol)
    )

    if df is None or df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data found for symbol '{clean_symbol}'.",
        )

    # Fetch latest price snapshot
    market_snapshot: dict = await loop.run_in_executor(
        None, partial(get_latest_price, clean_symbol)
    )

    # Compute technical indicators
    indicators: dict = await loop.run_in_executor(
        None, partial(get_indicator_summary, df)
    )

    return MarketSnapshotResponse(
        symbol=clean_symbol,
        current_price=market_snapshot.get("current_price"),
        open=market_snapshot.get("open"),
        high=market_snapshot.get("high"),
        low=market_snapshot.get("low"),
        close=market_snapshot.get("close"),
        volume=market_snapshot.get("volume"),
        rsi=indicators.get("rsi"),
        ema20=indicators.get("sma20"),  # SMA20 mapped to ema20 per project convention
        ema50=indicators.get("ema50"),
        macd=indicators.get("macd"),
        atr=indicators.get("atr"),
    )
