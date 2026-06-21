"""
services/explanation_service.py
-------------------------------
Explainability layer for PhantomClaw v2.

Pure deterministic logic.
No OpenAI calls. No database writes. No Streamlit imports. No FastAPI imports.
"""

from models.agent_vote_model import AgentVote
from models.explanation_model import AgentExplanation, ExplanationResult
from models.portfolio_model import PortfolioOptimizationResult
from models.position_model import PositionSizingResult
from models.trade_model import (
    ChallengeResult,
    ExecutionDecision,
    RiskAssessment,
    TradeRecommendation,
    TrustAssessment,
)


def generate_explanation(
    recommendation: TradeRecommendation,
    challenge: ChallengeResult,
    risk: RiskAssessment,
    trust: TrustAssessment,
    decision: ExecutionDecision,
    votes: list[AgentVote],
    position_sizing: PositionSizingResult,
    portfolio_optimization: PortfolioOptimizationResult,
) -> ExplanationResult:
    """
    Generate a deterministic explanation for the complete pipeline execution.
    """
    
    agent_breakdown = [
        AgentExplanation(
            agent_name=v.agent_name,
            signal=v.signal,
            confidence=v.confidence,
            reason=v.reason,
        )
        for v in votes
    ]

    consensus_reason = (
        f"Consensus reached {recommendation.action} with "
        f"{recommendation.confidence:.0%} confidence. Reason: {recommendation.reason}"
    )

    challenge_summary = (
        f"Support: {challenge.support_reasoning} | "
        f"Opposing: {challenge.opposing_reasoning}"
    )
    
    factors = ", ".join(risk.risk_factors) if risk.risk_factors else "None"
    risk_summary = f"Risk Level: {risk.risk_level} (Score: {risk.risk_score}). Factors: {factors}"
    
    trust_summary = f"Trust Level: {trust.trust_level} (Score: {trust.trust_score})."
    
    position_summary = (
        f"Method: {position_sizing.position_method} | "
        f"Qty: {position_sizing.quantity} | "
        f"Risk: ${position_sizing.risk_amount:.2f} | "
        f"Capital: ${position_sizing.capital_exposure:.2f}"
    )

    portfolio_summary = (
        f"Method: {portfolio_optimization.optimization_method} | "
        f"Portfolio Risk: {portfolio_optimization.portfolio_risk_percent:.2f}% | "
        f"Pos Risk: {portfolio_optimization.position_risk_percent:.2f}% | "
        f"Reason: {portfolio_optimization.optimization_reason}"
    )

    decision_summary = f"Final decision was to {decision.decision}. {decision.rationale}"

    return ExplanationResult(
        final_decision=decision.decision,
        consensus_reason=consensus_reason,
        agent_breakdown=agent_breakdown,
        challenge_summary=challenge_summary,
        risk_summary=risk_summary,
        trust_summary=trust_summary,
        position_summary=position_summary,
        portfolio_summary=portfolio_summary,
        decision_summary=decision_summary,
    )
