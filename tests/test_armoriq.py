"""
tests/test_armoriq.py
---------------------
Deterministic unit tests for engines/armoriq.py (evaluate_risk).

All tests use hand-crafted TradeRecommendation + indicators dicts.
No network calls, no LLM, no DB.

Thresholds (from constants/risk_thresholds.py):
    LOW_CONFIDENCE       = 50  (%)
    VERY_LOW_CONFIDENCE  = 40  (%)
    OVERBOUGHT_RSI       = 70.0
    OVERSOLD_RSI         = 30.0
    HIGH_VOLATILITY_ATR  = 5.0
    VERY_HIGH_VOLATILITY_ATR = 10.0
    MAX_POSITION_SIZE    = 100
    EXTREME_POSITION_SIZE = 200
    MEDIUM_RISK_THRESHOLD = 30
    HIGH_RISK_THRESHOLD   = 60
"""

import pytest

from engines.armoriq import evaluate_risk
from models.trade_model import RiskAssessment, TradeRecommendation


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _rec(
    symbol: str = "AAPL",
    action: str = "BUY",
    quantity: int = 10,
    confidence: float = 0.85,
    reason: str = "Test",
) -> TradeRecommendation:
    return TradeRecommendation(
        symbol=symbol,
        action=action,
        quantity=quantity,
        confidence=confidence,
        reason=reason,
    )


def _indicators(
    rsi: float | None = 50.0,
    macd: float | None = 0.5,
    macd_signal: float | None = 0.4,
    sma20: float | None = 150.0,
    ema50: float | None = 148.0,
    atr: float | None = 1.5,
) -> dict:
    return {
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "sma20": sma20,
        "ema50": ema50,
        "atr": atr,
    }


# ─── Case 1: High confidence, neutral RSI, low ATR, small quantity → LOW ──────


class TestCase1HighConfidenceLowRisk:
    """High-confidence BUY with benign indicators should produce LOW risk."""

    def test_risk_level_is_low(self):
        result = evaluate_risk(_rec(confidence=0.85, action="BUY", quantity=10), _indicators(rsi=50.0, atr=1.5))
        assert result.risk_level == "LOW"

    def test_risk_score_below_medium_threshold(self):
        result = evaluate_risk(_rec(confidence=0.85, action="BUY", quantity=10), _indicators(rsi=50.0, atr=1.5))
        assert result.risk_score < 30

    def test_returns_risk_assessment_type(self):
        result = evaluate_risk(_rec(), _indicators())
        assert isinstance(result, RiskAssessment)


# ─── Case 2: Low confidence → higher risk score ───────────────────────────────


class TestCase2LowConfidence:
    """confidence=0.3 (30%) is below VERY_LOW_CONFIDENCE=40% — should add +30."""

    def test_low_confidence_increases_risk(self):
        high_conf = evaluate_risk(_rec(confidence=0.85), _indicators())
        low_conf  = evaluate_risk(_rec(confidence=0.30), _indicators())
        assert low_conf.risk_score > high_conf.risk_score

    def test_very_low_confidence_factor_present(self):
        result = evaluate_risk(_rec(confidence=0.30), _indicators())
        assert any("confidence" in f.lower() for f in result.risk_factors)

    def test_low_confidence_exact_penalty(self):
        """confidence=0.3 → 30% < VERY_LOW_CONFIDENCE(40%) → +30 penalty.
        With known symbol, all indicators present and benign → base score = 30."""
        result = evaluate_risk(
            _rec(symbol="AAPL", action="BUY", quantity=10, confidence=0.30),
            _indicators(rsi=50.0, atr=1.5),
        )
        assert result.risk_score >= 30


# ─── Case 3: BUY with RSI > 70 → risk increase ───────────────────────────────


class TestCase3BuyOverboughtRSI:
    """BUY when RSI > OVERBOUGHT_RSI(70) conflicts — should add +20."""

    def test_overbought_rsi_increases_risk_for_buy(self):
        normal = evaluate_risk(_rec(action="BUY"), _indicators(rsi=50.0))
        overbought = evaluate_risk(_rec(action="BUY"), _indicators(rsi=75.0))
        assert overbought.risk_score > normal.risk_score

    def test_overbought_factor_in_risk_factors(self):
        result = evaluate_risk(_rec(action="BUY"), _indicators(rsi=75.0))
        assert any("overbought" in f.lower() or "rsi" in f.lower() for f in result.risk_factors)

    def test_overbought_rsi_exactly_at_threshold(self):
        """RSI=70.0 is not > 70 — should NOT trigger the overbought penalty."""
        at_boundary = evaluate_risk(_rec(action="BUY"), _indicators(rsi=70.0))
        just_over   = evaluate_risk(_rec(action="BUY"), _indicators(rsi=70.1))
        assert just_over.risk_score > at_boundary.risk_score


# ─── Case 4: SELL with RSI < 30 → risk increase ──────────────────────────────


class TestCase4SellOversoldRSI:
    """SELL when RSI < OVERSOLD_RSI(30) conflicts — should add +20."""

    def test_oversold_rsi_increases_risk_for_sell(self):
        normal   = evaluate_risk(_rec(action="SELL"), _indicators(rsi=50.0))
        oversold = evaluate_risk(_rec(action="SELL"), _indicators(rsi=25.0))
        assert oversold.risk_score > normal.risk_score

    def test_oversold_factor_in_risk_factors(self):
        result = evaluate_risk(_rec(action="SELL"), _indicators(rsi=25.0))
        assert any("oversold" in f.lower() or "rsi" in f.lower() for f in result.risk_factors)


# ─── Case 5: Quantity > 100 → higher risk ────────────────────────────────────


class TestCase5LargePositionSize:
    """quantity > MAX_POSITION_SIZE(100) → +15; > EXTREME_POSITION_SIZE(200) → +25."""

    def test_large_quantity_increases_risk(self):
        small = evaluate_risk(_rec(quantity=10),  _indicators())
        large = evaluate_risk(_rec(quantity=150), _indicators())
        assert large.risk_score > small.risk_score

    def test_large_position_factor_in_risk_factors(self):
        result = evaluate_risk(_rec(quantity=150), _indicators())
        assert any("position" in f.lower() for f in result.risk_factors)

    def test_extreme_quantity_higher_than_large(self):
        large   = evaluate_risk(_rec(quantity=150), _indicators())
        extreme = evaluate_risk(_rec(quantity=250), _indicators())
        assert extreme.risk_score > large.risk_score


# ─── Case 6: Multiple risk factors combined → HIGH risk ──────────────────────


class TestCase6MultipleRiskFactors:
    """
    Combine: low confidence + overbought RSI + very high ATR + large quantity.
    Expected total: +30 (very low conf) + 20 (overbought BUY) + 20 (very high ATR)
                  + 15 (large qty) = 85 → HIGH risk (≥ 60).
    """

    def test_high_risk_level(self):
        rec = _rec(
            action="BUY",
            quantity=150,       # > MAX_POSITION_SIZE(100) → +15
            confidence=0.30,    # 30% < VERY_LOW_CONFIDENCE(40%) → +30
        )
        ind = _indicators(
            rsi=75.0,           # overbought BUY → +20
            atr=12.0,           # > VERY_HIGH_VOLATILITY_ATR(10) → +20
        )
        result = evaluate_risk(rec, ind)
        assert result.risk_level == "HIGH"

    def test_high_risk_score_above_60(self):
        rec = _rec(action="BUY", quantity=150, confidence=0.30)
        ind = _indicators(rsi=75.0, atr=12.0)
        result = evaluate_risk(rec, ind)
        assert result.risk_score >= 60

    def test_multiple_factors_all_present(self):
        rec = _rec(action="BUY", quantity=150, confidence=0.30)
        ind = _indicators(rsi=75.0, atr=12.0)
        result = evaluate_risk(rec, ind)
        assert len(result.risk_factors) >= 4

    def test_risk_score_clamped_at_100(self):
        """risk_score must never exceed 100, even with many factors."""
        rec = _rec(action="BUY", quantity=250, confidence=0.10)
        ind = _indicators(rsi=85.0, atr=15.0, macd=None, sma20=None, ema50=None)
        result = evaluate_risk(rec, ind)
        assert result.risk_score <= 100
