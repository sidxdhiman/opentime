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
from typing import List, Optional

from pydantic import BaseModel, Field

from chronos_engine.core.models import IntentType, PatternItem, RetrievedContext, UserInput
from chronos_engine.temporal.models import (
    PastSelfQuestionResult,
    TemporalComparisonResult,
    TemporalEventDetectionResult,
    TemporalLifecycleResult,
    TemporalThreadMatchResult,
)


class IntentResult(BaseModel):
    """Result of user intent detection.

    Populated by the deterministic ``IntentDetector``. The taxonomy and
    confidence shape follow the ChronOS plan. ``intent`` is ``None`` only
    when no detector ran; a detector always resolves to at least ``UNKNOWN``.
    """

    intent: Optional[IntentType] = None
    confidence: float = 0.0
    signals: List[str] = Field(default_factory=list)


class UserEmotionState(str, Enum):
    """Interaction-language emotion labels inferred by ``UserStateDetector``.

    These describe what the input's *language suggests* about the current
    interaction, never a claim about the user themselves. ``NEUTRAL`` is the
    default when the input does not clearly signal an emotion.
    """

    CALM = "CALM"
    POSITIVE = "POSITIVE"
    EXCITED = "EXCITED"
    CONFIDENT = "CONFIDENT"
    CURIOUS = "CURIOUS"
    NEUTRAL = "NEUTRAL"
    UNCERTAIN = "UNCERTAIN"
    OVERWHELMED = "OVERWHELMED"
    FRUSTRATED = "FRUSTRATED"
    ANXIOUS = "ANXIOUS"
    SAD = "SAD"
    TIRED = "TIRED"
    ANGRY = "ANGRY"
    MOTIVATED = "MOTIVATED"
    FOCUSED = "FOCUSED"
    RELIEVED = "RELIEVED"


class UserEnergy(str, Enum):
    """Coarse interaction-energy levels. ``None`` is used when the input
    carries no energy signal at all (no fabricated energy level)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class UserCognitiveState(str, Enum):
    """Cognitive-interaction signals, kept separate from emotional state."""

    CLEAR = "CLEAR"
    UNCERTAIN = "UNCERTAIN"
    CONFUSED = "CONFUSED"
    FOCUSED = "FOCUSED"
    OVERWHELMED = "OVERWHELMED"
    EXPLORATORY = "EXPLORATORY"
    DECISIVE = "DECISIVE"


class UserStateResult(BaseModel):
    """Inferred interaction-state signals.

    Populated by the deterministic ``UserStateDetector``. These are cautious
    inferences about what the input's language suggests about the current
    interaction state, never claims of fact about the user.

    Every dimension is ``None`` / ``0.0`` / empty when there is not enough
    evidence for it — the detector never fabricates a state.
    """

    emotional_state: Optional[UserEmotionState] = None
    secondary_states: List[UserEmotionState] = Field(default_factory=list)
    confidence: float = 0.0
    signals: List[str] = Field(default_factory=list)
    valence: Optional[float] = None  # -1.0 (negative) .. +1.0 (positive)
    energy: Optional[UserEnergy] = None
    cognitive_state: Optional[UserCognitiveState] = None
    urgency: Optional[float] = None  # 0.0 (none) .. 1.0 (very urgent)
    engagement: Optional[float] = None  # 0.0 (low) .. 1.0 (high)


class GoalStatus(str, Enum):
    """How the current input relates to a goal.

    ``NONE`` means the input does not meaningfully relate to a goal. The other
    values describe a specific relationship to an (existing or new) goal.
    """

    NONE = "NONE"
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    PROGRESS = "PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    BLOCKED = "BLOCKED"
    CHANGED = "CHANGED"


class GoalAnalysisItem(BaseModel):
    """A single goal relationship produced by ``GoalDetector``."""

    status: GoalStatus = GoalStatus.NONE
    goal: str = ""
    matched_existing_goal: Optional[str] = None
    confidence: float = 0.0
    signals: List[str] = Field(default_factory=list)


class GoalAnalysisResult(BaseModel):
    """Goal analysis for one user input.

    ``items`` holds one result per relevant goal (a new goal plus any existing
    goals the input relates to). The top-level fields mirror the strongest
    item (highest confidence) so callers get a flat primary read.
    """

    status: GoalStatus = GoalStatus.NONE
    goal: Optional[str] = None
    matched_existing_goal: Optional[str] = None
    confidence: float = 0.0
    signals: List[str] = Field(default_factory=list)
    items: List[GoalAnalysisItem] = Field(default_factory=list)


class ContradictionResult(BaseModel):
    """A detected difference between the current input and stored context.

    A *change* (e.g. a goal that was abandoned) and a *contradiction* (e.g. a
    stated preference that actively conflicts with a stored one) share this
    shape. The field is not a moral judgment about the user — it describes that
    the current state differs from previously stored state.
    """

    type: Optional[str] = None
    description: Optional[str] = None
    previous_value: Optional[str] = None
    current_value: Optional[str] = None
    confidence: float = 0.0
    supporting_memory_ids: List[str] = Field(default_factory=list)


class ConsistencyResult(BaseModel):
    """Full output of the consistency / continuity check.

    ``contradictions`` holds events that actively conflict with stored context.
    ``changes`` holds evolution events (goal changes, decision changes) which
    are continuity signals rather than conflicts. ``is_consistent`` is True when
    nothing conflicts; a goal *change* alone does not mark the user inconsistent.
    """

    is_consistent: bool = True
    confidence: float = 0.0
    contradictions: List[ContradictionResult] = Field(default_factory=list)
    changes: List[ContradictionResult] = Field(default_factory=list)
    supporting_memory_ids: List[str] = Field(default_factory=list)


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
    goal_analysis: Optional[GoalAnalysisResult] = None

    context: Optional[RetrievedContext] = None

    goals: List[str] = Field(default_factory=list)
    patterns: List[PatternItem] = Field(default_factory=list)
    contradictions: List[ContradictionResult] = Field(default_factory=list)

    temporal_event_detection: Optional[TemporalEventDetectionResult] = None

    temporal_thread_match: Optional[TemporalThreadMatchResult] = None

    # Phase 3D: honest, additive record of what the temporal lifecycle
    # manager did (thread created / event attached / nothing attempted).
    # ``None`` only for states built before lifecycle handling ran.
    temporal_lifecycle: Optional[TemporalLifecycleResult] = None

    # Phase 3E: honest, additive, read-only Past-vs-Present verdict for the
    # thread this interaction touched. ``None`` only for states built before
    # comparison ran; the result itself reports skipped/insufficient honestly.
    temporal_comparison: Optional[TemporalComparisonResult] = None

    # Phase 3F: honest, additive, read-only decision about whether a
    # past-self question is appropriate for this thread (and WHAT it should
    # be about — never the final conversational wording).
    past_self_question: Optional[PastSelfQuestionResult] = None

    engine_state: Optional[EngineStateResult] = None
    confidence: Optional[float] = None
