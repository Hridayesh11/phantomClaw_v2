"""
agents/trend_agent.py
---------------------
Trend Agent — PhantomClaw v2 multi-agent consensus layer.

Uses the relationship between SMA20 and EMA50 to determine whether
short-term price momentum is above or below the long-term trend.

Returns an AgentVote (not a TradeRecommendation). The ConsensusEngine
aggregates votes from all agents into a final TradeRecommendation.

No LLM. No OpenAI. No randomness. Fully deterministic.
"""

from __future__ import annotations

import logging

from models.agent_vote_model import AgentVote

logger = logging.getLogger(__name__)

# ─── Signal Thresholds ────────────────────────────────────────────────────────

_CONFIDENCE:      float = 0.8
_HOLD_CONFIDENCE: float = 0.5
_AGENT_NAME:      str   = "TrendAgent"


def analyze(
    symbol: str,
    market_snapshot: dict,
    indicators: dict,
) -> AgentVote:
    """
    Generate a trend-following agent vote.

    Rules:
        SMA20 or EMA50 missing → HOLD  (insufficient data)
        SMA20 > EMA50          → BUY   (short-term above long-term trend)
        SMA20 ≤ EMA50          → SELL  (short-term below long-term trend)

    Args:
        symbol:          Ticker symbol (e.g. "AAPL").
        market_snapshot: Latest OHLCV snapshot dict.
        indicators:      Computed indicator dict (sma20, ema50, rsi, macd, atr).

    Returns:
        AgentVote with signal, confidence, and reason.
    """
    sma20: float | None = indicators.get("sma20")
    ema50: float | None = indicators.get("ema50")

    # Missing indicators — cannot make a reliable trend call
    if sma20 is None or ema50 is None:
        logger.debug("TrendAgent HOLD: %s | SMA20=%s, EMA50=%s (unavailable)", symbol, sma20, ema50)
        return AgentVote(
            agent_name=_AGENT_NAME,
            signal="HOLD",
            confidence=_HOLD_CONFIDENCE,
            reason="Trend indicators unavailable.",
        )

    # BUY — short-term trend above long-term trend
    if sma20 > ema50:
        logger.debug("TrendAgent BUY: %s | SMA20=%.2f > EMA50=%.2f", symbol, sma20, ema50)
        return AgentVote(
            agent_name=_AGENT_NAME,
            signal="BUY",
            confidence=_CONFIDENCE,
            reason="Short-term trend above long-term trend.",
        )

    # SELL — short-term trend below long-term trend
    logger.debug("TrendAgent SELL: %s | SMA20=%.2f <= EMA50=%.2f", symbol, sma20, ema50)
    return AgentVote(
        agent_name=_AGENT_NAME,
        signal="SELL",
        confidence=_CONFIDENCE,
        reason="Short-term trend below long-term trend.",
    )
