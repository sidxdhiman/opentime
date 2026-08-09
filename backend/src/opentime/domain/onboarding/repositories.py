"""Repository interfaces for the onboarding domain.

These are abstract base classes only – no infrastructure code lives here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from opentime.domain.onboarding.entities import (
    OnboardingResponse,
    OnboardingSession,
    OnboardingStatus,
    OnboardingStep,
)


class OnboardingSessionRepository(ABC):
    @abstractmethod
    async def create(self, session: OnboardingSession) -> OnboardingSession: ...

    @abstractmethod
    async def get_by_id(self, session_id: str) -> OnboardingSession | None: ...

    @abstractmethod
    async def get_active_for_user(self, user_id: str) -> OnboardingSession | None:
        """Return the most recent IN_PROGRESS session for a user."""
        ...

    @abstractmethod
    async def get_completed_for_user(self, user_id: str) -> OnboardingSession | None:
        """Return the completed session for a user if one exists."""
        ...

    @abstractmethod
    async def update(self, session: OnboardingSession) -> OnboardingSession: ...

    @abstractmethod
    async def update_step(
        self,
        session_id: str,
        current_step: OnboardingStep,
        completed_steps: list[OnboardingStep],
        draft_data: dict | None = None,
    ) -> OnboardingSession: ...

    @abstractmethod
    async def mark_complete(self, session_id: str) -> OnboardingSession: ...

    @abstractmethod
    async def mark_failed(self, session_id: str, reason: str) -> None: ...


class OnboardingResponseRepository(ABC):
    @abstractmethod
    async def create(self, response: OnboardingResponse) -> OnboardingResponse: ...

    @abstractmethod
    async def get_by_id(self, response_id: str) -> OnboardingResponse | None: ...

    @abstractmethod
    async def get_for_session(self, session_id: str) -> list[OnboardingResponse]:
        """All responses for a session, ordered by step."""
        ...

    @abstractmethod
    async def get_for_step(
        self, user_id: str, session_id: str, step: OnboardingStep
    ) -> OnboardingResponse | None:
        """Latest response for a specific step within a session."""
        ...

    @abstractmethod
    async def get_all_for_user(self, user_id: str) -> list[OnboardingResponse]:
        """All responses a user has ever submitted (historical)."""
        ...
