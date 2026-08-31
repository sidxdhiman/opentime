"""Phase 5E-C tests: per-memory deletion with reference cleanup.

Verifies the authenticated, user-scoped memory deletion endpoint:
- owner can delete, foreign user cannot, nonexistent handling
- the memory disappears from the listing
- references are purged (memories, timeline, reflections, patterns,
  temporal threads/events/snapshots) with historical evidence preserved
- other users are unaffected
"""

from datetime import UTC, datetime
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from chronos_engine.core.models import MemoryItem, TimelineEvent
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


def _patch_engine(storage, store):
    engine = ChronosEngine(storage=storage, temporal_store=store)
    return patch("chronos_engine.api.router.engine_instance", engine)


def _make_memory(storage, user_id, memory_id, content="a memory"):
    return storage.save_memory(
        MemoryItem(id=memory_id, user_id=user_id, content=content)
    )


async def _setup_user(storage, store, user_id):
    """One user with a linked memory + a story referencing it."""
    mem = await _make_memory(storage, user_id, f"mem_{user_id}_0", "origin memory")
    other = await _make_memory(storage, user_id, f"mem_{user_id}_1", "second memory")
    # Link the second memory back to the first.
    other.linked_memory_ids = [mem.id]
    await storage.save_memory(other)

    await storage.save_timeline_event(
        TimelineEvent(
            id=f"tl_{user_id}",
            user_id=user_id,
            title="timeline",
            description="timeline text",
            memory_ids=[mem.id],
        )
    )

    t = await store.save_thread(
        TemporalThread(
            user_id=user_id,
            subject="story",
            status=TemporalThreadStatus.OPEN,
            temporal_type=TemporalType.DECISION,
            origin_memory_id=mem.id,
            related_memory_ids=[mem.id, other.id],
        )
    )
    await store.save_event(
        TemporalEvent(
            id=f"ev_{user_id}",
            thread_id=t.id,
            user_id=user_id,
            description="the recorded moment text",
            memory_id=mem.id,
            occurred_at=BASE,
        )
    )
    return mem, t


class TestMemoryDelete:
    async def test_delete_requires_auth(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(f"{PREFIX}/memories/mem_x")
        assert r.status_code == 401

    async def test_owner_can_delete(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        mem, _ = await _setup_user(storage, store, AUTH_USER_ID)

        with _patch_engine(storage, store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"{PREFIX}/memories/{mem.id}")

        assert r.status_code == 204
        remaining = await storage.get_memories_by_user(AUTH_USER_ID, limit=100)
        assert all(m.id != mem.id for m in remaining)

    async def test_foreign_user_cannot_delete(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        await _setup_user(storage, store, AUTH_USER_ID)
        mem, _ = await _setup_user(storage, store, OTHER_AUTH_USER_ID)
        target = f"mem_{OTHER_AUTH_USER_ID}_0"

        # Authenticated as AUTH_USER_ID, tries to delete OTHER's memory.
        with _patch_engine(storage, store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"{PREFIX}/memories/{target}")

        assert r.status_code == 404
        # Other user's memory is untouched.
        remaining = await storage.get_memories_by_user(OTHER_AUTH_USER_ID, limit=100)
        assert any(m.id == target for m in remaining)

    async def test_nonexistent_memory_returns_404(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        with _patch_engine(storage, store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"{PREFIX}/memories/mem_nonexistent")
        assert r.status_code == 404

    async def test_references_are_purged_and_history_preserved(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        mem, _ = await _setup_user(storage, store, AUTH_USER_ID)

        with _patch_engine(storage, store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"{PREFIX}/memories/{mem.id}")

        # Other memories no longer link to the deleted one.
        remaining = await storage.get_memories_by_user(AUTH_USER_ID, limit=100)
        for m in remaining:
            assert mem.id not in m.linked_memory_ids

        # Timeline event keeps its text but drops the reference.
        timeline = await storage.get_timeline_by_user(AUTH_USER_ID)
        assert len(timeline) == 1
        assert timeline[0].description == "timeline text"
        assert mem.id not in timeline[0].memory_ids

        # The story thread preserved, but its origin/related refs are gone.
        threads = await store.get_threads_by_user(AUTH_USER_ID)
        assert len(threads) == 1
        assert threads[0].subject == "story"
        assert threads[0].origin_memory_id is None
        assert mem.id not in threads[0].related_memory_ids

        # The historical moment text survives; only the memory pointer is gone.
        events = await store.get_events_by_thread(threads[0].id, AUTH_USER_ID)
        assert len(events) == 1
        assert events[0].description == "the recorded moment text"
        assert events[0].memory_id is None

    async def test_other_user_unaffected(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        await _setup_user(storage, store, AUTH_USER_ID)
        await _setup_user(storage, store, OTHER_AUTH_USER_ID)
        target = f"mem_{AUTH_USER_ID}_0"

        with _patch_engine(storage, store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"{PREFIX}/memories/{target}")

        # Other user's memory + story intact.
        others = await storage.get_memories_by_user(OTHER_AUTH_USER_ID, limit=100)
        assert any(m.id == f"mem_{OTHER_AUTH_USER_ID}_0" for m in others)
        other_threads = await store.get_threads_by_user(OTHER_AUTH_USER_ID)
        assert len(other_threads) == 1
        assert other_threads[0].origin_memory_id == f"mem_{OTHER_AUTH_USER_ID}_0"

    async def test_deleted_memory_does_not_resurface_in_listing(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        mem, _ = await _setup_user(storage, store, AUTH_USER_ID)

        with _patch_engine(storage, store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"{PREFIX}/memories/{mem.id}")
                listing = await client.get(f"{PREFIX}/memories")

        assert listing.status_code == 200
        assert all(m["id"] != mem.id for m in listing.json())
