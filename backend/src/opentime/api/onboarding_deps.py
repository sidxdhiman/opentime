"""
FastAPI dependency injectors for onboarding and Chronos services.

All dependencies are request-scoped where possible.
The MongoDB client is a process-level singleton; repos are cheap wrappers.
"""

from __future__ import annotations

from functools import cache

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from opentime.application.onboarding.context_builder import ChronosContextBuilder
from opentime.application.onboarding.init_service import ChronosInitializationService
from opentime.application.onboarding.service import OnboardingService
from opentime.infrastructure.mongodb.chronos_repos import (
    MongoAnalysisPreferenceRepository,
    MongoChronosStateRepository,
    MongoGoalRepository,
    MongoIdentityStateRepository,
    MongoMemoryRepository,
    MongoPatternRepository,
    MongoTimelineRepository,
)
from opentime.infrastructure.mongodb.client import get_mongo_db
from opentime.infrastructure.mongodb.onboarding_repos import (
    MongoOnboardingResponseRepository,
    MongoOnboardingSessionRepository,
)
from opentime.infrastructure.services.embedding_service import (
    EmbeddingService,
    create_embedding_service,
)
from opentime.infrastructure.services.llm_service import LLMService, create_llm_service


# ---------------------------------------------------------------------------
# Process-level service singletons (created once per worker)
# ---------------------------------------------------------------------------

@cache
def _get_llm_service() -> LLMService:
    return create_llm_service()


@cache
def _get_embedding_service() -> EmbeddingService:
    return create_embedding_service()


# ---------------------------------------------------------------------------
# Request-scoped dependencies
# ---------------------------------------------------------------------------


async def get_db() -> AsyncIOMotorDatabase:
    return await get_mongo_db()


async def get_onboarding_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> OnboardingService:
    return OnboardingService(
        session_repo=MongoOnboardingSessionRepository(db),
        response_repo=MongoOnboardingResponseRepository(db),
    )


async def get_chronos_init_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ChronosInitializationService:
    return ChronosInitializationService(
        memory_repo=MongoMemoryRepository(db),
        identity_repo=MongoIdentityStateRepository(db),
        goal_repo=MongoGoalRepository(db),
        timeline_repo=MongoTimelineRepository(db),
        pattern_repo=MongoPatternRepository(db),
        pref_repo=MongoAnalysisPreferenceRepository(db),
        chronos_repo=MongoChronosStateRepository(db),
        llm=_get_llm_service(),
        embedding=_get_embedding_service(),
    )


async def get_chronos_context_builder(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ChronosContextBuilder:
    return ChronosContextBuilder(
        chronos_repo=MongoChronosStateRepository(db),
        identity_repo=MongoIdentityStateRepository(db),
        memory_repo=MongoMemoryRepository(db),
        goal_repo=MongoGoalRepository(db),
        timeline_repo=MongoTimelineRepository(db),
        pattern_repo=MongoPatternRepository(db),
        pref_repo=MongoAnalysisPreferenceRepository(db),
    )
