"""
api/schemas/requests.py
-----------------------
Pydantic request models for the PhantomClaw v3 REST API.

All inbound request bodies are validated through these schemas.
Keep them thin — business logic belongs in services/, not here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Request body for the POST /analyze endpoint."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Ticker symbol to analyze (e.g. 'RELIANCE', 'AAPL').",
        examples=["RELIANCE", "AAPL", "TSLA"],
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        """Strip whitespace and uppercase the symbol."""
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Symbol must not be blank.")
        return cleaned
