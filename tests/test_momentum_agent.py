"""
tests/test_momentum_agent.py
-----------------------------
Deterministic unit tests for agents/momentum_agent.py.

No mocks. No API calls. No randomness.
All tests validate the AgentVote returned by analyze().

Thresholds (from momentum_agent.py):
    RSI_OVERSOLD   = 30.0
    RSI_OVERBOUGHT = 70.0
    BUY_CONFIDENCE  = 0.85
    SELL_CONFIDENCE = 0.85
    HOLD_CONFIDENCE = 0.50
"""

import pytest

from agents.momentum_agent import analyze
from models.agent_vote_model import AgentVote


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _indicators(
    rsi:  float | None = None,
    macd: float | None = None,
    sma20: float | None = 150.0,
    ema50: float | None = 148.0,
    atr:   float | None = 1.5,
) -> dict:
    return {"rsi": rsi, "macd": macd, "sma20": sma20, "ema50": ema50, "atr": atr}


_SNAPSHOT = {"symbol": "AAPL", "current_price": 150.0}


# ─── Return type ──────────────────────────────────────────────────────────────

class TestReturnType:
    def test_returns_agent_vote(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0, macd=0.5))
        assert isinstance(result, AgentVote)

    def test_agent_name_is_momentum_agent(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0, macd=0.5))
        assert result.agent_name == "MomentumAgent"


# ─── Case 1: RSI=20, MACD=0.5 → BUY ─────────────────────────────────────────

class TestCase1BuySignal:
    """RSI < 30 AND MACD > 0 should produce a BUY vote."""

    def test_signal_is_buy(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0, macd=0.5))
        assert result.signal == "BUY"

    def test_confidence_is_0_85(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0, macd=0.5))
        assert result.confidence == pytest.approx(0.85)

    def test_reason_mentions_oversold(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0, macd=0.5))
        assert "oversold" in result.reason.lower() or "bullish" in result.reason.lower()

    def test_rsi_exactly_at_threshold_no_buy(self):
        """RSI=30.0 is not < 30 — should NOT trigger BUY."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=30.0, macd=0.5))
        assert result.signal != "BUY"

    def test_buy_requires_positive_macd(self):
        """RSI < 30 but MACD=0 (not > 0) — should NOT trigger BUY."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0, macd=0.0))
        assert result.signal != "BUY"

    def test_buy_requires_negative_rsi_condition(self):
        """RSI < 30 but MACD < 0 — should NOT trigger BUY."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0, macd=-0.5))
        assert result.signal != "BUY"


# ─── Case 2: RSI=80, MACD=-0.5 → SELL ───────────────────────────────────────

class TestCase2SellSignal:
    """RSI > 70 AND MACD < 0 should produce a SELL vote."""

    def test_signal_is_sell(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=80.0, macd=-0.5))
        assert result.signal == "SELL"

    def test_confidence_is_0_85(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=80.0, macd=-0.5))
        assert result.confidence == pytest.approx(0.85)

    def test_reason_mentions_overbought(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=80.0, macd=-0.5))
        assert "overbought" in result.reason.lower() or "bearish" in result.reason.lower()

    def test_rsi_exactly_at_threshold_no_sell(self):
        """RSI=70.0 is not > 70 — should NOT trigger SELL."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=70.0, macd=-0.5))
        assert result.signal != "SELL"

    def test_sell_requires_negative_macd(self):
        """RSI > 70 but MACD=0 (not < 0) — should NOT trigger SELL."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=80.0, macd=0.0))
        assert result.signal != "SELL"


# ─── Case 3: RSI=50, MACD=0 → HOLD ──────────────────────────────────────────

class TestCase3HoldSignal:
    """Neutral RSI + flat MACD should produce a HOLD vote."""

    def test_signal_is_hold(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=50.0, macd=0.0))
        assert result.signal == "HOLD"

    def test_confidence_is_0_5(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=50.0, macd=0.0))
        assert result.confidence == pytest.approx(0.5)

    def test_reason_mentions_no_signal(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=50.0, macd=0.0))
        assert "no" in result.reason.lower() or "hold" in result.reason.lower()

    @pytest.mark.parametrize("rsi,macd", [
        (29.9, -0.1),   # RSI oversold but MACD not positive
        (70.1,  0.1),   # RSI overbought but MACD not negative
        (50.0,  1.5),   # MACD positive but RSI neutral
        (50.0, -1.5),   # MACD negative but RSI neutral
    ])
    def test_partial_signal_is_hold(self, rsi: float, macd: float):
        """Only one of the two conditions met → HOLD."""
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=rsi, macd=macd))
        assert result.signal == "HOLD"


# ─── Case 4: Missing RSI → HOLD ──────────────────────────────────────────────

class TestCase4MissingRsi:
    """Missing RSI should produce a HOLD vote (insufficient data)."""

    def test_signal_is_hold_when_rsi_missing(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=None, macd=0.5))
        assert result.signal == "HOLD"

    def test_signal_is_hold_when_macd_missing(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=20.0, macd=None))
        assert result.signal == "HOLD"

    def test_signal_is_hold_when_both_missing(self):
        result = analyze("AAPL", _SNAPSHOT, _indicators(rsi=None, macd=None))
        assert result.signal == "HOLD"
