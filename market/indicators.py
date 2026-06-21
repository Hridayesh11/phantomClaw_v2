"""
market/indicators.py
--------------------
Computes technical indicators using pandas-ta.
Works on a OHLCV DataFrame and returns a clean summary dict
for the latest bar (used as AI context and displayed in the dashboard).
"""

import logging
import pandas as pd

try:
    import pandas_ta as ta
except ImportError:
    ta = None  # handled gracefully below

logger = logging.getLogger(__name__)


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Append technical indicator columns to an OHLCV DataFrame.

    Computes:
        - RSI (14-period)
        - MACD (12/26/9 default)
        - SMA20
        - EMA50
        - ATR (14-period)

    Args:
        df: OHLCV DataFrame with columns Open, High, Low, Close, Volume

    Returns:
        The original DataFrame with additional indicator columns.
    """
    if df.empty:
        logger.warning("compute_indicators called with empty DataFrame")
        return df

    if ta is None:
        logger.error("pandas-ta is not installed. Run: pip install pandas-ta")
        return df

    # Work on a copy to avoid mutating the caller's data
    df = df.copy()

    # RSI — 14-period Relative Strength Index
    df["RSI"] = ta.rsi(df["Close"], length=14)

    # MACD — Moving Average Convergence Divergence
    macd_df = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        df["MACD"] = macd_df.iloc[:, 0]        # MACD line
        df["MACD_signal"] = macd_df.iloc[:, 2]  # Signal line

    # SMA20 — 20-period Simple Moving Average
    df["SMA20"] = ta.sma(df["Close"], length=20)

    # EMA50 — 50-period Exponential Moving Average
    df["EMA50"] = ta.ema(df["Close"], length=50)

    # ATR — 14-period Average True Range (volatility)
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)

    return df


def get_indicator_summary(df: pd.DataFrame) -> dict:
    """
    Extract the latest row's indicator values into a clean dict.

    Returns:
        Dict with keys: rsi, macd, macd_signal, sma20, ema50, atr
        All values are rounded floats or None if not available.
    """
    if df.empty:
        return _empty_summary()

    df = compute_indicators(df)
    latest = df.iloc[-1]

    def safe(col: str) -> float | None:
        try:
            val = latest.get(col)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return None
            return round(float(val), 4)
        except Exception:
            return None

    return {
        "rsi": safe("RSI"),
        "macd": safe("MACD"),
        "macd_signal": safe("MACD_signal"),
        "sma20": safe("SMA20"),
        "ema50": safe("EMA50"),
        "atr": safe("ATR"),
    }


def _empty_summary() -> dict:
    return {
        "rsi": None,
        "macd": None,
        "macd_signal": None,
        "sma20": None,
        "ema50": None,
        "atr": None,
    }
