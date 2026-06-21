"""
market/market_data.py
---------------------
Fetches real OHLCV market data from Yahoo Finance via yfinance.
Provides both historical DataFrames and a current-price snapshot.
"""

import logging
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# Supported ticker symbols (can be extended)
SUPPORTED_SYMBOLS = {"AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "SPY"}


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
    Fetch OHLCV data for a symbol using yfinance.

    Args:
        symbol:   Ticker symbol, e.g. 'AAPL'
        period:   How far back to fetch ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y')
        interval: Bar size ('1m', '5m', '15m', '1h', '1d', '1wk', '1mo')

    Returns:
        A pandas DataFrame with columns: Open, High, Low, Close, Volume
        Indexed by datetime. Empty DataFrame on failure.
    """
    symbol = validate_symbol(symbol)
    logger.info("Fetching market data for %s [period=%s, interval=%s]", symbol, period, interval)

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            logger.warning("No data returned for %s", symbol)
            return pd.DataFrame()

        # Keep only standard OHLCV columns
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)

        logger.info("Fetched %d bars for %s", len(df), symbol)
        return df

    except Exception as exc:
        logger.error("Failed to fetch market data for %s: %s", symbol, exc)
        return pd.DataFrame()


def get_latest_price(symbol: str) -> dict:
    """
    Return a dict with the most recent price info for a symbol.

    Returns:
        {
            "symbol": str,
            "current_price": float,
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": int,
        }
    """
    symbol = validate_symbol(symbol)
    df = fetch_market_data(symbol, period="5d", interval="1d")

    if df.empty:
        return {
            "symbol": symbol,
            "current_price": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "close": 0.0,
            "volume": 0,
        }

    latest = df.iloc[-1]
    return {
        "symbol": symbol,
        "current_price": round(float(latest["Close"]), 2),
        "open": round(float(latest["Open"]), 2),
        "high": round(float(latest["High"]), 2),
        "low": round(float(latest["Low"]), 2),
        "close": round(float(latest["Close"]), 2),
        "volume": int(latest["Volume"]),
    }
