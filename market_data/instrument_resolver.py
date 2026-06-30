"""
market_data/instrument_resolver.py
----------------------------------
Resolves user-facing stock symbols to Upstox Instrument Keys.

Resolution strategy (ordered):
  1. In-memory cache — O(1) lookup, avoids repeated API calls.
  2. Upstox Instrument Search API — live lookup for any NSE/BSE equity.
  3. Static fallback map — curated list of commonly used NSE symbols.

The static map is the safety net: if the API is down or the token is
invalid, PhantomClaw can still resolve the most popular symbols.
"""

import logging
import threading
from typing import Optional

import httpx

from utils.config import config

logger = logging.getLogger(__name__)

# ─── Upstox Instrument Search API ────────────────────────────────────────────

INSTRUMENT_SEARCH_URL = "https://api.upstox.com/v2/instruments/search"

# ─── Static Fallback Map ─────────────────────────────────────────────────────
# Curated NSE equity instrument keys for commonly used symbols.
# These are real ISIN-based keys that work with the Upstox API.

_STATIC_INSTRUMENT_MAP: dict[str, str] = {
    # NSE Large-Cap Equities
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "INFY": "NSE_EQ|INE009A01021",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "SBIN": "NSE_EQ|INE062A01020",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "ITC": "NSE_EQ|INE154A01025",
    "LT": "NSE_EQ|INE018A01030",
    "HCLTECH": "NSE_EQ|INE860A01027",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "MARUTI": "NSE_EQ|INE585B01010",
    "SUNPHARMA": "NSE_EQ|INE044A01036",
    "TITAN": "NSE_EQ|INE280A01028",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "WIPRO": "NSE_EQ|INE075A01022",
    "TATAMOTORS": "NSE_EQ|INE155A01022",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "ONGC": "NSE_EQ|INE213A01029",
    "NTPC": "NSE_EQ|INE733E01010",
    "POWERGRID": "NSE_EQ|INE752E01010",
    "TATASTEEL": "NSE_EQ|INE081A01020",
    "ADANIENT": "NSE_EQ|INE423A01024",
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "BAJAJFINSV": "NSE_EQ|INE918I01018",
    "JSWSTEEL": "NSE_EQ|INE019A01038",
    "TECHM": "NSE_EQ|INE669C01036",
    # NSE Indices
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "NIFTYIT": "NSE_INDEX|Nifty IT",
}

# ─── Thread-safe runtime cache ───────────────────────────────────────────────

_cache: dict[str, str] = {}
_cache_lock = threading.Lock()


def _search_instrument_via_api(symbol: str) -> Optional[str]:
    """
    Query the Upstox Instrument Search API for a symbol.

    Returns the instrument_key if found, or None if the API call fails
    or returns no matching NSE equity result.
    """
    if not config.UPSTOX_ACCESS_TOKEN or config.UPSTOX_ACCESS_TOKEN.startswith("your_"):
        logger.debug("Upstox access token not configured; skipping API search.")
        return None

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {config.UPSTOX_ACCESS_TOKEN}",
        "Api-Version": "2.0",
    }

    params = {
        "query": symbol,
        "segment": "NSE_EQ",
        "instrument_type": "EQ",
    }

    try:
        response = httpx.get(
            INSTRUMENT_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=config.UPSTOX_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        instruments = data.get("data", [])
        if not instruments:
            logger.debug("Instrument Search API returned no results for '%s'.", symbol)
            return None

        # Find exact match on trading_symbol
        for inst in instruments:
            if inst.get("trading_symbol", "").upper() == symbol:
                instrument_key = inst.get("instrument_key")
                logger.info(
                    "Resolved '%s' via Instrument Search API -> %s",
                    symbol, instrument_key,
                )
                return instrument_key

        # If no exact match, use the first result as best effort
        first = instruments[0]
        instrument_key = first.get("instrument_key")
        logger.info(
            "Resolved '%s' via Instrument Search API (best match: %s) -> %s",
            symbol, first.get("trading_symbol"), instrument_key,
        )
        return instrument_key

    except httpx.TimeoutException:
        logger.warning("Instrument Search API timed out for '%s'.", symbol)
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Instrument Search API returned HTTP %d for '%s': %s",
            exc.response.status_code, symbol, exc,
        )
        return None
    except Exception as exc:
        logger.warning("Instrument Search API failed for '%s': %s", symbol, exc)
        return None


def resolve_symbol(symbol: str) -> str:
    """
    Convert a plain ticker symbol into an Upstox instrument key.

    Resolution order:
      1. In-memory cache
      2. Upstox Instrument Search API (live)
      3. Static fallback map

    Args:
        symbol: e.g. 'RELIANCE'

    Returns:
        The resolved instrument key, e.g. 'NSE_EQ|INE002A01018'

    Raises:
        ValueError: If the symbol cannot be resolved by any method.
    """
    if not symbol or not symbol.strip():
        raise ValueError("Symbol cannot be empty.")

    normalized = symbol.strip().upper()

    # 1. Check runtime cache
    with _cache_lock:
        cached = _cache.get(normalized)
    if cached:
        logger.debug("Cache hit for '%s' -> %s", normalized, cached)
        return cached

    # 2. Try Upstox Instrument Search API
    api_result = _search_instrument_via_api(normalized)
    if api_result:
        with _cache_lock:
            _cache[normalized] = api_result
        return api_result

    # 3. Fall back to static map
    static_result = _STATIC_INSTRUMENT_MAP.get(normalized)
    if static_result:
        logger.info("Resolved '%s' via static fallback map -> %s", normalized, static_result)
        with _cache_lock:
            _cache[normalized] = static_result
        return static_result

    # All methods exhausted
    logger.error("Could not resolve symbol: %s (API + static map exhausted)", normalized)
    raise ValueError(f"Unknown symbol: {normalized}")


def clear_cache() -> None:
    """Clear the in-memory instrument key cache."""
    with _cache_lock:
        _cache.clear()
    logger.info("Instrument key cache cleared.")
