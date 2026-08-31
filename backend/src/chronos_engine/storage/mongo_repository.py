"""Persistent MongoDB storage adapter for the ChronOS Engine.

Replaces the in-memory adapter so that every memory the engine stores survives
restarts and is scoped per user.  Uses the same Motor client as the rest of
OpenTime, but keeps its own collections because the engine uses its own
document models (engine memories carry embeddings + linked memories).

Since Phase 3D this module also hosts ``MongoTemporalStore``, the persistent
implementation of the temporal domain (threads / events / snapshots) used by
the temporal lifecycle manager. Collections follow the established
``engine_*`` naming: ``engine_temporal_threads``, ``engine_temporal_events``,
``engine_temporal_snapshots``.
"""

from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from chronos_engine.core.interfaces import BaseStorageAdapter, BaseTemporalStore
from chronos_engine.core.models import (
    IdentityProfile,
    InteractionRecord,
    MemoryItem,
    PatternItem,
    ReflectionInsight,
    TimelineEvent,
)
from chronos_engine.temporal.models import (
    ReturnLedger,
    TemporalEvent,
    TemporalSnapshot,
    TemporalThread,
    TemporalThreadStatus,
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
        # MongoDB .limit(0) means "no limit" — clamp to at least 1
        effective_limit = max(1, limit)
        cursor = (
            db["engine_memories"]
            .find({"user_id": user_id})
            .sort("timestamp", -1)
            .limit(effective_limit)
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

    # ── Interactions ─────────────────────────────────────────────────────

    async def save_interaction(self, record: InteractionRecord) -> InteractionRecord:
        db = await self._db()
        doc = record.model_dump(mode="json")
        await db["engine_interactions"].replace_one(
            {"id": record.id, "user_id": record.user_id}, doc, upsert=True
        )
        return record

    async def get_interactions_by_user(
        self, user_id: str, limit: int = 50
    ) -> List[InteractionRecord]:
        db = await self._db()
        # MongoDB .limit(0) means "no limit" — clamp to at least 1
        effective_limit = max(1, limit)
        cursor = (
            db["engine_interactions"]
            .find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(effective_limit)
        )
        return [InteractionRecord(**d) for d in await cursor.to_list(length=None)]

    async def delete_all_for_user(self, user_id: str) -> None:
        db = await self._db()
        for collection in (
            "engine_memories",
            "engine_timeline",
            "engine_identity",
            "engine_reflections",
            "engine_patterns",
            "engine_interactions",
        ):
            await db[collection].delete_many({"user_id": user_id})


class MongoTemporalStore(BaseTemporalStore):
    """Persistent MongoDB store for the temporal domain (Phase 3D).

    Follows the exact conventions of :class:`MongoStorageAdapter`:
    ``model_dump(mode="json")`` serialization, ``replace_one`` upserts keyed
    by ``{"id", "user_id"}``, and user-scoped queries on every read. The
    database handle is resolved lazily through ``get_mongo_db()`` like the
    adapter above, but may also be injected (the ``chronos_repos`` pattern)
    so tests can run against ``mongomock-motor``.

    Older documents remain readable: every ``TemporalThread`` /
    ``TemporalEvent`` field has a safe default, so documents written before a
    new optional field existed deserialize cleanly.
    """

    _LIVE_STATUSES = {
        TemporalThreadStatus.OPEN.value,
        TemporalThreadStatus.ACTIVE.value,
        TemporalThreadStatus.CHANGED.value,
    }

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db_override: Optional[AsyncIOMotorDatabase] = db

    async def _db(self) -> AsyncIOMotorDatabase:
        if self._db_override is not None:
            return self._db_override
        return await get_mongo_db()

    # ── Threads ────────────────────────────────────────────────────────────

    async def save_thread(self, thread: TemporalThread) -> TemporalThread:
        db = await self._db()
        doc = thread.model_dump(mode="json")
        await db["engine_temporal_threads"].replace_one(
            {"id": thread.id, "user_id": thread.user_id}, doc, upsert=True
        )
        return thread

    async def get_thread(self, thread_id: str, user_id: str) -> Optional[TemporalThread]:
        db = await self._db()
        doc = await db["engine_temporal_threads"].find_one(
            {"id": thread_id, "user_id": user_id}
        )
        return TemporalThread(**doc) if doc else None

    async def get_threads_by_user(self, user_id: str) -> List[TemporalThread]:
        db = await self._db()
        cursor = (
            db["engine_temporal_threads"]
            .find({"user_id": user_id})
            .sort("created_at", -1)
        )
        return [TemporalThread(**d) async for d in cursor]

    async def get_candidate_threads(
        self, user_id: str, limit: int = 25
    ) -> List[TemporalThread]:
        """Bounded candidate retrieval for matching — live threads only.

        Targeted indexed read over ``engine_temporal_threads`` only; never a
        scan of memories or events.
        """
        db = await self._db()
        cursor = (
            db["engine_temporal_threads"]
            .find({"user_id": user_id, "status": {"$in": list(self._LIVE_STATUSES)}})
            .sort("created_at", -1)
            .limit(limit)
        )
        return [TemporalThread(**d) async for d in cursor]

    async def find_thread_by_origin_memory(
        self, user_id: str, memory_id: str
    ) -> Optional[TemporalThread]:
        """Indexed duplicate guard for lifecycle idempotency."""
        db = await self._db()
        doc = await db["engine_temporal_threads"].find_one(
            {"user_id": user_id, "origin_memory_id": memory_id}
        )
        return TemporalThread(**doc) if doc else None

    # ── Events ─────────────────────────────────────────────────────────────

    async def save_event(self, event: TemporalEvent) -> TemporalEvent:
        db = await self._db()
        doc = event.model_dump(mode="json")
        # Unconditionally include user_id in the write query for defense-in-depth
        query: dict = {"id": event.id, "user_id": event.user_id}
        await db["engine_temporal_events"].replace_one(query, doc, upsert=True)
        return event

    async def get_events_by_thread(
        self, thread_id: str, user_id: str
    ) -> List[TemporalEvent]:
        db = await self._db()
        cursor = (
            db["engine_temporal_events"]
            .find({"thread_id": thread_id, "user_id": user_id})
            .sort("occurred_at", 1)
        )
        return [TemporalEvent(**d) async for d in cursor]

    # ── Snapshots ──────────────────────────────────────────────────────────

    async def save_snapshot(self, snapshot: TemporalSnapshot) -> TemporalSnapshot:
        db = await self._db()
        doc = snapshot.model_dump(mode="json")
        await db["engine_temporal_snapshots"].replace_one(
            {"id": snapshot.id, "user_id": snapshot.user_id}, doc, upsert=True
        )
        return snapshot

    async def get_snapshots_by_user(self, user_id: str) -> List[TemporalSnapshot]:
        db = await self._db()
        cursor = (
            db["engine_temporal_snapshots"]
            .find({"user_id": user_id})
            .sort("timestamp", 1)
        )
        return [TemporalSnapshot(**d) async for d in cursor]

    # ── Return-hook ledger (Phase 5D) ────────────────────────────────────

    async def get_return_ledger(self, user_id: str) -> Optional[ReturnLedger]:
        db = await self._db()
        doc = await db["engine_return_ledgers"].find_one({"user_id": user_id})
        return ReturnLedger(**doc) if doc else None

    async def save_return_ledger(self, ledger: ReturnLedger) -> ReturnLedger:
        db = await self._db()
        doc = ledger.model_dump(mode="json")
        await db["engine_return_ledgers"].replace_one(
            {"user_id": ledger.user_id}, doc, upsert=True
        )
        return ledger

    async def delete_all_for_user(self, user_id: str) -> None:
        db = await self._db()
        # Delete this user's threads, then any events/snapshots owned by them
        thread_ids = await db["engine_temporal_threads"].distinct(
            "id", {"user_id": user_id}
        )
        await db["engine_temporal_events"].delete_many(
            {"$or": [{"user_id": user_id}, {"thread_id": {"$in": thread_ids}}]}
        )
        await db["engine_temporal_snapshots"].delete_many({"user_id": user_id})
        await db["engine_temporal_threads"].delete_many({"user_id": user_id})
        await db["engine_return_ledgers"].delete_many({"user_id": user_id})
