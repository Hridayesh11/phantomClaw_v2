"""
trading/ledger.py
-----------------
Persistence wrapper for the trading subsystem.
Uses database.db for executing SQL operations.
"""

import logging
from typing import List

from database.db import get_all_execution_logs, save_execution_log
from trading.models import TradeFill

logger = logging.getLogger(__name__)


class TradeLedger:
    """
    Append-only log of executed trades.
    Decouples the persistence mechanism from the execution engine.
    """

    def record_trade(self, fill: TradeFill) -> int:
        """
        Record a successful trade fill to the database.
        Returns the database primary key.
        """
        return save_execution_log(
            fill_id=str(fill.fill_id),
            order_id=str(fill.order_id),
            symbol=fill.symbol,
            side=fill.side.value,
            quantity=fill.quantity,
            price=fill.price,
            fees=fill.fees,
            slippage=fill.slippage,
            timestamp=fill.timestamp
        )

    def get_history(self) -> List[dict]:
        """
        Retrieve all execution history.
        Useful for building the equity curve and computing analytics.
        """
        return get_all_execution_logs()
