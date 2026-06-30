"""
api/routes/analyze.py
---------------------
Analysis endpoint for PhantomClaw v3.

Orchestrates the full pipeline by delegating to
services.analysis_service.run_full_analysis().

No business logic lives here — the route handler only:
  1. Validates input via Pydantic schema.
  2. Calls the service layer.
  3. Maps the FullAnalysisResult to the API response shape.
  4. Maps domain exceptions to HTTP status codes.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from api.schemas.requests import AnalyzeRequest
from api.schemas.responses import AnalyzeResponse
from services.analysis_service import run_full_analysis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Run the full PhantomClaw analysis pipeline",
    description=(
        "Execute the complete AI-powered trade analysis pipeline: "
        "Market Data → Technical Indicators → OpenClaw → Consensus → "
        "Challenge Agent → ArmorIQ Risk → Trust Engine → Execution Controller → "
        "SQLite persistence. Returns a simplified analysis summary."
    ),
    responses={
        200: {"description": "Analysis completed successfully"},
        400: {"description": "Invalid symbol or no market data available"},
        500: {"description": "Pipeline stage failure or internal error"},
    },
)
async def analyze_symbol(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run the full PhantomClaw pipeline for the given symbol.

    The pipeline proceeds through all stages in order:
      Market Data → Indicators → OpenClaw → Consensus → Challenge →
      ArmorIQ → Trust → Execution → DB Persist → Response

    Raises:
        HTTPException 400: Invalid/empty symbol or missing market data.
        HTTPException 500: Agent failure or unexpected internal error.
    """
    try:
        result = await run_full_analysis(request.symbol)
    except ValueError as exc:
        logger.warning("Bad request for symbol '%s': %s", request.symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error("Pipeline error for symbol '%s': %s", request.symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    # Map the full pipeline result to the simplified API response
    rec = result.trade_recommendation
    return AnalyzeResponse(
        symbol=rec.symbol,
        action=rec.action,
        confidence=int(rec.confidence * 100),
        trust_score=result.trust_assessment.trust_score,
        risk=result.risk_assessment.risk_level,
        execution=result.execution_decision.decision,
        reason=rec.reason,
    )
