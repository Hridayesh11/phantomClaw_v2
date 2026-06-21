"""
backtesting/strategy_agent.py
------------------------------
Deterministic rule-based strategy agent for the PhantomClaw backtesting engine.

PURPOSE
-------
The live pipeline uses OpenClaw (LLM) for trade recommendations.
Backtesting must be:
  - Deterministic  — same inputs always produce the same output.
  - Reproducible   — no randomness, no external API calls.
  - Zero-cost      — no OpenAI tokens consumed.

This module implements the same interface as agents/openclaw.py but uses
pure technical-indicator rules instead of an LLM.

RULES
-----
  BUY  signal: RSI < 30 AND MACD > 0  (oversold + bullish momentum)
  SELL signal: RSI > 70 AND MACD < 0  (overbought + bearish momentum)
  Otherwise:   HOLD with quantity=0 (no active trade)

DESIGN CONTRACT
---------------
  - Input/output types are identical to generate_trade_recommendation().
  - Callers in backtest_engine.py can swap this module in without any other
    changes to the pipeline.
  - Never raises — always returns a valid TradeRecommendation.
"""

from __future__ import annotations

import logging

from models.trade_model import TradeRecommendation

logger = logging.getLogger(__name__)

# ─── Signal Thresholds ────────────────────────────────────────────────────────

_RSI_OVERSOLD: float = 30.0     # RSI below this → oversold (BUY signal)
_RSI_OVERBOUGHT: float = 70.0   # RSI above this → overbought (SELL signal)
_SIGNAL_CONFIDENCE: float = 0.8
_NO_SIGNAL_CONFIDENCE: float = 0.3
_DEFAULT_QUANTITY: int = 10


# ─── Public Interface ─────────────────────────────────────────────────────────


def generate_strategy_recommendation(
    symbol: str,
    market_snapshot: dict,
    indicators: dict,
) -> TradeRecommendation:
    """
    Generate a deterministic, rule-based trade recommendation.

    No LLM. No OpenAI. No randomness.

    Args:
        symbol:          Ticker symbol (e.g. "AAPL").
        market_snapshot: Latest OHLCV snapshot dict (same format as live pipeline).
        indicators:      Computed indicator dict with keys: rsi, macd, macd_signal,
                         sma20, ema50, atr.

    Returns:
        A validated TradeRecommendation Pydantic model.
        HOLD (quantity=0) signals no active trade — the Execution Controller
        will treat this as a pass-through bar.

    Signal logic:
        BUY  → RSI < 30 AND MACD > 0
        SELL → RSI > 70 AND MACD < 0
        HOLD → no high-conviction setup (quantity=0)
    """
    rsi: float | None = indicators.get("rsi")
    macd: float | None = indicators.get("macd")

    # ── BUY signal: oversold market with bullish MACD momentum ────────────────
    if rsi is not None and macd is not None and rsi < _RSI_OVERSOLD and macd > 0:
        logger.debug(
            "Strategy BUY signal: %s | RSI=%.2f < %.0f, MACD=%.4f > 0",
            symbol, rsi, _RSI_OVERSOLD, macd,
        )
        return TradeRecommendation(
            symbol=symbol.upper(),
            action="BUY",
            quantity=_DEFAULT_QUANTITY,
            confidence=_SIGNAL_CONFIDENCE,
            reason="Oversold market with bullish MACD momentum",
        )

    # ── SELL signal: overbought market with bearish MACD momentum ─────────────
    if rsi is not None and macd is not None and rsi > _RSI_OVERBOUGHT and macd < 0:
        logger.debug(
            "Strategy SELL signal: %s | RSI=%.2f > %.0f, MACD=%.4f < 0",
            symbol, rsi, _RSI_OVERBOUGHT, macd,
        )
        return TradeRecommendation(
            symbol=symbol.upper(),
            action="SELL",
            quantity=_DEFAULT_QUANTITY,
            confidence=_SIGNAL_CONFIDENCE,
            reason="Overbought market with bearish MACD momentum",
        )

    # ── No high-conviction setup ───────────────────────────────────────────────────────────
    logger.debug(
        "Strategy: no signal for %s | RSI=%s, MACD=%s",
        symbol, rsi, macd,
    )
    return TradeRecommendation(
        symbol=symbol.upper(),
        action="HOLD",
        quantity=0,
        confidence=_NO_SIGNAL_CONFIDENCE,
        reason="No high-conviction setup",
    )
