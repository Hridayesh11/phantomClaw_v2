"""
tests/test_trend_agent.py
--------------------------
Deterministic unit tests for agents/trend_agent.py.

No mocks. No API calls. No randomness.
All tests validate the AgentVote returned by analyze().
"""

import pytest

from agents.trend_agent import analyze
from models.agent_vote_model import AgentVote


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _indicators(
    sma20: float | None = None,
    ema50: float | None = None,
    rsi:   float | None = 50.0,
    macd:  float | None = 0.0,
    atr:   float | None = 1.5,
) -> dict:
    return {"sma20": sma20, "ema50": ema50, "rsi": rsi, "macd": macd, "atr": atr}


_SNAPSHOT = {"symbol": "AAPL", "current_price": 150.0}


# ─── Return type ──────────────────────────────────────────────────────────────

class TestReturnType:
    def test_returns_agent_vote(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=160.0, ema50=150.0))
        assert isinstance(result, AgentVote)

    def test_agent_name_is_trend_agent(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=160.0, ema50=150.0))
        assert result.agent_name == "TrendAgent"


# ─── Case 1: sma20 > ema50 → BUY ─────────────────────────────────────────────

class TestCase1BuySignal:
    """SMA20 above EMA50 should produce a BUY vote."""

    def test_signal_is_buy(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=160.0, ema50=150.0))
        assert result.signal == "BUY"

    def test_confidence_is_0_8(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=160.0, ema50=150.0))
        assert result.confidence == pytest.approx(0.8)

    def test_reason_mentions_trend(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=160.0, ema50=150.0))
        assert "above" in result.reason.lower() or "trend" in result.reason.lower()


# ─── Case 2: sma20 < ema50 → SELL ────────────────────────────────────────────

class TestCase2SellSignal:
    """SMA20 below EMA50 should produce a SELL vote."""

    def test_signal_is_sell(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=140.0, ema50=150.0))
        assert result.signal == "SELL"

    def test_confidence_is_0_8(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=140.0, ema50=150.0))
        assert result.confidence == pytest.approx(0.8)

    def test_reason_mentions_below(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=140.0, ema50=150.0))
        assert "below" in result.reason.lower() or "trend" in result.reason.lower()

    def test_sma20_equal_ema50_is_sell(self):
        """Boundary: SMA20 == EMA50 is not > EMA50, so must be SELL."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=150.0, ema50=150.0))
        assert result.signal == "SELL"


# ─── Case 3: missing sma20 → HOLD ────────────────────────────────────────────

class TestCase3MissingSma20:
    """Missing SMA20 should produce a HOLD vote at reduced confidence."""

    def test_signal_is_hold(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=None, ema50=150.0))
        assert result.signal == "HOLD"

    def test_confidence_is_0_5(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=None, ema50=150.0))
        assert result.confidence == pytest.approx(0.5)

    def test_reason_mentions_unavailable(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=None, ema50=150.0))
        assert "unavailable" in result.reason.lower()


# ─── Case 4: missing ema50 → HOLD ────────────────────────────────────────────

class TestCase4MissingEma50:
    """Missing EMA50 should produce a HOLD vote."""

    def test_signal_is_hold(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=160.0, ema50=None))
        assert result.signal == "HOLD"

    def test_confidence_is_0_5(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=160.0, ema50=None))
        assert result.confidence == pytest.approx(0.5)


# ─── Case 5: both missing → HOLD ─────────────────────────────────────────────

class TestCase5BothMissing:
    """Both SMA20 and EMA50 missing should still produce a HOLD."""

    def test_signal_is_hold(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(sma20=None, ema50=None))
        assert result.signal == "HOLD"
