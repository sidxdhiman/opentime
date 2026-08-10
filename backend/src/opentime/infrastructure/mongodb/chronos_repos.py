"""MongoDB implementations of all Chronos domain repositories."""

from __future__ import annotations

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from opentime.domain.chronos.entities import (
    AnalysisPreferenceRecord,
    ChronosState,
    Goal,
    GoalStatus,
    IdentityState,
    Memory,
    Pattern,
    TimelineEvent,
)
from opentime.domain.chronos.repositories import (
    AnalysisPreferenceRepository,
    ChronosStateRepository,
    GoalRepository,
    IdentityStateRepository,
    MemoryRepository,
    PatternRepository,
    TimelineRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


class MongoMemoryRepository(MemoryRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["memories"]

    async def create(self, memory: Memory) -> Memory:
        doc = memory.model_dump(mode="json")
        await self._col.insert_one(doc)
        return memory

    async def get_by_id(self, memory_id: str, user_id: str) -> Memory | None:
        doc = await self._col.find_one({"id": memory_id, "user_id": user_id})
        return Memory(**doc) if doc else None

    async def get_for_user(
        self, user_id: str, limit: int = 50, skip: int = 0
    ) -> list[Memory]:
        cursor = (
            self._col.find({"user_id": user_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [Memory(**d) async for d in cursor]

    async def get_genesis(self, user_id: str) -> Memory | None:
        doc = await self._col.find_one({"user_id": user_id, "is_genesis": True})
        return Memory(**doc) if doc else None

    async def exists_genesis(self, user_id: str) -> bool:
        count = await self._col.count_documents(
            {"user_id": user_id, "is_genesis": True}, limit=1
        )
        return count > 0

    async def search_by_topics(self, user_id: str, topics: list[str]) -> list[Memory]:
        cursor = self._col.find(
            {"user_id": user_id, "topics": {"$in": topics}}
        ).sort("importance", -1).limit(20)
        return [Memory(**d) async for d in cursor]

    async def update(self, memory: Memory) -> Memory | None:
        doc = memory.model_dump(mode="json")
        result = await self._col.replace_one(
            {"id": memory.id, "user_id": memory.user_id}, doc
        )
        return memory if result.matched_count else None

    async def delete_all_for_user(self, user_id: str) -> int:
        result = await self._col.delete_many({"user_id": user_id})
        return result.deleted_count


# ---------------------------------------------------------------------------
# Identity State
# ---------------------------------------------------------------------------


class MongoIdentityStateRepository(IdentityStateRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["identity_states"]

    async def create(self, state: IdentityState) -> IdentityState:
        doc = state.model_dump(mode="json")
        await self._col.insert_one(doc)
        return state

    async def get_latest(self, user_id: str) -> IdentityState | None:
        doc = await self._col.find_one(
            {"user_id": user_id}, sort=[("version", -1)]
        )
        return IdentityState(**doc) if doc else None

    async def get_all_versions(self, user_id: str) -> list[IdentityState]:
        cursor = self._col.find({"user_id": user_id}).sort("version", 1)
        return [IdentityState(**d) async for d in cursor]

    async def get_by_id(self, state_id: str, user_id: str) -> IdentityState | None:
        doc = await self._col.find_one({"id": state_id, "user_id": user_id})
        return IdentityState(**doc) if doc else None

    async def delete_all_for_user(self, user_id: str) -> int:
        result = await self._col.delete_many({"user_id": user_id})
        return result.deleted_count


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


class MongoGoalRepository(GoalRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["goals"]

    async def create(self, goal: Goal) -> Goal:
        doc = goal.model_dump(mode="json")
        await self._col.insert_one(doc)
        return goal

    async def get_by_id(self, goal_id: str, user_id: str) -> Goal | None:
        doc = await self._col.find_one({"id": goal_id, "user_id": user_id})
        return Goal(**doc) if doc else None

    async def get_active_for_user(self, user_id: str) -> list[Goal]:
        cursor = self._col.find(
            {"user_id": user_id, "status": GoalStatus.ACTIVE}
        ).sort("importance", -1)
        return [Goal(**d) async for d in cursor]

    async def get_all_for_user(self, user_id: str) -> list[Goal]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", -1)
        return [Goal(**d) async for d in cursor]

    async def update_status(
        self, goal_id: str, user_id: str, status: GoalStatus
    ) -> Goal | None:
        await self._col.update_one(
            {"id": goal_id, "user_id": user_id},
            {"$set": {"status": status}},
        )
        return await self.get_by_id(goal_id, user_id)

    async def update(self, goal: Goal) -> Goal | None:
        doc = goal.model_dump(mode="json")
        result = await self._col.replace_one(
            {"id": goal.id, "user_id": goal.user_id}, doc
        )
        return goal if result.matched_count else None

    async def delete_all_for_user(self, user_id: str) -> int:
        result = await self._col.delete_many({"user_id": user_id})
        return result.deleted_count


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


class MongoTimelineRepository(TimelineRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["timeline_events"]

    async def create(self, event: TimelineEvent) -> TimelineEvent:
        doc = event.model_dump(mode="json")
        await self._col.insert_one(doc)
        return event

    async def get_for_user(
        self, user_id: str, limit: int = 100, skip: int = 0
    ) -> list[TimelineEvent]:
        cursor = (
            self._col.find({"user_id": user_id})
            .sort("event_time", -1)
            .skip(skip)
            .limit(limit)
        )
        return [TimelineEvent(**d) async for d in cursor]

    async def get_range(
        self, user_id: str, from_date: datetime, to_date: datetime
    ) -> list[TimelineEvent]:
        cursor = self._col.find(
            {
                "user_id": user_id,
                "event_time": {
                    "$gte": from_date.isoformat(),
                    "$lte": to_date.isoformat(),
                },
            }
        ).sort("event_time", 1)
        return [TimelineEvent(**d) async for d in cursor]

    async def delete_all_for_user(self, user_id: str) -> int:
        result = await self._col.delete_many({"user_id": user_id})
        return result.deleted_count


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------


class MongoPatternRepository(PatternRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["patterns"]

    async def create(self, pattern: Pattern) -> Pattern:
        doc = pattern.model_dump(mode="json")
        await self._col.insert_one(doc)
        return pattern

    async def get_for_user(self, user_id: str) -> list[Pattern]:
        cursor = self._col.find({"user_id": user_id}).sort("confidence", -1)
        return [Pattern(**d) async for d in cursor]

    async def increment_evidence(
        self, pattern_id: str, user_id: str
    ) -> Pattern | None:
        now = _now()
        await self._col.update_one(
            {"id": pattern_id, "user_id": user_id},
            {
                "$inc": {"evidence_count": 1},
                "$set": {"last_updated": now.isoformat()},
            },
        )
        doc = await self._col.find_one({"id": pattern_id, "user_id": user_id})
        return Pattern(**doc) if doc else None

    async def delete_all_for_user(self, user_id: str) -> int:
        result = await self._col.delete_many({"user_id": user_id})
        return result.deleted_count


# ---------------------------------------------------------------------------
# Analysis Preferences
# ---------------------------------------------------------------------------


class MongoAnalysisPreferenceRepository(AnalysisPreferenceRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["analysis_preferences"]

    async def create_many(
        self, records: list[AnalysisPreferenceRecord]
    ) -> list[AnalysisPreferenceRecord]:
        if not records:
            return []
        docs = [r.model_dump(mode="json") for r in records]
        await self._col.insert_many(docs)
        return records

    async def get_for_user(self, user_id: str) -> list[AnalysisPreferenceRecord]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", 1)
        return [AnalysisPreferenceRecord(**d) async for d in cursor]

    async def replace_all_for_user(
        self, user_id: str, records: list[AnalysisPreferenceRecord]
    ) -> list[AnalysisPreferenceRecord]:
        await self._col.delete_many({"user_id": user_id})
        if records:
            docs = [r.model_dump(mode="json") for r in records]
            await self._col.insert_many(docs)
        return records

    async def delete_all_for_user(self, user_id: str) -> int:
        result = await self._col.delete_many({"user_id": user_id})
        return result.deleted_count


# ---------------------------------------------------------------------------
# Chronos State
# ---------------------------------------------------------------------------


class MongoChronosStateRepository(ChronosStateRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["chronos_states"]

    async def create(self, state: ChronosState) -> ChronosState:
        doc = state.model_dump(mode="json")
        await self._col.insert_one(doc)
        return state

    async def get_for_user(self, user_id: str) -> ChronosState | None:
        doc = await self._col.find_one(
            {"user_id": user_id}, sort=[("version", -1)]
        )
        return ChronosState(**doc) if doc else None

    async def update(self, state: ChronosState) -> ChronosState:
        state.last_updated_at = _now()
        doc = state.model_dump(mode="json")
        await self._col.replace_one({"id": state.id}, doc, upsert=False)
        return state

    async def exists_for_user(self, user_id: str) -> bool:
        count = await self._col.count_documents({"user_id": user_id}, limit=1)
        return count > 0

    async def delete_all_for_user(self, user_id: str) -> int:
        result = await self._col.delete_many({"user_id": user_id})
        return result.deleted_count
