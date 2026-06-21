"""
agents/challenge_agent.py
--------------------------
Challenge Agent — PhantomClaw's built-in devil's advocate.

Receives the OpenClaw trade recommendation and produces both supporting
arguments AND opposing counterarguments. All LLM calls are delegated to
the llm/ layer — this agent never imports OpenAI directly.

Philosophy: "We don't trust AI — we verify it."
"""

import json
import logging

from llm.openai_client import call_llm
from llm.prompts import CHALLENGE_SYSTEM_PROMPT
from models.trade_model import TradeRecommendation, ChallengeResult

logger = logging.getLogger(__name__)


def challenge_recommendation(
    recommendation: TradeRecommendation,
    indicators: dict,
) -> ChallengeResult:
    """
    Challenge a trade recommendation with both support and opposition arguments.

    Args:
        recommendation: The TradeRecommendation from OpenClaw.
        indicators:     Technical indicator context (rsi, macd, atr, etc.)

    Returns:
        A ChallengeResult with support_reasoning and opposing_reasoning.
    """
    user_prompt = f"""
The OpenClaw AI has produced the following trade recommendation. Analyze it critically.

Trade Recommendation:
  Symbol     : {recommendation.symbol}
  Action     : {recommendation.action}
  Quantity   : {recommendation.quantity} shares
  Confidence : {recommendation.confidence:.2%}
  Reason     : {recommendation.reason}

Market Context (Technical Indicators):
  RSI (14)          : {indicators.get('rsi', 'N/A')}
  MACD              : {indicators.get('macd', 'N/A')}
  MACD Signal       : {indicators.get('macd_signal', 'N/A')}
  SMA20             : {indicators.get('sma20', 'N/A')}
  EMA50             : {indicators.get('ema50', 'N/A')}
  ATR (volatility)  : {indicators.get('atr', 'N/A')}

Produce a balanced challenge. Respond with a JSON object only.
""".strip()

    logger.info(
        "Challenge Agent analyzing: %s %s %s",
        recommendation.action,
        recommendation.quantity,
        recommendation.symbol,
    )

    try:
        raw = call_llm(CHALLENGE_SYSTEM_PROMPT, user_prompt, temperature=0.4, max_tokens=600)
        data = json.loads(raw)

        result = ChallengeResult(
            support_reasoning=str(
                data.get("support_reasoning", "No support argument generated.")
            ),
            opposing_reasoning=str(
                data.get("opposing_reasoning", "No opposing argument generated.")
            ),
        )
        logger.info("Challenge Agent completed for %s", recommendation.symbol)
        return result

    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.error("Challenge Agent failed to parse LLM response: %s", exc)
        # Return a graceful fallback — never crash the pipeline
        return ChallengeResult(
            support_reasoning="Challenge Agent was unable to generate support arguments.",
            opposing_reasoning=f"Challenge Agent encountered an error: {exc}",
        )
