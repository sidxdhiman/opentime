"""Phase 5G-C: Data architecture consistency & source-of-truth hardening.

The ChronOS engine stores (engine_*) are the authoritative source for
memories, identity, timeline events and patterns. The app-layer stores
must NOT be treated as an independent second truth for these entities.

These tests prove Dashboard (engine endpoints) and My Data
(app endpoints) observe the SAME underlying engine store, and that
mutations/deletions/archives are reflected consistently across both
views without any write-synchronization mechanism.

Covers:
  1. Dashboard and My Data return the same memory data (engine source).
  2. Dashboard and My Data return the same identity data (engine source).
  3. Dashboard and My Data return the same timeline data (engine source).
  4. Dashboard and My Data return the same pattern data (engine source).
  5. A mutation (edited traits / genesis / new memory) is reflected in both.
  6. Delete memory is reflected consistently (no app-store resurrection).
  7. Reload (a fresh engine read) preserves state.
  8. Cross-user isolation: User A cannot see or affect User B's data.
  9. A deleted engine genesis never resurrects from the app store (no fallback).
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from chronos_engine.core.models import (
    IdentityProfile,
    MemoryItem,
    MemoryType,
    PatternCategory,
    PatternItem,
    TimelineEvent,
)
from chronos_engine.engine import ChronosEngine
from chronos_engine.storage import InMemoryStorageAdapter, InMemoryTemporalStore
from opentime.api.dependencies import get_current_user
from opentime.domain.chronos.entities import ContentType
from opentime.domain.chronos.entities import Memory as AppMemory
from opentime.infrastructure.mongodb.chronos_repos import MongoMemoryRepository
from opentime.main import app
from tests.conftest import (
    AUTH_USER_ID,
    OTHER_AUTH_USER_ID,
    make_user_response,
)

ENGINE_PREFIX = "/api/v1/chronos/engine"
APP_PREFIX = "/api/v1/chronos"


async def _find_genesis(engine, user_id):
    """Return the authoritative engine genesis MemoryItem for a user, or None."""
    memories = await engine.storage.get_memories_by_user(user_id, limit=500)
    return next((m for m in memories if m.is_genesis), None)


def _make_engine(storage=None, store=None):
    return ChronosEngine(
        storage=storage or InMemoryStorageAdapter(),
        temporal_store=store or InMemoryTemporalStore(),
    )


@pytest.fixture
def engine():
    """An in-memory engine whose storage is shared via module singleton patch."""
    storage = InMemoryStorageAdapter()
    store = InMemoryTemporalStore()
    eng = _make_engine(storage, store)
    with patch("chronos_engine.api.router.engine_instance", eng):
        yield eng


async def _seed_engine_data(eng, user_id):
    """Seed a representative engine memory, timeline, identity and pattern."""
    await eng.storage.save_memory(
        MemoryItem(
            id=f"mem_{user_id}",
            user_id=user_id,
            content=f"Memory for {user_id}",
            memory_type=MemoryType.EPISODIC,
            importance_score=0.8,
            is_genesis=True,
        )
    )
    await eng.storage.save_timeline_event(
        TimelineEvent(
            id=f"tl_{user_id}",
            user_id=user_id,
            title="A timeline event",
            description="desc",
        )
    )
    await eng.storage.save_identity(
        IdentityProfile(
            user_id=user_id,
            interests=["coding"],
            values=["curiosity"],
            skills=["persistent"],
            version=1,
        )
    )
    await eng.storage.save_pattern(
        PatternItem(
            id=f"pat_{user_id}",
            user_id=user_id,
            category=PatternCategory.HABIT,
            title="baseline",
            description="Pattern for user",
            confidence_score=0.5,
        )
    )


class TestMyDataReadsEngineSource:
    """My Data endpoints must read from the same engine store as the dashboard."""

    async def test_memories_are_identical_between_views(self, engine, override_auth):
        await _seed_engine_data(engine, AUTH_USER_ID)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            dash = await client.get(f"{ENGINE_PREFIX}/memories")
            mydata = await client.get(f"{APP_PREFIX}/memories")

        assert dash.status_code == 200 and mydata.status_code == 200
        dash_memories = {m["id"]: m["content"] for m in dash.json()}
        mydata_memories = {m["id"]: m["content"] for m in mydata.json()}
        # The engine memory is present in BOTH views.
        assert dash_memories["mem_" + AUTH_USER_ID] == "Memory for " + AUTH_USER_ID
        assert mydata_memories["mem_" + AUTH_USER_ID] == "Memory for " + AUTH_USER_ID
        # My Data does not fabricate app-only memories when engine data exists.
        assert set(mydata_memories) == set(dash_memories)

    async def test_identity_is_identical_between_views(self, engine, override_auth):
        await _seed_engine_data(engine, AUTH_USER_ID)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            dash = await client.get(f"{ENGINE_PREFIX}/identity")
            mydata = await client.get(f"{APP_PREFIX}/identity")

        assert dash.status_code == 200 and mydata.status_code == 200
        assert dash.json()["skills"] == ["persistent"]
        assert mydata.json()["skills"] == ["persistent"]
        assert mydata.json()["user_id"] == AUTH_USER_ID

    async def test_timeline_is_identical_between_views(self, engine, override_auth):
        await _seed_engine_data(engine, AUTH_USER_ID)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            dash = await client.get(f"{ENGINE_PREFIX}/timeline")
            mydata = await client.get(f"{APP_PREFIX}/timeline")

        assert dash.status_code == 200 and mydata.status_code == 200
        assert [e["title"] for e in dash.json()] == ["A timeline event"]
        assert [e["title"] for e in mydata.json()] == ["A timeline event"]

    async def test_patterns_are_identical_between_views(self, engine, override_auth):
        await _seed_engine_data(engine, AUTH_USER_ID)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            dash = await client.get(f"{ENGINE_PREFIX}/patterns")
            mydata = await client.get(f"{APP_PREFIX}/patterns")

        assert dash.status_code == 200 and mydata.status_code == 200
        assert [p["title"] for p in dash.json()] == ["baseline"]
        assert [p["title"] for p in mydata.json()] == ["baseline"]


class TestMutationConsistency:
    """A mutation must be reflected in both views after reload."""

    async def test_edited_traits_reflected_in_both_views(self, engine, override_auth):
        await _seed_engine_data(engine, AUTH_USER_ID)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(
                f"{APP_PREFIX}/identity/traits",
                json={"traits": ["resilient", "curious"]},
            )
            assert resp.status_code == 200

            # Reload both views -> same updated identity.
            mydata = await client.get(f"{APP_PREFIX}/identity")
            dash = await client.get(f"{ENGINE_PREFIX}/identity")

        assert set(mydata.json()["skills"]) == {"resilient", "curious"}
        assert set(dash.json()["skills"]) == {"resilient", "curious"}
        assert mydata.json()["version"] == dash.json()["version"]

    async def test_edited_genesis_reflected_in_engine_store(self, engine, override_auth):
        # Seed the authoritative engine genesis (as onboarding does).
        await engine.storage.save_memory(
            MemoryItem(
                id="gen_edit",
                user_id=AUTH_USER_ID,
                content="Original genesis",
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(
                f"{APP_PREFIX}/genesis", json={"content": "Updated genesis content here"}
            )
            assert resp.status_code == 200
            assert resp.json()["content"] == "Updated genesis content here"

            # The engine store now contains the updated genesis memory.
            dash = await client.get(f"{ENGINE_PREFIX}/memories")
            mydata = await client.get(f"{APP_PREFIX}/memories")

        engine_genesis = next(
            (m for m in dash.json() if m.get("is_genesis")), None
        )
        assert engine_genesis is not None
        assert engine_genesis["content"] == "Updated genesis content here"
        # Both views observe the same authoritative engine genesis.
        mydata_genesis = next(
            (m for m in mydata.json() if m.get("is_genesis")), None
        )
        assert mydata_genesis is not None
        assert mydata_genesis["content"] == "Updated genesis content here"


class TestDeleteConsistency:
    """Delete must clear both views and not resurrect from the app store."""

    async def test_single_memory_delete_reflected_in_mydata(self, engine, override_auth):
        await _seed_engine_data(engine, AUTH_USER_ID)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"{ENGINE_PREFIX}/memories/mem_{AUTH_USER_ID}")
            assert resp.status_code == 204

            dash = await client.get(f"{ENGINE_PREFIX}/memories")
            mydata = await client.get(f"{APP_PREFIX}/memories")

        assert dash.status_code == 200 and mydata.status_code == 200
        assert dash.json() == []
        assert mydata.json() == []

    async def test_delete_all_does_not_resurrect_app_genesis(self, engine, override_auth, mock_db):
        from opentime.api.onboarding_deps import get_db

        async def _dep():
            return mock_db

        # Seed an app-layer genesis memory.
        repo = MongoMemoryRepository(mock_db)
        await repo.create(
            AppMemory(
                user_id=AUTH_USER_ID,
                content="App-only genesis that must stay deleted",
                content_type=ContentType.TEXT,
                source="genesis",
                importance=1.0,
                is_genesis=True,
            )
        )

        # The engine has already progressed with a non-genesis memory, so the
        # engine store is authoritative and an app-layer genesis must NOT be
        # resurrected into My Data.
        await engine.storage.save_memory(
            MemoryItem(
                id="mem_past",
                user_id=AUTH_USER_ID,
                content="A regular memory",
                memory_type=MemoryType.EPISODIC,
                importance_score=0.5,
                is_genesis=False,
            )
        )

        app.dependency_overrides[get_db] = _dep
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                mydata = await client.get(f"{APP_PREFIX}/memories")
        finally:
            app.dependency_overrides.pop(get_db, None)

        # The stale app-layer genesis is not resurrected: only the engine memory
        # is surfaced, and it is NOT the deleted-genesis content.
        assert mydata.status_code == 200
        assert [m["content"] for m in mydata.json()] == ["A regular memory"]


class TestReloadPersistence:
    """Re-reading from the engine store preserves the current state."""

    async def test_reload_preserves_engine_state(self, engine, override_auth):
        await _seed_engine_data(engine, AUTH_USER_ID)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.get(f"{APP_PREFIX}/identity")
            second = await client.get(f"{APP_PREFIX}/identity")

        assert first.json()["skills"] == second.json()["skills"]
        assert first.json()["version"] == second.json()["version"]
        assert first.json()["user_id"] == second.json()["user_id"] == AUTH_USER_ID


class TestCrossUserIsolation:
    """User A cannot see or affect User B's engine data via My Data."""

    async def test_mydata_memories_are_user_scoped(self, engine, override_auth):
        await _seed_engine_data(engine, AUTH_USER_ID)
        await _seed_engine_data(engine, OTHER_AUTH_USER_ID)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            mydata = await client.get(f"{APP_PREFIX}/memories")

        contents = [m["content"] for m in mydata.json()]
        assert "Memory for " + OTHER_AUTH_USER_ID not in contents
        assert "Memory for " + AUTH_USER_ID in contents

    async def test_mydata_identity_is_user_scoped(self, engine, override_auth):
        await _seed_engine_data(engine, AUTH_USER_ID)
        await _seed_engine_data(engine, OTHER_AUTH_USER_ID)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            mydata = await client.get(f"{APP_PREFIX}/identity")

        assert mydata.json()["user_id"] == AUTH_USER_ID
        assert mydata.json()["skills"] == ["persistent"]


class TestStorageParity:
    """InMemory and Mongo adapters share the same persistence contract.

    Mongo reconstructs ``MemoryItem(**d)`` from ``model_dump(mode="json")`` (the
    wire/persistence format). The ``is_genesis`` flag added for the engine
    source-of-truth must survive that round-trip unchanged, and the InMemory
    adapter (used everywhere in the engine) must return it identically on
    read-back so both views observe the same document.
    """

    def test_is_genesis_survives_mongo_roundtrip(self):
        original = MemoryItem(
            id="g1",
            user_id=AUTH_USER_ID,
            content="genesis",
            memory_type=MemoryType.EPISODIC,
            is_genesis=True,
        )
        persisted = original.model_dump(mode="json")
        rebuilt = MemoryItem(**persisted)
        assert rebuilt.is_genesis is True
        assert rebuilt.content == "genesis"

    def test_is_genesis_defaults_false(self):
        plain = MemoryItem(
            id="m1", user_id=AUTH_USER_ID, content="non-genesis"
        )
        assert plain.model_dump(mode="json")["is_genesis"] is False

    async def test_inmemory_preserves_is_genesis_on_readback(self):
        storage = InMemoryStorageAdapter()
        await storage.save_memory(
            MemoryItem(
                id="g2",
                user_id=AUTH_USER_ID,
                content="genesis",
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )
        memories = await storage.get_memories_by_user(AUTH_USER_ID)
        assert len(memories) == 1
        assert memories[0].is_genesis is True

    async def test_inmemory_identity_pattern_timeline_roundtrip(self):
        storage = InMemoryStorageAdapter()
        await storage.save_identity(
            IdentityProfile(
                user_id=AUTH_USER_ID,
                interests=["coding"],
                values=["curiosity"],
                skills=["persistent"],
                version=1,
            )
        )
        await storage.save_pattern(
            PatternItem(
                id="p1",
                user_id=AUTH_USER_ID,
                category=PatternCategory.HABIT,
                title="baseline",
                description="d",
                confidence_score=0.5,
            )
        )
        await storage.save_timeline_event(
            TimelineEvent(
                id="t1",
                user_id=AUTH_USER_ID,
                title="event",
                description="d",
            )
        )

        identity = await engine_identity(storage, AUTH_USER_ID)
        assert identity.skills == ["persistent"]
        assert identity.version == 1

        patterns = await storage.get_patterns_by_user(AUTH_USER_ID)
        assert [p.title for p in patterns] == ["baseline"]

        timeline = await storage.get_timeline_by_user(AUTH_USER_ID)
        assert [e.title for e in timeline] == ["event"]


async def engine_identity(storage, user_id):
    engine = ChronosEngine(storage=storage, temporal_store=InMemoryTemporalStore())
    return await engine.get_identity(user_id)


class TestGenesisLifecycle:
    """A deleted engine genesis must NEVER be resurrected from the app store.

    The engine store is the single authoritative source. There is no fallback
    to the application-layer genesis copy. These tests lock that invariant
    down for the full lifecycle: exists -> deleted -> reload -> app copy
    present -> cross-user isolation -> fresh onboarding.
    """

    async def _seed_app_genesis(self, mock_db, content="App-only genesis copy"):
        repo = MongoMemoryRepository(mock_db)
        await repo.create(
            AppMemory(
                user_id=AUTH_USER_ID,
                content=content,
                content_type=ContentType.TEXT,
                source="genesis",
                importance=1.0,
                is_genesis=True,
            )
        )

    async def _with_app_db(self, mock_db):
        from opentime.api.onboarding_deps import get_db

        async def _dep():
            return mock_db

        app.dependency_overrides[get_db] = _dep
        return get_db

    async def _client_memories(self, engine, override_auth, mock_db=None):
        if mock_db is not None:
            get_db = await self._with_app_db(mock_db)
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    return (await client.get(f"{APP_PREFIX}/memories")).json()
            finally:
                app.dependency_overrides.pop(get_db, None)
        else:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return (await client.get(f"{APP_PREFIX}/memories")).json()

    async def _patch_genesis(self, content, user_id=None):
        """PATCH /chronos/genesis. For an explicit ``user_id`` the current-user
        dependency is overridden so a distinct user can attempt the edit."""
        if user_id is not None:

            async def _dep():
                return make_user_response(user_id)

            app.dependency_overrides[get_current_user] = _dep
            try:
                return await self._do_patch(content)
            finally:
                app.dependency_overrides.pop(get_current_user, None)
        return await self._do_patch(content)

    async def _do_patch(self, content):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.patch(
                f"{APP_PREFIX}/genesis", json={"content": content}
            )

    async def test_engine_genesis_exists_is_visible(self, engine, override_auth):
        await engine.storage.save_memory(
            MemoryItem(
                id="gen_1",
                user_id=AUTH_USER_ID,
                content="I was born here",
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )
        memories = await self._client_memories(engine, override_auth)
        assert any(m["id"] == "gen_1" and m["is_genesis"] for m in memories)

    async def test_engine_genesis_deleted_is_not_visible(self, engine, override_auth, mock_db):
        await engine.storage.save_memory(
            MemoryItem(
                id="gen_del",
                user_id=AUTH_USER_ID,
                content="to be deleted",
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )
        # A stale application-store genesis copy still exists.
        await self._seed_app_genesis(mock_db, content="app genesis that must not resurface")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"{ENGINE_PREFIX}/memories/gen_del")
            assert resp.status_code == 204

        # My Data must NOT show the genesis even though the app store still has a copy.
        memories = await self._client_memories(engine, override_auth, mock_db)
        assert memories == []

    async def test_reload_after_deletion_keeps_genesis_deleted(
        self, engine, override_auth, mock_db
    ):
        await engine.storage.save_memory(
            MemoryItem(
                id="gen_reload",
                user_id=AUTH_USER_ID,
                content="reload me",
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )
        await self._seed_app_genesis(mock_db)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.delete(f"{ENGINE_PREFIX}/memories/gen_reload")

        # Reload repeatedly: genesis must never come back from the app copy.
        for _ in range(3):
            memories = await self._client_memories(engine, override_auth, mock_db)
            assert memories == []

    async def test_app_store_genesis_does_not_resurrect_deleted_engine_genesis(
        self, engine, override_auth, mock_db
    ):
        # App-store genesis exists and engine is TOTALLY empty after deletion.
        await engine.storage.save_memory(
            MemoryItem(
                id="gen_x",
                user_id=AUTH_USER_ID,
                content="engine genesis",
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )
        await self._seed_app_genesis(mock_db, content="stale app genesis")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.delete(f"{ENGINE_PREFIX}/memories/gen_x")

        # Even with an empty engine store, the app-store copy never resurfaces.
        memories = await self._client_memories(engine, override_auth, mock_db)
        assert memories == []
        assert all("stale app genesis" not in m["content"] for m in memories)

    async def test_new_user_onboarding_genesis_appears(self, engine, override_auth):
        # Mirror init_service: onboarding writes the genesis to the engine store.
        from chronos_engine.api.router import engine_instance

        # init_service saves an EngineMemoryItem(is_genesis=True) on the engine.
        await engine_instance.storage.save_memory(
            MemoryItem(
                id="onb_gen",
                user_id=AUTH_USER_ID,
                content="Onboarding genesis text",
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )

        memories = await self._client_memories(engine, override_auth)
        assert any(m["id"] == "onb_gen" and m["is_genesis"] for m in memories)
        assert any(m["content"] == "Onboarding genesis text" for m in memories)

    async def test_genesis_cross_user_isolation(self, engine, override_auth, mock_db):
        await engine.storage.save_memory(
            MemoryItem(
                id="gen_a",
                user_id=AUTH_USER_ID,
                content="user A genesis",
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )
        await engine.storage.save_memory(
            MemoryItem(
                id="gen_b",
                user_id=OTHER_AUTH_USER_ID,
                content="user B genesis",
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )
        await self._seed_app_genesis(mock_db)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.delete(f"{ENGINE_PREFIX}/memories/gen_a")

        # User A sees nothing (their genesis was deleted); User B unaffected.
        memories_a = await self._client_memories(engine, override_auth, mock_db)
        assert memories_a == []
        others = await engine.storage.get_memories_by_user(OTHER_AUTH_USER_ID)
        assert [m.id for m in others] == ["gen_b"]


class TestGenesisEditLifecycle:
    """PATCH /genesis must be engine-authoritative and never resurrect.

    The engine genesis is the single source of truth for normal editing. If the
    engine genesis is absent (deleted), PATCH must NOT recreate it from the
    application-layer copy — it returns 404 and the deletion stays permanent.
    Onboarding remains the only path that (re)creates a genesis memory.
    """

    async def _seed_engine_genesis(self, engine, mem_id="gen", content="engine genesis"):
        return await engine.storage.save_memory(
            MemoryItem(
                id=mem_id,
                user_id=AUTH_USER_ID,
                content=content,
                memory_type=MemoryType.EPISODIC,
                is_genesis=True,
            )
        )

    async def _seed_app_genesis(self, mock_db, content="App-only genesis copy"):
        repo = MongoMemoryRepository(mock_db)
        await repo.create(
            AppMemory(
                user_id=AUTH_USER_ID,
                content=content,
                content_type=ContentType.TEXT,
                source="genesis",
                importance=1.0,
                is_genesis=True,
            )
        )

    async def _delete_engine_genesis(self, engine, mem_id):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"{ENGINE_PREFIX}/memories/{mem_id}")
            assert resp.status_code == 204

    async def _patch_genesis(self, content, user_id=None):
        """PATCH /chronos/genesis. For an explicit ``user_id`` the current-user
        dependency is overridden so a distinct user can attempt the edit."""
        if user_id is not None:

            async def _dep():
                return make_user_response(user_id)

            app.dependency_overrides[get_current_user] = _dep
            try:
                return await self._do_patch(content)
            finally:
                app.dependency_overrides.pop(get_current_user, None)
        return await self._do_patch(content)

    async def _do_patch(self, content):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.patch(
                f"{APP_PREFIX}/genesis", json={"content": content}
            )

    # 1. Existing genesis edit: onboarding created engine genesis -> PATCH -> updated.
    async def test_existing_engine_genesis_edit(self, engine, override_auth):
        await self._seed_engine_genesis(engine, mem_id="g_edit1", content="original text")

        resp = await self._patch_genesis("edited text here")
        assert resp.status_code == 200
        assert resp.json()["content"] == "edited text here"

        genesis = await _find_genesis(engine, AUTH_USER_ID)
        assert genesis is not None and genesis.content == "edited text here"

    # 2. Deleted genesis cannot be edited back into existence from the app copy.
    async def test_deleted_engine_genesis_cannot_be_edited_back(
        self, engine, override_auth, mock_db
    ):
        await self._seed_engine_genesis(engine, mem_id="g_del2", content="engine genesis")
        await self._seed_app_genesis(mock_db, content="app genesis must not resurface")

        await self._delete_engine_genesis(engine, "g_del2")

        # PATCH must NOT recreate the engine genesis from the app-store copy.
        resp = await self._patch_genesis("attempt to resurrect")
        assert resp.status_code == 404
        assert await _find_genesis(engine, AUTH_USER_ID) is None

    # 3. Reload after a rejected edit keeps the genesis deleted.
    async def test_reload_after_deleted_genesis_edit_remains_absent(
        self, engine, override_auth, mock_db
    ):
        await self._seed_engine_genesis(engine, mem_id="g_rel2", content="engine genesis")
        await self._seed_app_genesis(mock_db)

        await self._delete_engine_genesis(engine, "g_rel2")
        resp = await self._patch_genesis("attempt to revive deleted genesis")
        assert resp.status_code == 404

        for _ in range(3):
            memories = await engine.storage.get_memories_by_user(AUTH_USER_ID, limit=500)
            assert all(not m.is_genesis for m in memories)

    # 4. New-user bootstrap: onboarding creates the engine genesis, PATCH works.
    async def test_new_user_bootstrap_patch_works(self, engine, override_auth):
        # Mirror onboarding: engine genesis is created through the bootstrap path.
        await self._seed_engine_genesis(engine, mem_id="g_boot", content="onboarding genesis")

        resp = await self._patch_genesis("edited onboarding genesis")
        assert resp.status_code == 200

        genesis = await _find_genesis(engine, AUTH_USER_ID)
        assert genesis is not None and genesis.content == "edited onboarding genesis"

    # 5. Cross-user isolation: one user cannot edit another user's engine genesis.
    async def test_genesis_edit_cross_user_isolated(self, engine, override_auth):
        await self._seed_engine_genesis(engine, mem_id="g_a5", content="user A genesis")
        # User A's on-disk genesis remains the authoritative record.

        # User B has no engine genesis of their own -> 404, cannot touch A's.
        resp = await self._patch_genesis("hijack attempt", user_id=OTHER_AUTH_USER_ID)
        assert resp.status_code == 404

        genesis = await _find_genesis(engine, AUTH_USER_ID)
        assert genesis is not None and genesis.content == "user A genesis"
        others = await engine.storage.get_memories_by_user(OTHER_AUTH_USER_ID, limit=500)
        assert all(not m.is_genesis for m in others)

    # 6. Full lifecycle: create -> edit -> delete -> edit attempt -> retrieve.
    async def test_full_genesis_lifecycle_no_resurrection(
        self, engine, override_auth, mock_db
    ):
        # create (bootstrap through onboarding's engine write)
        await self._seed_engine_genesis(engine, mem_id="g_life", content="born genesis")
        assert (await _find_genesis(engine, AUTH_USER_ID)).content == "born genesis"

        # edit
        resp = await self._patch_genesis("edited life genesis")
        assert resp.status_code == 200
        assert (await _find_genesis(engine, AUTH_USER_ID)).content == "edited life genesis"

        # delete (a stale app-store genesis copy remains)
        await self._seed_app_genesis(mock_db, content="stale app genesis")
        await self._delete_engine_genesis(engine, "g_life")

        # edit attempt -> refused
        resp = await self._patch_genesis("must not appear")
        assert resp.status_code == 404

        # retrieve -> remains deleted, no resurrection from the app copy
        assert await _find_genesis(engine, AUTH_USER_ID) is None
        memories = await engine.storage.get_memories_by_user(AUTH_USER_ID, limit=500)
        assert all(not m.is_genesis for m in memories)

