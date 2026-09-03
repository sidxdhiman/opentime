"""Phase 5G-C: legacy backfill migration tests.

The engine stores are authoritative. Users who onboarded before 5G-C may hold
application-store data (memories / identity_states / timeline_events /
patterns) with no engine records. The ``LegacyBackfillService`` is an
idempotent, user-scoped, additive migration that copies that data into the
engine stores without a runtime fallback.

These tests pin down the migration contract:
  1. legacy app-only data -> migration -> engine data exists
  2. migration -> migration again -> no duplicates / no overwrite
  3. existing newer engine data -> migration -> engine state is NOT
     overwritten by stale app data
  4. User A legacy data -> migration -> User B unaffected
  5. dry-run does not write
"""

from datetime import UTC, datetime

import pytest

from chronos_engine.core.models import IdentityProfile, MemoryItem
from opentime.application.migration.legacy_backfill import LegacyBackfillService
from opentime.domain.chronos.entities import (
    ClaimType,
    ContentType,
    IdentityState,
    IdentityTrait,
    PatternType,
    TypedClaim,
)
from opentime.domain.chronos.entities import (
    Memory as AppMemory,
)
from opentime.domain.chronos.entities import (
    Pattern as AppPattern,
)
from opentime.domain.chronos.entities import (
    TimelineEvent as AppTimelineEvent,
)
from opentime.infrastructure.mongodb.chronos_repos import (
    MongoIdentityStateRepository,
    MongoMemoryRepository,
    MongoPatternRepository,
    MongoTimelineRepository,
)
from tests.conftest import AUTH_USER_ID, OTHER_AUTH_USER_ID

BASE = datetime(2026, 1, 1, tzinfo=UTC)


async def _count(db, collection, query=None):
    return await db[collection].count_documents(query or {})


@pytest.fixture
def service(mock_db):
    return LegacyBackfillService(mock_db)


async def _seed_legacy_user(db, user_id, *, content="legacy memory", has_identity=True):
    """Seed a fully-populated legacy application-store user (no engine data)."""
    mem_repo = MongoMemoryRepository(db)
    identity_repo = MongoIdentityStateRepository(db)
    timeline_repo = MongoTimelineRepository(db)
    pattern_repo = MongoPatternRepository(db)

    await mem_repo.create(
        AppMemory(
            user_id=user_id,
            content=content,
            content_type=ContentType.TEXT,
            source="genesis",
            importance=1.0,
            is_genesis=True,
        )
    )
    await mem_repo.create(
        AppMemory(
            user_id=user_id,
            content=f"secondary memory for {user_id}",
            content_type=ContentType.TEXT,
            source="onboarding",
            importance=0.6,
            is_genesis=False,
        )
    )

    if has_identity:
        await identity_repo.create(
            IdentityState(
                user_id=user_id,
                version=3,
                traits=[IdentityTrait(
                    trait="persistent",
                    claim_type=ClaimType.FACT,
                    confidence=0.9,
                )],
                interests=[TypedClaim(
                    value="coding",
                    claim_type=ClaimType.FACT,
                    confidence=0.9,
                )],
                values=[TypedClaim(
                    value="curiosity",
                    claim_type=ClaimType.FACT,
                    confidence=0.9,
                )],
                valid_from=BASE,
            )
        )

    await timeline_repo.create(
        AppTimelineEvent(
            user_id=user_id,
            event_time=BASE,
            title="Started project",
            description="kicked off",
            category="milestone",
            source_memory_id=None,
        )
    )

    await pattern_repo.create(
        AppPattern(
            user_id=user_id,
            type=PatternType.BASELINE,
            pattern="tends to focus deeply",
            confidence=0.4,
            source_memory_ids=[],
        )
    )


class TestLegacyMigration:
    async def test_legacy_app_data_backfills_engine(self, service, mock_db):
        await _seed_legacy_user(mock_db, AUTH_USER_ID)

        result = await service.backfill_user(AUTH_USER_ID)

        assert result.memories_migrated == 2
        assert result.identity_created is True
        assert result.timeline_migrated == 1
        assert result.patterns_migrated == 1

        assert await _count(mock_db, "engine_memories", {"user_id": AUTH_USER_ID}) == 2
        genesis = await mock_db["engine_memories"].find_one(
            {"user_id": AUTH_USER_ID, "is_genesis": True}
        )
        assert genesis is not None

        profile = await mock_db["engine_identity"].find_one({"user_id": AUTH_USER_ID})
        assert profile is not None
        assert profile["skills"] == ["persistent"]
        assert profile["interests"] == ["coding"]
        assert profile["values"] == ["curiosity"]
        assert profile["version"] == 3

        assert await _count(mock_db, "engine_timeline", {"user_id": AUTH_USER_ID}) == 1
        assert await _count(mock_db, "engine_patterns", {"user_id": AUTH_USER_ID}) == 1

    async def test_migration_is_idempotent_no_duplicates(self, service, mock_db):
        await _seed_legacy_user(mock_db, AUTH_USER_ID)

        first = await service.backfill_user(AUTH_USER_ID)
        second = await service.backfill_user(AUTH_USER_ID)

        # Second pass migrates nothing new and skips everything already present.
        assert second.memories_migrated == 0
        assert second.memories_skipped == 2
        assert second.identity_created is False
        assert second.identity_skipped is True
        assert second.timeline_migrated == 0
        assert second.patterns_migrated == 0

        assert await _count(mock_db, "engine_memories", {"user_id": AUTH_USER_ID}) == 2
        assert await _count(mock_db, "engine_identity", {"user_id": AUTH_USER_ID}) == 1
        assert await _count(mock_db, "engine_timeline", {"user_id": AUTH_USER_ID}) == 1
        assert await _count(mock_db, "engine_patterns", {"user_id": AUTH_USER_ID}) == 1
        # First run migrates everything; second run is a no-op (no duplicates).
        assert first.memories_migrated == 2 and second.memories_migrated == 0
        assert (first.memories_migrated
                + first.timeline_migrated
                + first.patterns_migrated
                + int(first.identity_created)) == 5

    async def test_newer_engine_state_not_overwritten(self, service, mock_db):
        # Legacy memory that ALSO exists in the engine with NEWER content.
        mem_repo = MongoMemoryRepository(mock_db)
        legacy_mem = await mem_repo.create(
            AppMemory(
                user_id=AUTH_USER_ID,
                content="STALE legacy content",
                source="genesis",
                importance=1.0,
                is_genesis=True,
            )
        )
        # Engine already progressed: same id, different (newer) content.
        await mock_db["engine_memories"].replace_one(
            {"id": legacy_mem.id, "user_id": AUTH_USER_ID},
            MemoryItem(
                id=legacy_mem.id,
                user_id=AUTH_USER_ID,
                content="NEWER engine content",
                memory_type="episodic",
                is_genesis=False,
            ).model_dump(mode="json"),
            upsert=True,
        )
        # Engine identity already exists (newer).
        await mock_db["engine_identity"].replace_one(
            {"user_id": AUTH_USER_ID},
            IdentityProfile(
                user_id=AUTH_USER_ID,
                interests=["engine-interest"],
                skills=["engine-skill"],
                version=9,
            ).model_dump(mode="json"),
            upsert=True,
        )

        result = await service.backfill_user(AUTH_USER_ID)

        # Memory not overwritten (skipped because id already exists in engine).
        assert result.memories_migrated == 0
        doc = await mock_db["engine_memories"].find_one({"id": legacy_mem.id})
        assert doc["content"] == "NEWER engine content"
        # Identity not overwritten (skipped because engine identity exists).
        assert result.identity_created is False
        assert result.identity_skipped is True
        prof = await mock_db["engine_identity"].find_one({"user_id": AUTH_USER_ID})
        assert prof["version"] == 9
        assert prof["skills"] == ["engine-skill"]

    async def test_user_isolation(self, service, mock_db):
        await _seed_legacy_user(mock_db, AUTH_USER_ID, content="A legacy")
        await _seed_legacy_user(mock_db, OTHER_AUTH_USER_ID, content="B legacy")

        await service.backfill_user(AUTH_USER_ID)

        # User B's engine store is untouched (no duplicates, no partial data).
        assert await _count(mock_db, "engine_memories", {"user_id": OTHER_AUTH_USER_ID}) == 0
        assert await mock_db["engine_identity"].find_one({"user_id": OTHER_AUTH_USER_ID}) is None
        # But User A has data.
        assert await _count(mock_db, "engine_memories", {"user_id": AUTH_USER_ID}) == 2

    async def test_backfill_all_returns_summary(self, service, mock_db):
        await _seed_legacy_user(mock_db, AUTH_USER_ID)
        await _seed_legacy_user(mock_db, OTHER_AUTH_USER_ID)

        summary = await service.backfill_all()

        assert summary.users == 2
        assert summary.memories_migrated == 4
        assert summary.identities_created == 2
        assert summary.timeline_migrated == 2
        assert summary.patterns_migrated == 2

    async def test_dry_run_writes_nothing(self, service, mock_db):
        await _seed_legacy_user(mock_db, AUTH_USER_ID)

        result = await service.backfill_user(AUTH_USER_ID, dry_run=True)

        assert result.memories_migrated == 2
        assert result.identity_created is True
        assert result.timeline_migrated == 1
        assert result.patterns_migrated == 1
        # Nothing was actually written to the engine stores.
        assert await _count(mock_db, "engine_memories", {"user_id": AUTH_USER_ID}) == 0
        assert await mock_db["engine_identity"].find_one({"user_id": AUTH_USER_ID}) is None
        assert await _count(mock_db, "engine_timeline", {"user_id": AUTH_USER_ID}) == 0
        assert await _count(mock_db, "engine_patterns", {"user_id": AUTH_USER_ID}) == 0

    async def test_legacy_user_scan_discovery(self, service, mock_db):
        await _seed_legacy_user(mock_db, OTHER_AUTH_USER_ID)
        ids = await service._all_legacy_user_ids()
        assert ids == [OTHER_AUTH_USER_ID]
