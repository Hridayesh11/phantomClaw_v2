"""
market/market_data.py
---------------------
Public interface for fetching market data in PhantomClaw v3.

All calls delegate to the MarketDataProvider singleton (Upstox).
This module provides convenience functions used by:
  - services/analysis_service.py
  - api/routes/market.py
  - app.py (Streamlit)
  - backtesting/backtest_engine.py

No market data logic lives here — it is purely a delegation layer.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from market_data.provider_factory import get_market_provider

logger = logging.getLogger(__name__)


def validate_symbol(symbol: str) -> str:
    """Normalize and validate a ticker symbol."""
    symbol = symbol.strip().upper()
    return symbol  # We allow any symbol — ArmorIQ will penalize unknown ones


def fetch_market_data(
    symbol: str,
    period: str = "3mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a symbol via the MarketDataProvider (Upstox).

    Args:
        symbol:   Ticker symbol, e.g. 'RELIANCE'
        period:   How far back to fetch ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y')
        interval: Bar size ('1m', '5m', '15m', '1h', '1d', '1wk', '1mo')

    Returns:
        A pandas DataFrame with columns: Open, High, Low, Close, Volume
        Indexed by datetime. Empty DataFrame on failure.
    """
    symbol = validate_symbol(symbol)

    # Map 'period' to start/end dates
    end_date = datetime.now().date()
    period_days = {
        "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
        "6mo": 180, "1y": 365, "2y": 730,
    }
    start_date = end_date - timedelta(days=period_days.get(period, 90))

    provider = get_market_provider()
    return provider.fetch_history(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
    )


def get_latest_price(symbol: str) -> dict:
    """
    Return a dict with the most recent price info for a symbol via the MarketDataProvider.
    """
    symbol = validate_symbol(symbol)
    provider = get_market_provider()
    return provider.fetch_latest_snapshot(symbol)
