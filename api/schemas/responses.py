"""
api/schemas/responses.py
------------------------
Pydantic response models for the PhantomClaw v3 REST API.

These are API-layer schemas that shape outbound JSON. They reference
or re-export domain models from models/ where appropriate, ensuring
the API layer never leaks internal implementation details.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ─── Health ───────────────────────────────────────────────────────────────────


class ComponentHealth(BaseModel):
    """Health status of a single infrastructure component."""

    name: str = Field(..., description="Component identifier")
    status: Literal["ok", "degraded", "unavailable"] = Field(
        ..., description="Current status"
    )
    detail: Optional[str] = Field(
        default=None, description="Optional diagnostic message"
    )


class HealthResponse(BaseModel):
    """Structured health check response."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Overall application health"
    )
    service: str = Field(default="PhantomClaw v3", description="Service name")
    version: str = Field(default="3.0.0", description="API version")
    components: list[ComponentHealth] = Field(
        default_factory=list, description="Per-component health details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of this health check",
    )


# ─── Market ───────────────────────────────────────────────────────────────────


class MarketSnapshotResponse(BaseModel):
    """Live market data and computed technical indicators for a symbol."""

    symbol: str = Field(..., description="Ticker symbol")
    current_price: Optional[float] = Field(
        default=None, description="Last traded price"
    )
    open: Optional[float] = Field(default=None, description="Open price")
    high: Optional[float] = Field(default=None, description="High price")
    low: Optional[float] = Field(default=None, description="Low price")
    close: Optional[float] = Field(default=None, description="Close price")
    volume: Optional[int] = Field(default=None, description="Trade volume")

    # Technical indicators
    rsi: Optional[float] = Field(default=None, description="RSI (14-period)")
    ema20: Optional[float] = Field(
        default=None, description="EMA 20-period (mapped from SMA20)"
    )
    ema50: Optional[float] = Field(
        default=None, description="EMA 50-period"
    )
    macd: Optional[float] = Field(default=None, description="MACD line value")
    atr: Optional[float] = Field(
        default=None, description="ATR (14-period)"
    )


# ─── Analyze ──────────────────────────────────────────────────────────────────


class AnalyzeResponse(BaseModel):
    """Simplified analysis result for the POST /analyze endpoint."""

    symbol: str = Field(..., description="Analyzed ticker symbol")
    action: str = Field(
        ..., description="Recommended action: BUY, SELL, or HOLD"
    )
    confidence: int = Field(
        ..., description="Model confidence as a percentage (0–100)"
    )
    trust_score: int = Field(
        ..., description="Trust Engine score (0–100)"
    )
    risk: str = Field(
        ..., description="Risk level: LOW, MEDIUM, or HIGH"
    )
    execution: str = Field(
        ..., description="Execution decision: EXECUTE, HOLD, or BLOCK"
    )
    reason: str = Field(
        ..., description="Human-readable rationale for the recommendation"
    )


# ─── History ──────────────────────────────────────────────────────────────────


class TradeHistoryEntry(BaseModel):
    """A single historical trade log entry."""

    id: Optional[int] = Field(default=None, description="Trade log primary key")
    symbol: str
    action: str
    quantity: int
    confidence: float
    price: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    atr: Optional[float] = None
    risk_score: int
    risk_level: str
    trust_score: int
    trust_level: str
    decision: str
    reason: str
    support_reasoning: Optional[str] = None
    opposing_reasoning: Optional[str] = None
    timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TradeHistoryResponse(BaseModel):
    """Paginated list of trade history entries."""

    count: int = Field(..., description="Number of entries returned")
    trades: list[TradeHistoryEntry] = Field(
        default_factory=list, description="Trade log entries, newest-first"
    )


# ─── Root ─────────────────────────────────────────────────────────────────────


class RootResponse(BaseModel):
    """Basic service identity returned by GET /."""

    name: str = Field(default="PhantomClaw v3", description="Service name")
    version: str = Field(default="3.0.0", description="API version")
    status: str = Field(default="running", description="Running status")
    docs_url: str = Field(
        default="/docs", description="Interactive API documentation URL"
    )


# ─── Error ────────────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standard error body returned by global exception handlers."""

    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Human-readable error message")
    status_code: int = Field(..., description="HTTP status code")
