"""
market_data/upstox_provider.py
------------------------------
Production-ready Upstox implementation of MarketDataProvider.

Features:
  - Implements all four canonical methods: get_quote, get_ohlc,
    get_historical_data, validate_symbol
  - Configurable HTTP timeout via UPSTOX_REQUEST_TIMEOUT
  - Lightweight in-memory response caching with configurable TTL
  - Retry logic with exponential backoff (via retry.py decorator)
  - Structured logging for every API call
  - Graceful error handling — never raises on API failures,
    returns empty/default values instead
  - All credentials read from utils.config — nothing hardcoded
"""

import logging
import threading
import time as _time
from datetime import date
from typing import Any, Dict, Optional

import httpx
import pandas as pd

from market_data.base_provider import MarketDataProvider
from market_data.instrument_resolver import resolve_symbol
from market_data.retry import with_retry
from utils.config import config

logger = logging.getLogger(__name__)

# ─── Upstox API endpoints ────────────────────────────────────────────────────

UPSTOX_BASE_URL = "https://api.upstox.com/v2"
HISTORICAL_DAY_URL = UPSTOX_BASE_URL + "/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"
LATEST_QUOTE_URL = UPSTOX_BASE_URL + "/market-quote/quotes"
OHLC_QUOTE_URL = UPSTOX_BASE_URL + "/market-quote/ohlc"

# ─── Interval mapping ────────────────────────────────────────────────────────

_INTERVAL_MAP: dict[str, str] = {
    "1m": "1minute",
    "5m": "5minute",
    "15m": "15minute",
    "30m": "30minute",
    "1h": "60minute",
    "1d": "day",
    "1wk": "week",
    "1mo": "month",
}


# ─── Response Cache ──────────────────────────────────────────────────────────


class _ResponseCache:
    """
    Lightweight thread-safe in-memory cache with per-key TTL.

    Avoids hammering the Upstox API when the same symbol is queried
    multiple times in quick succession (e.g. market route + analysis pipeline).
    """

    def __init__(self, ttl_seconds: int = 30):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            timestamp, value = entry
            if _time.monotonic() - timestamp > self._ttl:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (_time.monotonic(), value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# ─── Provider Implementation ─────────────────────────────────────────────────


class UpstoxProvider(MarketDataProvider):
    """
    Fetches live market data from the Upstox REST API v2.

    - HTTP client reuses connections via httpx.Client
    - All requests go through the @with_retry decorator
    - Responses are cached in-memory for MARKET_CACHE_TTL seconds
    - Timeout is configurable via UPSTOX_REQUEST_TIMEOUT
    """

    def __init__(self) -> None:
        self.headers: dict[str, str] = {
            "Accept": "application/json",
            "Authorization": f"Bearer {config.UPSTOX_ACCESS_TOKEN}",
            "Api-Version": "2.0",
        }
        self.client = httpx.Client(
            headers=self.headers,
            timeout=config.UPSTOX_REQUEST_TIMEOUT,
        )
        self._cache = _ResponseCache(ttl_seconds=config.MARKET_CACHE_TTL)

    # ── Low-level HTTP ────────────────────────────────────────────────────

    @with_retry
    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """Execute a GET request with retry + backoff."""
        return self.client.get(url, params=params)

    # ── Canonical interface ───────────────────────────────────────────────

    def get_quote(self, symbol: str) -> dict:
        """
        Fetch the latest full quote from Upstox.

        Returns a dict matching the MarketDataProvider contract:
        {symbol, current_price, open, high, low, close, volume}
        """
        cache_key = f"quote:{symbol.upper()}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for quote '%s'", symbol)
            return cached

        try:
            instrument_key = resolve_symbol(symbol)
        except ValueError as exc:
            logger.error("Symbol resolution failed for '%s': %s", symbol, exc)
            return self._empty_snapshot(symbol)

        try:
            response = self._get(LATEST_QUOTE_URL, params={"instrument_key": instrument_key})
            data = response.json()

            if data.get("status") != "success":
                logger.error("Upstox quotes API returned non-success for '%s': %s", symbol, data)
                return self._empty_snapshot(symbol)

            quote = data.get("data", {}).get(instrument_key)
            if not quote:
                logger.warning("No quote data returned for '%s' (key=%s)", symbol, instrument_key)
                return self._empty_snapshot(symbol)

            ohlc = quote.get("ohlc", {})
            result = {
                "symbol": symbol.upper(),
                "current_price": float(quote.get("last_price", 0.0)),
                "open": float(ohlc.get("open", 0.0)),
                "high": float(ohlc.get("high", 0.0)),
                "low": float(ohlc.get("low", 0.0)),
                "close": float(ohlc.get("close", 0.0)),
                "volume": int(quote.get("volume", 0)),
            }

            self._cache.set(cache_key, result)
            logger.info("Fetched live quote for '%s': price=%.2f", symbol, result["current_price"])
            return result

        except Exception as exc:
            logger.error("Failed to fetch quote for '%s': %s", symbol, exc)
            return self._empty_snapshot(symbol)

    def get_ohlc(self, symbol: str) -> dict:
        """
        Fetch only the OHLC values for a symbol.

        Uses the dedicated Upstox OHLC endpoint for a lighter payload.
        Falls back to the full quote if the OHLC endpoint fails.
        """
        cache_key = f"ohlc:{symbol.upper()}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for OHLC '%s'", symbol)
            return cached

        try:
            instrument_key = resolve_symbol(symbol)
        except ValueError as exc:
            logger.error("Symbol resolution failed for OHLC '%s': %s", symbol, exc)
            return self._empty_ohlc(symbol)

        try:
            response = self._get(OHLC_QUOTE_URL, params={"instrument_key": instrument_key})
            data = response.json()

            if data.get("status") != "success":
                logger.warning("Upstox OHLC API returned non-success for '%s'; falling back to full quote.", symbol)
                full_quote = self.get_quote(symbol)
                return {
                    "symbol": full_quote.get("symbol", symbol.upper()),
                    "open": full_quote.get("open", 0.0),
                    "high": full_quote.get("high", 0.0),
                    "low": full_quote.get("low", 0.0),
                    "close": full_quote.get("close", 0.0),
                }

            quote_data = data.get("data", {}).get(instrument_key, {})
            ohlc = quote_data.get("ohlc", {})

            result = {
                "symbol": symbol.upper(),
                "open": float(ohlc.get("open", 0.0)),
                "high": float(ohlc.get("high", 0.0)),
                "low": float(ohlc.get("low", 0.0)),
                "close": float(ohlc.get("close", 0.0)),
            }

            self._cache.set(cache_key, result)
            logger.info("Fetched OHLC for '%s'", symbol)
            return result

        except Exception as exc:
            logger.error("Failed to fetch OHLC for '%s': %s", symbol, exc)
            return self._empty_ohlc(symbol)

    def get_historical_data(
        self,
        symbol: str,
        interval: str = "1d",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV candles from Upstox.

        Args:
            symbol:    Ticker symbol (e.g. 'RELIANCE')
            interval:  Bar size key from _INTERVAL_MAP
            from_date: Start date (defaults to 90 days ago)
            to_date:   End date (defaults to today)

        Returns:
            DataFrame with [Open, High, Low, Close, Volume], datetime-indexed.
            Empty DataFrame on any failure.
        """
        logger.info("Fetching historical data from Upstox for '%s' (%s)", symbol, interval)

        try:
            instrument_key = resolve_symbol(symbol)
        except ValueError as exc:
            logger.error("Symbol resolution failed for historical '%s': %s", symbol, exc)
            return pd.DataFrame()

        # Map interval
        upstox_interval = _INTERVAL_MAP.get(interval, "day")

        # Default date range
        if to_date is None:
            from datetime import datetime
            to_date = datetime.now().date()
        if from_date is None:
            from datetime import timedelta
            from_date = to_date - timedelta(days=90)

        from_date_str = from_date.strftime("%Y-%m-%d")
        to_date_str = to_date.strftime("%Y-%m-%d")

        url = HISTORICAL_DAY_URL.format(
            instrument_key=instrument_key,
            interval=upstox_interval,
            to_date=to_date_str,
            from_date=from_date_str,
        )

        try:
            response = self._get(url)
            data = response.json()

            if data.get("status") != "success":
                logger.error(
                    "Upstox historical API returned non-success for '%s': %s", symbol, data
                )
                return pd.DataFrame()

            candles = data.get("data", {}).get("candles", [])
            if not candles:
                logger.warning("No historical data returned for '%s'", symbol)
                return pd.DataFrame()

            # Upstox returns: [timestamp, open, high, low, close, volume, oi]
            df = pd.DataFrame(
                candles,
                columns=["timestamp", "Open", "High", "Low", "Close", "Volume", "OI"],
            )

            # Convert timestamp to datetime and set as index
            df["Date"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
            df.set_index("Date", inplace=True)

            # Standardize column types
            df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
            df["Volume"] = df["Volume"].astype(int)

            # Sort chronologically
            df.sort_index(inplace=True)

            logger.info("Fetched %d candles for '%s' (%s to %s)", len(df), symbol, from_date_str, to_date_str)
            return df

        except Exception as exc:
            logger.error("Failed to fetch historical data for '%s': %s", symbol, exc)
            return pd.DataFrame()

    def validate_symbol(self, symbol: str) -> bool:
        """
        Check whether a symbol can be resolved by the instrument resolver.

        Does NOT make an API call if the symbol is already cached or in the
        static fallback map. Only hits the Instrument Search API as a last resort.

        Returns:
            True if the symbol resolves to a valid instrument key.
        """
        try:
            resolve_symbol(symbol)
            return True
        except ValueError:
            return False

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _empty_snapshot(symbol: str) -> dict:
        return {
            "symbol": symbol.upper(),
            "current_price": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "close": 0.0,
            "volume": 0,
        }

    @staticmethod
    def _empty_ohlc(symbol: str) -> dict:
        return {
            "symbol": symbol.upper(),
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "close": 0.0,
        }
