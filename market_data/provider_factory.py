"""
market_data/provider_factory.py
-------------------------------
Factory to instantiate and return the correct MarketDataProvider.

Returns a module-level singleton to:
  - Reuse the httpx.Client connection pool
  - Share the in-memory response cache across all callers
  - Avoid re-reading config on every call
"""

from __future__ import annotations

import threading

from market_data.base_provider import MarketDataProvider
from market_data.upstox_provider import UpstoxProvider

_provider: MarketDataProvider | None = None
_lock = threading.Lock()


def get_market_provider() -> MarketDataProvider:
    """
    Returns a singleton MarketDataProvider instance.

    Thread-safe — safe to call from async route handlers
    and background threads concurrently.
    """
    global _provider
    if _provider is None:
        with _lock:
            if _provider is None:
                _provider = UpstoxProvider()
    return _provider
