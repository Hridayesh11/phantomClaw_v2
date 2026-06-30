"""
tests/test_provider_factory.py
------------------------------
Deterministic unit tests for provider_factory.py.
"""

from market_data.base_provider import MarketDataProvider
from market_data.provider_factory import get_market_provider
from market_data.upstox_provider import UpstoxProvider

def test_get_market_provider_returns_upstox():
    provider = get_market_provider()
    
    assert isinstance(provider, MarketDataProvider)
    assert isinstance(provider, UpstoxProvider)
