"""
models/explanation_model.py
---------------------------
Pydantic models for the Phase 9 Explainability Layer.

Provides a structured representation of the entire pipeline's reasoning,
aggregating decisions and context from all agents and engines.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentExplanation(BaseModel):
    """
    Summarized reasoning from a single agent.
    """

    agent_name: str = Field(..., description="Name of the agent")
    signal: str = Field(..., description="Trade signal (BUY, SELL, HOLD)")
    confidence: float = Field(..., description="Agent confidence [0.0-1.0]")
    reason: str = Field(..., description="Agent's rationale")


class ExplanationResult(BaseModel):
    """
    Aggregated explanation for the entire PhantomClaw decision pipeline.
    """

    final_decision: str = Field(
        ..., description="Final execution decision (EXECUTE, HOLD, BLOCK)"
    )
    consensus_reason: str = Field(
        ..., description="The combined reason from the consensus engine"
    )
    agent_breakdown: list[AgentExplanation] = Field(
        default_factory=list, description="Individual agent votes and rationale"
    )
    challenge_summary: str = Field(
        ..., description="Summary of Challenge Agent's support/opposing arguments"
    )
    risk_summary: str = Field(
        ..., description="Summary of ArmorIQ's risk assessment"
    )
    trust_summary: str = Field(
        ..., description="Summary of Trust Engine's trust assessment"
    )
    position_summary: str = Field(
        ..., description="Summary of dynamic position sizing"
    )
    decision_summary: str = Field(
        ..., description="Overall summary of why the execution decision was made"
    )
