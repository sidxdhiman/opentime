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
    """

    id: str = Field(default_factory=lambda: f"tevent_{_short_uuid()}")
    thread_id: Optional[str] = None
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
