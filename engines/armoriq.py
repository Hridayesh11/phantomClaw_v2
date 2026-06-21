"""
engines/armoriq.py
------------------
ArmorIQ Risk Engine — PhantomClaw's pure-Python risk evaluator.

RULE: This engine NEVER uses an LLM. Deterministic logic only.
Its transparency and predictability is what makes it trustworthy.

All thresholds are imported from constants/risk_thresholds.py.
No magic numbers in this file.

Risk factors evaluated:
  1. Very low confidence
  2. Low confidence
  3. Overbought RSI for BUY / oversold RSI for SELL
  4. Extreme RSI zones
  5. High ATR (volatility)
  6. Very high ATR
  7. Large position size
  8. Extreme position size
  9. Unknown symbol
  10. Missing critical indicator data
"""

import logging

from constants.risk_thresholds import (
    LOW_CONFIDENCE,
    VERY_LOW_CONFIDENCE,
    OVERBOUGHT_RSI,
    OVERSOLD_RSI,
    EXTREME_OVERBOUGHT_RSI,
    EXTREME_OVERSOLD_RSI,
    HIGH_VOLATILITY_ATR,
    VERY_HIGH_VOLATILITY_ATR,
    MAX_POSITION_SIZE,
    EXTREME_POSITION_SIZE,
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
)
from models.trade_model import TradeRecommendation, RiskAssessment

logger = logging.getLogger(__name__)

# ─── Known symbols — unknowns receive a small penalty ─────────────────────────
KNOWN_SYMBOLS: frozenset[str] = frozenset({
    "AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "GOOG",
    "AMZN", "META", "NFLX", "AMD", "INTC", "SPY",
    "QQQ", "DIS", "BABA", "TSM", "ORCL", "CRM",
    "UBER", "SNAP", "TWTR", "PYPL", "SQ", "COIN",
})


def evaluate_risk(
    recommendation: TradeRecommendation,
    indicators: dict,
) -> RiskAssessment:
    """
    Score the risk of a trade recommendation using deterministic rules.

    Args:
        recommendation: The OpenClaw trade recommendation.
        indicators:     Technical indicator dict (rsi, macd, atr, sma20, ema50)

    Returns:
        RiskAssessment with risk_score (0–100), risk_level, and risk_factors list.
    """
    risk_score: int = 0
    risk_factors: list[str] = []

    symbol = recommendation.symbol.upper()
    action = recommendation.action.upper()
    quantity = recommendation.quantity
    confidence_pct = recommendation.confidence * 100  # Convert to percentage for comparison

    rsi = indicators.get("rsi")
    atr = indicators.get("atr")

    # ─── Factor 1 & 2: Confidence penalties ───────────────────────────────
    if confidence_pct < VERY_LOW_CONFIDENCE:
        risk_score += 30
        risk_factors.append(
            f"Very low AI confidence ({confidence_pct:.0f}% < {VERY_LOW_CONFIDENCE}%)"
        )
    elif confidence_pct < LOW_CONFIDENCE:
        risk_score += 15
        risk_factors.append(
            f"Low AI confidence ({confidence_pct:.0f}% < {LOW_CONFIDENCE}%)"
        )

    # ─── Factor 3 & 4: RSI conflict and extreme zones ─────────────────────
    if rsi is not None:
        if action == "BUY" and rsi > OVERBOUGHT_RSI:
            risk_score += 20
            risk_factors.append(
                f"Overbought RSI ({rsi:.1f} > {OVERBOUGHT_RSI}) conflicts with BUY"
            )
        elif action == "SELL" and rsi < OVERSOLD_RSI:
            risk_score += 20
            risk_factors.append(
                f"Oversold RSI ({rsi:.1f} < {OVERSOLD_RSI}) conflicts with SELL"
            )

        if rsi > EXTREME_OVERBOUGHT_RSI:
            risk_score += 10
            risk_factors.append(f"Extreme overbought RSI ({rsi:.1f} > {EXTREME_OVERBOUGHT_RSI})")
        elif rsi < EXTREME_OVERSOLD_RSI:
            risk_score += 10
            risk_factors.append(f"Extreme oversold RSI ({rsi:.1f} < {EXTREME_OVERSOLD_RSI})")
    else:
        risk_score += 5
        risk_factors.append("RSI data unavailable — cannot assess momentum")

    # ─── Factor 5 & 6: ATR volatility ─────────────────────────────────────
    if atr is not None:
        if atr > VERY_HIGH_VOLATILITY_ATR:
            risk_score += 20
            risk_factors.append(
                f"Very high volatility ATR={atr:.2f} (threshold {VERY_HIGH_VOLATILITY_ATR})"
            )
        elif atr > HIGH_VOLATILITY_ATR:
            risk_score += 10
            risk_factors.append(
                f"Elevated volatility ATR={atr:.2f} (threshold {HIGH_VOLATILITY_ATR})"
            )
    else:
        risk_score += 5
        risk_factors.append("ATR data unavailable — cannot assess volatility")

    # ─── Factor 7 & 8: Position size ──────────────────────────────────────
    if quantity > EXTREME_POSITION_SIZE:
        risk_score += 25
        risk_factors.append(
            f"Extreme position size ({quantity} shares > {EXTREME_POSITION_SIZE})"
        )
    elif quantity > MAX_POSITION_SIZE:
        risk_score += 15
        risk_factors.append(
            f"Large position size ({quantity} shares > {MAX_POSITION_SIZE})"
        )

    # ─── Factor 9: Unknown symbol ──────────────────────────────────────────
    if symbol not in KNOWN_SYMBOLS:
        risk_score += 10
        risk_factors.append(f"Unrecognized symbol '{symbol}' — limited historical context")

    # ─── Factor 10: Missing critical indicators ────────────────────────────
    missing = [k for k in ("macd", "sma20", "ema50") if indicators.get(k) is None]
    if missing:
        risk_score += 5
        risk_factors.append(f"Missing indicators: {', '.join(missing)}")

    # ─── Clamp score and classify level ───────────────────────────────────
    risk_score = min(100, max(0, risk_score))

    if risk_score >= HIGH_RISK_THRESHOLD:
        risk_level = "HIGH"
    elif risk_score >= MEDIUM_RISK_THRESHOLD:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    logger.info(
        "ArmorIQ → risk_score=%d (%s) | %d factor(s) triggered",
        risk_score, risk_level, len(risk_factors),
    )

    return RiskAssessment(
        risk_score=risk_score,
        risk_level=risk_level,
        risk_factors=risk_factors,
    )
