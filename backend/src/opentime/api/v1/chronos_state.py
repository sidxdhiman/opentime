"""
Chronos state read + edit endpoints.

READ:
  GET  /chronos/state               → full ChronosState document
  GET  /chronos/identity            → latest identity snapshot
  GET  /chronos/memories            → paginated memories
  GET  /chronos/timeline            → paginated timeline events
  GET  /chronos/goals               → active goals
  GET  /chronos/patterns            → behavioural patterns
  POST /chronos/context             → assembled LLM context snapshot

EDIT (all send the impact warning flag):
  PATCH /chronos/goals/{goal_id}         → edit a goal
  POST  /chronos/goals                   → add a new goal
  DELETE /chronos/goals/{goal_id}        → remove a goal
  PATCH /chronos/preferences             → replace all analysis preferences
  PATCH /chronos/genesis                 → edit genesis memory text
  PATCH /chronos/identity/traits         → replace identity traits list

All mutations are scoped by user_id from the JWT.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from opentime.api.dependencies import get_current_user
from opentime.api.onboarding_deps import (
    get_chronos_context_builder,
    get_db,
)
from opentime.application.auth.dto import UserResponse
from opentime.application.onboarding.context_builder import ChronosContextBuilder
from opentime.domain.chronos.entities import (
    AnalysisPreferenceRecord,
    ClaimType,
    Goal,
    GoalStatus,
    IdentityState,
    IdentityTrait,
)
from opentime.infrastructure.mongodb.chronos_repos import (
    MongoAnalysisPreferenceRepository,
    MongoChronosStateRepository,
    MongoGoalRepository,
    MongoIdentityStateRepository,
    MongoMemoryRepository,
    MongoPatternRepository,
    MongoTimelineRepository,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/chronos", tags=["Chronos State"])

# ── Shared edit DTOs ──────────────────────────────────────────────────────────


class GoalEditRequest(BaseModel):
    title: str
    description: str | None = None
    category: str = "other"
    importance: float = Field(default=0.7, ge=0.0, le=1.0)
    status: GoalStatus = GoalStatus.ACTIVE


class GoalCreateRequest(BaseModel):
    title: str
    description: str | None = None
    category: str = "other"
    importance: float = Field(default=0.7, ge=0.0, le=1.0)


class PreferencesEditRequest(BaseModel):
    preferences: list[str]   # replaces the full set


class GenesisEditRequest(BaseModel):
    content: str = Field(min_length=10)


class TraitEditRequest(BaseModel):
    """Replaces the full traits list. Preserves existing claim_type."""
    traits: list[str]


# ── Read endpoints ────────────────────────────────────────────────────────────


@router.get("/state", summary="Get Chronos initialisation state")
async def get_chronos_state(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    user_id = str(current_user.id)
    state = await MongoChronosStateRepository(db).get_for_user(user_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail="Chronos not yet initialised. Complete onboarding first.",
        )
    return state.model_dump(mode="json")


@router.get("/identity", summary="Get latest identity snapshot")
async def get_identity(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    user_id = str(current_user.id)
    state = await MongoIdentityStateRepository(db).get_latest(user_id)
    if not state:
        raise HTTPException(status_code=404, detail="Identity not yet established.")
    return state.model_dump(mode="json")


@router.get("/memories", summary="Get user memories (paginated)")
async def get_memories(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    user_id = str(current_user.id)
    memories = await MongoMemoryRepository(db).get_for_user(user_id, limit=limit, skip=skip)
    result = []
    for m in memories:
        d = m.model_dump(mode="json")
        d.pop("embedding", None)
        result.append(d)
    return result


@router.get("/timeline", summary="Get timeline events (paginated)")
async def get_timeline(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    user_id = str(current_user.id)
    events = await MongoTimelineRepository(db).get_for_user(user_id, limit=limit, skip=skip)
    return [e.model_dump(mode="json") for e in events]


@router.get("/goals", summary="Get goals")
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


@router.get("/patterns", summary="Get behavioural patterns")
async def get_patterns(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[dict[str, Any]]:
    user_id = str(current_user.id)
    patterns = await MongoPatternRepository(db).get_for_user(user_id)
    return [p.model_dump(mode="json") for p in patterns]


@router.get("/preferences", summary="Get analysis preferences")
async def get_preferences(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[dict[str, Any]]:
    user_id = str(current_user.id)
    prefs = await MongoAnalysisPreferenceRepository(db).get_for_user(user_id)
    return [p.model_dump(mode="json") for p in prefs]


@router.post("/context", summary="Assemble Chronos context snapshot for LLM")
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


# ── Edit endpoints ────────────────────────────────────────────────────────────


@router.patch("/goals/{goal_id}", summary="Edit a goal")
async def edit_goal(
    goal_id: str,
    body: GoalEditRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    user_id = str(current_user.id)
    repo = MongoGoalRepository(db)
    goal = await repo.get_by_id(goal_id, user_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    goal.title = body.title
    goal.description = body.description
    goal.category = body.category
    goal.importance = body.importance
    goal.status = body.status

    updated = await repo.update(goal)
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed.")
    return updated.model_dump(mode="json")


@router.post("/goals", summary="Add a new goal", status_code=201)
async def create_goal(
    body: GoalCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    user_id = str(current_user.id)
    goal = Goal(
        user_id=user_id,
        title=body.title,
        description=body.description,
        category=body.category,
        importance=body.importance,
        status=GoalStatus.ACTIVE,
        source="user_edit",
        confidence=1.0,
    )
    saved = await MongoGoalRepository(db).create(goal)
    return saved.model_dump(mode="json")


@router.delete("/goals/{goal_id}", status_code=204, summary="Delete a goal")
async def delete_goal(
    goal_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    user_id = str(current_user.id)
    repo = MongoGoalRepository(db)
    goal = await repo.get_by_id(goal_id, user_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")
    # Soft-delete: mark as abandoned rather than destroying history
    goal.status = GoalStatus.ABANDONED
    await repo.update(goal)


@router.patch("/preferences", summary="Replace analysis preferences")
async def update_preferences(
    body: PreferencesEditRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[dict[str, Any]]:
    user_id = str(current_user.id)
    records = [
        AnalysisPreferenceRecord(user_id=user_id, preference=p)
        for p in body.preferences
        if p.strip()
    ]
    saved = await MongoAnalysisPreferenceRepository(db).replace_all_for_user(
        user_id, records
    )
    return [r.model_dump(mode="json") for r in saved]


@router.patch("/genesis", summary="Edit genesis memory content")
async def edit_genesis(
    body: GenesisEditRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    user_id = str(current_user.id)
    repo = MongoMemoryRepository(db)
    genesis = await repo.get_genesis(user_id)
    if not genesis:
        raise HTTPException(status_code=404, detail="Genesis memory not found.")

    genesis.content = body.content
    # Clear stale derived fields — they'll be re-extracted on next Chronos cycle
    genesis.summary = None
    genesis.topics = []
    genesis.entities = []
    genesis.embedding = []   # stale — re-embed on next pipeline run

    updated = await repo.update(genesis)
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed.")
    d = updated.model_dump(mode="json")
    d.pop("embedding", None)
    return d


@router.patch("/identity/traits", summary="Replace identity traits")
async def update_traits(
    body: TraitEditRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    user_id = str(current_user.id)
    repo = MongoIdentityStateRepository(db)
    current = await repo.get_latest(user_id)
    if not current:
        raise HTTPException(status_code=404, detail="Identity not yet established.")

    new_traits = [
        IdentityTrait(
            trait=t.strip(),
            claim_type=ClaimType.USER_STATEMENT,  # user explicitly set these
            confidence=1.0,
        )
        for t in body.traits
        if t.strip()
    ]

    # Create a new version — never overwrite history
    new_state = IdentityState(
        user_id=user_id,
        version=current.version + 1,
        traits=new_traits,
        interests=current.interests,
        values=current.values,
        self_perception=current.self_perception,
        current_phase=current.current_phase,
        valid_from=datetime.now(timezone.utc),
        valid_until=None,
    )
    # Close out the old version
    current.valid_until = datetime.now(timezone.utc)
    await repo.create(new_state)   # inserts new version
    return new_state.model_dump(mode="json")
