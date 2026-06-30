"""
api/main.py
-----------
FastAPI application factory for PhantomClaw v3.

Responsibilities:
  - Create and configure the FastAPI application.
  - Register all API routers with their prefixes.
  - Enable CORS for cross-origin requests.
  - Configure structured logging.
  - Register global exception handlers.
  - Manage application lifespan (startup/shutdown).
  - Auto-generate OpenAPI documentation.

This file contains NO business logic. All domain work is delegated to
the services layer and route-specific modules.

Usage:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import analyze, health, history, market, portfolio, ledger
from api.schemas.responses import ErrorResponse, RootResponse
from database.db import init_db
from utils.config import config

# ─── Logging Configuration ───────────────────────────────────────────────────

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format=LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.

    Startup:
      - Initialize the SQLite database (create tables if missing).
      - Log configuration summary.

    Shutdown:
      - Log graceful shutdown.
    """
    logger.info("=" * 60)
    logger.info("PhantomClaw v3 — Starting up")
    logger.info("=" * 60)

    # Initialize database
    init_db()
    logger.info("Database initialized: %s", config.DATABASE_URL)

    # Log config summary (no secrets)
    logger.info("OpenAI model: %s", config.OPENAI_MODEL)
    logger.info("Log level: %s", config.LOG_LEVEL)
    logger.info("FastAPI URL: %s", config.FASTAPI_URL)
    logger.info("=" * 60)
    logger.info("PhantomClaw v3 — Ready to serve requests")
    logger.info("=" * 60)

    yield

    logger.info("=" * 60)
    logger.info("PhantomClaw v3 — Shutting down gracefully")
    logger.info("=" * 60)


# ─── Application ──────────────────────────────────────────────────────────────


app = FastAPI(
    title="PhantomClaw v3",
    version="3.0.0",
    description=(
        "AI-powered trade analysis pipeline.\n\n"
        "PhantomClaw v3 runs a multi-agent pipeline including:\n"
        "- **OpenClaw Agent** — Primary AI trade analysis\n"
        "- **Consensus Engine** — Multi-strategy weighted voting\n"
        "- **Challenge Agent** — Devil's advocate reasoning\n"
        "- **ArmorIQ Risk Engine** — Deterministic risk scoring\n"
        "- **Trust Engine** — Adaptive confidence calibration\n"
        "- **Execution Controller** — Final trade gate\n\n"
        "POST `/analyze` with a symbol to run the full pipeline."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "PhantomClaw Team",
    },
    license_info={
        "name": "MIT",
    },
)


# ─── CORS Middleware ──────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Logging Middleware ───────────────────────────────────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every incoming request with timing information."""
    start_time = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )

    return response


# ─── Global Exception Handlers ───────────────────────────────────────────────


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return a clean 422 response for Pydantic validation errors."""
    errors = exc.errors()
    detail = "; ".join(
        f"{'.'.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg', 'unknown error')}"
        for e in errors
    )
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, detail)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="ValidationError",
            detail=detail,
            status_code=422,
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Standardize all HTTPException responses to use ErrorResponse schema."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTPException",
            detail=str(exc.detail),
            status_code=exc.status_code,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler for unexpected errors — never leak stack traces."""
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            detail="An unexpected internal error occurred.",
            status_code=500,
        ).model_dump(),
    )


# ─── Root Endpoint ────────────────────────────────────────────────────────────


@app.get(
    "/",
    response_model=RootResponse,
    tags=["Status"],
    summary="Root — service identity",
)
async def root() -> RootResponse:
    """Return basic project information and documentation link."""
    return RootResponse()


# ─── Router Registration ─────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(market.router)
app.include_router(analyze.router)
app.include_router(history.router)
app.include_router(portfolio.router)
app.include_router(ledger.router)
