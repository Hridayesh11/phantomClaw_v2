"""
models/trade_model.py
---------------------
Pydantic v2 data models for PhantomClaw v2.

All data flowing through the pipeline is strictly typed and validated here.
These models are the shared contract between agents, engines, services,
the database layer, and the dashboard.

Design rule: No module outside models/ defines its own data shapes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from models.explanation_model import ExplanationResult
from models.position_model import PositionSizingResult


# ─── OpenClaw Agent Output ────────────────────────────────────────────────────


class TradeRecommendation(BaseModel):
    """
    Raw trade recommendation produced by the OpenClaw agent or ConsensusEngine.

    `action` is constrained to "BUY", "SELL", or "HOLD".
    `confidence` must be in [0.0, 1.0].

    Cross-field validation rules:
        BUY  → quantity must be > 0
        SELL → quantity must be > 0
        HOLD → quantity must be exactly 0
    """

    symbol: str = Field(..., description="Ticker symbol, e.g. 'AAPL'")
    action: Literal["BUY", "SELL", "HOLD"] = Field(..., description="Trade direction")
    quantity: int = Field(..., ge=0, description="Number of shares (0 for HOLD, positive for BUY/SELL)")
    confidence: float = Field(..., description="Model confidence in the recommendation [0.0–1.0]")
    reason: str = Field(..., description="Human-readable rationale for the trade")

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        """Ensure confidence is strictly within [0.0, 1.0]."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 6)

    @model_validator(mode="after")
    def action_quantity_consistent(self) -> "TradeRecommendation":
        """
        Enforce action/quantity consistency:
            BUY  → quantity > 0
            SELL → quantity > 0
            HOLD → quantity == 0
        """
        if self.action in ("BUY", "SELL") and self.quantity == 0:
            raise ValueError(
                f"action='{self.action}' requires quantity > 0, got quantity=0."
            )
        if self.action == "HOLD" and self.quantity != 0:
            raise ValueError(
                f"action='HOLD' requires quantity=0, got quantity={self.quantity}."
            )
        return self


# ─── Challenge Agent Output ───────────────────────────────────────────────────


class ChallengeResult(BaseModel):
    """
    Devil's-advocate analysis produced by the Challenge agent.

    Both fields are required — the agent must always produce both
    a supporting and an opposing argument, never just one.
    """

    support_reasoning: str = Field(
        ..., description="Arguments that support the original trade recommendation"
    )
    opposing_reasoning: str = Field(
        ..., description="Arguments that oppose or challenge the recommendation"
    )


# ─── ArmorIQ Risk Engine Output ───────────────────────────────────────────────


class RiskAssessment(BaseModel):
    """
    Risk evaluation from the ArmorIQ pure-Python engine.

    `risk_level` is constrained to exactly "LOW", "MEDIUM", or "HIGH".
    `risk_score` must be in [0, 100].
    `risk_factors` lists every triggered rule (useful for dashboard display).
    """

    risk_score: int = Field(..., description="Aggregate risk score [0–100]")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ..., description="Categorical risk level derived from risk_score"
    )
    # Retained for armoriq.py compatibility: lists every triggered risk rule.
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Human-readable list of triggered risk factors",
    )

    @field_validator("risk_score")
    @classmethod
    def score_in_range(cls, v: int) -> int:
        """Ensure risk_score is within [0, 100]."""
        if not (0 <= v <= 100):
            raise ValueError(f"risk_score must be between 0 and 100, got {v}")
        return v


# ─── Adaptive Trust Engine Output ────────────────────────────────────────────


class TrustAssessment(BaseModel):
    """
    Trust score computed by the Trust Engine.

    Formula: trust_score = clamp(int(confidence * 100) - risk_score, 0, 100)

    `trust_level` is constrained to exactly "LOW", "MEDIUM", or "HIGH".
    `trust_score` must be in [0, 100].
    """

    trust_score: int = Field(..., description="Final trust score [0–100]")
    trust_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ..., description="Categorical trust level derived from trust_score"
    )

    @field_validator("trust_score")
    @classmethod
    def score_in_range(cls, v: int) -> int:
        """Ensure trust_score is within [0, 100]."""
        if not (0 <= v <= 100):
            raise ValueError(f"trust_score must be between 0 and 100, got {v}")
        return v


# ─── Execution Controller Output ─────────────────────────────────────────────


class ExecutionDecision(BaseModel):
    """
    Final decision produced by the Execution Controller.

    `decision` is constrained to exactly "EXECUTE", "HOLD", or "BLOCK".
    `rationale` provides a one-line explanation (retained for controller.py
    compatibility and dashboard display).
    """

    decision: Literal["EXECUTE", "HOLD", "BLOCK"] = Field(
        ..., description="Final execution gate decision"
    )
    # Retained for execution_controller.py compatibility.
    rationale: str = Field(
        default="", description="One-line explanation of why this decision was made"
    )


# ─── Full Pipeline Result ─────────────────────────────────────────────────────


class FullAnalysisResult(BaseModel):
    """
    Aggregated output from a complete PhantomClaw pipeline run.

    This is the single object returned by analysis_service.run_full_analysis()
    and consumed by both the FastAPI server and the Streamlit dashboard.

    Field names match the spec exactly — services and dashboard reference
    these names directly.
    """

    trade_recommendation: TradeRecommendation
    challenge_result: ChallengeResult
    risk_assessment: RiskAssessment
    trust_assessment: TrustAssessment
    execution_decision: ExecutionDecision
    market_snapshot: dict = Field(..., description="Raw OHLCV snapshot dict from market module")
    technical_indicators: dict = Field(
        ..., description="Computed indicator values dict from indicators module"
    )
    explanation: Optional[ExplanationResult] = Field(
        default=None, description="Detailed explanation of the pipeline's reasoning"
    )
    position_sizing: Optional[PositionSizingResult] = Field(
        default=None, description="Dynamic position sizing calculation result"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of when this analysis was run",
    )


# ─── Trade Log Entry (persistence schema) ────────────────────────────────────


class TradeLogEntry(BaseModel):
    """
    Schema for a single persisted trade analysis record.

    Mirrors the `trade_logs` SQLAlchemy ORM table.
    Optional fields may be None if market data was unavailable at analysis time.
    """

    id: Optional[int] = Field(default=None, description="Auto-incremented primary key")
    symbol: str
    action: str
    quantity: int
    confidence: float

    # Market context at time of analysis
    price: Optional[float] = Field(default=None, description="Close price at analysis time")
    rsi: Optional[float] = Field(default=None, description="RSI(14) at analysis time")
    macd: Optional[float] = Field(default=None, description="MACD line value at analysis time")
    atr: Optional[float] = Field(default=None, description="ATR(14) at analysis time")

    # Risk and trust scoring
    risk_score: int
    risk_level: str
    trust_score: int
    trust_level: str

    # Decision
    decision: str
    reason: str

    # Challenge agent reasoning
    support_reasoning: Optional[str] = Field(
        default=None, description="Challenge Agent support argument"
    )
    opposing_reasoning: Optional[str] = Field(
        default=None, description="Challenge Agent opposing argument"
    )

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}  # Pydantic v2: replaces class Config
