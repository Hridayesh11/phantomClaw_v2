"""
api/routes/health.py
--------------------
Health check endpoint for PhantomClaw v3.

Verifies connectivity of all critical infrastructure components:
  - Database (SQLite via SQLAlchemy)
  - Market data provider (Upstox)
  - AI pipeline (OpenAI API key configured)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.schemas.responses import ComponentHealth, HealthResponse
from database.db import engine
from market_data.provider_factory import get_market_provider
from utils.config import config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


def _check_database() -> ComponentHealth:
    """Verify database connectivity by executing a lightweight probe."""
    try:
        with Session(engine) as session:
            session.execute(text("SELECT 1"))
        return ComponentHealth(name="database", status="ok")
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return ComponentHealth(
            name="database", status="unavailable", detail=str(exc)
        )


def _check_market_provider() -> ComponentHealth:
    """Verify market data provider is instantiable and configured."""
    try:
        provider = get_market_provider()
        # Check that provider object is usable (instantiation alone validates config)
        if provider is None:
            return ComponentHealth(
                name="market_data", status="unavailable", detail="Provider returned None"
            )

        # Verify required Upstox credentials are set
        if not config.UPSTOX_ACCESS_TOKEN or config.UPSTOX_ACCESS_TOKEN.startswith("your_"):
            return ComponentHealth(
                name="market_data",
                status="degraded",
                detail="Upstox access token not configured",
            )

        return ComponentHealth(name="market_data", status="ok")
    except Exception as exc:
        logger.warning("Market provider health check failed: %s", exc)
        return ComponentHealth(
            name="market_data", status="unavailable", detail=str(exc)
        )


def _check_ai_pipeline() -> ComponentHealth:
    """Verify AI pipeline readiness by checking OpenAI API key configuration."""
    try:
        if not config.OPENAI_API_KEY or config.OPENAI_API_KEY.startswith("your_"):
            return ComponentHealth(
                name="ai_pipeline",
                status="degraded",
                detail="OpenAI API key not configured",
            )
        return ComponentHealth(name="ai_pipeline", status="ok")
    except Exception as exc:
        logger.warning("AI pipeline health check failed: %s", exc)
        return ComponentHealth(
            name="ai_pipeline", status="unavailable", detail=str(exc)
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
    description=(
        "Verify the health of all critical infrastructure components: "
        "database, market data provider, and AI pipeline."
    ),
    responses={
        200: {"description": "Health status (may be degraded)"},
        503: {"description": "Service is unhealthy"},
    },
)
async def health_check() -> HealthResponse:
    """Return structured health status of all infrastructure components."""
    components = [
        _check_database(),
        _check_market_provider(),
        _check_ai_pipeline(),
    ]

    # Determine overall status
    statuses = {c.status for c in components}
    if "unavailable" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    response = HealthResponse(
        status=overall,
        components=components,
    )

    if overall == "unhealthy":
        logger.error("Health check: UNHEALTHY — %s", components)
    elif overall == "degraded":
        logger.warning("Health check: DEGRADED — %s", components)
    else:
        logger.debug("Health check: HEALTHY")

    return response
