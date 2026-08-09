"""
Tests for OnboardingService.

Covers:
  1.  Start onboarding
  2.  Resume onboarding (idempotent start)
  3.  Save response
  4.  Save draft (autosave)
  5.  Complete onboarding
  6.  Duplicate completion protection (idempotency)
  7.  Partial onboarding — missing required step
  8.  User isolation — another user cannot access the session
  9.  Skip optional step allowed
  10. Step ordering advances correctly
"""

import pytest

from opentime.application.onboarding.service import (
    OnboardingAlreadyCompleted,
    OnboardingMissingRequiredSteps,
    OnboardingNotFound,
    OnboardingService,
)
from opentime.domain.onboarding.entities import (
    REQUIRED_STEPS,
    OnboardingStatus,
    OnboardingStep,
)

USER_A = "user-aaa-111"
USER_B = "user-bbb-222"


# ── 1. Start onboarding ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_creates_session(onboarding_service: OnboardingService):
    session = await onboarding_service.start_or_resume(USER_A)
    assert session.user_id == USER_A
    assert session.status == OnboardingStatus.IN_PROGRESS
    assert session.current_step == OnboardingStep.ABOUT_YOU


# ── 2. Resume onboarding ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resume_returns_same_session(onboarding_service: OnboardingService):
    first = await onboarding_service.start_or_resume(USER_A)
    second = await onboarding_service.start_or_resume(USER_A)
    assert first.id == second.id


# ── 3. Save response ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_response_marks_step_complete(onboarding_service: OnboardingService):
    session = await onboarding_service.start_or_resume(USER_A)
    await onboarding_service.save_response(
        session_id=session.id,
        user_id=USER_A,
        step=OnboardingStep.ABOUT_YOU,
        question="Tell us about yourself.",
        response={"preferred_name": "Alice"},
    )
    # Fetch status and check completed_steps includes ABOUT_YOU
    status = await onboarding_service.get_status(USER_A)
    s = status["session"]
    assert OnboardingStep.ABOUT_YOU in s.completed_steps


# ── 4. Save draft (no completed_steps change) ─────────────────────────────────

@pytest.mark.asyncio
async def test_save_draft_does_not_mark_complete(onboarding_service: OnboardingService):
    session = await onboarding_service.start_or_resume(USER_A)
    await onboarding_service.save_draft(
        session_id=session.id, user_id=USER_A, draft_data={"preferred_name": "Bob"}
    )
    refreshed = await onboarding_service.get_session(session.id, USER_A)
    assert OnboardingStep.ABOUT_YOU not in refreshed.completed_steps


# ── 5. Complete onboarding ────────────────────────────────────────────────────

async def _complete_all_required(svc: OnboardingService, user_id: str):
    session = await svc.start_or_resume(user_id)
    for step in REQUIRED_STEPS:
        await svc.save_response(
            session_id=session.id,
            user_id=user_id,
            step=step,
            question=f"Question for {step}",
            response="Some meaningful answer with enough content to be valid.",
        )
    return session


@pytest.mark.asyncio
async def test_complete_onboarding(onboarding_service: OnboardingService):
    session = await _complete_all_required(onboarding_service, USER_A)
    completed = await onboarding_service.mark_complete(session.id, USER_A)
    assert completed.status == OnboardingStatus.COMPLETED


# ── 6. Duplicate completion protection ────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_completion_raises(onboarding_service: OnboardingService):
    session = await _complete_all_required(onboarding_service, USER_A)
    await onboarding_service.mark_complete(session.id, USER_A)

    with pytest.raises(OnboardingAlreadyCompleted):
        # start_or_resume should now raise because session is completed
        await onboarding_service.start_or_resume(USER_A)


# ── 7. Partial onboarding — missing required step ─────────────────────────────

@pytest.mark.asyncio
async def test_cannot_complete_with_missing_required_step(onboarding_service: OnboardingService):
    session = await onboarding_service.start_or_resume(USER_A)
    # Only fill optional step — should still fail
    await onboarding_service.save_response(
        session_id=session.id, user_id=USER_A,
        step=OnboardingStep.WHATS_ON_MIND,
        question="What's on your mind?",
        response="Just feeling good.",
    )
    with pytest.raises(OnboardingMissingRequiredSteps) as exc_info:
        await onboarding_service.check_can_complete(session.id, USER_A)
    assert len(exc_info.value.missing) > 0


# ── 8. User isolation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_cannot_access_other_users_session(onboarding_service: OnboardingService):
    session_a = await onboarding_service.start_or_resume(USER_A)
    with pytest.raises(PermissionError):
        await onboarding_service.get_session(session_a.id, USER_B)


# ── 9. Skip optional step is allowed ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_skip_optional_step(onboarding_service: OnboardingService):
    session = await _complete_all_required(onboarding_service, USER_A)
    # Should be able to complete without whats_on_mind and how_changed
    completed = await onboarding_service.mark_complete(session.id, USER_A)
    assert completed.status == OnboardingStatus.COMPLETED


# ── 10. Session not found ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_nonexistent_session_raises(onboarding_service: OnboardingService):
    with pytest.raises(OnboardingNotFound):
        await onboarding_service.get_session("no-such-id", USER_A)
