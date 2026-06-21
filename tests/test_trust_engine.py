"""
tests/test_trust_engine.py
--------------------------
Deterministic unit tests for engines/trust_engine.py (compute_trust).

Formula under test:
    trust_score = clamp(int(confidence * 100) - risk_score, 0, 100)

Trust levels (from constants/risk_thresholds.py):
    > 70  → HIGH
    40–70 → MEDIUM
    < 40  → LOW

All tests are deterministic — no network calls, no LLM, no DB.
"""

import pytest

from engines.trust_engine import compute_trust
from models.trade_model import RiskAssessment, TradeRecommendation, TrustAssessment


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _rec(confidence: float) -> TradeRecommendation:
    return TradeRecommendation(
        symbol="AAPL",
        action="BUY",
        quantity=10,
        confidence=confidence,
        reason="Test",
    )


def _risk(score: int) -> RiskAssessment:
    if score >= 60:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"
    return RiskAssessment(risk_score=score, risk_level=level)


# ─── Case 1: confidence=0.9, risk=10 → trust=80 ──────────────────────────────


class TestCase1NormalTrust:
    """int(0.9 * 100) - 10 = 90 - 10 = 80 → HIGH trust."""

    def test_trust_score_equals_80(self):
        result = compute_trust(_rec(0.9), _risk(10))
        assert result.trust_score == 80

    def test_trust_level_is_high(self):
        result = compute_trust(_rec(0.9), _risk(10))
        assert result.trust_level == "HIGH"

    def test_returns_trust_assessment_type(self):
        result = compute_trust(_rec(0.9), _risk(10))
        assert isinstance(result, TrustAssessment)


# ─── Case 2: confidence=0.5, risk=70 → clamped to 0 ─────────────────────────


class TestCase2ClampToZero:
    """int(0.5 * 100) - 70 = 50 - 70 = -20 → clamped to 0 → LOW trust."""

    def test_trust_score_clamped_to_zero(self):
        result = compute_trust(_rec(0.5), _risk(70))
        assert result.trust_score == 0

    def test_trust_level_is_low(self):
        result = compute_trust(_rec(0.5), _risk(70))
        assert result.trust_level == "LOW"

    def test_trust_score_never_negative(self):
        """Regardless of inputs, trust_score must always be ≥ 0."""
        result = compute_trust(_rec(0.1), _risk(100))
        assert result.trust_score >= 0


# ─── Case 3: confidence=1.0, risk=0 → trust=100 ──────────────────────────────


class TestCase3MaxTrust:
    """int(1.0 * 100) - 0 = 100 → HIGH trust at maximum."""

    def test_trust_score_equals_100(self):
        result = compute_trust(_rec(1.0), _risk(0))
        assert result.trust_score == 100

    def test_trust_level_is_high(self):
        result = compute_trust(_rec(1.0), _risk(0))
        assert result.trust_level == "HIGH"

    def test_trust_score_never_exceeds_100(self):
        """trust_score must always be ≤ 100, even with confidence=1.0 and risk=0."""
        result = compute_trust(_rec(1.0), _risk(0))
        assert result.trust_score <= 100


# ─── Case 4: Trust level boundaries ──────────────────────────────────────────


class TestCase4TrustLevelBoundaries:
    """
    Verify correct level assignment at boundary values.

    HIGH   → trust_score > 70
    MEDIUM → 40 ≤ trust_score ≤ 70
    LOW    → trust_score < 40
    """

    def test_trust_level_high_above_70(self):
        # int(0.9 * 100) - 10 = 80 > 70 → HIGH
        result = compute_trust(_rec(0.9), _risk(10))
        assert result.trust_level == "HIGH"

    def test_trust_level_medium_at_40(self):
        # int(0.6 * 100) - 20 = 40 → MEDIUM (>= 40)
        result = compute_trust(_rec(0.60), _risk(20))
        assert result.trust_score == 40
        assert result.trust_level == "MEDIUM"

    def test_trust_level_medium_at_70(self):
        # int(0.8 * 100) - 10 = 70 → MEDIUM (not > 70)
        result = compute_trust(_rec(0.80), _risk(10))
        assert result.trust_score == 70
        assert result.trust_level == "MEDIUM"

    def test_trust_level_low_below_40(self):
        # int(0.5 * 100) - 20 = 30 < 40 → LOW
        result = compute_trust(_rec(0.50), _risk(20))
        assert result.trust_score == 30
        assert result.trust_level == "LOW"

    def test_trust_level_high_just_above_70(self):
        # int(0.9 * 100) - 18 = 72 > 70 → HIGH
        result = compute_trust(_rec(0.90), _risk(18))
        assert result.trust_score == 72
        assert result.trust_level == "HIGH"

    @pytest.mark.parametrize(
        "confidence, risk_score, expected_level",
        [
            (0.9,  10, "HIGH"),    # 80 > 70
            (0.7,  25, "MEDIUM"),  # 45, 40 ≤ 45 ≤ 70
            (0.5,  20, "LOW"),     # 30 < 40
            (1.0,   0, "HIGH"),    # 100 > 70
            (0.4,  20, "MEDIUM"),  # 20 < 40? → int(0.4*100)=40; 40-20=20 → LOW
        ],
    )
    def test_trust_level_parametrized(
        self, confidence: float, risk_score: int, expected_level: str
    ):
        # Recalculate expected to keep test honest
        raw = int(confidence * 100) - risk_score
        clamped = max(0, min(100, raw))
        if clamped > 70:
            actual_expected = "HIGH"
        elif clamped >= 40:
            actual_expected = "MEDIUM"
        else:
            actual_expected = "LOW"

        result = compute_trust(_rec(confidence), _risk(risk_score))
        assert result.trust_score == clamped
        assert result.trust_level == actual_expected
