"""
backtesting/backtest_engine.py
-------------------------------
PhantomClaw v2 Backtesting Engine.

Simulates historical execution of the PhantomClaw pipeline candle-by-candle
across a specified date range. Completely deterministic — no OpenAI calls,
no LLM usage, no randomness.

Pipeline per candle:
    market data (single bar, no lookahead)
    → StrategyAgent  (rule-based, deterministic — replaces OpenClaw for backtesting)
    → ArmorIQ Risk Engine
    → Trust Engine
    → Execution Controller
    → Portfolio.buy() / Portfolio.sell()
    → equity snapshot

The Challenge Agent is deliberately excluded from backtesting.
It is an LLM-based component and would add cost and non-determinism.
The live pipeline (analysis_service.py) includes it; the backtest does not.

Data fetching:
    A 60-day warmup buffer is prepended to start_date so that rolling indicators
    (EMA50, MACD) are fully seeded before the first simulated trading bar.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from backtesting.metrics import calculate_all_metrics
from backtesting.portfolio import Portfolio
from backtesting.strategy_agent import generate_strategy_recommendation
from controller.execution_controller import make_decision
from engines.armoriq import evaluate_risk
from engines.trust_engine import compute_trust
from market.indicators import compute_indicators
from market.market_data import validate_symbol

logger = logging.getLogger(__name__)

# Warmup buffer prepended before start_date so indicators are fully seeded
_WARMUP_DAYS: int = 60


# ─── Internal Helpers ─────────────────────────────────────────────────────────


def _parse_date(value: str | date) -> date:
    """Parse a date string (%Y-%m-%d) or pass through a date object."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def _bar_to_market_snapshot(symbol: str, row: pd.Series) -> dict:
    """Convert a single OHLCV row into the market snapshot dict format."""
    return {
        "symbol":        symbol.upper(),
        "current_price": round(float(row["Close"]), 2),
        "open":          round(float(row["Open"]),  2),
        "high":          round(float(row["High"]),  2),
        "low":           round(float(row["Low"]),   2),
        "close":         round(float(row["Close"]), 2),
        "volume":        int(row["Volume"]),
    }


def _bar_to_indicators(df_with_indicators: pd.DataFrame) -> dict:
    """
    Extract the latest row's indicator values from a computed DataFrame.

    Returns a dict with keys: rsi, macd, macd_signal, sma20, ema50, atr.
    All values are rounded floats or None when unavailable (NaN → None).
    """
    latest = df_with_indicators.iloc[-1]

    def _safe(col: str) -> float | None:
        try:
            val = latest.get(col)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return None
            return round(float(val), 4)
        except Exception:
            return None

    return {
        "rsi":         _safe("RSI"),
        "macd":        _safe("MACD"),
        "macd_signal": _safe("MACD_signal"),
        "sma20":       _safe("SMA20"),
        "ema50":       _safe("EMA50"),
        "atr":         _safe("ATR"),
    }


def _row_date(idx_value: Any) -> date:
    """Safely coerce a DataFrame index value to a Python date."""
    if isinstance(idx_value, datetime):
        return idx_value.date()
    if isinstance(idx_value, date):
        return idx_value
    return pd.Timestamp(idx_value).date()


# ─── Public Interface ─────────────────────────────────────────────────────────


def run_backtest(
    symbol: str,
    start_date: str | date,
    end_date:   str | date,
    initial_cash: float = 100_000.0,
) -> dict:
    """
    Run a deterministic historical simulation of the PhantomClaw pipeline.

    Fetches OHLCV data from (start_date - 60 days) to end_date so that
    rolling indicators warm up properly before the first traded bar.
    The simulation itself only executes trades from start_date onward.

    Args:
        symbol:       Ticker symbol (e.g. "AAPL"). Case-insensitive.
        start_date:   First date to trade (inclusive). Format: "YYYY-MM-DD" or date.
        end_date:     Last date to trade (inclusive). Format: "YYYY-MM-DD" or date.
        initial_cash: Starting cash balance (default $100,000).

    Returns:
        Dict with keys:
            metrics       : dict  — all performance metrics
            trade_history : list  — executed paper trades (list of dicts)
            equity_curve  : list  — daily equity snapshots (list of dicts)
            summary       : dict  — {final_equity, return_pct, win_rate, max_drawdown}

    Raises:
        ValueError:   Empty symbol, bad date range, or no market data found.
        RuntimeError: Unrecoverable engine failure during simulation.
    """
    # ── 1. Validate inputs ────────────────────────────────────────────────────
    symbol = validate_symbol(symbol)
    if not symbol:
        raise ValueError("Symbol must not be empty.")

    start_date = _parse_date(start_date)
    end_date   = _parse_date(end_date)

    if start_date >= end_date:
        raise ValueError(
            f"start_date ({start_date}) must be before end_date ({end_date})."
        )

    logger.info(
        "Backtest started ─── symbol=%s | range=%s → %s | cash=%.0f",
        symbol, start_date, end_date, initial_cash,
    )

    # ── 2. Fetch data with 60-day warmup buffer ───────────────────────────────
    start_fetch: date = start_date - timedelta(days=_WARMUP_DAYS)

    logger.info(
        "Fetching market data: %s from %s to %s (incl. %d-day warmup buffer)",
        symbol, start_fetch, end_date, _WARMUP_DAYS,
    )

    try:
        ticker = yf.Ticker(symbol)
        full_df = ticker.history(
            start=start_fetch.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1d",
        )
        if not full_df.empty:
            full_df = full_df[["Open", "High", "Low", "Close", "Volume"]].copy()
            full_df.dropna(inplace=True)
    except Exception as exc:
        logger.error("Failed to fetch market data for %s: %s", symbol, exc)
        full_df = pd.DataFrame()

    if full_df is None or full_df.empty:
        raise ValueError(
            f"No market data returned for '{symbol}' "
            f"between {start_fetch} and {end_date}. "
            "Verify the symbol and date range."
        )

    # ── 3. Pre-compute all indicator columns once across full dataset ─────────
    full_df.index = pd.to_datetime(full_df.index)
    full_df = compute_indicators(full_df)

    # ── 4. Isolate the simulation window [start_date, end_date] ──────────────
    sim_df = full_df[
        (full_df.index.date >= start_date) &  # type: ignore[operator]
        (full_df.index.date <= end_date)       # type: ignore[operator]
    ]

    if sim_df.empty:
        raise ValueError(
            f"No trading bars found for '{symbol}' between {start_date} and {end_date}. "
            "The market may have been closed during this entire range."
        )

    logger.info(
        "Simulation window: %d trading bars | warmup pool: %d bars",
        len(sim_df), len(full_df),
    )

    # ── 5. Initialise portfolio ───────────────────────────────────────────────
    portfolio = Portfolio(initial_cash=initial_cash)

    # ── 6. Candle-by-candle simulation ───────────────────────────────────────
    for i, (idx, row) in enumerate(sim_df.iterrows()):
        bar_date   = _row_date(idx)
        close_px   = float(row["Close"])

        # Rolling window: all full_df bars up to and including this bar
        # → guarantees no lookahead bias in indicator values
        bar_pos    = full_df.index.get_loc(idx)
        window_df  = full_df.iloc[: bar_pos + 1]

        market_snapshot = _bar_to_market_snapshot(symbol, row)
        indicators      = _bar_to_indicators(window_df)

        try:
            # ── StrategyAgent (deterministic — no LLM) ────────────────────────
            recommendation = generate_strategy_recommendation(
                symbol, market_snapshot, indicators
            )

            # ── ArmorIQ Risk Engine ───────────────────────────────────────────
            risk = evaluate_risk(recommendation, indicators)

            # ── Trust Engine ──────────────────────────────────────────────────
            trust = compute_trust(recommendation, risk)

            # ── Execution Controller ──────────────────────────────────────────
            decision = make_decision(trust)

        except Exception as exc:
            logger.warning(
                "Pipeline error on %s (bar %d/%d): %s — skipping bar",
                bar_date, i + 1, len(sim_df), exc,
            )
            portfolio.record_equity(close_px, bar_date)
            continue

        # ── Execute paper order (only if EXECUTE and quantity > 0) ────────────
        if decision.decision == "EXECUTE" and recommendation.quantity > 0:
            if recommendation.action == "BUY":
                portfolio.buy(close_px, recommendation.quantity, bar_date)
            elif recommendation.action == "SELL":
                portfolio.sell(close_px, recommendation.quantity, bar_date)

        # ── Record equity snapshot ────────────────────────────────────────────
        portfolio.record_equity(close_px, bar_date)

        logger.debug(
            "[%s] signal=%s q=%d decision=%s | equity=%.2f",
            bar_date,
            recommendation.action,
            recommendation.quantity,
            decision.decision,
            portfolio.current_value(close_px),
        )

    if not portfolio.equity_curve:
        raise ValueError(
            f"Backtest produced no equity data for '{symbol}'. "
            "All bars may have been skipped."
        )

    # ── 7. Compute final metrics ──────────────────────────────────────────────
    last_close    = float(sim_df.iloc[-1]["Close"])
    final_equity  = portfolio.current_value(last_close)

    metrics = calculate_all_metrics(
        trade_history=portfolio.trade_history,
        equity_curve=portfolio.equity_curve,
        initial_cash=initial_cash,
    )

    # ── 8. Rich completion log ────────────────────────────────────────────────
    logger.info(
        "Backtest completed ─── symbol=%s | trades=%d | final_equity=%.2f "
        "| return=%.2f%% | win_rate=%.1f%% | max_drawdown=%.2f%%",
        symbol,
        metrics["trade_counts"]["total"],
        final_equity,
        metrics["total_return_pct"],
        metrics["win_rate_pct"],
        metrics["max_drawdown_pct"],
    )

    # ── 9. Return structured result ───────────────────────────────────────────
    return {
        "metrics":       metrics,
        "trade_history": [t._asdict() for t in portfolio.trade_history],
        "equity_curve":  [e._asdict() for e in portfolio.equity_curve],
        "summary": {
            "final_equity": round(final_equity, 2),
            "return_pct":   metrics["total_return_pct"],
            "win_rate":     metrics["win_rate_pct"],
            "max_drawdown": metrics["max_drawdown_pct"],
        },
    }
