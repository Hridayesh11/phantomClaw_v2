"""
tests/test_mean_reversion_agent.py
------------------------------------
Deterministic unit tests for agents/mean_reversion_agent.py.

No mocks. No API calls. No randomness.
All tests validate the AgentVote returned by analyze().

Thresholds (from mean_reversion_agent.py):
    RSI_EXTREME_OVERSOLD   = 25.0
    RSI_EXTREME_OVERBOUGHT = 75.0
    SIGNAL_CONFIDENCE      = 0.75
    HOLD_CONFIDENCE        = 0.50
"""

import pytest

from agents.mean_reversion_agent import analyze
from models.agent_vote_model import AgentVote


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _indicators(
    rsi:  float | None = None,
    macd: float | None = 0.0,
    sma20: float | None = 150.0,
    ema50: float | None = 148.0,
    atr:   float | None = 1.5,
) -> dict:
    return {"rsi": rsi, "macd": macd, "sma20": sma20, "ema50": ema50, "atr": atr}


_SNAPSHOT = {"symbol": "AAPL", "current_price": 150.0}


# ─── Return type ──────────────────────────────────────────────────────────────

class TestReturnType:
    def test_returns_agent_vote(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0))
        assert isinstance(result, AgentVote)

    def test_agent_name_is_mean_reversion(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0))
        assert result.agent_name == "MeanReversionAgent"


# ─── Case 1: RSI=20 → BUY ────────────────────────────────────────────────────

class TestCase1BuySignal:
    """RSI < 25 should produce a BUY vote (extreme oversold)."""

    def test_signal_is_buy(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0))
        assert result.signal == "BUY"

    def test_confidence_is_0_75(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0))
        assert result.confidence == pytest.approx(0.75)

    def test_reason_mentions_oversold(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0))
        assert "oversold" in result.reason.lower() or "reversion" in result.reason.lower()

    def test_rsi_value_in_reason(self):
        """The reason should embed the actual RSI value."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0))
        assert "20" in result.reason

    def test_rsi_exactly_at_threshold_no_buy(self):
        """RSI=25.0 is not < 25 — must NOT trigger BUY."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=25.0))
        assert result.signal != "BUY"

    def test_rsi_just_below_threshold_is_buy(self):
        """RSI=24.9 is < 25 — must trigger BUY."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=24.9))
        assert result.signal == "BUY"


# ─── Case 2: RSI=80 → SELL ───────────────────────────────────────────────────

class TestCase2SellSignal:
    """RSI > 75 should produce a SELL vote (extreme overbought)."""

    def test_signal_is_sell(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=80.0))
        assert result.signal == "SELL"

    def test_confidence_is_0_75(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=80.0))
        assert result.confidence == pytest.approx(0.75)

    def test_reason_mentions_overbought(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=80.0))
        assert "overbought" in result.reason.lower() or "reversion" in result.reason.lower()

    def test_rsi_exactly_at_threshold_no_sell(self):
        """RSI=75.0 is not > 75 — must NOT trigger SELL."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=75.0))
        assert result.signal != "SELL"

    def test_rsi_just_above_threshold_is_sell(self):
        """RSI=75.1 is > 75 — must trigger SELL."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=75.1))
        assert result.signal == "SELL"


# ─── Case 3: RSI=50 → HOLD ───────────────────────────────────────────────────

class TestCase3HoldSignal:
    """Neutral RSI (25–75 range) should produce a HOLD vote."""

    def test_signal_is_hold(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=50.0))
        assert result.signal == "HOLD"

    def test_confidence_is_0_5(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=50.0))
        assert result.confidence == pytest.approx(0.5)

    def test_reason_mentions_neutral(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=50.0))
        assert "neutral" in result.reason.lower() or "no" in result.reason.lower()

    @pytest.mark.parametrize("rsi", [25.0, 30.0, 50.0, 70.0, 75.0])
    def test_neutral_range_is_hold(self, rsi: float):
        """All values in the neutral RSI range [25, 75] must produce HOLD."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=rsi))
        assert result.signal == "HOLD"


# ─── Case 4: Missing RSI → HOLD ──────────────────────────────────────────────

class TestCase4MissingRsi:
    """Missing RSI should produce a HOLD vote (insufficient data)."""

    def test_signal_is_hold_when_rsi_none(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=None))
        assert result.signal == "HOLD"

    def test_confidence_is_0_5_when_rsi_missing(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=None))
        assert result.confidence == pytest.approx(0.5)
