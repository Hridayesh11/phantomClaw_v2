"""
main.py
-------
FastAPI entry point for PhantomClaw v2.

This file contains NO business logic. Its only responsibilities are:
  - Declare the FastAPI application and its lifespan.
  - Register HTTP endpoints.
  - Delegate all work to services/analysis_service.py.
  - Map domain exceptions to appropriate HTTP status codes.

Architecture:
    FastAPI (main.py)
        ↓
    analysis_service.run_full_analysis()
        ↓
    Pipeline (agents → engines → controller → db → memory)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from database.db import get_recent_trades, init_db
from market.indicators import get_indicator_summary
from market.market_data import fetch_market_data, get_latest_price, validate_symbol
from models.trade_model import FullAnalysisResult
from services.analysis_service import run_full_analysis

logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize resources on startup; release on shutdown."""
    logger.info("PhantomClaw v2 starting up — initialising database…")
    init_db()
    logger.info("Database ready.")
    yield
    logger.info("PhantomClaw v2 shutting down.")


# ─── Application ──────────────────────────────────────────────────────────────


app = FastAPI(
    title="PhantomClaw v2",
    version="1.0.0",
    description=(
        "AI-powered trade analysis pipeline. "
        "POST /analyze with a symbol to run the full PhantomClaw pipeline."
    ),
    lifespan=lifespan,
)


# ─── Request Models ───────────────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    """Request body for the /analyze endpoint."""

    symbol: str


# ─── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/", tags=["Status"], summary="Root — service identity")
async def root() -> dict:
    """Return the service name and running status."""
    return {"name": "PhantomClaw v2", "status": "running"}


@app.get("/health", tags=["Status"], summary="Health check")
async def health() -> dict:
    """Return a simple health probe suitable for load-balancer checks."""
    return {"status": "healthy", "service": "PhantomClaw v2", "version": "1.0.0"}


@app.post(
    "/analyze",
    response_model=FullAnalysisResult,
    tags=["Analysis"],
    summary="Run the full PhantomClaw pipeline for a symbol",
)
async def analyze(request: AnalyzeRequest) -> FullAnalysisResult:
    """
    Execute the complete analysis pipeline and return a FullAnalysisResult.

    - **400** — invalid or empty symbol, or no market data available.
    - **500** — agent failure or unexpected internal error.
    """
    try:
        return await run_full_analysis(request.symbol)
    except ValueError as exc:
        logger.warning("Bad request for symbol '%s': %s", request.symbol, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("Pipeline error for symbol '%s': %s", request.symbol, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error for symbol '%s': %s", request.symbol, exc)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.") from exc


@app.get(
    "/history",
    tags=["History"],
    summary="Retrieve recent trade log entries",
)
async def history(
    limit: int = Query(default=20, ge=1, le=200, description="Number of records to return"),
) -> list[dict]:
    """Return the most recent trade log entries, newest-first."""
    return get_recent_trades(limit=limit)


@app.get(
    "/market/{symbol}",
    tags=["Market"],
    summary="Fetch live market data and technical indicators for a symbol",
)
async def market(symbol: str) -> dict:
    """
    Return the latest price snapshot and computed technical indicators.

    - **404** — no market data available for the requested symbol.
    """
    clean_symbol = validate_symbol(symbol)
    df = fetch_market_data(clean_symbol)

    if df is None or df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No market data found for symbol '{clean_symbol}'.",
        )

    return {
        "market_snapshot": get_latest_price(clean_symbol),
        "technical_indicators": get_indicator_summary(df),
    }
