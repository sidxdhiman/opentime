"""
Chronos state read endpoints.

These expose the persistent Chronos state for a user:
  GET  /chronos/state               → full ChronosState document
  GET  /chronos/identity            → latest identity snapshot
  GET  /chronos/memories            → paginated memories
  GET  /chronos/timeline            → paginated timeline events
  GET  /chronos/goals               → active goals
  POST /chronos/context             → assembled LLM context snapshot

All queries are scoped by user_id from the JWT token.
Internal embeddings and raw Chronos metadata are NOT exposed.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from opentime.api.dependencies import get_current_user
from opentime.api.onboarding_deps import (
    get_chronos_context_builder,
    get_db,
)
from opentime.application.auth.dto import UserResponse
from opentime.application.onboarding.context_builder import ChronosContextBuilder
from opentime.infrastructure.mongodb.chronos_repos import (
    MongoChronosStateRepository,
    MongoGoalRepository,
    MongoIdentityStateRepository,
    MongoMemoryRepository,
    MongoPatternRepository,
    MongoTimelineRepository,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/chronos", tags=["Chronos State"])


# ---------------------------------------------------------------------------
# Chronos State
# ---------------------------------------------------------------------------


@router.get(
    "/state",
    summary="Get Chronos initialisation state",
)
async def get_chronos_state(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    user_id = str(current_user.id)
    repo = MongoChronosStateRepository(db)
    state = await repo.get_for_user(user_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chronos not yet initialised for this user. Complete onboarding first.",
        )
    # Exclude internal implementation fields like embedding IDs
    d = state.model_dump(mode="json")
    return d


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


@router.get(
    "/identity",
    summary="Get latest identity snapshot",
)
async def get_identity(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    user_id = str(current_user.id)
    repo = MongoIdentityStateRepository(db)
    state = await repo.get_latest(user_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identity not yet established. Complete onboarding first.",
        )
    return state.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Memories
# ---------------------------------------------------------------------------


@router.get(
    "/memories",
    summary="Get user memories (paginated)",
)
async def get_memories(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    user_id = str(current_user.id)
    repo = MongoMemoryRepository(db)
    memories = await repo.get_for_user(user_id, limit=limit, skip=skip)
    # Never expose raw embedding vectors through the public API
    result = []
    for m in memories:
        d = m.model_dump(mode="json")
        d.pop("embedding", None)
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


@router.get(
    "/timeline",
    summary="Get timeline events (paginated)",
)
async def get_timeline(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    user_id = str(current_user.id)
    repo = MongoTimelineRepository(db)
    events = await repo.get_for_user(user_id, limit=limit, skip=skip)
    return [e.model_dump(mode="json") for e in events]


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


@router.get(
    "/goals",
    summary="Get active goals",
)
async def get_goals(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    active_only: bool = Query(default=True),
) -> list[dict[str, Any]]:
    user_id = str(current_user.id)
    repo = MongoGoalRepository(db)
    goals = (
        await repo.get_active_for_user(user_id)
        if active_only
        else await repo.get_all_for_user(user_id)
    )
    return [g.model_dump(mode="json") for g in goals]


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------


@router.get(
    "/patterns",
    summary="Get behavioural patterns",
)
async def get_patterns(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[dict[str, Any]]:
    user_id = str(current_user.id)
    repo = MongoPatternRepository(db)
    patterns = await repo.get_for_user(user_id)
    return [p.model_dump(mode="json") for p in patterns]


# ---------------------------------------------------------------------------
# Context (for LLM use)
# ---------------------------------------------------------------------------


@router.post(
    "/context",
    summary="Assemble Chronos context snapshot for LLM",
)
async def get_context(
    current_user: UserResponse = Depends(get_current_user),
    builder: ChronosContextBuilder = Depends(get_chronos_context_builder),
    memory_limit: int = Query(default=10, ge=1, le=50),
    timeline_limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    user_id = str(current_user.id)
    return await builder.build(
        user_id=user_id,
        memory_limit=memory_limit,
        timeline_limit=timeline_limit,
    )
