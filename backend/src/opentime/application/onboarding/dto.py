"""DTOs (Data Transfer Objects) for the onboarding API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from opentime.domain.onboarding.entities import (
    AboutYouData,
    AnalysisPreference,
    GoalCategory,
    GoalInput,
    OnboardingStatus,
    OnboardingStep,
)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class StartOnboardingRequest(BaseModel):
    """Body for POST /onboarding/start.  Empty – session is created server-side."""
    pass


class SaveResponseRequest(BaseModel):
    """Generic onboarding step response.  The `response` field is free-form."""
    step: OnboardingStep
    response: str | dict[str, Any] | list[Any]
    question: str
    media_url: str | None = None
    # Optional autosave flag – if True, response is stored as draft only
    is_draft: bool = False


class SaveAboutYouRequest(BaseModel):
    preferred_name: str | None = None
    age_range: str | None = None
    country: str | None = None
    city_region: str | None = None
    timezone: str | None = None
    occupation: str | None = None
    preferred_language: str = "en"


class SaveGoalsRequest(BaseModel):
    goals: list[GoalInput] = Field(min_length=1)


class SaveAnalysisPrefsRequest(BaseModel):
    preferences: list[AnalysisPreference | str]   # allow custom strings
    custom_text: str | None = None


class CompleteOnboardingRequest(BaseModel):
    """Trigger Chronos initialization after all required steps are done."""
    pass


class ResumeOnboardingRequest(BaseModel):
    """Client asks whether an active session exists to resume."""
    pass


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class OnboardingSessionResponse(BaseModel):
    session_id: str
    user_id: str
    status: OnboardingStatus
    current_step: OnboardingStep
    completed_steps: list[OnboardingStep]
    started_at: datetime
    completed_at: datetime | None


class OnboardingStatusResponse(BaseModel):
    has_active_session: bool
    has_completed_session: bool
    session: OnboardingSessionResponse | None = None


class StepSavedResponse(BaseModel):
    session_id: str
    step: OnboardingStep
    saved: bool = True
    message: str = "Response saved."


class CompleteOnboardingResponse(BaseModel):
    session_id: str
    status: OnboardingStatus
    chronos_initialised: bool
    message: str
