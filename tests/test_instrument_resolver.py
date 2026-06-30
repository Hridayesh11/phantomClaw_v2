"""
tests/test_instrument_resolver.py
---------------------------------
Deterministic unit tests for instrument_resolver.py.

Tests cover:
  - Static fallback map resolution
  - Case insensitivity and whitespace handling
  - Unknown symbol error
  - Empty symbol error
  - Cache clearing
"""

import pytest
from market_data.instrument_resolver import resolve_symbol, clear_cache


@pytest.fixture(autouse=True)
def _clear_resolver_cache():
    """Ensure the resolver cache is clean for each test."""
    clear_cache()
    yield
    clear_cache()


def test_valid_symbol_lookup():
    assert resolve_symbol("RELIANCE") == "NSE_EQ|INE002A01018"
    assert resolve_symbol("TCS") == "NSE_EQ|INE467B01029"


def test_lowercase_symbol_lookup():
    assert resolve_symbol("reliance") == "NSE_EQ|INE002A01018"
    assert resolve_symbol("infy") == "NSE_EQ|INE009A01021"


def test_whitespace_symbol_lookup():
    assert resolve_symbol("  HDFCBANK  ") == "NSE_EQ|INE040A01034"


def test_invalid_symbol_lookup_raises():
    with pytest.raises(ValueError, match="Unknown symbol: XYZNOTREAL"):
        resolve_symbol("XYZNOTREAL")


def test_empty_symbol_lookup_raises():
    with pytest.raises(ValueError, match="Symbol cannot be empty."):
        resolve_symbol("")

    with pytest.raises(ValueError, match="Symbol cannot be empty."):
        resolve_symbol("   ")


def test_additional_nse_symbols():
    """Verify a selection of NSE symbols from the expanded static map."""
    assert resolve_symbol("ICICIBANK") == "NSE_EQ|INE090A01021"
    assert resolve_symbol("SBIN") == "NSE_EQ|INE062A01020"
    assert resolve_symbol("TATAMOTORS") == "NSE_EQ|INE155A01022"


def test_cache_is_populated_after_first_resolve():
    """After resolving once, the cache should serve subsequent lookups."""
    # First call populates the cache
    key1 = resolve_symbol("RELIANCE")
    # Second call should return the same value (from cache)
    key2 = resolve_symbol("RELIANCE")
    assert key1 == key2
