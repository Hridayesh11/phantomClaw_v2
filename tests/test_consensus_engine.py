"""
tests/test_consensus_engine.py
--------------------------------
Deterministic unit tests for consensus/consensus_engine.py.

All tests validate the TradeRecommendation returned by get_consensus().

Consensus constants (from consensus_engine.py):
    MIN_CONSENSUS_SCORE = 1.5

Agent confidence values (reference):
    TrendAgent:        BUY/SELL=0.8,  HOLD=0.5
    MomentumAgent:     BUY/SELL=0.85, HOLD=0.5
    MeanReversionAgent:BUY/SELL=0.75, HOLD=0.5

HOLD encoding in TradeRecommendation: action="HOLD", quantity=0
"""

import pytest

from consensus.consensus_engine import MIN_CONSENSUS_SCORE, get_consensus
from models.agent_vote_model import AgentVote
from models.trade_model import TradeRecommendation

_SNAPSHOT = {"symbol": "AAPL", "current_price": 150.0}

def _ind(
    sma20: float | None = 150.0,
    ema50: float | None = 148.0,
    rsi:   float | None = 50.0,
    macd:  float | None = 0.0,
    atr:   float | None = 1.5,
) -> dict:
    return {"sma20": sma20, "ema50": ema50, "rsi": rsi, "macd": macd, "atr": atr}

# ─── Mocks for OpenClaw votes ──────────────────────────────────────────────────

def _openclaw_vote(signal: str, confidence: float) -> AgentVote:
    return AgentVote(
        agent_name="OpenClawAgent",
        signal=signal,
        confidence=confidence,
        reason="Test reason."
    )

def _openclaw_fallback() -> AgentVote:
    return AgentVote(
        agent_name="OpenClawAgent",
        signal="HOLD",
        confidence=0.5,
        reason="OpenClaw unavailable."
    )

# ─── Test Cases ───────────────────────────────────────────────────────────────

class TestConsensusEngine:

    def test_openclaw_buy_trend_buy_others_hold(self):
        """
        OpenClaw BUY (0.9), Trend BUY (0.8), Momentum HOLD (0.5), MeanRev HOLD (0.5).
        BUY_SCORE = 1.7
        HOLD_SCORE = 1.0
        Winner: BUY
        Final Confidence = (0.9^2 + 0.8^2) / (0.9 + 0.8) = (0.81 + 0.64) / 1.7 = 1.45 / 1.7 = 0.852941
        """
        oc_vote = _openclaw_vote("BUY", 0.9)
        # Trend BUY, others HOLD
        ind = _ind(sma20=160.0, ema50=150.0, rsi=50.0, macd=0.0)
        
        result = get_consensus("AAPL", oc_vote, _SNAPSHOT, ind)
        
        assert result.action == "BUY"
        assert result.quantity == 10
        expected_conf = (0.9**2 + 0.8**2) / (0.9 + 0.8)
        assert result.confidence == pytest.approx(expected_conf, rel=1e-4)

    def test_openclaw_sell_momentum_sell(self):
        """
        OpenClaw SELL (0.8), Trend HOLD (0.5), Momentum SELL (0.85), MeanRev HOLD (0.5).
        SELL_SCORE = 1.65
        HOLD_SCORE = 1.0
        Winner: SELL
        """
        oc_vote = _openclaw_vote("SELL", 0.8)
        # Momentum SELL, Trend HOLD (sma20=None)
        ind = _ind(sma20=None, ema50=150.0, rsi=75.0, macd=-0.5)
        
        result = get_consensus("AAPL", oc_vote, _SNAPSHOT, ind)
        
        assert result.action == "SELL"
        assert result.quantity == 10
        expected_conf = (0.8**2 + 0.85**2) / (0.8 + 0.85)
        assert result.confidence == pytest.approx(expected_conf, rel=1e-4)

    def test_consensus_tie(self):
        """
        Since tie >= 1.5 is mathematically impossible with the fixed agent
        confidences without mocking, we construct a tie at 0.85.
        Trend BUY (0.8), Mom SELL (0.85). MeanRev HOLD (0.5).
        OpenClaw votes BUY (0.05).
        BUY = 0.8 + 0.05 = 0.85.
        SELL = 0.85.
        HOLD = 0.5.
        Tie between BUY and SELL at 0.85.
        """
        oc_vote = _openclaw_vote("BUY", 0.05)
        # Trend BUY (160>150), Mom SELL (rsi=72, macd=-0.5), MeanRev HOLD (rsi=72)
        ind = _ind(sma20=160.0, ema50=150.0, rsi=72.0, macd=-0.5)
        
        result = get_consensus("AAPL", oc_vote, _SNAPSHOT, ind)
        
        assert result.action == "HOLD"
        assert result.quantity == 0
        assert result.reason == "Consensus tie."

    def test_low_consensus_score(self):
        """
        All agents vote differently or with low confidence.
        OpenClaw BUY (0.3). Trend HOLD (0.5). Mom HOLD (0.5). MeanRev BUY (0.75) -> wait, MeanRev HOLD (0.5).
        HOLD_SCORE = 1.5 -> Tie with threshold? Minimum score is 1.5. If it's exactly 1.5, it passes!
        "If max_score < MIN_CONSENSUS_SCORE: force HOLD" -> 1.5 is NOT < 1.5.
        Let's test max_score < 1.5.
        OpenClaw SELL (0.3), Trend BUY (0.8), Mom HOLD (0.5), MeanRev SELL (0.75 - wait, if MeanRev is SELL, rsi>75. Mom is SELL if rsi>70 & macd<0.
        Let's do: Trend BUY (0.8), Mom HOLD (0.5), MeanRev HOLD (0.5) -> HOLD is 1.0, BUY is 0.8.
        OpenClaw SELL (0.3).
        Total: BUY=0.8, HOLD=1.0, SELL=0.3.
        Max score = 1.0. This is < 1.5!
        """
        oc_vote = _openclaw_vote("SELL", 0.3)
        ind = _ind(sma20=160.0, ema50=150.0, rsi=50.0, macd=0.0)
        
        result = get_consensus("AAPL", oc_vote, _SNAPSHOT, ind)
        
        assert result.action == "HOLD"
        assert result.quantity == 0
        assert result.reason == "Consensus strength below threshold."

    def test_openclaw_unavailable_fallback(self):
        """
        If OpenClaw fails, we pass the fallback vote.
        Fallback is HOLD (0.5).
        Trend BUY (0.8), Mom BUY (0.85 -> rsi=20, macd=1), MeanRev BUY (0.75 -> rsi=20).
        BUY_SCORE = 0.8 + 0.85 + 0.75 = 2.40.
        HOLD_SCORE = 0.5 (from OpenClaw).
        Winner = BUY.
        """
        oc_vote = _openclaw_fallback()
        ind = _ind(sma20=160.0, ema50=150.0, rsi=20.0, macd=1.0)
        
        result = get_consensus("AAPL", oc_vote, _SNAPSHOT, ind)
        
        assert result.action == "BUY"
        assert result.quantity == 10
        expected_conf = (0.8**2 + 0.85**2 + 0.75**2) / (0.8 + 0.85 + 0.75)
        assert result.confidence == pytest.approx(expected_conf, rel=1e-4)
