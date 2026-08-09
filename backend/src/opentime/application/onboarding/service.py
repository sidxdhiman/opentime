"""
OnboardingService – orchestrates the multi-step onboarding flow.

Responsibilities:
- Create / resume sessions
- Accept and persist raw user responses (append-only)
- Update session step progress
- Guard against duplicate completion
- Delegate post-completion processing to ChronosInitializationService
"""

from __future__ import annotations

import structlog

from opentime.domain.onboarding.entities import (
    OPTIONAL_STEPS,
    REQUIRED_STEPS,
    OnboardingResponse,
    OnboardingSession,
    OnboardingStatus,
    OnboardingStep,
)
from opentime.domain.onboarding.repositories import (
    OnboardingResponseRepository,
    OnboardingSessionRepository,
)

logger = structlog.get_logger()


class OnboardingAlreadyCompleted(Exception):
    pass


class OnboardingNotFound(Exception):
    pass


class OnboardingMissingRequiredSteps(Exception):
    def __init__(self, missing: list[OnboardingStep]) -> None:
        self.missing = missing
        super().__init__(f"Missing required steps: {[s.value for s in missing]}")


class OnboardingService:
    def __init__(
        self,
        session_repo: OnboardingSessionRepository,
        response_repo: OnboardingResponseRepository,
    ) -> None:
        self._sessions = session_repo
        self._responses = response_repo

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def start_or_resume(self, user_id: str) -> OnboardingSession:
        """Return the existing active session or create a new one.
        If a completed session exists, raise OnboardingAlreadyCompleted."""
        completed = await self._sessions.get_completed_for_user(user_id)
        if completed:
            raise OnboardingAlreadyCompleted(
                f"User {user_id} has already completed onboarding."
            )

        active = await self._sessions.get_active_for_user(user_id)
        if active:
            logger.info("onboarding_resumed", user_id=user_id, session_id=active.id)
            return active

        session = OnboardingSession(user_id=user_id)
        await self._sessions.create(session)
        logger.info("onboarding_started", user_id=user_id, session_id=session.id)
        return session

    async def get_status(self, user_id: str) -> dict:
        completed = await self._sessions.get_completed_for_user(user_id)
        active = await self._sessions.get_active_for_user(user_id)
        return {
            "has_active_session": active is not None,
            "has_completed_session": completed is not None,
            "session": active or completed,
        }

    async def get_session(self, session_id: str, user_id: str) -> OnboardingSession:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise OnboardingNotFound(f"Session {session_id} not found.")
        if session.user_id != user_id:
            raise PermissionError("Forbidden")
        return session

    # ------------------------------------------------------------------
    # Response saving
    # ------------------------------------------------------------------

    async def save_response(
        self,
        session_id: str,
        user_id: str,
        step: OnboardingStep,
        question: str,
        response: object,
        media_url: str | None = None,
        is_draft: bool = False,
    ) -> OnboardingResponse:
        session = await self.get_session(session_id, user_id)

        if session.status == OnboardingStatus.COMPLETED:
            raise OnboardingAlreadyCompleted("Session already completed.")

        # Persist the raw response (never overwrite; create a new record)
        record = OnboardingResponse(
            user_id=user_id,
            session_id=session_id,
            step=step,
            question=question,
            response=response,  # type: ignore[arg-type]
            media_url=media_url,
        )
        await self._responses.create(record)

        if not is_draft:
            # Mark step as completed if not already
            completed = list(session.completed_steps)
            if step not in completed:
                completed.append(step)

            # Advance current_step to next uncompleted
            current = _next_step(completed)
            await self._sessions.update_step(
                session_id=session_id,
                current_step=current,
                completed_steps=completed,
            )

        logger.info(
            "onboarding_response_saved",
            user_id=user_id,
            session_id=session_id,
            step=step,
            is_draft=is_draft,
        )
        return record

    async def save_draft(
        self,
        session_id: str,
        user_id: str,
        draft_data: dict,
    ) -> None:
        """Autosave partial step data without creating a full response record."""
        session = await self.get_session(session_id, user_id)
        if session.status == OnboardingStatus.COMPLETED:
            return
        await self._sessions.update_step(
            session_id=session_id,
            current_step=session.current_step,
            completed_steps=session.completed_steps,
            draft_data=draft_data,
        )

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    async def check_can_complete(
        self, session_id: str, user_id: str
    ) -> OnboardingSession:
        session = await self.get_session(session_id, user_id)

        if session.status == OnboardingStatus.COMPLETED:
            raise OnboardingAlreadyCompleted("Already completed.")

        missing = [s for s in REQUIRED_STEPS if s not in session.completed_steps]
        if missing:
            raise OnboardingMissingRequiredSteps(missing)

        return session

    async def get_all_responses(
        self, session_id: str, user_id: str
    ) -> list[OnboardingResponse]:
        await self.get_session(session_id, user_id)  # ownership check
        return await self._responses.get_for_session(session_id)

    async def mark_complete(
        self, session_id: str, user_id: str
    ) -> OnboardingSession:
        session = await self.check_can_complete(session_id, user_id)
        return await self._sessions.mark_complete(session.id)

    async def mark_failed(
        self, session_id: str, user_id: str, reason: str
    ) -> None:
        await self.get_session(session_id, user_id)
        await self._sessions.mark_failed(session_id, reason)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from opentime.domain.onboarding.entities import ONBOARDING_STEP_ORDER  # noqa: E402


def _next_step(completed: list[OnboardingStep]) -> OnboardingStep:
    """Return the first step in the canonical order that is not completed."""
    completed_set = set(completed)
    for step in ONBOARDING_STEP_ORDER:
        if step not in completed_set:
            return step
    # All steps done – stay on last
    return ONBOARDING_STEP_ORDER[-1]
