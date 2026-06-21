"""
agents/momentum_agent.py
------------------------
Momentum Agent — PhantomClaw v2 multi-agent consensus layer.

Uses RSI and MACD to identify high-conviction momentum signals.
Returns an AgentVote (not a TradeRecommendation). The ConsensusEngine
aggregates votes from all agents into a final TradeRecommendation.

No LLM. No OpenAI. No randomness. Fully deterministic.
"""

from __future__ import annotations

import logging

from models.agent_vote_model import AgentVote

logger = logging.getLogger(__name__)

# ─── Signal Thresholds ────────────────────────────────────────────────────────

_RSI_OVERSOLD:    float = 30.0
_RSI_OVERBOUGHT:  float = 70.0
_BUY_CONFIDENCE:  float = 0.85
_SELL_CONFIDENCE: float = 0.85
_HOLD_CONFIDENCE: float = 0.50
_AGENT_NAME:      str   = "MomentumAgent"


def analyze(
    symbol: str,
    market_snapshot: dict,
    indicators: dict,
) -> AgentVote:
    """
    Generate a momentum-based agent vote.

    Rules:
        RSI < 30 AND MACD > 0 → BUY  (oversold + bullish momentum)
        RSI > 70 AND MACD < 0 → SELL (overbought + bearish momentum)
        Otherwise              → HOLD (no high-conviction momentum signal)

    Args:
        symbol:          Ticker symbol (e.g. "AAPL").
        market_snapshot: Latest OHLCV snapshot dict.
        indicators:      Computed indicator dict (rsi, macd, macd_signal, sma20, ema50, atr).

    Returns:
        AgentVote with signal, confidence, and reason.
    """
    rsi:  float | None = indicators.get("rsi")
    macd: float | None = indicators.get("macd")

    # BUY — oversold market with bullish MACD momentum
    if rsi is not None and macd is not None and rsi < _RSI_OVERSOLD and macd > 0:
        logger.debug(
            "MomentumAgent BUY: %s | RSI=%.2f < %.0f, MACD=%.4f > 0",
            symbol, rsi, _RSI_OVERSOLD, macd,
        )
        return AgentVote(
            agent_name=_AGENT_NAME,
            signal="BUY",
            confidence=_BUY_CONFIDENCE,
            reason="Oversold RSI with bullish MACD momentum.",
        )

    # SELL — overbought market with bearish MACD momentum
    if rsi is not None and macd is not None and rsi > _RSI_OVERBOUGHT and macd < 0:
        logger.debug(
            "MomentumAgent SELL: %s | RSI=%.2f > %.0f, MACD=%.4f < 0",
            symbol, rsi, _RSI_OVERBOUGHT, macd,
        )
        return AgentVote(
            agent_name=_AGENT_NAME,
            signal="SELL",
            confidence=_SELL_CONFIDENCE,
            reason="Overbought RSI with bearish MACD momentum.",
        )

    # HOLD — no high-conviction momentum signal
    logger.debug("MomentumAgent HOLD: %s | RSI=%s, MACD=%s", symbol, rsi, macd)
    return AgentVote(
        agent_name=_AGENT_NAME,
        signal="HOLD",
        confidence=_HOLD_CONFIDENCE,
        reason="No high-conviction momentum signal.",
    )
