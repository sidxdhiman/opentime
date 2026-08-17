"""Structured reasoning-mode models for the ChronOS Engine.

``ReasoningMode`` names the reasoning modes ChronOS can engage during a single
DEEP interaction. ``ReasoningPlan`` is the deterministic, minimum-sufficient
set of modes selected for that interaction. ``AIReasoningResult`` is the
structured output contract the AI provider must return.

The plan always ends with ``GENERATE`` (the AI produces the final response).
The other modes are added only when deterministic evidence supports them, so a
plan is never a fixed sequence of five calls — it is the smallest set that
fully addresses the interaction.

These models intentionally do not import ``chronos_engine.core.models`` so the
reasoning package stays out of the deferred-import cycle.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ReasoningMode(StrEnum):
    """Reasoning modes ChronOS can engage for one DEEP interaction."""

    CLASSIFY = "CLASSIFY"
    INTERPRET = "INTERPRET"
    REASON = "REASON"
    REFLECT = "REFLECT"
    GENERATE = "GENERATE"


class ReasoningPlan(BaseModel):
    """The deterministic, minimum-sufficient plan for one AI call."""

    modes: list[ReasoningMode]
    primary_mode: ReasoningMode
    reason: str
    confidence: float
    requires_history: bool = False
    requires_context: bool = False


class AIReasoningResult(BaseModel):
    """Structured AI output contract for the DEEP path.

    Only ``answer`` is required. The mode-specific fields are optional and are
    populated only for the modes the plan engaged.
    """

    interpretation: str | None = None
    reasoning: str | None = None
    reflection: str | None = None
    answer: str
    uncertainties: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)
