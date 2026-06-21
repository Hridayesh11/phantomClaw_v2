"""
agents/openclaw_agent.py
------------------------
Wrapper for OpenClaw to integrate it into the AgentVote consensus architecture.

Preserves backward compatibility by leaving generate_trade_recommendation()
untouched, converting its output into an AgentVote.
"""

import logging

from agents.openclaw import generate_trade_recommendation
from models.agent_vote_model import AgentVote

logger = logging.getLogger(__name__)


def generate_vote(symbol: str, market_snapshot: dict, indicators: dict) -> AgentVote:
    """
    Generate an AgentVote using the OpenClaw LLM.

    Args:
        symbol:          Ticker symbol.
        market_snapshot: Latest OHLCV snapshot dict.
        indicators:      Computed indicator dict.

    Returns:
        AgentVote representing OpenClaw's decision.
    """
    try:
        recommendation = generate_trade_recommendation(
            symbol, market_snapshot, indicators
        )
        # Convert TradeRecommendation to AgentVote
        return AgentVote(
            agent_name="OpenClawAgent",
            signal=recommendation.action,
            confidence=recommendation.confidence,
            reason=recommendation.reason,
        )
    except Exception as exc:
        logger.error("OpenClawAgent failed: %s", exc)
        return AgentVote(
            agent_name="OpenClawAgent",
            signal="HOLD",
            confidence=0.5,
            reason="OpenClaw unavailable.",
        )
