"""Phase 5B: Trust, security, and user data control.

Verifies the now-authenticated ChronOS engine endpoints:
  - Unauthenticated requests are rejected (401)
  - Data access is scoped to the authenticated user (cross-user isolation)
  - Export returns only the current user's data, with no embeddings
  - Delete removes only the current user's data (no orphaned temporal events)
  - Storage-level delete_all_for_user behaviour for the InMemory paths
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from chronos_engine.core.models import (
    InteractionRecord,
    MemoryItem,
    PatternCategory,
    PatternItem,
    TimelineEvent,
)
from chronos_engine.engine import ChronosEngine
from chronos_engine.storage import InMemoryStorageAdapter, InMemoryTemporalStore
from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)
from opentime.main import app
from tests.conftest import AUTH_USER_ID, OTHER_AUTH_USER_ID

PREFIX = "/api/v1/chronos/engine"
BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _patch_engine(storage: InMemoryStorageAdapter, store: InMemoryTemporalStore):
    engine = ChronosEngine(storage=storage, temporal_store=store)
    return patch("chronos_engine.api.router.engine_instance", engine)


class _FakeDb:
    """Minimal async fake DB that records delete_many calls per collection."""

    def __init__(self) -> None:
        self.deleted: dict[str, list] = {}

    def __getitem__(self, name: str) -> "_FakeCollection":
        return _FakeCollection(self.deleted, name)


class _FakeCollection:
    def __init__(self, store: dict, name: str) -> None:
        self._store = store
        self._name = name

    async def delete_many(self, query: dict) -> None:
        self._store.setdefault(self._name, []).append(query)


def _noop_upload_dir():
    return Path("/tmp/opencode-nonexistent-upload")


async def _make_thread(store, user_id, subject="Thread"):
    t = TemporalThread(
        user_id=user_id,
        subject=subject,
        status=TemporalThreadStatus.OPEN,
        temporal_type=TemporalType.DECISION,
    )
    return await store.save_thread(t)


async def _make_event(store, thread_id, user_id, description="event"):
    e = TemporalEvent(
        thread_id=thread_id,
        user_id=user_id,
        description=description,
        temporal_type=TemporalType.DECISION,
        occurred_at=BASE + timedelta(days=1),
    )
    return await store.save_event(e)


async def _seed_user(storage, user_id):
    await storage.save_memory(
        MemoryItem(
            id=f"mem_{user_id}",
            user_id=user_id,
            content=f"memory for {user_id}",
            timestamp=BASE + timedelta(days=1),
            importance_score=0.8,
        )
    )
    await storage.save_timeline_event(
        TimelineEvent(
            id=f"tl_{user_id}",
            user_id=user_id,
            title=f"timeline for {user_id}",
            description="desc",
            timestamp=BASE + timedelta(days=1),
        )
    )
    await storage.save_pattern(
        PatternItem(
            id=f"pat_{user_id}",
            user_id=user_id,
            category=PatternCategory.HABIT,
            title=f"pattern for {user_id}",
            description="desc",
            confidence_score=0.9,
        )
    )


class TestUnauthenticated:
    """Endpoints now require a valid bearer token."""

    async def test_memories_requires_auth(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"{PREFIX}/memories")
        assert resp.status_code == 401

    async def test_export_requires_auth(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"{PREFIX}/export")
        assert resp.status_code == 401

    async def test_delete_requires_auth(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(PREFIX)
        assert resp.status_code == 401


class TestCrossUserIsolation:
    """A user can only see their own engine data via the API."""

    async def test_memories_are_scoped(self, override_auth):
        storage = InMemoryStorageAdapter()
        await _seed_user(storage, AUTH_USER_ID)
        await _seed_user(storage, OTHER_AUTH_USER_ID)

        with _patch_engine(storage, InMemoryTemporalStore()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"{PREFIX}/memories")
        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()]
        assert f"mem_{AUTH_USER_ID}" in ids
        assert f"mem_{OTHER_AUTH_USER_ID}" not in ids

    async def test_threads_of_other_user_invisible(self, override_auth):
        store = InMemoryTemporalStore()
        other = await _make_thread(store, OTHER_AUTH_USER_ID, subject="secret story")

        with _patch_engine(InMemoryStorageAdapter(), store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"{PREFIX}/threads")
                assert resp.status_code == 200
                assert all(t["id"] != other.id for t in resp.json())

                resp2 = await client.get(f"{PREFIX}/threads/{other.id}")
                assert resp2.status_code == 404


class TestExport:
    """Export returns only the authenticated user's data and no embeddings."""

    async def test_export_contains_own_data_only(self, override_auth):
        storage = InMemoryStorageAdapter()
        await _seed_user(storage, AUTH_USER_ID)
        await _seed_user(storage, OTHER_AUTH_USER_ID)

        with _patch_engine(storage, InMemoryTemporalStore()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"{PREFIX}/export")
        assert resp.status_code == 200
        data = resp.json()

        own = {m["id"] for m in data["memories"]}
        assert f"mem_{AUTH_USER_ID}" in own
        assert f"mem_{OTHER_AUTH_USER_ID}" not in own

        for m in data["memories"]:
            assert "embedding" not in m

    async def test_export_includes_user_id(self, override_auth):
        storage = InMemoryStorageAdapter()
        with _patch_engine(storage, InMemoryTemporalStore()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"{PREFIX}/export")
        assert resp.status_code == 200
        assert resp.json()["user_id"] == AUTH_USER_ID


class TestDelete:
    """Delete removes only the authenticated user's engine data."""

    async def test_delete_only_removes_own_data(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        await _seed_user(storage, AUTH_USER_ID)
        await _seed_user(storage, OTHER_AUTH_USER_ID)
        own_thread = await _make_thread(store, AUTH_USER_ID)
        await _make_event(store, own_thread.id, AUTH_USER_ID)
        other_thread = await _make_thread(store, OTHER_AUTH_USER_ID)
        await _make_event(store, other_thread.id, OTHER_AUTH_USER_ID)

        with _patch_engine(storage, store), patch(
            "chronos_engine.api.router.get_mongo_db", return_value=_FakeDb()
        ), patch(
            "chronos_engine.api.router._upload_dir", return_value=_noop_upload_dir()
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(PREFIX)
        assert resp.status_code == 204

        assert f"mem_{OTHER_AUTH_USER_ID}" in {
            m.id for m in await storage.get_memories_by_user(OTHER_AUTH_USER_ID)
        }
        assert await store.get_thread(other_thread.id, OTHER_AUTH_USER_ID) is not None
        assert len(await store.get_events_by_thread(other_thread.id, OTHER_AUTH_USER_ID)) == 1

        assert await storage.get_memories_by_user(AUTH_USER_ID) == []
        assert await store.get_thread(own_thread.id, AUTH_USER_ID) is None
        assert len(await store.get_events_by_thread(own_thread.id, AUTH_USER_ID)) == 0


class TestStorageDeleteAllForUser:
    """Storage-level delete_all_for_user behaviour."""

    async def test_inmemory_store_clears_threads_events_and_ownership(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, AUTH_USER_ID)
        await _make_event(store, t.id, AUTH_USER_ID)
        await _make_event(store, t.id, AUTH_USER_ID)

        await store.delete_all_for_user(AUTH_USER_ID)

        assert await store.get_thread(t.id, AUTH_USER_ID) is None
        assert await store.get_events_by_thread(t.id, AUTH_USER_ID) == []

    async def test_inmemory_storage_clears_all_collections(self):
        storage = InMemoryStorageAdapter()
        await storage.save_memory(
            MemoryItem(
                id="m1", user_id=AUTH_USER_ID, content="x",
                timestamp=BASE, importance_score=0.5,
            )
        )
        await storage.save_interaction(
            InteractionRecord(
                id="r1", user_id=AUTH_USER_ID, user_content="u",
                final_response="f", provider_name="chron", model_name="m",
            )
        )

        await storage.delete_all_for_user(AUTH_USER_ID)

        assert await storage.get_memories_by_user(AUTH_USER_ID) == []
        assert await storage.get_interactions_by_user(AUTH_USER_ID) == []
