"""
trading/models.py
-----------------
Core Pydantic models for the trading engine.
Defines Orders, Trade Fills, and statuses.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Order(BaseModel):
    """
    Represents an intent to trade.
    Passed from the ExecutionEngine to the BaseBroker.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique order ID")
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int = Field(..., gt=0, description="Number of shares to trade")
    
    # Conditional fields for non-market orders
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Audit fields updated by the broker upon terminal status
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    fees_paid: float = 0.0
    reject_reason: Optional[str] = None


class TradeFill(BaseModel):
    """
    Event emitted by a BaseBroker when an Order is fully or partially executed.
    Passed back to the ExecutionEngine to update PortfolioManager and TradeLedger.
    """
    fill_id: UUID = Field(default_factory=uuid4, description="Unique fill ID")
    order_id: UUID = Field(..., description="The ID of the parent Order")
    symbol: str
    side: OrderSide
    quantity: int
    price: float = Field(..., description="Execution price after slippage")
    fees: float = Field(..., description="Brokerage fees applied to this fill")
    slippage: float = Field(default=0.0, description="Amount of slippage applied")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
