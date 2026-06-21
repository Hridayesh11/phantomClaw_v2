"""
engines/trust_engine.py
-----------------------
Adaptive Trust Engine — Combines AI confidence with risk score to
produce a final trust rating that determines execution eligibility.

Formula:
    trust_score = clamp(int(confidence * 100) - risk_score, 0, 100)

Trust levels:
    > 70  → HIGH   (trade eligible for execution)
    40-70 → MEDIUM (hold and monitor)
    < 40  → LOW    (block the trade)
"""

import logging
from models.trade_model import TradeRecommendation, RiskAssessment, TrustAssessment

logger = logging.getLogger(__name__)


def compute_trust(
    recommendation: TradeRecommendation,
    risk: RiskAssessment,
) -> TrustAssessment:
    """
    Compute the trust score and level for a trade.

    Args:
        recommendation: OpenClaw's trade recommendation (provides confidence).
        risk:           ArmorIQ's risk assessment (provides risk_score).

    Returns:
        TrustAssessment with trust_score and trust_level.
    """
    raw_trust = int(recommendation.confidence * 100) - risk.risk_score
    trust_score = max(0, min(100, raw_trust))  # Clamp to [0, 100]

    if trust_score > 70:
        trust_level = "HIGH"
    elif trust_score >= 40:
        trust_level = "MEDIUM"
    else:
        trust_level = "LOW"

    logger.info(
        "Trust Engine → confidence=%.0f%% - risk=%d = trust_score=%d (%s)",
        recommendation.confidence * 100,
        risk.risk_score,
        trust_score,
        trust_level,
    )

    return TrustAssessment(trust_score=trust_score, trust_level=trust_level)
