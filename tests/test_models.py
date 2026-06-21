"""
tests/test_models.py
--------------------
Pydantic validation tests for models/trade_model.py.

All tests are deterministic — no network calls, no LLM, no DB.
"""

import pytest
from pydantic import ValidationError

from models.trade_model import (
    ExecutionDecision,
    RiskAssessment,
    TradeRecommendation,
    TrustAssessment,
)


# ─── TradeRecommendation ──────────────────────────────────────────────────────


class TestTradeRecommendation:
    """Tests for TradeRecommendation Pydantic model validation."""

    def test_valid_recommendation(self):
        rec = TradeRecommendation(
            symbol="AAPL",
            action="BUY",
            quantity=10,
            confidence=0.8,
            reason="Bullish",
        )
        assert rec.symbol == "AAPL"
        assert rec.action == "BUY"
        assert rec.quantity == 10
        assert rec.confidence == pytest.approx(0.8, rel=1e-5)
        assert rec.reason == "Bullish"

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValidationError):
            TradeRecommendation(
                symbol="AAPL",
                action="BUY",
                quantity=10,
                confidence=1.2,
                reason="Bullish",
            )

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError):
            TradeRecommendation(
                symbol="AAPL",
                action="BUY",
                quantity=10,
                confidence=-0.1,
                reason="Bullish",
            )

    def test_invalid_action_raises(self):
        """action must be exactly 'BUY' or 'SELL'."""
        with pytest.raises(ValidationError):
            TradeRecommendation(
                symbol="AAPL",
                action="HOLD",
                quantity=10,
                confidence=0.7,
                reason="Test",
            )

    def test_zero_quantity_raises(self):
        """quantity must be > 0."""
        with pytest.raises(ValidationError):
            TradeRecommendation(
                symbol="AAPL",
                action="BUY",
                quantity=0,
                confidence=0.7,
                reason="Test",
            )

    def test_confidence_boundary_zero(self):
        """confidence=0.0 is valid (lower boundary)."""
        rec = TradeRecommendation(
            symbol="TSLA",
            action="SELL",
            quantity=5,
            confidence=0.0,
            reason="Bearish",
        )
        assert rec.confidence == 0.0

    def test_confidence_boundary_one(self):
        """confidence=1.0 is valid (upper boundary)."""
        rec = TradeRecommendation(
            symbol="TSLA",
            action="BUY",
            quantity=5,
            confidence=1.0,
            reason="Very bullish",
        )
        assert rec.confidence == 1.0


# ─── RiskAssessment ───────────────────────────────────────────────────────────


class TestRiskAssessment:
    """Tests for RiskAssessment Pydantic model validation."""

    def test_valid_risk_score(self):
        risk = RiskAssessment(risk_score=50, risk_level="MEDIUM")
        assert risk.risk_score == 50
        assert risk.risk_level == "MEDIUM"

    def test_risk_score_too_high_raises(self):
        with pytest.raises(ValidationError):
            RiskAssessment(risk_score=150, risk_level="HIGH")

    def test_risk_score_negative_raises(self):
        with pytest.raises(ValidationError):
            RiskAssessment(risk_score=-1, risk_level="LOW")

    def test_risk_score_boundaries(self):
        """Boundary values 0 and 100 must both be valid."""
        low = RiskAssessment(risk_score=0, risk_level="LOW")
        high = RiskAssessment(risk_score=100, risk_level="HIGH")
        assert low.risk_score == 0
        assert high.risk_score == 100

    def test_invalid_risk_level_raises(self):
        with pytest.raises(ValidationError):
            RiskAssessment(risk_score=50, risk_level="EXTREME")

    def test_risk_factors_default_empty(self):
        """risk_factors should default to an empty list."""
        risk = RiskAssessment(risk_score=20, risk_level="LOW")
        assert risk.risk_factors == []


# ─── TrustAssessment ──────────────────────────────────────────────────────────


class TestTrustAssessment:
    """Tests for TrustAssessment Pydantic model validation."""

    def test_valid_trust_score(self):
        trust = TrustAssessment(trust_score=80, trust_level="HIGH")
        assert trust.trust_score == 80
        assert trust.trust_level == "HIGH"

    def test_trust_score_negative_raises(self):
        with pytest.raises(ValidationError):
            TrustAssessment(trust_score=-10, trust_level="LOW")

    def test_trust_score_above_100_raises(self):
        with pytest.raises(ValidationError):
            TrustAssessment(trust_score=101, trust_level="HIGH")

    def test_trust_score_boundaries(self):
        """Boundary values 0 and 100 must both be valid."""
        low = TrustAssessment(trust_score=0, trust_level="LOW")
        high = TrustAssessment(trust_score=100, trust_level="HIGH")
        assert low.trust_score == 0
        assert high.trust_score == 100

    def test_invalid_trust_level_raises(self):
        with pytest.raises(ValidationError):
            TrustAssessment(trust_score=50, trust_level="VERY_HIGH")


# ─── ExecutionDecision ────────────────────────────────────────────────────────


class TestExecutionDecision:
    """Tests for ExecutionDecision Pydantic model validation."""

    @pytest.mark.parametrize("decision", ["EXECUTE", "HOLD", "BLOCK"])
    def test_valid_decisions(self, decision: str):
        ed = ExecutionDecision(decision=decision)
        assert ed.decision == decision

    def test_invalid_decision_raises(self):
        with pytest.raises(ValidationError):
            ExecutionDecision(decision="INVALID")

    def test_rationale_defaults_to_empty_string(self):
        ed = ExecutionDecision(decision="HOLD")
        assert ed.rationale == ""

    def test_rationale_can_be_set(self):
        ed = ExecutionDecision(decision="EXECUTE", rationale="All criteria met.")
        assert ed.rationale == "All criteria met."
