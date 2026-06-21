"""
agents/openclaw.py
------------------
OpenClaw Agent — PhantomClaw's primary AI trade analyst.

Analyzes real market data + technical indicators and produces a structured
trade recommendation. All LLM calls are delegated to the llm/ layer —
this agent never imports OpenAI directly.
"""

import json
import logging

from llm.openai_client import call_llm
from llm.prompts import OPENCLAW_SYSTEM_PROMPT
from models.trade_model import TradeRecommendation

logger = logging.getLogger(__name__)


def generate_trade_recommendation(
    symbol: str,
    market_data: dict,
    indicators: dict,
) -> TradeRecommendation:
    """
    Generate a trade recommendation for a given symbol.

    Args:
        symbol:      Ticker symbol (e.g. "AAPL")
        market_data: Latest OHLCV snapshot dict from market module
        indicators:  Computed indicator summary dict from indicators module

    Returns:
        A validated TradeRecommendation Pydantic model.

    Raises:
        ValueError: If the LLM response cannot be parsed into a valid recommendation.
    """
    user_prompt = f"""
Analyze the following market data and generate a trade recommendation.

Symbol: {symbol}

Latest Market Data:
  Current Price : ${market_data.get('current_price', 'N/A')}
  Open          : ${market_data.get('open', 'N/A')}
  High          : ${market_data.get('high', 'N/A')}
  Low           : ${market_data.get('low', 'N/A')}
  Close         : ${market_data.get('close', 'N/A')}
  Volume        : {market_data.get('volume', 'N/A'):,}

Technical Indicators:
  RSI (14)      : {indicators.get('rsi', 'N/A')}
  MACD          : {indicators.get('macd', 'N/A')}
  MACD Signal   : {indicators.get('macd_signal', 'N/A')}
  SMA20         : {indicators.get('sma20', 'N/A')}
  EMA50         : {indicators.get('ema50', 'N/A')}
  ATR (14)      : {indicators.get('atr', 'N/A')}

Based on this data, provide your trade recommendation as a JSON object.
""".strip()

    logger.info("OpenClaw generating recommendation for %s", symbol)

    try:
        raw = call_llm(OPENCLAW_SYSTEM_PROMPT, user_prompt, temperature=0.3, max_tokens=512)
        data = json.loads(raw)

        # Normalise fields for safety
        data["symbol"] = symbol.upper()
        data["action"] = str(data.get("action", "BUY")).upper()
        data["quantity"] = int(data.get("quantity", 10))
        data["confidence"] = float(data.get("confidence", 0.5))
        data["reason"] = str(data.get("reason", ""))

        recommendation = TradeRecommendation(**data)
        logger.info(
            "OpenClaw → %s %d %s (confidence=%.2f)",
            recommendation.action,
            recommendation.quantity,
            recommendation.symbol,
            recommendation.confidence,
        )
        return recommendation

    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.error("OpenClaw failed to parse LLM response: %s", exc)
        raise ValueError(
            f"OpenClaw could not generate a valid recommendation: {exc}"
        ) from exc
