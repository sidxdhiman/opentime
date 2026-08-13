"""Structured state representation for the ChronOS Engine.

``ChronosState`` is the central object that will eventually hold everything
ChronOS understands about a single user interaction. It is built by the
``StateBuilder`` right after retrieval and flows through the rest of the
pipeline unchanged.

At this stage only the sections that already have data today are populated.
The intent / user-state / engine-state / contradiction detectors do not exist
yet, so those sections default to empty values instead of fabricated ones.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from chronos_engine.core.models import IntentType, PatternItem, RetrievedContext, UserInput


class IntentResult(BaseModel):
    """Result of user intent detection.

    Populated by the deterministic ``IntentDetector``. The taxonomy and
    confidence shape follow the ChronOS plan. ``intent`` is ``None`` only
    when no detector ran; a detector always resolves to at least ``UNKNOWN``.
    """

    intent: Optional[IntentType] = None
    confidence: float = 0.0
    signals: List[str] = Field(default_factory=list)


class UserStateResult(BaseModel):
    """Inferred interaction-state signals.

    Populated by a future ``UserStateDetector``. These are cautious inferences
    about the interaction, never claims of fact about the user.
    """

    emotional_state: Optional[Dict[str, Any]] = None
    energy: Optional[Dict[str, Any]] = None
    cognitive_state: Optional[Dict[str, Any]] = None
    urgency: Optional[float] = None
    engagement: Optional[float] = None


class ContradictionResult(BaseModel):
    """A detected contradiction between the current input and stored context."""

    type: Optional[str] = None
    previous: Optional[str] = None
    current: Optional[str] = None
    confidence: float = 0.0


class EngineStatus(str, Enum):
    """Operational state of the engine.

    These are operational states describing the engine's assessment, not
    claims of consciousness.
    """

    NEUTRAL = "NEUTRAL"
    CURIOUS = "CURIOUS"
    CONFIDENT = "CONFIDENT"
    CAUTIOUS = "CAUTIOUS"
    CONCERNED = "CONCERNED"
    UNCERTAIN = "UNCERTAIN"
    ALERT = "ALERT"
    POSITIVE = "POSITIVE"
    FOCUSED = "FOCUSED"
    WAITING_FOR_CONTEXT = "WAITING_FOR_CONTEXT"


class EngineStateResult(BaseModel):
    """The engine's own operational assessment of the interaction."""

    status: EngineStatus = EngineStatus.NEUTRAL
    confidence: float = 0.0
    reason: Optional[str] = None


class ChronosState(BaseModel):
    """Everything ChronOS currently understands about one user interaction.

    Intentionally minimal: sections whose detectors do not exist yet stay
    empty (``None`` / ``[]``). The ``StateBuilder`` populates the sections
    that already have data today (current input, retrieved context, goals,
    patterns, timeline/life phase).
    """

    id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    current_input: UserInput

    intent: Optional[IntentResult] = None
    user_state: Optional[UserStateResult] = None

    context: Optional[RetrievedContext] = None

    goals: List[str] = Field(default_factory=list)
    patterns: List[PatternItem] = Field(default_factory=list)
    contradictions: List[ContradictionResult] = Field(default_factory=list)

    engine_state: Optional[EngineStateResult] = None
    confidence: Optional[float] = None
