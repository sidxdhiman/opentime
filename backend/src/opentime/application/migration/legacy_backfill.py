"""Idempotent legacy-data backfill from the application store to engine stores.

Phase 5G-C made the ChronOS engine stores the authoritative source of truth
for memories, identity, timeline events and patterns. Users who onboarded
before 5G-C may have application-store data ("memories", "identity_states",
"timeline_events", "patterns") with no corresponding engine records.

Rather than a runtime fallback (which could resurrect logically-deleted
records), this operator-run backfill copies legacy application data into the
engine stores ONCE. It is:

  * idempotent          - safe to run multiple times (no duplicates)
  * user-scoped        - only the requested user's data is touched
  * conflict-safe      - never overwrites newer engine state with stale
                         application state
  * additive           - deletes nothing from either store

Source -> Destination -> Conflict rule -> Deletion behavior
------------------------------------------------------------
memories         -> engine_memories     skip if engine id+user already exists  | none
identity_states  -> engine_identity     only create when no engine identity     | none
timeline_events  -> engine_timeline     skip if engine id+user already exists  | none
patterns         -> engine_patterns     skip if engine id+user already exists  | none

The engine write path mirrors ``MongoStorageAdapter``: ``replace_one`` with an
upsert keyed on ``{id, user_id}`` (identity keyed on ``user_id``). Because the
id presence is checked first, a re-run never duplicates and never overwrites.
"""

from __future__ import annotations

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from chronos_engine.core.models import (
    IdentityProfile,
    MemoryItem,
    MemoryType,
    PatternCategory,
    PatternItem,
)
from chronos_engine.core.models import (
    TimelineEvent as EngineTimelineEvent,
)
from opentime.infrastructure.mongodb.chronos_repos import (
    MongoIdentityStateRepository,
    MongoMemoryRepository,
    MongoPatternRepository,
    MongoTimelineRepository,
)

logger = structlog.get_logger()


class UserBackfillResult(BaseModel):
    user_id: str
    memories_migrated: int = 0
    memories_skipped: int = 0
    identity_created: bool = False
    identity_skipped: bool = False
    timeline_migrated: int = 0
    timeline_skipped: int = 0
    patterns_migrated: int = 0
    patterns_skipped: int = 0


class BackfillSummary(BaseModel):
    users: int = 0
    memories_migrated: int = 0
    memories_skipped: int = 0
    identities_created: int = 0
    identities_skipped: int = 0
    timeline_migrated: int = 0
    timeline_skipped: int = 0
    patterns_migrated: int = 0
    patterns_skipped: int = 0
    results: list[UserBackfillResult] = Field(default_factory=list)


class LegacyBackfillService:
    """Backfills legacy application-store data into the engine stores."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._mem_repo = MongoMemoryRepository(db)
        self._identity_repo = MongoIdentityStateRepository(db)
        self._timeline_repo = MongoTimelineRepository(db)
        self._pattern_repo = MongoPatternRepository(db)

    # -- existence / write helpers (mirror MongoStorageAdapter semantics) --

    async def _engine_memory_ids(self, user_id: str) -> set[str]:
        cursor = self._db["engine_memories"].find(
            {"user_id": user_id}, {"id": 1}
        )
        return {d["id"] async for d in cursor}

    async def _engine_timeline_ids(self, user_id: str) -> set[str]:
        cursor = self._db["engine_timeline"].find(
            {"user_id": user_id}, {"id": 1}
        )
        return {d["id"] async for d in cursor}

    async def _engine_pattern_ids(self, user_id: str) -> set[str]:
        cursor = self._db["engine_patterns"].find(
            {"user_id": user_id}, {"id": 1}
        )
        return {d["id"] async for d in cursor}

    async def _engine_identity_exists(self, user_id: str) -> bool:
        doc = await self._db["engine_identity"].find_one({"user_id": user_id}, {"_id": 1})
        return doc is not None

    # -- per-entity backfills --

    async def _backfill_memories(
        self, user_id: str, existing: set[str], dry_run: bool = False
    ) -> tuple[int, int]:
        migrated = 0
        skipped = 0
        memories = await self._mem_repo.get_for_user(user_id, limit=1000)
        for mem in memories:
            if mem.id in existing:
                skipped += 1
                continue
            engine_mem = MemoryItem(
                id=mem.id,
                user_id=user_id,
                content=mem.content,
                memory_type=MemoryType.EPISODIC,
                importance_score=mem.importance,
                is_genesis=mem.is_genesis,
                created_at=mem.created_at,
                timestamp=mem.event_time,
                linked_memory_ids=list(mem.linked_memory_ids),
            )
            if not dry_run:
                await self._db["engine_memories"].replace_one(
                    {"id": mem.id, "user_id": user_id},
                    engine_mem.model_dump(mode="json"),
                    upsert=True,
                )
            migrated += 1
        return migrated, skipped

    async def _backfill_identity(
        self, user_id: str, dry_run: bool = False
    ) -> tuple[bool, bool]:
        if await self._engine_identity_exists(user_id):
            logger.info("legacy_backfill_identity_skipped", user_id=user_id)
            return False, True
        state = await self._identity_repo.get_latest(user_id)
        if state is None:
            logger.info("legacy_backfill_identity_none", user_id=user_id)
            return False, False
        profile = IdentityProfile(
            user_id=user_id,
            interests=[t.value for t in state.interests if t.value],
            values=[t.value for t in state.values if t.value],
            skills=[t.trait for t in state.traits if t.trait],
            version=state.version,
            last_updated=state.valid_from or state.created_at,
        )
        if not dry_run:
            await self._db["engine_identity"].replace_one(
                {"user_id": user_id},
                profile.model_dump(mode="json"),
                upsert=True,
            )
        logger.info("legacy_backfill_identity_created", user_id=user_id)
        return True, False

    async def _backfill_timeline(
        self, user_id: str, existing: set[str], dry_run: bool = False
    ) -> tuple[int, int]:
        migrated = 0
        skipped = 0
        events = await self._timeline_repo.get_for_user(user_id, limit=1000)
        for ev in events:
            if ev.id in existing:
                skipped += 1
                continue
            engine_event = EngineTimelineEvent(
                id=ev.id,
                user_id=user_id,
                title=ev.title,
                description=ev.description,
                timestamp=ev.event_time,
                life_phase=ev.category or "General",
                memory_ids=[ev.source_memory_id] if ev.source_memory_id else [],
            )
            if not dry_run:
                await self._db["engine_timeline"].replace_one(
                    {"id": ev.id, "user_id": user_id},
                    engine_event.model_dump(mode="json"),
                    upsert=True,
                )
            migrated += 1
        return migrated, skipped

    async def _backfill_patterns(
        self, user_id: str, existing: set[str], dry_run: bool = False
    ) -> tuple[int, int]:
        migrated = 0
        skipped = 0
        patterns = await self._pattern_repo.get_for_user(user_id)
        for pat in patterns:
            if pat.id in existing:
                skipped += 1
                continue
            engine_pattern = PatternItem(
                id=pat.id,
                user_id=user_id,
                category=PatternCategory.HABIT,
                title=pat.pattern,
                description=pat.pattern,
                confidence_score=pat.confidence,
                supporting_memory_ids=list(pat.source_memory_ids),
            )
            if not dry_run:
                await self._db["engine_patterns"].replace_one(
                    {"id": pat.id, "user_id": user_id},
                    engine_pattern.model_dump(mode="json"),
                    upsert=True,
                )
            migrated += 1
        return migrated, skipped

    async def backfill_user(
        self, user_id: str, dry_run: bool = False
    ) -> UserBackfillResult:
        """Backfill one user's legacy application data into the engine stores."""
        existing_mem = await self._engine_memory_ids(user_id)
        mem_migrated, mem_skipped = await self._backfill_memories(
            user_id, existing_mem, dry_run
        )

        identity_created, identity_skipped = await self._backfill_identity(
            user_id, dry_run
        )

        existing_tl = await self._engine_timeline_ids(user_id)
        tl_migrated, tl_skipped = await self._backfill_timeline(
            user_id, existing_tl, dry_run
        )

        existing_pat = await self._engine_pattern_ids(user_id)
        pat_migrated, pat_skipped = await self._backfill_patterns(
            user_id, existing_pat, dry_run
        )

        result = UserBackfillResult(
            user_id=user_id,
            memories_migrated=mem_migrated,
            memories_skipped=mem_skipped,
            identity_created=identity_created,
            identity_skipped=identity_skipped,
            timeline_migrated=tl_migrated,
            timeline_skipped=tl_skipped,
            patterns_migrated=pat_migrated,
            patterns_skipped=pat_skipped,
        )
        logger.info(
            "legacy_backfill_user_done",
            user_id=user_id,
            dry_run=dry_run,
            **result.model_dump(exclude={"user_id"}),
        )
        return result

    async def backfill_all(
        self, user_ids: list[str] | None = None, dry_run: bool = False
    ) -> BackfillSummary:
        """Backfill legacy data. If ``user_ids`` is None, scan all distinct users
        who have application-store data and backfill each."""
        if user_ids is None:
            user_ids = await self._all_legacy_user_ids()

        results = [await self.backfill_user(uid, dry_run) for uid in user_ids]
        summary = BackfillSummary(
            users=len(results),
            memories_migrated=sum(r.memories_migrated for r in results),
            memories_skipped=sum(r.memories_skipped for r in results),
            identities_created=sum(1 for r in results if r.identity_created),
            identities_skipped=sum(1 for r in results if r.identity_skipped),
            timeline_migrated=sum(r.timeline_migrated for r in results),
            timeline_skipped=sum(r.timeline_skipped for r in results),
            patterns_migrated=sum(r.patterns_migrated for r in results),
            patterns_skipped=sum(r.patterns_skipped for r in results),
            results=results,
        )
        logger.info("legacy_backfill_all_done", **summary.model_dump(exclude={"results"}))
        return summary

    async def _all_legacy_user_ids(self) -> list[str]:
        user_ids: set[str] = set()
        for collection in (
            "memories",
            "identity_states",
            "timeline_events",
            "patterns",
        ):
            cursor = self._db[collection].distinct("user_id")
            user_ids.update(await cursor)
        return sorted(user_ids)
