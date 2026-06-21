"""
models/agent_vote_model.py
--------------------------
Pydantic model for internal multi-agent votes in PhantomClaw v2.

PURPOSE
-------
AgentVote is the internal representation of a single agent's opinion.
It is produced by each specialist agent (TrendAgent, MomentumAgent,
MeanReversionAgent) and consumed exclusively by the ConsensusEngine.

It is intentionally separate from TradeRecommendation, which is the
*external* output model consumed by the pipeline, FastAPI, and Streamlit.

Design rule: Agents return AgentVote. The ConsensusEngine converts a
             collection of AgentVotes into a single TradeRecommendation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AgentVote(BaseModel):
    """
    Internal vote cast by a single deterministic specialist agent.

    Fields:
        agent_name : Human-readable name of the agent (e.g. "TrendAgent").
        signal     : Trade direction — exactly "BUY", "SELL", or "HOLD".
        confidence : Agent's conviction in its signal [0.0–1.0].
        reason     : Human-readable rationale for the vote.
    """

    agent_name: str = Field(..., description="Name of the agent producing this vote")
    signal:     Literal["BUY", "SELL", "HOLD"] = Field(
        ..., description="Agent's trade signal"
    )
    confidence: float = Field(
        ..., description="Agent confidence in its signal [0.0–1.0]"
    )
    reason: str = Field(..., description="Human-readable rationale")

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        """Ensure confidence is within [0.0, 1.0]."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(
                f"AgentVote.confidence must be between 0.0 and 1.0, got {v}"
            )
        return round(v, 6)
