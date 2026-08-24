"""Temporal Intelligence domain models for the ChronOS Engine.

This module defines the *vocabulary* and *data shapes* for Phase 3A of the
ChronOS Temporal Intelligence architecture. A ``TemporalThread`` represents a
meaningful topic or story that can span multiple moments in a user's life
("Past Self" ↔ "Present Self"); each connected moment is a ``TemporalEvent``
anchored to an existing engine memory; a ``TemporalSnapshot`` captures what
the user's world looked like at one point in time.

Phase 3A scope: data models only.

- No detection logic (Phase 3B)
- No thread matching (Phase 3C)
- No resolution / comparison / conversation layers (Phase 3D+)
- Nothing here is created automatically by the engine yet

A TemporalThread is NOT a replacement for Memory. Memory answers "what
happened?"; a TemporalThread will eventually answer "how are multiple
moments connected across time?". Threads only reference existing memory IDs.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _short_uuid() -> str:
    return uuid4().hex[:12]


class TemporalType(str, Enum):
    """Categories of meaningful temporal information.

    These values define the domain vocabulary only. No detector assigns them
    in Phase 3A; classification arrives with Temporal Event Detection.
    """

    FUTURE_EXPECTATION = "FUTURE_EXPECTATION"
    DECISION = "DECISION"
    GOAL = "GOAL"
    FEAR = "FEAR"
    PREDICTION = "PREDICTION"
    QUESTION = "QUESTION"
    PROMISE = "PROMISE"
    LIFE_EVENT = "LIFE_EVENT"
    BELIEF = "BELIEF"
    MILESTONE = "MILESTONE"


class TemporalThreadStatus(str, Enum):
    """Lifecycle states of a TemporalThread.

    Domain states only — no transition logic exists in Phase 3A. A thread is
    born OPEN; how it moves between statuses is decided by later phases.
    """

    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    ABANDONED = "ABANDONED"
    CHANGED = "CHANGED"
    ARCHIVED = "ARCHIVED"


class TemporalThread(BaseModel):
    """A meaningful topic/story that can span multiple moments over time.

    Example shape (IDs are never auto-populated in Phase 3A)::

        TemporalThread(
            origin_memory_id="mem_001",
            related_memory_ids=["mem_001", "mem_145", "mem_290"],
        )

    All memory references are plain strings pointing at existing
    ``MemoryItem.id`` values; threads hold no copies of memory content.
    """

    id: str = Field(default_factory=lambda: f"thread_{_short_uuid()}")
    user_id: str
    temporal_type: Optional[TemporalType] = None
    subject: str = ""
    description: Optional[str] = None
    status: TemporalThreadStatus = TemporalThreadStatus.OPEN
    origin_memory_id: Optional[str] = None
    related_memory_ids: List[str] = Field(default_factory=list)
    importance: float = 0.5
    confidence: float = 0.5
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class TemporalEvent(BaseModel):
    """One meaningful moment within a TemporalThread.

    An event anchors to at most one existing engine memory via
    ``memory_id``. Detection and automatic persistence do not exist in
    Phase 3A; events are pure representations.

    ``thread_id`` is ``None`` until thread matching assigns the event to a
    thread (a later temporal phase). Detected-but-unmatched events keep it
    empty rather than fabricating a thread reference.

    ``user_id`` is optional with a safe default so older documents and
    detector-produced events remain valid; the lifecycle manager sets it
    when an event is persisted so stores can enforce user isolation.
    """

    id: str = Field(default_factory=lambda: f"tevent_{_short_uuid()}")
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    temporal_type: Optional[TemporalType] = None
    description: str = ""
    memory_id: Optional[str] = None
    occurred_at: datetime = Field(default_factory=_utcnow)
    recorded_at: datetime = Field(default_factory=_utcnow)
    importance: float = 0.5
    confidence: float = 0.5


class TemporalEventDetectionResult(BaseModel):
    """Structured output of deterministic temporal event detection.

    Kept separate from ``TemporalEvent`` so the event stays a clean domain
    representation while detector metadata lives here. When evidence is
    insufficient, ``detected`` is ``False`` and ``event`` is ``None`` — an
    event is never fabricated.

    ``confidence`` is a deterministic, evidence-weighted score in ``[0, 1]``
    derived from matched signals and existing ChronOS detector outputs. It
    reflects evidence strength, not a calibrated AI probability.
    """

    detected: bool = False
    event: Optional[TemporalEvent] = None
    confidence: float = 0.0
    reason: str = ""
    signals: List[str] = Field(default_factory=list)


class TemporalThreadMatchResult(BaseModel):
    """Structured output of deterministic TemporalThread matching (Phase 3C).

    Answers one question for a newly detected ``TemporalEvent``: does it
    belong to an existing thread? A false connection is worse than no
    connection, so the result is conservative:

    - no current event            -> ``attempted=False``, ``matched=False``
    - no candidate threads        -> ``attempted=True``,  ``matched=False``
    - candidates below threshold  -> ``matched=False`` (never force a match)
    - several plausible threads   -> ``ambiguous=True``, ``matched=False``

    ``confidence`` mirrors the winning candidate's deterministic score; it is
    an explainable evidence-weighted value in ``[0, 1]``, not a statistically
    calibrated probability.

    When matched, the event's ``thread_id`` may be populated *in memory* by
    the caller; this model never persists anything and never creates threads.
    """

    attempted: bool = False
    matched: bool = False
    thread_id: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""
    signals: List[str] = Field(default_factory=list)
    ambiguous: bool = False
    candidate_count: int = 0
    matched_thread: Optional[TemporalThread] = None


class TemporalLifecycleResult(BaseModel):
    """Structured, honest output of the temporal lifecycle manager (Phase 3D).

    Answers one question per interaction: did a detected ``TemporalEvent``
    create a new thread, continue an existing one, or leave everything
    untouched — and was it actually persisted? The result never overstates
    success:

    - no temporal event        -> ``attempted=False``, ``skipped=True``
    - ambiguous match          -> ``attempted=True`` with no mutation made
    - new thread               -> ``created=True`` (plus event persisted)
    - confident continuation   -> ``updated=True``
    - storage failure          -> ``persisted=False`` with the failure reason

    ``previous_status`` / ``current_status`` / ``transitioned`` describe any
    lifecycle status change applied to the thread. ``confidence`` is an
    explainable evidence-weighted score in ``[0, 1]``, not a calibrated
    probability.
    """

    attempted: bool = False
    created: bool = False
    updated: bool = False
    persisted: bool = False
    thread_id: Optional[str] = None
    event_id: Optional[str] = None
    thread_subject: Optional[str] = None
    previous_status: Optional[TemporalThreadStatus] = None
    current_status: Optional[TemporalThreadStatus] = None
    transitioned: bool = False
    reason: str = ""
    confidence: float = 0.0
    signals: List[str] = Field(default_factory=list)
    ambiguous: bool = False
    skipped: bool = False


class TemporalComparisonRelation(str, Enum):
    """Deterministic verdict of a Past-vs-Present thread comparison (Phase 3E).

    Describes how the newest moment in a ``TemporalThread`` relates to where
    that story began. The vocabulary is intentionally small and honest:

    - UNRESOLVED              the story is still open; nothing conclusive
    - CONFIRMED               present restates/reaffirms the past position
    - CHANGED                 present moved away from the past direction
    - RESOLVED                the story reached an explicit outcome
    - EVOLVED                 present shows ongoing development without closure
    - CONTRADICTED            present actively conflicts with the past stance
    - INSUFFICIENT_EVIDENCE   not enough distinct grounded moments to compare

    These are explainable rule outcomes over stored evidence, never claims of
    psychological truth about the user.
    """

    UNRESOLVED = "UNRESOLVED"
    CONFIRMED = "CONFIRMED"
    CHANGED = "CHANGED"
    RESOLVED = "RESOLVED"
    EVOLVED = "EVOLVED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class TemporalComparisonResult(BaseModel):
    """Structured, read-only output of a Past-vs-Present comparison (Phase 3E).

    Answers one question per interaction: for the temporal thread this input
    touched, how does the present moment compare to where the story began?
    The comparison is strictly observational — it never mutates threads or
    events and never persists anything.

    Honesty contract:

    - no thread touched this turn -> ``attempted=False``
    - fewer than two distinct grounded moments
      -> ``comparable=False``, relation ``INSUFFICIENT_EVIDENCE``
    - a relation is only claimed when deterministic evidence supports it;
      otherwise ``UNRESOLVED`` / ``INSUFFICIENT_EVIDENCE`` is returned

    ``past_summary`` / ``present_summary`` are conservative templates quoting
    the stored evidence (by ``TemporalType``); they never invent content.
    ``evidence_event_ids`` / ``evidence_memory_ids`` expose exactly which
    stored artifacts back the verdict (deduplicated). ``confidence`` is an
    explainable evidence-weighted score capped below ``1.0`` — not a
    calibrated probability.
    """

    attempted: bool = False
    comparable: bool = False
    relation: TemporalComparisonRelation = TemporalComparisonRelation.INSUFFICIENT_EVIDENCE
    confidence: float = 0.0
    thread_id: Optional[str] = None
    past_event_id: Optional[str] = None
    present_event_id: Optional[str] = None
    past_summary: str = ""
    present_summary: str = ""
    evidence_memory_ids: List[str] = Field(default_factory=list)
    evidence_event_ids: List[str] = Field(default_factory=list)
    signals: List[str] = Field(default_factory=list)
    reason: str = ""


class PastSelfPerspective(str, Enum):
    """Structured interaction perspective for past-self questions (Phase 3F).

    Marks whose voice a planned question conceptually reconnects. The only
    producer in this phase is ``PAST_TO_PRESENT``: the question is framed as
    the user's earlier self reaching their present self. This is a structured
    label for the future rendering layer — Phase 3F never simulates a
    personality and never pretends to literally BE the past user.
    """

    PAST_TO_PRESENT = "PAST_TO_PRESENT"


class PastSelfQuestionType(str, Enum):
    """The kind of past-self interaction the planner decided is appropriate.

    Deterministic rule outcomes over stored temporal evidence, not claims
    about what the user feels:

    - CHECK_IN         ongoing story; ask how it is going now
    - OUTCOME_REVEAL   an outcome arrived; invite the present self to react
    - REFLECTION       something shifted; invite looking back on it
    - REVISIT          still open with real continuity; worth revisiting
    - REASSURANCE      a stance held; acknowledge it endured
    - SURPRISE         reserved: no deterministic producer exists yet in
                       Phase 3F (documented, tested absence)
    """

    CHECK_IN = "CHECK_IN"
    OUTCOME_REVEAL = "OUTCOME_REVEAL"
    REFLECTION = "REFLECTION"
    REVISIT = "REVISIT"
    REASSURANCE = "REASSURANCE"
    SURPRISE = "SURPRISE"


class PastSelfQuestionIntent(BaseModel):
    """WHAT ChronOS wants to ask, separated from HOW it may be phrased.

    ``focus`` is the grounded topic of the question (abstract description).
    ``canonical_template`` is a deterministic skeleton containing a literal
    ``{subject}`` placeholder filled by the future rendering layer from the
    evidence-grounded thread subject — never invented content. Neither field
    is a conversational AI sentence; wording/personalization is deferred.
    """

    focus: str = ""
    canonical_template: str = ""
    perspective: PastSelfPerspective = PastSelfPerspective.PAST_TO_PRESENT


class PastSelfQuestionResult(BaseModel):
    """Structured decision of the Past-Self Question Planner (Phase 3F).

    Answers one question per interaction: should ChronOS ask the present
    user something on behalf of their past self about this temporal thread?
    The planner is deterministic, read-only and conservative — a comparison
    existing does NOT automatically justify a question.

    Honesty contract:

    - no temporal thread touched     -> ``attempted=False``
    - comparison insufficient/weak,
      single-moment history,
      ambiguous relationship         -> ``should_ask=False``, no fabricated
                                        question type or intent

    Evidence fields reference ONLY artifacts already stored by earlier
    phases (mirroring the comparison's deduplicated ids). ``confidence`` is
    an explainable evidence-weighted score capped below ``1.0``.
    """

    attempted: bool = False
    should_ask: bool = False
    question_type: Optional[PastSelfQuestionType] = None
    reason: str = ""
    confidence: float = 0.0
    thread_id: Optional[str] = None
    comparison_relation: Optional[TemporalComparisonRelation] = None
    past_event_id: Optional[str] = None
    present_event_id: Optional[str] = None
    supporting_memory_ids: List[str] = Field(default_factory=list)
    supporting_event_ids: List[str] = Field(default_factory=list)
    intent: Optional[PastSelfQuestionIntent] = None
    signals: List[str] = Field(default_factory=list)


class TemporalRelevanceDecision(str, Enum):
    """Deterministic verdict of the Temporal Relevance & Timing engine
    (Phase 3G).

    Answers ONE question about an already-planned past-self question: is
    NOW the right moment to surface it? The vocabulary is deliberately
    small and honest:

    - SURFACE_NOW    relevant to this conversation AND the moment is
                     contextually appropriate.
    - DEFER          the question is meaningful, but the current moment is
                     not appropriate ("not now" — a decision only; DEFER
                     never schedules, persists or resurfaces anything).
    - SKIP           no valid planned question, no meaningful topical
                     relation, or evidence too weak/ambiguous to ground a
                     confident surface decision.

    These are explainable rule outcomes over handed-in evidence, never
    claims about what the user feels or wants.
    """

    SURFACE_NOW = "SURFACE_NOW"
    DEFER = "DEFER"
    SKIP = "SKIP"


class TemporalRelevanceResult(BaseModel):
    """Structured, read-only output of temporal relevance & timing (Phase 3G).

    Consumes the already-computed Phase 3F ``PastSelfQuestionResult`` plus
    the current interaction evidence and produces one structured decision:
    whether the planned past-self question should be surfaced NOW, deferred,
    or skipped. The engine never overrides Phase 3F — a planned question is
    required input, never invented here.

    Honesty contract:

    - no valid planned past-self question -> ``should_surface=False``,
      ``decision=SKIP`` (never fabricated)
    - every score contribution appears as an explainable line in
      ``signals`` (positive) or ``blocking_signals`` (negative); there is
      no hidden scoring

    ``relevance_score`` / ``timing_score`` are deterministic,
    evidence-weighted values in ``[0, 0.95]``; ``confidence`` is an
    explainable blend capped below ``1.0`` — not a calibrated probability.
    Strictly read-only: nothing is mutated, persisted, scheduled or shown.
    """

    attempted: bool = False
    decision: TemporalRelevanceDecision = TemporalRelevanceDecision.SKIP
    should_surface: bool = False
    reason: str = ""
    confidence: float = 0.0
    relevance_score: float = 0.0
    timing_score: float = 0.0
    thread_id: str | None = None
    question_type: PastSelfQuestionType | None = None
    signals: list[str] = Field(default_factory=list)
    blocking_signals: list[str] = Field(default_factory=list)
    supporting_memory_ids: list[str] = Field(default_factory=list)
    supporting_event_ids: list[str] = Field(default_factory=list)


class PastSelfConversationMoment(BaseModel):
    """A composed, user-facing past-self conversation moment (Phase 3H).

    Turns a valid Phase 3G ``SURFACE_NOW`` permission into deterministic,
    evidence-grounded conversational content: a subtle connection between
    the user's present self and an earlier version of themselves — never a
    simulated persona and never roleplay dialogue.

    Honesty contract:

    - ``should_surface=False`` whenever any hard gate fails (relevance not
      ``SURFACE_NOW``, Phase 3F refusal, missing/ambiguous evidence) and the
      text fields stay empty — an honest empty result instead of fabricated
      content.
    - every rendered line quotes or paraphrases ONLY handed-in evidence
      (thread subject/description, anchored event descriptions, comparison
      summaries); no emotions, motivations, outcomes, durations or history
      are ever invented.
    - internal IDs never appear in user-facing fields; they live only in
      ``evidence_memory_ids`` / ``evidence_event_ids``.

    ``confidence`` is the weaker link of the Phase 3F question and Phase 3G
    relevance confidences (capped below ``1.0``): the surfaced moment can
    never be more confident than its weakest permission.
    """  # noqa: E501

    attempted: bool = False
    should_surface: bool = False
    thread_id: str | None = None
    perspective: PastSelfPerspective = PastSelfPerspective.PAST_TO_PRESENT
    question_type: PastSelfQuestionType | None = None
    relation: TemporalComparisonRelation | None = None
    opening: str = ""
    context: str = ""
    bridge: str = ""
    question: str = ""
    confidence: float = 0.0
    evidence_memory_ids: list[str] = Field(default_factory=list)
    evidence_event_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class TemporalSnapshot(BaseModel):
    """The user's situation as it stood at one point in time.

    Deliberately decoupled from ``ChronosState``: the user state is stored
    as a serializable representation (``user_state`` dict) instead of a
    typed model import, so snapshots never create circular dependencies or
    fragile coupling to the interaction-state schema. Snapshots are never
    created automatically in Phase 3A.
    """

    id: str = Field(default_factory=lambda: f"tsnap_{_short_uuid()}")
    user_id: str
    timestamp: datetime = Field(default_factory=_utcnow)
    context_description: str = ""
    memory_id: Optional[str] = None
    user_state: Optional[Dict[str, Any]] = None
    relevant_goals: List[str] = Field(default_factory=list)
    relevant_beliefs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
