"""Phase 5D tests: return-context API contract and data flow.

Verifies the ``GET /chronos/engine/return-context`` endpoint returns a
grounded, user-scoped context; that cross-user data never leaks; that the
in-app return-hook preference (``PATCH``) maps to real behavior; and that
deleted data cannot resurface.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from chronos_engine.core.models import InteractionRecord
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


async def _make_thread(store, user_id, subject="Story", status=TemporalThreadStatus.OPEN):
    t = TemporalThread(
        user_id=user_id,
        subject=subject,
        status=status,
        temporal_type=TemporalType.DECISION,
    )
    return await store.save_thread(t)


async def _make_event(store, thread_id, user_id, description, at):
    e = TemporalEvent(
        thread_id=thread_id,
        user_id=user_id,
        description=description,
        temporal_type=TemporalType.DECISION,
        occurred_at=at,
        recorded_at=at,
    )
    return await store.save_event(e)


async def _setup_user(store, user_id, now):
    """Add an interaction + a progressing story so return context exists."""
    storage = InMemoryStorageAdapter()
    await storage.save_interaction(
        InteractionRecord(
            id=f"i_{user_id}_old",
            user_id=user_id,
            user_content="earlier",
            final_response="ok",
            created_at=now - timedelta(days=3),
        )
    )
    t = await _make_thread(store, user_id, "changing jobs")
    await _make_event(store, t.id, user_id, "considering the move", now - timedelta(days=2))
    await _make_event(store, t.id, user_id, "I decided to move", now - timedelta(hours=1))
    t.status = TemporalThreadStatus.RESOLVED
    await store.save_thread(t)
    return storage


async def test_return_context_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(f"{PREFIX}/return-context")
    assert r.status_code == 401


async def test_return_context_returns_grounded_context(override_auth):
    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    store = InMemoryTemporalStore()
    storage = await _setup_user(store, AUTH_USER_ID, now)

    with _patch_engine(storage, store):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"{PREFIX}/return-context")
    assert r.status_code == 200
    data = r.json()
    assert data["user_kind"] == "MEANINGFULLY_RETURNING"
    assert data["has_return_context"] is True
    assert any(c["change_type"] == "STORY_RESOLVED" for c in data["changes"])
    blob = " ".join(
        [data["welcome"], data.get("summary_section", "")]
        + [c["headline"] + " " + c.get("detail", "") for c in data["changes"]]
        + [data.get("suggested_story_subject", ""), data.get("suggested_story_because", "")]
    )
    assert "mem_" not in blob and "tevent_" not in blob and "_5d" not in blob


async def test_return_context_user_isolation(override_auth):
    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    store = InMemoryTemporalStore()
    storage_a = await _setup_user(store, AUTH_USER_ID, now)

    other = await _make_thread(store, OTHER_AUTH_USER_ID, "private secret")
    await _make_event(
        store, other.id, OTHER_AUTH_USER_ID, "private event", now - timedelta(hours=1)
    )
    other.status = TemporalThreadStatus.RESOLVED
    await store.save_thread(other)

    with _patch_engine(storage_a, store):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"{PREFIX}/return-context")
    data = r.json()
    assert all(c["subject"] != "private secret" for c in data["changes"])


async def test_return_context_duplicate_suppression_and_deletion(override_auth):
    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    store = InMemoryTemporalStore()
    storage = await _setup_user(store, AUTH_USER_ID, now)

    with _patch_engine(storage, store):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.get(f"{PREFIX}/return-context")
            assert first.json()["has_return_context"] is True
            second = await client.get(f"{PREFIX}/return-context")
            assert second.json()["has_return_context"] is False

    await store.delete_all_for_user(AUTH_USER_ID)
    storage = InMemoryStorageAdapter()
    with _patch_engine(storage, store):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"{PREFIX}/return-context")
    assert r.json()["has_return_context"] is False
    assert r.json()["changes"] == []


async def test_return_context_preference_toggle(override_auth):
    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    store = InMemoryTemporalStore()
    storage = await _setup_user(store, AUTH_USER_ID, now)

    with _patch_engine(storage, store):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.patch(f"{PREFIX}/return-context", json={"enabled": False})
            off = await client.get(f"{PREFIX}/return-context")
            assert off.json()["has_return_context"] is False

            await client.patch(f"{PREFIX}/return-context", json={"enabled": True})
            on = await client.get(f"{PREFIX}/return-context")
            assert on.status_code == 200
            assert on.json()["user_kind"] == "MEANINGFULLY_RETURNING"
