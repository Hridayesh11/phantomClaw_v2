"""
consensus/consensus_engine.py
------------------------------
Consensus Engine — PhantomClaw v2 multi-agent coordination layer.

PURPOSE
-------
Aggregates AgentVote outputs from three deterministic specialist agents
into a single TradeRecommendation via majority-vote logic.

AGENTS AGGREGATED
-----------------
  1. TrendAgent         — SMA20 vs EMA50
  2. MomentumAgent      — RSI + MACD
  3. MeanReversionAgent — extreme RSI levels

VOTE RESOLUTION
---------------
  BUY ≥ 2 votes  → BUY   (quantity=10)
  SELL ≥ 2 votes → SELL  (quantity=10)
  Tie (1-1-1)    → HOLD  (quantity=0)

CONFIDENCE THRESHOLD
--------------------
  MIN_CONSENSUS_CONFIDENCE = 0.7

  After majority is resolved, the average confidence of the majority
  group is computed. If it falls below 0.7, the decision is forced to
  HOLD regardless of the vote outcome.

HOLD
----
  HOLD is a first-class action in TradeRecommendation.
  action="HOLD", quantity=0 is always used directly.

No LLM. No OpenAI. No randomness. Fully deterministic.
"""

from __future__ import annotations

import logging

from agents.mean_reversion_agent import analyze as mean_reversion_analyze
from agents.momentum_agent import analyze as momentum_analyze
from agents.trend_agent import analyze as trend_analyze
from models.agent_vote_model import AgentVote
from models.trade_model import TradeRecommendation

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

_EXECUTE_QUANTITY:       int   = 10
_HOLD_QUANTITY:          int   = 0
MIN_CONSENSUS_CONFIDENCE: float = 0.7


# ─── Public Interface ─────────────────────────────────────────────────────────


def get_consensus(
    symbol: str,
    market_snapshot: dict,
    indicators: dict,
) -> TradeRecommendation:
    """
    Run all three specialist agents and return a majority-vote consensus.

    Args:
        symbol:          Ticker symbol (e.g. "AAPL").
        market_snapshot: Latest OHLCV snapshot dict (same format as live pipeline).
        indicators:      Computed indicator dict (rsi, macd, macd_signal, sma20, ema50, atr).

    Returns:
        A single TradeRecommendation representing the consensus decision.
        action="HOLD" with quantity=0 means no order should be placed.

    Vote logic:
        ≥ 2 BUY  votes → BUY  (quantity=10) if avg_confidence ≥ 0.7
        ≥ 2 SELL votes → SELL (quantity=10) if avg_confidence ≥ 0.7
        Tie            → HOLD (quantity=0)
        avg_confidence < MIN_CONSENSUS_CONFIDENCE → force HOLD
    """
    # ── 1. Collect votes from all agents ─────────────────────────────────────
    votes: list[AgentVote] = [
        trend_analyze(symbol, market_snapshot, indicators),
        momentum_analyze(symbol, market_snapshot, indicators),
        mean_reversion_analyze(symbol, market_snapshot, indicators),
    ]

    # ── 2. Log individual votes ───────────────────────────────────────────────
    for v in votes:
        logger.info(
            "  [%s] signal=%-4s confidence=%.0f%% | %s",
            v.agent_name, v.signal, v.confidence * 100, v.reason,
        )

    # ── 3. Count directional votes ────────────────────────────────────────────
    buy_votes  = [v for v in votes if v.signal == "BUY"]
    sell_votes = [v for v in votes if v.signal == "SELL"]
    hold_votes = [v for v in votes if v.signal == "HOLD"]

    logger.info(
        "Vote tally for %s: BUY=%d SELL=%d HOLD=%d",
        symbol, len(buy_votes), len(sell_votes), len(hold_votes),
    )

    # ── 4. Resolve majority ───────────────────────────────────────────────────
    if len(buy_votes) >= 2:
        majority       = buy_votes
        action         = "BUY"
        quantity       = _EXECUTE_QUANTITY
        majority_label = "BUY"
    elif len(sell_votes) >= 2:
        majority       = sell_votes
        action         = "SELL"
        quantity       = _EXECUTE_QUANTITY
        majority_label = "SELL"
    else:
        # Three-way tie — immediate HOLD, no threshold check needed
        majority       = votes
        action         = "HOLD"
        quantity       = _HOLD_QUANTITY
        majority_label = "HOLD (tie)"

    # ── 5. Compute average confidence of the majority group ───────────────────
    avg_confidence = round(
        sum(v.confidence for v in majority) / len(majority), 6
    )

    logger.info(
        "Majority: %s | avg_confidence=%.0f%% (threshold=%.0f%%)",
        majority_label, avg_confidence * 100, MIN_CONSENSUS_CONFIDENCE * 100,
    )

    # ── 6. Apply confidence threshold override ────────────────────────────────
    if quantity > 0 and avg_confidence < MIN_CONSENSUS_CONFIDENCE:
        logger.info(
            "Consensus confidence %.0f%% < threshold %.0f%% → forcing HOLD for %s",
            avg_confidence * 100, MIN_CONSENSUS_CONFIDENCE * 100, symbol,
        )
        action         = "HOLD"
        quantity       = _HOLD_QUANTITY
        majority_label = "HOLD (low confidence)"
        combined_reason = (
            f"Consensus confidence below threshold "
            f"({avg_confidence:.0%} < {MIN_CONSENSUS_CONFIDENCE:.0%})."
        )
    else:
        # ── 7. Concatenate reasons from majority agents ────────────────────────
        combined_reason = " | ".join(
            f"[{v.agent_name}] {v.reason}" for v in majority
        )

    # ── 8. Build and log final result ─────────────────────────────────────────
    result = TradeRecommendation(
        symbol=symbol.upper(),
        action=action,
        quantity=quantity,
        confidence=avg_confidence,
        reason=combined_reason,
    )

    decision_label = action if quantity > 0 else majority_label
    logger.info(
        "Consensus FINAL → %s | confidence=%.0f%% | %s",
        decision_label, avg_confidence * 100, combined_reason[:100],
    )

    return result
