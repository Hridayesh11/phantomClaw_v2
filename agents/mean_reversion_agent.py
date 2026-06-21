"""
agents/mean_reversion_agent.py
------------------------------
Mean Reversion Agent — PhantomClaw v2 multi-agent consensus layer.

Uses extreme RSI levels to identify likely mean-reversion setups.
Returns an AgentVote (not a TradeRecommendation). The ConsensusEngine
aggregates votes from all agents into a final TradeRecommendation.

ATR is available in the indicator dict for future volatility-gating
extensions but is not used in the current signal rules.

No LLM. No OpenAI. No randomness. Fully deterministic.
"""

from __future__ import annotations

import logging

from models.agent_vote_model import AgentVote

logger = logging.getLogger(__name__)

# ─── Signal Thresholds ────────────────────────────────────────────────────────

_RSI_EXTREME_OVERSOLD:   float = 25.0
_RSI_EXTREME_OVERBOUGHT: float = 75.0
_SIGNAL_CONFIDENCE:      float = 0.75
_HOLD_CONFIDENCE:        float = 0.50
_AGENT_NAME:             str   = "MeanReversionAgent"


def analyze(
    symbol: str,
    market_snapshot: dict,
    indicators: dict,
) -> AgentVote:
    """
    Generate a mean-reversion agent vote.

    Rules:
        RSI < 25 → BUY  (extreme oversold — price likely to bounce)
        RSI > 75 → SELL (extreme overbought — price likely to pull back)
        Otherwise → HOLD (RSI in neutral range, no reversion opportunity)

    ATR is accepted in the indicator dict for forward-compatibility
    (e.g. gating signals when volatility is too high) but is not used
    in the current implementation.

    Args:
        symbol:          Ticker symbol (e.g. "AAPL").
        market_snapshot: Latest OHLCV snapshot dict.
        indicators:      Computed indicator dict (rsi, macd, macd_signal, sma20, ema50, atr).

    Returns:
        AgentVote with signal, confidence, and reason.
    """
    rsi: float | None = indicators.get("rsi")

    # BUY — extreme oversold, expect mean reversion upward
    if rsi is not None and rsi < _RSI_EXTREME_OVERSOLD:
        logger.debug(
            "MeanReversionAgent BUY: %s | RSI=%.2f < %.0f",
            symbol, rsi, _RSI_EXTREME_OVERSOLD,
        )
        return AgentVote(
            agent_name=_AGENT_NAME,
            signal="BUY",
            confidence=_SIGNAL_CONFIDENCE,
            reason=f"Extreme oversold RSI ({rsi:.1f}) — mean reversion expected.",
        )

    # SELL — extreme overbought, expect mean reversion downward
    if rsi is not None and rsi > _RSI_EXTREME_OVERBOUGHT:
        logger.debug(
            "MeanReversionAgent SELL: %s | RSI=%.2f > %.0f",
            symbol, rsi, _RSI_EXTREME_OVERBOUGHT,
        )
        return AgentVote(
            agent_name=_AGENT_NAME,
            signal="SELL",
            confidence=_SIGNAL_CONFIDENCE,
            reason=f"Extreme overbought RSI ({rsi:.1f}) — mean reversion expected.",
        )

    # HOLD — RSI is in a neutral range
    logger.debug("MeanReversionAgent HOLD: %s | RSI=%s", symbol, rsi)
    return AgentVote(
        agent_name=_AGENT_NAME,
        signal="HOLD",
        confidence=_HOLD_CONFIDENCE,
        reason="RSI in neutral range — no mean-reversion opportunity.",
    )
