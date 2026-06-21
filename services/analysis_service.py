"""
services/analysis_service.py
-----------------------------
Orchestration layer for PhantomClaw v2.

PURPOSE
-------
This module is the single entry point for a full pipeline run.
Neither Streamlit nor FastAPI contains any business logic — they only call:

    result = await run_full_analysis(symbol)

PIPELINE ORDER
--------------
    1.  Validate symbol
    2.  Fetch market data          ← market.market_data
    3.  Compute indicators         ← market.indicators
    4.  OpenClaw Agent             ← agents.openclaw
    5.  Weighted Consensus Engine  ← consensus.consensus_engine
    6.  Challenge Agent            ← agents.challenge_agent
    7.  ArmorIQ Risk Engine        ← engines.armoriq
    8.  Trust Engine               ← engines.trust_engine
    9.  Execution Controller       ← controller.execution_controller
    10. Persist to database        ← database.db.save_trade_log()   (exactly once)
    11. Memory placeholder         ← memory.trade_memory.save_memory()
    12. Return FullAnalysisResult

DATABASE WRITE CONTRACT
-----------------------
save_trade_log() is called exactly once per pipeline run, here.
save_memory() is a no-op placeholder for future ChromaDB integration.
No other module writes to the database on behalf of this pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial

from agents.challenge_agent import challenge_recommendation
from agents.mean_reversion_agent import analyze as mean_reversion_analyze
from agents.momentum_agent import analyze as momentum_analyze
from agents.openclaw_agent import generate_vote as generate_openclaw_vote
from agents.trend_agent import analyze as trend_analyze
from consensus.consensus_engine import get_consensus
from controller.execution_controller import make_decision
from database.db import save_trade_log
from engines.armoriq import evaluate_risk
from engines.trust_engine import compute_trust
from market.indicators import get_indicator_summary
from market.market_data import fetch_market_data, get_latest_price, validate_symbol
from memory.trade_memory import save_memory
from models.trade_model import FullAnalysisResult
from risk.position_sizer import calculate_position_size
from services.explanation_service import generate_explanation

logger = logging.getLogger(__name__)


# ─── Public Interface ─────────────────────────────────────────────────────────


async def run_full_analysis(symbol: str) -> FullAnalysisResult:
    """
    Execute the complete PhantomClaw analysis pipeline for a given symbol.

    This is the single orchestration entry point. Callers (FastAPI, Streamlit)
    must not contain any of this logic — they call this function and display
    the returned FullAnalysisResult.

    Args:
        symbol: Ticker symbol to analyse (e.g. "AAPL"). Case-insensitive.

    Returns:
        FullAnalysisResult aggregating all pipeline outputs.

    Raises:
        ValueError:     On empty/invalid symbols or missing market data.
        RuntimeError:   When a pipeline stage fails in an unrecoverable way.
    """
    # ── Step 1: Validate symbol ────────────────────────────────────────────────
    if not symbol or not symbol.strip():
        raise ValueError("Symbol must not be empty.")

    symbol = validate_symbol(symbol)
    logger.info("Pipeline started for symbol: %s", symbol)

    # ── Step 2: Fetch market data ──────────────────────────────────────────────
    logger.info("[1/8] Fetching market data for %s", symbol)
    loop = asyncio.get_running_loop()

    df = await loop.run_in_executor(None, partial(fetch_market_data, symbol))
    if df is None or df.empty:
        raise ValueError(
            f"No market data returned for '{symbol}'. "
            "Verify the symbol is valid and markets are open."
        )

    market_snapshot: dict = await loop.run_in_executor(
        None, partial(get_latest_price, symbol)
    )

    # ── Step 3: Compute technical indicators ───────────────────────────────────
    logger.info("[2/8] Computing technical indicators for %s", symbol)
    technical_indicators: dict = await loop.run_in_executor(
        None, partial(get_indicator_summary, df)
    )

    # ── Step 4: OpenClaw Agent ─────────────────────────────────────────────────
    logger.info("[3/9] Running OpenClaw Agent for %s", symbol)
    try:
        openclaw_vote = await loop.run_in_executor(
            None,
            partial(
                generate_openclaw_vote,
                symbol,
                market_snapshot,
                technical_indicators,
            ),
        )
    except Exception as exc:
        raise RuntimeError(
            f"OpenClaw Agent failed for '{symbol}': {exc}"
        ) from exc

    # ── Step 5: Weighted Consensus Engine ──────────────────────────────────────
    logger.info("[4/9] Running Weighted Consensus Engine for %s", symbol)
    try:
        trade_recommendation = await loop.run_in_executor(
            None,
            partial(
                get_consensus,
                symbol,
                openclaw_vote,
                market_snapshot,
                technical_indicators,
            ),
        )
    except Exception as exc:
        raise RuntimeError(
            f"Consensus Engine failed for '{symbol}': {exc}"
        ) from exc

    # ── Step 5.5: Dynamic Position Sizing ──────────────────────────────────────
    logger.info("[4.5/9] Calculating Dynamic Position Size for %s", symbol)
    
    current_price = market_snapshot.get("current_price", 0.0)
    atr = technical_indicators.get("atr", 0.0)
    portfolio_value = 100_000.0  # Simulated default portfolio size
    
    position_sizing = calculate_position_size(
        portfolio_value=portfolio_value,
        price=current_price,
        atr=atr,
    )
    
    if trade_recommendation.action in ("BUY", "SELL"):
        trade_recommendation.quantity = position_sizing.quantity

    # ── Step 6: Challenge Agent ────────────────────────────────────────────────
    logger.info("[5/9] Running Challenge Agent for %s", symbol)
    try:
        challenge_result = await loop.run_in_executor(
            None,
            partial(challenge_recommendation, trade_recommendation, technical_indicators),
        )
    except Exception as exc:
        raise RuntimeError(
            f"Challenge Agent failed for '{symbol}': {exc}"
        ) from exc

    # ── Step 7: ArmorIQ Risk Engine ────────────────────────────────────────────
    logger.info("[6/9] Running ArmorIQ Risk Engine for %s", symbol)
    risk_assessment = evaluate_risk(trade_recommendation, technical_indicators)

    # ── Step 8: Trust Engine ───────────────────────────────────────────────────
    logger.info("[7/9] Running Trust Engine for %s", symbol)
    trust_assessment = compute_trust(trade_recommendation, risk_assessment)

    # ── Step 9: Execution Controller ──────────────────────────────────────────
    logger.info("[8/9] Running Execution Controller for %s", symbol)
    execution_decision = make_decision(trust_assessment)

    # ── Step 9.5: Explanation Layer ───────────────────────────────────────────
    logger.info("[8.5/9] Generating Explanation for %s", symbol)
    votes = [
        openclaw_vote,
        trend_analyze(symbol, market_snapshot, technical_indicators),
        momentum_analyze(symbol, market_snapshot, technical_indicators),
        mean_reversion_analyze(symbol, market_snapshot, technical_indicators),
    ]
    explanation = generate_explanation(
        trade_recommendation,
        challenge_result,
        risk_assessment,
        trust_assessment,
        execution_decision,
        votes,
        position_sizing,
    )

    # ── Step 10: Persist to database (exactly once) ────────────────────────────
    logger.info("[9/9] Persisting trade log for %s", symbol)
    rec = trade_recommendation
    risk = risk_assessment
    trust = trust_assessment
    decision = execution_decision
    challenge = challenge_result
    indicators = technical_indicators
    market = market_snapshot

    try:
        trade_id = save_trade_log(
            symbol=rec.symbol,
            action=rec.action,
            quantity=rec.quantity,
            confidence=rec.confidence,
            price=market.get("current_price"),
            rsi=indicators.get("rsi"),
            macd=indicators.get("macd"),
            atr=indicators.get("atr"),
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            trust_score=trust.trust_score,
            trust_level=trust.trust_level,
            decision=decision.decision,
            reason=rec.reason,
            support_reasoning=challenge.support_reasoning,
            opposing_reasoning=challenge.opposing_reasoning,
        )
        logger.info("Trade log persisted: id=%d symbol=%s", trade_id, symbol)
    except Exception as exc:
        logger.error("Database write failed for '%s': %s", symbol, exc)
        raise RuntimeError(
            f"Failed to persist trade log for '{symbol}': {exc}"
        ) from exc

    # ── Step 11: Memory placeholder (no-op; future ChromaDB) ─────────────────
    result = FullAnalysisResult(
        trade_recommendation=trade_recommendation,
        challenge_result=challenge_result,
        risk_assessment=risk_assessment,
        trust_assessment=trust_assessment,
        execution_decision=execution_decision,
        explanation=explanation,
        position_sizing=position_sizing,
        market_snapshot=market_snapshot,
        technical_indicators=technical_indicators,
    )
    save_memory(result)  # Currently a no-op — see memory/trade_memory.py

    # ── Step 12: Return FullAnalysisResult ────────────────────────────────────
    logger.info(
        "Pipeline complete: %s %d %s → %s (trust=%d, risk=%d)",
        rec.action,
        rec.quantity,
        rec.symbol,
        decision.decision,
        trust.trust_score,
        risk.risk_score,
    )
    return result
