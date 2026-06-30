"""
market_data/base_provider.py
----------------------------
Abstract base class for all Market Data Providers.
Isolates PhantomClaw v3 from vendor-specific market data APIs.

Providers must implement:
  - get_quote(symbol)           → latest quote dict
  - get_ohlc(symbol)            → OHLC dict
  - get_historical_data(...)    → OHLCV DataFrame
  - validate_symbol(symbol)     → bool

Legacy bridge methods (fetch_history, fetch_latest_snapshot) delegate to
the new interface so existing callers remain unaffected.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

import pandas as pd


class MarketDataProvider(ABC):
    """
    Abstract base class defining the contract for market data fetching.
    All providers (Upstox, etc.) must implement this interface.
    """

    # ── New canonical interface ───────────────────────────────────────────

    @abstractmethod
    def get_quote(self, symbol: str) -> dict:
        """
        Fetch the latest quote for a symbol.

        Args:
            symbol: Ticker symbol (e.g., 'RELIANCE')

        Returns:
            A dictionary with at minimum:
            {
                "symbol": str,
                "current_price": float,
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": int
            }
        """

    @abstractmethod
    def get_ohlc(self, symbol: str) -> dict:
        """
        Fetch the latest OHLC snapshot for a symbol.

        Args:
            symbol: Ticker symbol (e.g., 'RELIANCE')

        Returns:
            {
                "symbol": str,
                "open": float,
                "high": float,
                "low": float,
                "close": float,
            }
        """

    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        interval: str = "1d",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a given symbol.

        Args:
            symbol:    Ticker symbol (e.g., 'RELIANCE')
            interval:  Bar size ('1d', '1m', '5m', '15m', '30m', '1h')
            from_date: Start date of the history
            to_date:   End date of the history

        Returns:
            A pandas DataFrame with columns: Open, High, Low, Close, Volume
            The DataFrame must be datetime indexed.
        """

    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """
        Check whether a symbol is recognized by the provider.

        Args:
            symbol: Ticker symbol to validate.

        Returns:
            True if the symbol can be resolved, False otherwise.
        """

    # ── Legacy bridge methods (backward compatibility) ────────────────────

    def fetch_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Legacy bridge — delegates to get_historical_data().

        Existing callers (market.market_data, backtesting) use this
        signature. New code should call get_historical_data() directly.
        """
        return self.get_historical_data(
            symbol=symbol,
            interval=interval,
            from_date=start_date,
            to_date=end_date,
        )

    def fetch_latest_snapshot(self, symbol: str) -> dict:
        """
        Legacy bridge — delegates to get_quote().

        Existing callers (market.market_data, api routes) use this
        signature. New code should call get_quote() directly.
        """
        return self.get_quote(symbol)
