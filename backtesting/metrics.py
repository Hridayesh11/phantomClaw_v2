"""
backtesting/metrics.py
-----------------------
Performance metric calculations for the PhantomClaw backtesting engine.

All functions are pure — they accept trade history and/or an equity curve
and return a plain dict. No I/O, no side effects.

Metrics provided:
  - total_return        : % gain/loss from initial to final equity
  - win_rate            : % of trades that were profitable
  - max_drawdown        : largest peak-to-trough decline in equity (%)
  - trade_count         : total number of executed trades
  - equity_curve_stats  : min, max, final, and start equity values
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backtesting.portfolio import EquityPoint, TradeRecord

logger = logging.getLogger(__name__)


# ─── Total Return ─────────────────────────────────────────────────────────────


def calculate_total_return(
    equity_curve: list["EquityPoint"],
    initial_cash: float,
) -> float:
    """
    Calculate the percentage total return over the backtest period.

    Formula: ((final_equity - initial_cash) / initial_cash) * 100

    Args:
        equity_curve:  List of EquityPoint records (must have at least one entry).
        initial_cash:  The portfolio's starting cash value.

    Returns:
        Total return as a percentage (positive = profit, negative = loss).
        Returns 0.0 if equity_curve is empty or initial_cash is zero.
    """
    if not equity_curve or initial_cash == 0:
        return 0.0

    final_equity = equity_curve[-1].equity
    return round(((final_equity - initial_cash) / initial_cash) * 100, 4)


# ─── Win Rate ─────────────────────────────────────────────────────────────────


def calculate_win_rate(trade_history: list["TradeRecord"]) -> float:
    """
    Calculate the percentage of completed round-trips (BUY→SELL pairs) that
    were profitable.

    Method: Match each SELL to the most recent BUY at the time of the sell.
    A trade is a "win" if sell_price > buy_price.

    Args:
        trade_history: List of TradeRecord entries from Portfolio.

    Returns:
        Win rate as a percentage [0.0–100.0].
        Returns 0.0 if there are no completed sell trades.
    """
    buys: list[float] = []
    wins = 0
    total_sells = 0

    for trade in trade_history:
        if trade.action == "BUY":
            buys.append(trade.price)
        elif trade.action == "SELL" and buys:
            buy_price = buys.pop(0)   # FIFO matching
            total_sells += 1
            if trade.price > buy_price:
                wins += 1

    if total_sells == 0:
        return 0.0

    return round((wins / total_sells) * 100, 2)


# ─── Max Drawdown ─────────────────────────────────────────────────────────────


def calculate_max_drawdown(equity_curve: list["EquityPoint"]) -> float:
    """
    Calculate the maximum peak-to-trough drawdown over the backtest period.

    Formula: ((trough - peak) / peak) * 100  — expressed as a negative %.

    Args:
        equity_curve: List of EquityPoint records ordered by date.

    Returns:
        Max drawdown as a negative percentage (e.g. -15.3 means 15.3% loss).
        Returns 0.0 if equity_curve has fewer than 2 points.
    """
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0].equity
    max_dd = 0.0

    for point in equity_curve[1:]:
        equity = point.equity
        if equity > peak:
            peak = equity
        elif peak > 0:
            drawdown = ((equity - peak) / peak) * 100
            if drawdown < max_dd:
                max_dd = drawdown

    return round(max_dd, 4)


# ─── Trade Count ──────────────────────────────────────────────────────────────


def calculate_trade_count(trade_history: list["TradeRecord"]) -> dict[str, int]:
    """
    Count total, buy, and sell trades.

    Args:
        trade_history: List of TradeRecord entries from Portfolio.

    Returns:
        Dict with keys: total, buys, sells.
    """
    buys = sum(1 for t in trade_history if t.action == "BUY")
    sells = sum(1 for t in trade_history if t.action == "SELL")
    return {"total": buys + sells, "buys": buys, "sells": sells}


# ─── Equity Curve Stats ───────────────────────────────────────────────────────


def calculate_equity_curve_stats(
    equity_curve: list["EquityPoint"],
    initial_cash: float,
) -> dict[str, float]:
    """
    Summarise the equity curve with min, max, start, and final equity values.

    Args:
        equity_curve:  List of EquityPoint records.
        initial_cash:  Starting portfolio cash.

    Returns:
        Dict with keys: start, final, peak, trough.
        All values are in the same currency unit as initial_cash.
        Returns zeroed dict if equity_curve is empty.
    """
    if not equity_curve:
        return {"start": initial_cash, "final": 0.0, "peak": 0.0, "trough": 0.0}

    equities = [p.equity for p in equity_curve]
    return {
        "start":  round(initial_cash, 2),
        "final":  round(equities[-1], 2),
        "peak":   round(max(equities), 2),
        "trough": round(min(equities), 2),
    }


# ─── Aggregate Metrics ────────────────────────────────────────────────────────


def calculate_all_metrics(
    trade_history: list["TradeRecord"],
    equity_curve: list["EquityPoint"],
    initial_cash: float,
) -> dict:
    """
    Compute and return all backtest metrics in a single dict.

    Args:
        trade_history: Executed trade records from Portfolio.
        equity_curve:  Equity curve snapshots from Portfolio.
        initial_cash:  The portfolio's starting cash.

    Returns:
        Dict containing:
            total_return_pct     float   – % gain/loss
            win_rate_pct         float   – % of profitable sell trades
            max_drawdown_pct     float   – largest peak-to-trough decline (negative)
            trade_counts         dict    – {total, buys, sells}
            equity_stats         dict    – {start, final, peak, trough}
    """
    metrics = {
        "total_return_pct":  calculate_total_return(equity_curve, initial_cash),
        "win_rate_pct":      calculate_win_rate(trade_history),
        "max_drawdown_pct":  calculate_max_drawdown(equity_curve),
        "trade_counts":      calculate_trade_count(trade_history),
        "equity_stats":      calculate_equity_curve_stats(equity_curve, initial_cash),
    }

    logger.info(
        "Backtest metrics: return=%.2f%% | win_rate=%.1f%% | max_dd=%.2f%% | trades=%d",
        metrics["total_return_pct"],
        metrics["win_rate_pct"],
        metrics["max_drawdown_pct"],
        metrics["trade_counts"]["total"],
    )

    return metrics
