"""
backtesting/portfolio.py
------------------------
Simulated paper-trading portfolio for the PhantomClaw backtesting engine.

Tracks cash, share positions, trade history, and equity over time.
No real broker integration — all values are simulated in memory.

Design contracts:
  - Cash can never go negative (buy is rejected with a warning).
  - Selling more shares than owned is rejected with a warning.
  - Every executed trade is recorded in trade_history.
  - equity_curve records portfolio value at each recorded date.
  - Use current_value(price) to obtain total portfolio worth (cash + shares).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import NamedTuple

logger = logging.getLogger(__name__)


# ─── Trade Record ─────────────────────────────────────────────────────────────


class TradeRecord(NamedTuple):
    """Immutable record of a single executed paper trade."""

    date: date
    action: str          # "BUY" or "SELL"
    price: float
    quantity: int
    cash_after: float    # cash balance immediately after the trade
    shares_after: int    # share count immediately after the trade


# ─── Equity Point ─────────────────────────────────────────────────────────────


class EquityPoint(NamedTuple):
    """Portfolio total value at a single point in time."""

    date: date
    equity: float        # cash + (shares × market_price)


# ─── Portfolio ────────────────────────────────────────────────────────────────


@dataclass
class Portfolio:
    """
    Paper-trading portfolio that simulates buy/sell decisions day by day.

    Args:
        initial_cash: Starting cash balance (default $100,000).
    """

    initial_cash: float = 100_000.0

    # ── Mutable state (reset to initial values at construction) ───────────────
    cash: float = field(init=False)
    shares: int = field(init=False)
    trade_history: list[TradeRecord] = field(init=False, default_factory=list)
    equity_curve: list[EquityPoint] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self.cash = self.initial_cash
        self.shares = 0

    # ── Core Methods ──────────────────────────────────────────────────────────

    def current_value(self, price: float) -> float:
        """
        Return total portfolio value: cash + market value of held shares.

        Args:
            price: Current market price per share.
        """
        return self.cash + (self.shares * price)

    def buy(self, price: float, quantity: int, trade_date: date) -> bool:
        """
        Execute a simulated buy order.

        Args:
            price:      Price per share.
            quantity:   Number of shares to buy.
            trade_date: Date of the trade (used for history/equity).

        Returns:
            True if the order was executed; False if cash was insufficient.
        """
        cost = price * quantity
        if cost > self.cash:
            logger.warning(
                "BUY rejected on %s: cost %.2f exceeds cash %.2f (qty=%d @ %.2f)",
                trade_date, cost, self.cash, quantity, price,
            )
            return False

        self.cash -= cost
        self.shares += quantity

        self.trade_history.append(
            TradeRecord(
                date=trade_date,
                action="BUY",
                price=price,
                quantity=quantity,
                cash_after=self.cash,
                shares_after=self.shares,
            )
        )
        logger.info(
            "BUY  %d shares @ %.2f on %s | cash=%.2f shares=%d",
            quantity, price, trade_date, self.cash, self.shares,
        )
        return True

    def sell(self, price: float, quantity: int, trade_date: date) -> bool:
        """
        Execute a simulated sell order.

        Args:
            price:      Price per share.
            quantity:   Number of shares to sell.
            trade_date: Date of the trade (used for history/equity).

        Returns:
            True if the order was executed; False if shares were insufficient.
        """
        if quantity > self.shares:
            logger.warning(
                "SELL rejected on %s: requested %d shares but only own %d",
                trade_date, quantity, self.shares,
            )
            return False

        self.cash += price * quantity
        self.shares -= quantity

        self.trade_history.append(
            TradeRecord(
                date=trade_date,
                action="SELL",
                price=price,
                quantity=quantity,
                cash_after=self.cash,
                shares_after=self.shares,
            )
        )
        logger.info(
            "SELL %d shares @ %.2f on %s | cash=%.2f shares=%d",
            quantity, price, trade_date, self.cash, self.shares,
        )
        return True

    def record_equity(self, price: float, equity_date: date) -> None:
        """
        Append the current total portfolio value to the equity curve.

        Args:
            price:        Current market price per share.
            equity_date:  Date to stamp this equity point with.
        """
        value = self.current_value(price)
        self.equity_curve.append(EquityPoint(date=equity_date, equity=value))
