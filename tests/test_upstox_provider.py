"""
tests/test_upstox_provider.py
-----------------------------
Deterministic tests for UpstoxProvider utilizing httpx mocks.

Tests cover:
  - get_quote (via fetch_latest_snapshot bridge)
  - get_historical_data (via fetch_history bridge)
  - get_ohlc
  - validate_symbol
  - Error/empty scenarios
  - Response caching
"""

from datetime import date

import httpx
import pytest

from market_data.instrument_resolver import clear_cache as clear_resolver_cache
from market_data.upstox_provider import UpstoxProvider


class MockResponse:
    """Lightweight mock for httpx.Response."""

    def __init__(self, json_data, status_code=200, headers=None):
        self._json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("Error", request=None, response=self)


@pytest.fixture(autouse=True)
def _clean_state():
    """Clear caches between tests."""
    clear_resolver_cache()
    yield
    clear_resolver_cache()


def test_fetch_history_success(monkeypatch):
    provider = UpstoxProvider()

    def mock_get(*args, **kwargs):
        # [timestamp, open, high, low, close, volume, oi]
        return MockResponse({
            "status": "success",
            "data": {
                "candles": [
                    ["2024-01-01T00:00:00+05:30", 150.0, 155.0, 149.0, 154.0, 1000, 0],
                    ["2024-01-02T00:00:00+05:30", 154.0, 158.0, 153.0, 157.0, 1500, 0],
                ]
            },
        })

    monkeypatch.setattr(provider.client, "get", mock_get)

    df = provider.fetch_history("RELIANCE", date(2024, 1, 1), date(2024, 1, 2))
    assert not df.empty
    assert len(df) == 2
    assert "Close" in df.columns
    assert df.iloc[0]["Close"] == 154.0
    assert df.iloc[1]["Volume"] == 1500


def test_fetch_history_empty_on_error_status(monkeypatch):
    provider = UpstoxProvider()

    def mock_get(*args, **kwargs):
        return MockResponse({"status": "error"})

    monkeypatch.setattr(provider.client, "get", mock_get)

    df = provider.fetch_history("RELIANCE", date(2024, 1, 1), date(2024, 1, 2))
    assert df.empty


def test_fetch_latest_snapshot_success(monkeypatch):
    provider = UpstoxProvider()

    def mock_get(*args, **kwargs):
        return MockResponse({
            "status": "success",
            "data": {
                "NSE_EQ|INE002A01018": {
                    "last_price": 2500.5,
                    "volume": 50000,
                    "ohlc": {
                        "open": 2490.0,
                        "high": 2510.0,
                        "low": 2480.0,
                        "close": 2495.0,
                    },
                }
            },
        })

    monkeypatch.setattr(provider.client, "get", mock_get)

    snapshot = provider.fetch_latest_snapshot("RELIANCE")
    assert snapshot["symbol"] == "RELIANCE"
    assert snapshot["current_price"] == 2500.5
    assert snapshot["open"] == 2490.0
    assert snapshot["volume"] == 50000


def test_fetch_latest_snapshot_invalid_symbol():
    provider = UpstoxProvider()
    # resolve_symbol raises ValueError for unknown symbols;
    # get_quote catches it and returns empty snapshot
    snapshot = provider.fetch_latest_snapshot("XYZNOTREAL")
    assert snapshot["current_price"] == 0.0
    assert snapshot["volume"] == 0


def test_get_ohlc_success(monkeypatch):
    provider = UpstoxProvider()

    def mock_get(*args, **kwargs):
        return MockResponse({
            "status": "success",
            "data": {
                "NSE_EQ|INE002A01018": {
                    "ohlc": {
                        "open": 2490.0,
                        "high": 2510.0,
                        "low": 2480.0,
                        "close": 2495.0,
                    }
                }
            },
        })

    monkeypatch.setattr(provider.client, "get", mock_get)

    ohlc = provider.get_ohlc("RELIANCE")
    assert ohlc["symbol"] == "RELIANCE"
    assert ohlc["open"] == 2490.0
    assert ohlc["high"] == 2510.0
    assert ohlc["close"] == 2495.0


def test_validate_symbol_known():
    provider = UpstoxProvider()
    assert provider.validate_symbol("RELIANCE") is True
    assert provider.validate_symbol("TCS") is True


def test_validate_symbol_unknown():
    provider = UpstoxProvider()
    assert provider.validate_symbol("XYZNOTREAL") is False


def test_response_cache_hit(monkeypatch):
    """After a successful get_quote, the second call should use the cache."""
    provider = UpstoxProvider()
    call_count = 0

    def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return MockResponse({
            "status": "success",
            "data": {
                "NSE_EQ|INE002A01018": {
                    "last_price": 2500.0,
                    "volume": 10000,
                    "ohlc": {"open": 2490.0, "high": 2510.0, "low": 2480.0, "close": 2495.0},
                }
            },
        })

    monkeypatch.setattr(provider.client, "get", mock_get)

    # First call - hits API
    result1 = provider.get_quote("RELIANCE")
    assert call_count == 1

    # Second call - should hit cache, NOT the API
    result2 = provider.get_quote("RELIANCE")
    assert call_count == 1  # No additional API call
    assert result1 == result2
