"""
Domain entities for the Chronos state machine.

These represent the structured output of Chronos initialisation and are
stored in MongoDB.  All inferences are tagged with a confidence score and
claim type so users / Chronos itself can distinguish fact from inference.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Claim provenance taxonomy
# ---------------------------------------------------------------------------


class ClaimType(str, Enum):
    FACT = "fact"                   # Explicitly stated and verifiable
    USER_STATEMENT = "user_statement"  # User said it – taken at face value
    INFERENCE = "inference"         # Derived from evidence
    HYPOTHESIS = "hypothesis"       # Tentative – low confidence


# ---------------------------------------------------------------------------
# Typed claim wrapper – wraps every inferred attribute
# ---------------------------------------------------------------------------


class TypedClaim(BaseModel):
    value: Any
    claim_type: ClaimType
    confidence: float = Field(ge=0.0, le=1.0)
    source_memory_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Memory entity
# ---------------------------------------------------------------------------


class ContentType(str, Enum):
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"


class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    content: str                        # Textual content or transcript
    content_type: ContentType = ContentType.TEXT
    source: str = "onboarding"          # "onboarding" | "genesis" | "manual" | ...
    source_reference: str | None = None  # session_id or response_id
    event_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # LLM-extracted metadata
    summary: str | None = None
    topics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    emotions: list[TypedClaim] = Field(default_factory=list)  # typed because inferred
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    # Semantic retrieval
    embedding: list[float] = Field(default_factory=list)

    # Extracted claims
    extracted_facts: list[TypedClaim] = Field(default_factory=list)

    # Links
    linked_memory_ids: list[str] = Field(default_factory=list)

    # Genesis-specific flag
    is_genesis: bool = False
    media_url: str | None = None


# ---------------------------------------------------------------------------
# Identity state (versioned snapshots)
# ---------------------------------------------------------------------------


class IdentityTrait(BaseModel):
    trait: str
    claim_type: ClaimType
    confidence: float = Field(ge=0.0, le=1.0)
    source_memory_id: str | None = None


class IdentityState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    version: int = 1
    traits: list[IdentityTrait] = Field(default_factory=list)
    interests: list[TypedClaim] = Field(default_factory=list)
    values: list[TypedClaim] = Field(default_factory=list)
    self_perception: list[TypedClaim] = Field(default_factory=list)
    current_phase: TypedClaim | None = None   # e.g. "student", "early career"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime | None = None       # null = currently active


# ---------------------------------------------------------------------------
# Goal entity
# ---------------------------------------------------------------------------


class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    title: str
    description: str | None = None
    category: str = "other"
    importance: float = Field(default=0.7, ge=0.0, le=1.0)
    status: GoalStatus = GoalStatus.ACTIVE
    source: str = "onboarding"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_memory_id: str | None = None


# ---------------------------------------------------------------------------
# Timeline event
# ---------------------------------------------------------------------------


class TimelineEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    event_time: datetime
    title: str
    description: str
    category: str = "general"
    source_memory_id: str | None = None
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Pattern baseline
# ---------------------------------------------------------------------------


class PatternType(str, Enum):
    BASELINE = "baseline"
    BEHAVIORAL = "behavioral"
    EMOTIONAL = "emotional"
    COGNITIVE = "cognitive"


class Pattern(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    type: PatternType = PatternType.BASELINE
    pattern: str
    confidence: float = Field(default=0.4, ge=0.0, le=1.0)
    evidence_count: int = 1
    source_memory_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Analysis preferences
# ---------------------------------------------------------------------------


class AnalysisPreferenceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    preference: str      # from AnalysisPreference enum value or custom string
    custom_text: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Chronos State – the master snapshot
# ---------------------------------------------------------------------------


class CurrentLifeState(BaseModel):
    phase: TypedClaim | None = None
    priorities: list[TypedClaim] = Field(default_factory=list)
    interests: list[TypedClaim] = Field(default_factory=list)
    concerns: list[TypedClaim] = Field(default_factory=list)
    responsibilities: list[TypedClaim] = Field(default_factory=list)
    projects: list[TypedClaim] = Field(default_factory=list)


class PersonalChange(BaseModel):
    change_type: str
    previous_state: TypedClaim
    current_state: TypedClaim
    approximate_period: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source_memory_id: str | None = None


class ChronosState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    version: int = 1
    identity_state_id: str | None = None      # FK to identity_states
    current_life_state: CurrentLifeState = Field(default_factory=CurrentLifeState)
    goal_ids: list[str] = Field(default_factory=list)
    interest_ids: list[str] = Field(default_factory=list)
    concerns: list[TypedClaim] = Field(default_factory=list)
    changes: list[PersonalChange] = Field(default_factory=list)
    analysis_preference_ids: list[str] = Field(default_factory=list)
    genesis_memory_id: str | None = None
    baseline_created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_initialised: bool = False
