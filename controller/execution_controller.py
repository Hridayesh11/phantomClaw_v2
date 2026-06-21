"""
controller/execution_controller.py
------------------------------------
Execution Controller — Final decision gate in the PhantomClaw pipeline.

Applies trust-level rules to determine whether a trade should be:
  - EXECUTE (HIGH trust)
  - HOLD    (MEDIUM trust)
  - BLOCK   (LOW trust)

Phase 1: No actual broker integration. Decisions are logged only.
"""

import logging
from models.trade_model import TrustAssessment, ExecutionDecision

logger = logging.getLogger(__name__)

# ─── Decision Rules ───────────────────────────────────────────────────────────
_DECISION_MAP = {
    "HIGH":   ("EXECUTE", "Trust score is high — trade meets all safety criteria."),
    "MEDIUM": ("HOLD",    "Trust score is moderate — recommend monitoring before action."),
    "LOW":    ("BLOCK",   "Trust score is too low — trade blocked by PhantomClaw safeguards."),
}


def make_decision(trust: TrustAssessment) -> ExecutionDecision:
    """
    Map a trust assessment to a final trade decision.

    Args:
        trust: TrustAssessment from the Trust Engine.

    Returns:
        ExecutionDecision with a decision string and rationale.
    """
    trust_level = trust.trust_level.upper()

    if trust_level not in _DECISION_MAP:
        logger.warning("Unknown trust level '%s' — defaulting to BLOCK", trust_level)
        trust_level = "LOW"

    decision, rationale = _DECISION_MAP[trust_level]

    enhanced_rationale = (
        f"{rationale} "
        f"(trust_score={trust.trust_score}, trust_level={trust.trust_level})"
    )

    logger.info(
        "Execution Controller → %s | %s",
        decision,
        enhanced_rationale,
    )

    return ExecutionDecision(decision=decision, rationale=enhanced_rationale)
