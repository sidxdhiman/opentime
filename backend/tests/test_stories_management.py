"""Phase 5E-C tests: Stories n+1 contract and user-controlled Story state.

Covers:

- GET /threads returns enough inline moment data to render Stories in one
  request (the n+1 fix).
- The Stories list/detail responses do not leak internal metadata
  (confidence, importance, origin/related memory ids).
- User-controlled archive/restore is scoped to the authenticated user,
  never mutates deterministic lifecycle status or history, and removes the
  story from active continuation candidates.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

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


def _patch_engine(store):
    engine = ChronosEngine(storage=InMemoryStorageAdapter(), temporal_store=store)
    return patch("chronos_engine.api.router.engine_instance", engine)


async def _make_thread(store, user_id, subject="A story", status=TemporalThreadStatus.OPEN):
    t = TemporalThread(
        user_id=user_id,
        subject=subject,
        status=status,
        temporal_type=TemporalType.DECISION,
        origin_memory_id="mem_origin",
        related_memory_ids=["mem_origin", "mem_rel"],
        importance=0.9,
        confidence=0.77,
    )
    return await store.save_thread(t)


async def _make_event(store, thread_id, user_id, description, at, memory_id="mem_origin"):
    e = TemporalEvent(
        thread_id=thread_id,
        user_id=user_id,
        description=description,
        temporal_type=TemporalType.DECISION,
        memory_id=memory_id,
        occurred_at=at,
        recorded_at=at,
        importance=0.9,
        confidence=0.77,
    )
    return await store.save_event(e)


# ── 1. n+1 data contract ────────────────────────────────────────────────


class TestStoriesDataContract:
    """GET /threads must return enough moment data in one request."""

    async def test_list_requires_auth(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"{PREFIX}/threads")
        assert r.status_code == 401

    async def test_list_includes_moments_inline(self, override_auth):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, AUTH_USER_ID, "changing jobs")
        await _make_event(store, t.id, AUTH_USER_ID, "first moment", BASE)
        await _make_event(store, t.id, AUTH_USER_ID, "later moment", BASE + timedelta(days=5))

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get(f"{PREFIX}/threads")

        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        story = data[0]
        assert story["event_count"] == 2
        # Moments are present inline: renders without a per-story detail call.
        moments = story["events"]
        assert [m["description"] for m in moments] == ["first moment", "later moment"]
        # Chronological ordering preserved.
        assert moments[0]["occurred_at"] <= moments[1]["occurred_at"]

    async def test_no_internal_metadata_leak(self, override_auth):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, AUTH_USER_ID, "private")
        await _make_event(store, t.id, AUTH_USER_ID, "m", BASE)

        for path in (f"{PREFIX}/threads", f"{PREFIX}/threads/{t.id}"):
            with _patch_engine(store):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    r = await client.get(path)
            blob = r.text
            assert "origin_memory_id" not in blob
            assert "related_memory_ids" not in blob
            assert "confidence" not in blob
            assert "importance" not in blob
            assert "mem_origin" not in blob
            assert "thread_id" not in blob

    async def test_list_user_isolation(self, override_auth):
        store = InMemoryTemporalStore()
        await _make_thread(store, AUTH_USER_ID, "my story")
        await _make_thread(store, OTHER_AUTH_USER_ID, "their secret")

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get(f"{PREFIX}/threads")
        assert [s["subject"] for s in r.json()] == ["my story"]


# ── 2. Story user-controlled archive / restore ──────────────────────────


class TestStoryManagement:
    """Archive/restore is user-scoped, non-destructive and presentation-only."""

    async def test_owner_can_archive_and_restore(self, override_auth):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, AUTH_USER_ID, "my story")
        await _make_event(store, t.id, AUTH_USER_ID, "moment", BASE)

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                archived = await client.post(f"{PREFIX}/threads/{t.id}/archive")
                restored = await client.post(f"{PREFIX}/threads/{t.id}/restore")

        assert archived.status_code == 200
        assert archived.json()["user_archived"] is True
        assert restored.status_code == 200
        assert restored.json()["user_archived"] is False

    async def test_archive_preserves_deterministic_status_and_history(self, override_auth):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, AUTH_USER_ID, "story")
        await _make_event(store, t.id, AUTH_USER_ID, "the moment", BASE)

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post(f"{PREFIX}/threads/{t.id}/archive")

        # The underlying lifecycle status still reads OPEN and events intact.
        fetched = await store.get_thread(t.id, AUTH_USER_ID)
        assert fetched.status == TemporalThreadStatus.OPEN
        assert fetched.user_archived is True
        events = await store.get_events_by_thread(t.id, AUTH_USER_ID)
        assert [e.description for e in events] == ["the moment"]

    async def test_foreign_user_cannot_archive(self, override_auth):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, OTHER_AUTH_USER_ID, "their story")

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.post(f"{PREFIX}/threads/{t.id}/archive")

        assert r.status_code == 404
        fetched = await store.get_thread(t.id, OTHER_AUTH_USER_ID)
        assert fetched.user_archived is False

    async def test_nonexistent_story_returns_404(self, override_auth):
        store = InMemoryTemporalStore()
        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.post(f"{PREFIX}/threads/thread_nope/archive")
        assert r.status_code == 404

    async def test_archive_removes_story_from_continuation_candidates(self, override_auth):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, AUTH_USER_ID, "story")

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post(f"{PREFIX}/threads/{t.id}/archive")

        # The lifecycle matcher must no longer consider this an active candidate.
        candidates = await store.get_candidate_threads(AUTH_USER_ID)
        assert [c.id for c in candidates] == []

    async def test_restored_story_is_candidate_again(self, override_auth):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, AUTH_USER_ID, "story")

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post(f"{PREFIX}/threads/{t.id}/archive")
                await client.post(f"{PREFIX}/threads/{t.id}/restore")

        candidates = await store.get_candidate_threads(AUTH_USER_ID)
        assert [c.id for c in candidates] == [t.id]
