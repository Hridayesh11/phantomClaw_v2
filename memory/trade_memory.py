"""
memory/trade_memory.py
-----------------------
Memory abstraction layer for PhantomClaw v2.

PURPOSE
-------
This module provides a stable, technology-agnostic interface for storing
and retrieving trade analysis memory. The interface is intentionally kept
minimal so that the backing store can be upgraded without touching any
agent or service code.

CURRENT BACKEND: SQLite (via database/db.py)
FUTURE BACKEND:  ChromaDB (vector store for semantic similarity search)

UPGRADE PATH
------------
Phase 1 (now):   SQLite — exact-match retrieval by symbol, ordered by recency.
Phase 2 (later): ChromaDB — embed trade summaries as vectors, retrieve by
                 semantic similarity. To upgrade:
                 1. Add `memory/chromadb_memory.py` implementing the same
                    `save_memory()` / `retrieve_similar_trades()` signatures.
                 2. Replace the import at the bottom of this file.
                 3. Zero changes required in agents/, services/, or app.py.

DESIGN CONTRACT
---------------
- `save_memory()` accepts a `FullAnalysisResult` — always.
- `retrieve_similar_trades()` returns `list[dict]` — always.
- The internal implementation may change; the interface must not.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from database.db import get_trades_by_symbol

if TYPE_CHECKING:
    from models.trade_model import FullAnalysisResult

logger = logging.getLogger(__name__)


# ─── Public Interface ─────────────────────────────────────────────────────────


def save_memory(analysis_result: "FullAnalysisResult") -> None:
    """
    Placeholder memory write interface.

    Database persistence is already handled by database/db.py through
    analysis_service.py.

    Future versions will write embeddings to ChromaDB without changing
    any caller code.

    Currently this is a no-op.
    """
    return None


def retrieve_similar_trades(symbol: str, limit: int = 5) -> list[dict]:
    """
    Retrieve past trade analyses for a given symbol.

    Phase 1: Returns the most recent N logs for this symbol from SQLite.
             "Similarity" is purely recency-based (no vector search yet).

    Phase 2: Will use ChromaDB to find semantically similar trades across
             all symbols — not just exact symbol matches. For example, a
             query for "AAPL" might return similar large-cap tech patterns
             seen in "MSFT" or "GOOGL" analyses.

    Args:
        symbol: Ticker symbol to retrieve memory for (case-insensitive).
        limit:  Maximum number of records to return (default 5).

    Returns:
        List of trade log dicts, ordered newest-first.
        Returns an empty list if no prior analyses exist for this symbol.
    """
    records = get_trades_by_symbol(symbol=symbol, limit=limit)

    logger.debug(
        "Memory retrieval: found %d record(s) for %s",
        len(records),
        symbol.upper(),
    )

    return records


# ─── Phase 2 Stub: ChromaDB Memory ───────────────────────────────────────────
#
# When ChromaDB is ready, create `memory/chromadb_memory.py` and implement:
#
#   class ChromaDBMemory:
#       def save_memory(self, analysis_result: FullAnalysisResult) -> None:
#           # 1. Serialise result to a text summary
#           # 2. Generate embedding via OpenAI embeddings API
#           # 3. Upsert into ChromaDB collection
#
#       def retrieve_similar_trades(self, symbol: str, limit: int = 5) -> list[dict]:
#           # 1. Generate query embedding for symbol
#           # 2. Query ChromaDB by cosine similarity
#           # 3. Return top-N results as dicts
#
# Then replace the two functions above with:
#   from memory.chromadb_memory import ChromaDBMemory
#   _backend = ChromaDBMemory()
#   save_memory = _backend.save_memory
#   retrieve_similar_trades = _backend.retrieve_similar_trades
#
# No other file needs to change.
