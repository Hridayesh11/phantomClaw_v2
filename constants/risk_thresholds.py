"""
constants/risk_thresholds.py
-----------------------------
All risk-related thresholds used by the ArmorIQ engine and Trust Engine.

Centralising constants here means:
  - No magic numbers scattered across engine code.
  - Threshold tuning requires changes in ONE place only.
  - Easy to expose these to a future admin UI or config file.
  - Clear documentation of what each threshold means.
"""

# ─── Confidence Thresholds ────────────────────────────────────────────────────

# Confidence values are expressed as percentages here (0–100)
# to match human-readable language. Divide by 100 when comparing
# with Pydantic TradeRecommendation.confidence (which is 0.0–1.0).

LOW_CONFIDENCE: int = 50          # Below this % = low confidence penalty
VERY_LOW_CONFIDENCE: int = 40     # Below this % = very low confidence (heavier penalty)

# ─── RSI Thresholds ───────────────────────────────────────────────────────────

OVERBOUGHT_RSI: float = 70.0      # RSI above this → overbought (risky for BUY)
OVERSOLD_RSI: float = 30.0        # RSI below this → oversold (risky for SELL)
EXTREME_OVERBOUGHT_RSI: float = 80.0   # Extreme overbought → extra penalty
EXTREME_OVERSOLD_RSI: float = 20.0     # Extreme oversold → extra penalty

# ─── Volatility Thresholds (ATR) ─────────────────────────────────────────────

HIGH_VOLATILITY_ATR: float = 5.0       # ATR above this → elevated volatility
VERY_HIGH_VOLATILITY_ATR: float = 10.0 # ATR above this → very high volatility

# ─── Position Size Thresholds ────────────────────────────────────────────────

MAX_POSITION_SIZE: int = 100    # Above this → large position size penalty
EXTREME_POSITION_SIZE: int = 200  # Above this → extreme position size penalty

# ─── Trust Score Boundaries ───────────────────────────────────────────────────

HIGH_TRUST_THRESHOLD: int = 70    # trust_score > this → HIGH trust → EXECUTE
MEDIUM_TRUST_THRESHOLD: int = 40  # trust_score > this → MEDIUM trust → HOLD
                                   # trust_score ≤ MEDIUM → LOW trust → BLOCK

# ─── Risk Score Levels ────────────────────────────────────────────────────────

HIGH_RISK_THRESHOLD: int = 60     # risk_score ≥ this → HIGH risk
MEDIUM_RISK_THRESHOLD: int = 30   # risk_score ≥ this → MEDIUM risk
                                   # risk_score < MEDIUM → LOW risk
