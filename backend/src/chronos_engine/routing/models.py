"""Structured AI-routing models for the ChronOS Engine.

``AIRoutingResult`` is the output of the deterministic ``AIRouter``. It
classifies whether the current ``ChronosState`` can be handled by the
deterministic engine (``FAST``) or whether deeper AI reasoning would be
materially useful (``DEEP``).

The router itself never calls an LLM: it only records a decision.

These models intentionally do not import ``chronos_engine.core.models`` so
they stay out of the deferred-import cycle (see ``response.models``).
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class RoutingPath(str, Enum):
    """Which processing path is sufficient for the current interaction.

    ``FAST`` — the deterministic engine can adequately process the state.
    ``DEEP`` — an AI model would materially improve the result.
    """

    FAST = "FAST"
    DEEP = "DEEP"


class AIRoutingResult(BaseModel):
    """Deterministic routing decision for one user interaction."""

    use_ai: bool
    path: RoutingPath
    confidence: float
    reason: str
    signals: List[str] = Field(default_factory=list)
