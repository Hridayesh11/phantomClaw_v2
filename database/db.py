"""
database/db.py
--------------
SQLite persistence layer for PhantomClaw v2.
Uses SQLAlchemy ORM with the modern 2.0 DeclarativeBase style.

Responsibilities:
  - Define the `TradeLog` ORM model (maps to `trade_logs` table)
  - Provide `init_db()`, `save_trade_log()`, `get_recent_trades()`
  - Return plain dicts (not ORM objects) from all query functions
  - All timestamps stored and returned as UTC datetimes

The database file is created automatically on first use.
Location is controlled by DATABASE_URL in .env.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from utils.config import config

logger = logging.getLogger(__name__)


# ─── Database Directory ───────────────────────────────────────────────────────

# Ensure the database directory exists before the engine is created.
_db_dir = os.path.join(os.path.dirname(__file__))
os.makedirs(_db_dir, exist_ok=True)


# ─── Engine ───────────────────────────────────────────────────────────────────

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + multi-thread
    poolclass=StaticPool,
    echo=False,
)


# ─── ORM Base & Model ─────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base for all ORM models."""


class TradeLog(Base):
    """
    ORM model representing a single PhantomClaw trade analysis record.

    Each row captures the complete state of one pipeline run:
    market context, AI recommendation, challenge arguments, risk/trust
    scoring, and the final execution decision.
    """

    __tablename__ = "trade_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Core trade fields ──
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Market context at time of analysis ──
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rsi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    atr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Risk & trust scoring ──
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False)
    trust_level: Mapped[str] = mapped_column(String(10), nullable=False)

    # ── Decision ──
    decision: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False, default="")

    # ── Challenge agent output ──
    support_reasoning: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    opposing_reasoning: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # ── Timestamp ──
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """Return all columns as a plain Python dict."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "confidence": self.confidence,
            "price": self.price,
            "rsi": self.rsi,
            "macd": self.macd,
            "atr": self.atr,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "trust_score": self.trust_score,
            "trust_level": self.trust_level,
            "decision": self.decision,
            "reason": self.reason,
            "support_reasoning": self.support_reasoning,
            "opposing_reasoning": self.opposing_reasoning,
            "timestamp": self.timestamp,
        }


class ExecutionLog(Base):
    """
    ORM model representing a fulfilled trade execution from the Trading Engine.
    """
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fill_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    order_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    
    fees: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fill_id": self.fill_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "fees": self.fees,
            "slippage": self.slippage,
            "timestamp": self.timestamp,
        }


# ─── Public API ───────────────────────────────────────────────────────────────


def init_db() -> None:
    """
    Create all ORM-mapped tables if they don't already exist.

    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS semantics.
    Should be called once at application startup (e.g. in main.py lifespan).
    """
    Base.metadata.create_all(engine)
    logger.info("Database initialised: %s", config.DATABASE_URL)


def save_trade_log(
    *,
    symbol: str,
    action: str,
    quantity: int,
    confidence: float,
    price: Optional[float] = None,
    rsi: Optional[float] = None,
    macd: Optional[float] = None,
    atr: Optional[float] = None,
    risk_score: int,
    risk_level: str,
    trust_score: int,
    trust_level: str,
    decision: str,
    reason: str,
    support_reasoning: Optional[str] = None,
    opposing_reasoning: Optional[str] = None,
) -> int:
    """
    Persist a single pipeline analysis result to the `trade_logs` table.

    All parameters are keyword-only to prevent positional argument mistakes.

    Args:
        symbol:              Ticker symbol (e.g. "AAPL")
        action:              "BUY" or "SELL"
        quantity:            Number of shares
        confidence:          OpenClaw confidence [0.0–1.0]
        price:               Close price at analysis time (optional)
        rsi:                 RSI value at analysis time (optional)
        macd:                MACD line value at analysis time (optional)
        atr:                 ATR value at analysis time (optional)
        risk_score:          ArmorIQ risk score [0–100]
        risk_level:          "LOW" | "MEDIUM" | "HIGH"
        trust_score:         Trust Engine score [0–100]
        trust_level:         "LOW" | "MEDIUM" | "HIGH"
        decision:            "EXECUTE" | "HOLD" | "BLOCK"
        reason:              OpenClaw rationale text
        support_reasoning:   Challenge Agent support argument (optional)
        opposing_reasoning:  Challenge Agent opposing argument (optional)

    Returns:
        The auto-generated primary key (id) of the new row.
    """
    record = TradeLog(
        symbol=symbol.upper(),
        action=action.upper(),
        quantity=quantity,
        confidence=round(confidence, 6),
        price=round(price, 4) if price is not None else None,
        rsi=round(rsi, 4) if rsi is not None else None,
        macd=round(macd, 6) if macd is not None else None,
        atr=round(atr, 4) if atr is not None else None,
        risk_score=risk_score,
        risk_level=risk_level,
        trust_score=trust_score,
        trust_level=trust_level,
        decision=decision,
        reason=reason[:1000],
        support_reasoning=support_reasoning[:2000] if support_reasoning else None,
        opposing_reasoning=opposing_reasoning[:2000] if opposing_reasoning else None,
        timestamp=datetime.now(timezone.utc),
    )

    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        new_id: int = record.id  # type: ignore[assignment]

    logger.info(
        "Saved trade log #%d: %s %s %s → %s",
        new_id, action, quantity, symbol, decision,
    )
    return new_id


def get_recent_trades(limit: int = 20) -> list[dict]:
    """
    Return the most recent N trade log entries as plain dicts.

    Results are ordered newest-first by timestamp.

    Args:
        limit: Maximum number of rows to return (default 20).

    Returns:
        List of dicts, each representing one `trade_logs` row.
        Empty list if no records exist.
    """
    with Session(engine) as session:
        rows = session.execute(
            select(TradeLog)
            .order_by(TradeLog.timestamp.desc())
            .limit(limit)
        ).scalars().all()

    return [row.to_dict() for row in rows]


def get_trades_by_symbol(symbol: str, limit: int = 50) -> list[dict]:
    """
    Return the most recent N trade logs for a specific symbol.

    Args:
        symbol: Ticker symbol to filter by (case-insensitive).
        limit:  Maximum number of rows to return.

    Returns:
        List of dicts, ordered newest-first.
    """
    with Session(engine) as session:
        rows = session.execute(
            select(TradeLog)
            .where(TradeLog.symbol == symbol.upper())
            .order_by(TradeLog.timestamp.desc())
            .limit(limit)
        ).scalars().all()

    return [row.to_dict() for row in rows]


def save_execution_log(
    *,
    fill_id: str,
    order_id: str,
    symbol: str,
    side: str,
    quantity: int,
    price: float,
    fees: float,
    slippage: float,
    timestamp: datetime
) -> int:
    """Persist a single trade fill to the execution_logs table."""
    record = ExecutionLog(
        fill_id=fill_id,
        order_id=order_id,
        symbol=symbol.upper(),
        side=side.upper(),
        quantity=quantity,
        price=price,
        fees=fees,
        slippage=slippage,
        timestamp=timestamp,
    )

    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        new_id: int = record.id  # type: ignore[assignment]

    logger.info("Saved execution log #%d: %s %d %s @ %.2f", new_id, side, quantity, symbol, price)
    return new_id


def get_all_execution_logs() -> list[dict]:
    """Return all execution logs ordered by timestamp ascending."""
    with Session(engine) as session:
        rows = session.execute(
            select(ExecutionLog)
            .order_by(ExecutionLog.timestamp.asc())
        ).scalars().all()

    return [row.to_dict() for row in rows]
