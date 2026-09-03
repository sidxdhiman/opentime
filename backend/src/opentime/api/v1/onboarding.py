"""
Onboarding API endpoints.

All endpoints require a valid JWT – the user_id is taken from the token,
never from the request body, preventing user impersonation.

Routes:
  POST  /onboarding/start                      → start or resume
  GET   /onboarding/status                     → check current status
  POST  /onboarding/{session_id}/response      → save a step response
  POST  /onboarding/{session_id}/draft         → autosave draft
  POST  /onboarding/{session_id}/complete      → trigger Chronos init
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from chronos_engine.telemetry import record_event as record_product_event
from opentime.api.dependencies import get_current_user
from opentime.api.onboarding_deps import (
    get_chronos_init_service,
    get_onboarding_service,
)
from opentime.application.auth.dto import UserResponse
from opentime.application.onboarding.dto import (
    CompleteOnboardingResponse,
    OnboardingSessionResponse,
    OnboardingStatusResponse,
    SaveResponseRequest,
    StepSavedResponse,
)
from opentime.application.onboarding.init_service import (
    ChronosAlreadyInitialized,
    ChronosInitializationService,
)
from opentime.application.onboarding.service import (
    OnboardingAlreadyCompleted,
    OnboardingMissingRequiredSteps,
    OnboardingNotFound,
    OnboardingService,
)
from opentime.domain.onboarding.entities import OnboardingStatus

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


def _session_to_response(s) -> OnboardingSessionResponse:
    return OnboardingSessionResponse(
        session_id=s.id,
        user_id=s.user_id,
        status=s.status,
        current_step=s.current_step,
        completed_steps=s.completed_steps,
        started_at=s.started_at,
        completed_at=s.completed_at,
    )


# ---------------------------------------------------------------------------
# Start / Resume
# ---------------------------------------------------------------------------


@router.post(
    "/start",
    response_model=OnboardingSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Start or resume onboarding",
)
async def start_onboarding(
    current_user: UserResponse = Depends(get_current_user),
    svc: OnboardingService = Depends(get_onboarding_service),
) -> OnboardingSessionResponse:
    user_id = str(current_user.id)
    try:
        session = await svc.start_or_resume(user_id)
    except OnboardingAlreadyCompleted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Onboarding already completed for this user.",
        )
    return _session_to_response(session)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=OnboardingStatusResponse,
    summary="Get onboarding status",
)
async def get_status(
    current_user: UserResponse = Depends(get_current_user),
    svc: OnboardingService = Depends(get_onboarding_service),
) -> OnboardingStatusResponse:
    user_id = str(current_user.id)
    result = await svc.get_status(user_id)
    return OnboardingStatusResponse(
        has_active_session=result["has_active_session"],
        has_completed_session=result["has_completed_session"],
        session=(
            _session_to_response(result["session"]) if result["session"] else None
        ),
    )


# ---------------------------------------------------------------------------
# Save step response
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/response",
    response_model=StepSavedResponse,
    summary="Save a step response",
)
async def save_response(
    session_id: str,
    body: SaveResponseRequest,
    current_user: UserResponse = Depends(get_current_user),
    svc: OnboardingService = Depends(get_onboarding_service),
) -> StepSavedResponse:
    user_id = str(current_user.id)
    try:
        await svc.save_response(
            session_id=session_id,
            user_id=user_id,
            step=body.step,
            question=body.question,
            response=body.response,
            media_url=body.media_url,
            is_draft=body.is_draft,
        )
    except OnboardingNotFound:
        raise HTTPException(status_code=404, detail="Session not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden.")
    except OnboardingAlreadyCompleted:
        raise HTTPException(status_code=409, detail="Session already completed.")

    return StepSavedResponse(session_id=session_id, step=body.step)


# ---------------------------------------------------------------------------
# Autosave draft
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/draft",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Autosave draft for current step",
)
async def save_draft(
    session_id: str,
    body: dict,
    current_user: UserResponse = Depends(get_current_user),
    svc: OnboardingService = Depends(get_onboarding_service),
) -> None:
    user_id = str(current_user.id)
    try:
        await svc.save_draft(session_id=session_id, user_id=user_id, draft_data=body)
    except OnboardingNotFound:
        raise HTTPException(status_code=404, detail="Session not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden.")


# ---------------------------------------------------------------------------
# Complete onboarding → trigger Chronos init
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/complete",
    response_model=CompleteOnboardingResponse,
    summary="Complete onboarding and initialise Chronos",
)
async def complete_onboarding(
    session_id: str,
    current_user: UserResponse = Depends(get_current_user),
    svc: OnboardingService = Depends(get_onboarding_service),
    init_svc: ChronosInitializationService = Depends(get_chronos_init_service),
) -> CompleteOnboardingResponse:
    import structlog
    log = structlog.get_logger()
    user_id = str(current_user.id)

    try:
        await svc.check_can_complete(session_id, user_id)
    except OnboardingNotFound:
        raise HTTPException(status_code=404, detail="Session not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden.")
    except OnboardingAlreadyCompleted:
        raise HTTPException(status_code=409, detail="Session already completed.")
    except OnboardingMissingRequiredSteps as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Required steps not completed.",
                "missing": [s.value for s in e.missing],
            },
        )

    responses = await svc.get_all_responses(session_id, user_id)

    chronos_ok = False
    try:
        await init_svc.initialize(user_id=user_id, responses=responses)
        chronos_ok = True
    except ChronosAlreadyInitialized:
        chronos_ok = True
    except Exception as exc:
        log.error("chronos_init_failed", user_id=user_id, error=str(exc))

    await svc.mark_complete(session_id, user_id)
    try:
        await record_product_event(
            user_id,
            "onboarding_completed",
            {"chronos_initialised": bool(chronos_ok)},
        )
    except Exception:  # telemetry must never break the onboarding flow
        pass

    return CompleteOnboardingResponse(
        session_id=session_id,
        status=OnboardingStatus.COMPLETED,
        chronos_initialised=chronos_ok,
        message=(
            "Onboarding complete. Chronos is ready."
            if chronos_ok
            else "Onboarding complete. Chronos initialization is pending."
        ),
    )
