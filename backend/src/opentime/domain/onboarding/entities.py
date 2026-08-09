"""
Domain entities for the onboarding flow.

These are pure Python dataclasses / Pydantic models that carry no
infrastructure concerns – no Motor, no SQLAlchemy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class OnboardingStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class OnboardingStep(str, Enum):
    ABOUT_YOU = "about_you"           # Step 1
    LIFE_RIGHT_NOW = "life_right_now" # Step 2
    WHATS_ON_MIND = "whats_on_mind"   # Step 3
    WHERE_GOING = "where_going"       # Step 4
    HOW_CHANGED = "how_changed"       # Step 5
    FIRST_MEMORY = "first_memory"     # Step 6
    ANALYSIS_PREFS = "analysis_prefs" # Step 7


# Ordered sequence used for step progression logic
ONBOARDING_STEP_ORDER: list[OnboardingStep] = [
    OnboardingStep.ABOUT_YOU,
    OnboardingStep.LIFE_RIGHT_NOW,
    OnboardingStep.WHATS_ON_MIND,
    OnboardingStep.WHERE_GOING,
    OnboardingStep.HOW_CHANGED,
    OnboardingStep.FIRST_MEMORY,
    OnboardingStep.ANALYSIS_PREFS,
]

# Steps that the user may skip without blocking completion
OPTIONAL_STEPS: set[OnboardingStep] = {
    OnboardingStep.WHATS_ON_MIND,
    OnboardingStep.HOW_CHANGED,
}

# Steps that are strictly required for Chronos initialisation
REQUIRED_STEPS: set[OnboardingStep] = {
    OnboardingStep.ABOUT_YOU,
    OnboardingStep.LIFE_RIGHT_NOW,
    OnboardingStep.WHERE_GOING,
    OnboardingStep.FIRST_MEMORY,
    OnboardingStep.ANALYSIS_PREFS,
}


# ---------------------------------------------------------------------------
# Onboarding Session
# ---------------------------------------------------------------------------


class OnboardingSession(BaseModel):
    """Tracks a single user's onboarding progress.  Stored in MongoDB."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    current_step: OnboardingStep = OnboardingStep.ABOUT_YOU
    completed_steps: list[OnboardingStep] = Field(default_factory=list)
    status: OnboardingStatus = OnboardingStatus.IN_PROGRESS
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    # Loose key-value store for transient autosave data (not final responses)
    draft_data: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return self.status == OnboardingStatus.COMPLETED

    @property
    def required_remaining(self) -> list[OnboardingStep]:
        return [s for s in REQUIRED_STEPS if s not in self.completed_steps]

    def can_complete(self) -> bool:
        return len(self.required_remaining) == 0


# ---------------------------------------------------------------------------
# Onboarding Response – raw user input, never overwritten
# ---------------------------------------------------------------------------


class OnboardingResponse(BaseModel):
    """A single raw answer to one onboarding step.  Immutable once created."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    session_id: str
    step: OnboardingStep
    question: str
    response: str | dict[str, Any] | list[Any]   # text, structured, or list (e.g. prefs)
    media_url: str | None = None      # if audio/video genesis memory
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Responses are append-only; a new record is written on re-submission
    version: int = 1


# ---------------------------------------------------------------------------
# Step 1 – About You  (structured payload stored alongside raw response)
# ---------------------------------------------------------------------------


class AboutYouData(BaseModel):
    preferred_name: str | None = None
    age_range: str | None = None           # e.g. "25-30", "30s"
    country: str | None = None
    city_region: str | None = None
    timezone: str | None = None            # IANA timezone string
    occupation: str | None = None
    preferred_language: str = "en"


# ---------------------------------------------------------------------------
# Step 4 – Goals
# ---------------------------------------------------------------------------


class GoalCategory(str, Enum):
    CAREER = "career"
    EDUCATION = "education"
    HEALTH = "health"
    RELATIONSHIPS = "relationships"
    FINANCE = "finance"
    CREATIVITY = "creativity"
    PERSONAL_GROWTH = "personal_growth"
    LIFESTYLE = "lifestyle"
    OTHER = "other"


class GoalInput(BaseModel):
    title: str
    description: str | None = None
    category: GoalCategory = GoalCategory.OTHER
    importance: float = Field(default=0.7, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Step 7 – Analysis Preferences
# ---------------------------------------------------------------------------


class AnalysisPreference(str, Enum):
    HOW_I_CHANGED = "how_i_changed"
    HABITS_PATTERNS = "habits_patterns"
    GOALS_PROGRESS = "goals_progress"
    THOUGHTS_BELIEFS = "thoughts_beliefs"
    RELATIONSHIPS = "relationships"
    CAREER = "career"
    EMOTIONAL_PATTERNS = "emotional_patterns"
    THINGS_I_FORGET = "things_i_forget"
    CUSTOM = "custom"
