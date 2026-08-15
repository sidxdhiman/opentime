"""Structured deterministic response models for the ChronOS Engine.

``DeterministicResponse`` is the AI-free interpretation ChronOS can produce
from a ``ChronosState`` alone. It is built by the ``ResponseGenerator`` with
pure templates and rules — no LLM, no network, no retrieval.

The operational state reuses ``EngineStateResult`` (status / confidence /
reason) from ``chronos_engine.state.models`` rather than duplicating it.

These models intentionally do not import ``chronos_engine.core.models``:
``core.models`` defers its own cross-package imports to the end of the module,
so response models stay out of that cycle.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from chronos_engine.state.models import EngineStateResult


class ChronosInterpretation(BaseModel):
    """Cautious, evidence-only interpretation of one user interaction.

    Every field is derived from information actually present in
    ``ChronosState``. Missing evidence yields ``None`` / a neutral phrase,
    never a fabricated claim about the user.
    """

    user_state_summary: str
    intent_summary: str
    goal_summary: Optional[str] = None
    context_summary: str
    pattern_summary: Optional[str] = None
    consistency_summary: Optional[str] = None


class DeterministicResponse(BaseModel):
    """Complete deterministic interpretation of a ``ChronosState``.

    ``rendered`` holds a human-readable natural-language rendering of the
    whole response; the structured fields carry the same information so
    callers can surface individual sections without parsing text.
    """

    user_signal: str
    chronos_interpretation: ChronosInterpretation
    observations: List[str] = Field(default_factory=list)
    chronos_state: EngineStateResult
    suggested_next_step: Optional[str] = None
    rendered: str
