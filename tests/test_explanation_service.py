"""
tests/test_explanation_service.py
---------------------------------
Tests for the Phase 9 Explainability Layer.
"""

from models.agent_vote_model import AgentVote
from models.explanation_model import ExplanationResult
from models.position_model import PositionSizingResult
from models.trade_model import (
    ChallengeResult,
    ExecutionDecision,
    RiskAssessment,
    TradeRecommendation,
    TrustAssessment,
)
from services.explanation_service import generate_explanation

# ─── Test Fixtures ───────────────────────────────────────────────────────────

def get_base_votes() -> list[AgentVote]:
    return [
        AgentVote(agent_name="OpenClawAgent", signal="BUY", confidence=0.8, reason="Bullish setup."),
        AgentVote(agent_name="TrendAgent", signal="BUY", confidence=0.8, reason="SMA > EMA."),
    ]

def get_challenge() -> ChallengeResult:
    return ChallengeResult(
        symbol="AAPL",
        support_reasoning="Strong volume.",
        opposing_reasoning="Overbought RSI.",
    )

def get_risk() -> RiskAssessment:
    return RiskAssessment(
        risk_score=40,
        risk_level="MEDIUM",
        risk_factors=["High volatility"],
    )

def get_trust() -> TrustAssessment:
    return TrustAssessment(
        trust_score=85,
        trust_level="HIGH",
    )

def get_decision(decision: str) -> ExecutionDecision:
    return ExecutionDecision(
        decision=decision,
        rationale=f"Decision to {decision}.",
    )

def get_recommendation(action: str) -> TradeRecommendation:
    qty = 10 if action in ["BUY", "SELL"] else 0
    return TradeRecommendation(
        symbol="AAPL",
        action=action,
        quantity=qty,
        confidence=0.8,
        reason=f"Consensus selected {action}.",
    )

def get_position_sizing() -> PositionSizingResult:
    return PositionSizingResult(
        quantity=142,
        risk_amount=1000.0,
        stop_distance=7.0,
        atr=3.5,
        capital_exposure=28400.0,
        position_method="ATR"
    )

# ─── Tests ───────────────────────────────────────────────────────────────────

def test_explanation_buy_execute():
    rec = get_recommendation("BUY")
    dec = get_decision("EXECUTE")
    
    result = generate_explanation(
        rec, get_challenge(), get_risk(), get_trust(), dec, get_base_votes(), get_position_sizing()
    )
    
    assert isinstance(result, ExplanationResult)
    assert result.final_decision == "EXECUTE"
    assert "Consensus reached BUY" in result.consensus_reason
    assert "80% confidence" in result.consensus_reason
    assert len(result.agent_breakdown) == 2
    assert result.agent_breakdown[0].agent_name == "OpenClawAgent"
    assert result.agent_breakdown[0].signal == "BUY"
    assert "Strong volume" in result.challenge_summary
    assert "Overbought RSI" in result.challenge_summary
    assert "Risk Level: MEDIUM" in result.risk_summary
    assert "High volatility" in result.risk_summary
    assert "Trust Level: HIGH" in result.trust_summary
    assert "Decision to EXECUTE" in result.decision_summary

def test_explanation_sell_execute():
    rec = get_recommendation("SELL")
    dec = get_decision("EXECUTE")
    
    result = generate_explanation(
        rec, get_challenge(), get_risk(), get_trust(), dec, get_base_votes(), get_position_sizing()
    )
    
    assert result.final_decision == "EXECUTE"
    assert "Consensus reached SELL" in result.consensus_reason

def test_explanation_hold_block():
    rec = get_recommendation("HOLD")
    dec = get_decision("BLOCK")
    
    result = generate_explanation(
        rec, get_challenge(), get_risk(), get_trust(), dec, get_base_votes(), get_position_sizing()
    )
    
    assert result.final_decision == "BLOCK"
    assert "Consensus reached HOLD" in result.consensus_reason

def test_risk_summary_no_factors():
    risk = RiskAssessment(risk_score=10, risk_level="LOW", risk_factors=[])
    
    result = generate_explanation(
        get_recommendation("BUY"), get_challenge(), risk, get_trust(), get_decision("EXECUTE"), get_base_votes(), get_position_sizing()
    )
    
    assert "Factors: None" in result.risk_summary

def test_trust_summary_content():
    trust = TrustAssessment(trust_score=30, trust_level="LOW")
    
    result = generate_explanation(
        get_recommendation("BUY"), get_challenge(), get_risk(), trust, get_decision("BLOCK"), get_base_votes(), get_position_sizing()
    )
    
    assert "Trust Level: LOW (Score: 30)" in result.trust_summary
