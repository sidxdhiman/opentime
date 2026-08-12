"""Persistent MongoDB storage adapter for the ChronOS Engine.

Replaces the in-memory adapter so that every memory the engine stores survives
restarts and is scoped per user.  Uses the same Motor client as the rest of
OpenTime, but keeps its own collections because the engine uses its own
document models (engine memories carry embeddings + linked memories).
"""

from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from chronos_engine.core.interfaces import BaseStorageAdapter
from chronos_engine.core.models import (
    IdentityProfile,
    MemoryItem,
    PatternItem,
    ReflectionInsight,
    TimelineEvent,
)
from opentime.infrastructure.mongodb.client import get_mongo_db


class MongoStorageAdapter(BaseStorageAdapter):
    def __init__(self) -> None:
        self._memories: AsyncIOMotorDatabase | None = None

    async def _db(self) -> AsyncIOMotorDatabase:
        return await get_mongo_db()

    # ── Memories ───────────────────────────────────────────────────────────

    async def save_memory(self, memory: MemoryItem) -> MemoryItem:
        db = await self._db()
        doc = memory.model_dump(mode="json")
        await db["engine_memories"].replace_one(
            {"id": memory.id, "user_id": memory.user_id}, doc, upsert=True
        )
        return memory

    async def get_memories_by_user(
        self, user_id: str, limit: int = 100
    ) -> List[MemoryItem]:
        db = await self._db()
        cursor = (
            db["engine_memories"]
            .find({"user_id": user_id})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return [MemoryItem(**d) async for d in cursor]

    # ── Timeline ───────────────────────────────────────────────────────────

    async def save_timeline_event(self, event: TimelineEvent) -> TimelineEvent:
        db = await self._db()
        doc = event.model_dump(mode="json")
        await db["engine_timeline"].replace_one(
            {"id": event.id, "user_id": event.user_id}, doc, upsert=True
        )
        return event

    async def get_timeline_by_user(self, user_id: str) -> List[TimelineEvent]:
        db = await self._db()
        cursor = (
            db["engine_timeline"]
            .find({"user_id": user_id})
            .sort("timestamp", 1)
        )
        return [TimelineEvent(**d) async for d in cursor]

    # ── Identity ───────────────────────────────────────────────────────────

    async def save_identity(self, profile: IdentityProfile) -> IdentityProfile:
        db = await self._db()
        doc = profile.model_dump(mode="json")
        await db["engine_identity"].replace_one(
            {"user_id": profile.user_id}, doc, upsert=True
        )
        return profile

    async def get_identity(self, user_id: str) -> Optional[IdentityProfile]:
        db = await self._db()
        doc = await db["engine_identity"].find_one({"user_id": user_id})
        return IdentityProfile(**doc) if doc else None

    # ── Reflections ────────────────────────────────────────────────────────

    async def save_reflection(self, insight: ReflectionInsight) -> ReflectionInsight:
        db = await self._db()
        doc = insight.model_dump(mode="json")
        await db["engine_reflections"].replace_one(
            {"id": insight.id, "user_id": insight.user_id}, doc, upsert=True
        )
        return insight

    async def get_reflections_by_user(
        self, user_id: str
    ) -> List[ReflectionInsight]:
        db = await self._db()
        cursor = (
            db["engine_reflections"]
            .find({"user_id": user_id})
            .sort("timestamp", -1)
        )
        return [ReflectionInsight(**d) async for d in cursor]

    # ── Patterns ───────────────────────────────────────────────────────────

    async def save_pattern(self, pattern: PatternItem) -> PatternItem:
        db = await self._db()
        doc = pattern.model_dump(mode="json")
        await db["engine_patterns"].replace_one(
            {"id": pattern.id, "user_id": pattern.user_id}, doc, upsert=True
        )
        return pattern

    async def get_patterns_by_user(self, user_id: str) -> List[PatternItem]:
        db = await self._db()
        cursor = (
            db["engine_patterns"]
            .find({"user_id": user_id})
            .sort("confidence_score", -1)
        )
        return [PatternItem(**d) async for d in cursor]
