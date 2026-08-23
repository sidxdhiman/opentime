"""Phase 3D tests: temporal persistence (InMemoryTemporalStore + MongoTemporalStore).

Round-trips for threads and events, user isolation, duplicate guards,
bounded candidate retrieval, and safe reads of older documents with missing
optional fields. Mongo tests follow the existing repository testing
convention: ``mongomock-motor`` injected through the constructor — no live
database required.
"""

from datetime import datetime, timedelta, timezone

import pytest

from chronos_engine.storage import InMemoryTemporalStore
from chronos_engine.storage.mongo_repository import MongoTemporalStore
from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalSnapshot,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)

USER = "user_3d_store"
OTHER = "user_3d_other"


# ── InMemoryTemporalStore lifecycle operations ────────────────────────────


@pytest.mark.asyncio
async def test_inmemory_thread_round_trip_and_update():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Decision about leaving my job")
    saved = await store.save_thread(thread)

    fetched = await store.get_thread(saved.id, USER)
    assert fetched is not None
    assert fetched.subject == "Decision about leaving my job"

    fetched.status = TemporalThreadStatus.RESOLVED
    await store.save_thread(fetched)

    refetched = await store.get_thread(saved.id, USER)
    assert refetched.status is TemporalThreadStatus.RESOLVED
    assert len(await store.get_threads_by_user(USER)) == 1


@pytest.mark.asyncio
async def test_inmemory_event_round_trip_and_attachment_ordering():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Learning guitar")
    await store.save_thread(thread)

    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    early = TemporalEvent(
        thread_id=thread.id, user_id=USER, description="First moment.",
        occurred_at=base + timedelta(days=5),
    )
    late = TemporalEvent(
        thread_id=thread.id, user_id=USER, description="Later moment.",
        occurred_at=base + timedelta(days=1),
    )
    await store.save_event(early)
    await store.save_event(late)

    events = await store.get_events_by_thread(thread.id, USER)
    assert [e.description for e in events] == ["Later moment.", "First moment."]

    # Re-saving the same event id updates in place (no duplicates).
    late.description = "Later moment, corrected."
    await store.save_event(late)
    events = await store.get_events_by_thread(thread.id, USER)
    assert len(events) == 2
    assert events[0].description == "Later moment, corrected."
    assert [e.id for e in events] == [late.id, early.id]


@pytest.mark.asyncio
async def test_inmemory_users_cannot_see_each_others_threads_or_events():
    store = InMemoryTemporalStore()
    thread_a = TemporalThread(user_id=USER, subject="Thread of user A")
    await store.save_thread(thread_a)
    await store.save_event(TemporalEvent(thread_id=thread_a.id, user_id=USER))

    # Thread isolation.
    assert await store.get_thread(thread_a.id, OTHER) is None
    assert await store.get_threads_by_user(OTHER) == []
    assert all(t.user_id == USER for t in await store.get_threads_by_user(USER))

    # Event isolation: even knowing the thread id, other users see nothing.
    assert await store.get_events_by_thread(thread_a.id, OTHER) == []
    assert len(await store.get_events_by_thread(thread_a.id, USER)) == 1


@pytest.mark.asyncio
async def test_inmemory_find_thread_by_origin_memory():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, origin_memory_id="mem_origin")
    await store.save_thread(thread)
    await store.save_thread(TemporalThread(user_id=OTHER, origin_memory_id="mem_theirs"))

    found = await store.find_thread_by_origin_memory(USER, "mem_origin")
    assert found is not None and found.id == thread.id
    assert await store.find_thread_by_origin_memory(USER, "missing") is None
    assert await store.find_thread_by_origin_memory(OTHER, "mem_origin") is None


@pytest.mark.asyncio
async def test_inmemory_candidate_retrieval_stays_bounded_and_live_only():
    store = InMemoryTemporalStore()
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(7):
        await store.save_thread(
            TemporalThread(user_id=USER, created_at=base + timedelta(days=i))
        )
    resolved = TemporalThread(user_id=USER, status=TemporalThreadStatus.RESOLVED)
    abandoned = TemporalThread(user_id=USER, status=TemporalThreadStatus.ABANDONED)
    archived = TemporalThread(user_id=USER, status=TemporalThreadStatus.ARCHIVED)
    foreign = TemporalThread(user_id=OTHER)
    for t in (resolved, abandoned, archived, foreign):
        await store.save_thread(t)

    candidates = await store.get_candidate_threads(USER, limit=3)
    assert len(candidates) == 3
    assert all(t.status is TemporalThreadStatus.OPEN for t in candidates)
    assert candidates[0].created_at > candidates[-1].created_at


# ── MongoTemporalStore (mongomock-motor) ──────────────────────────────────


@pytest.fixture
def mongo_store(mock_db):
    return MongoTemporalStore(mock_db)


@pytest.mark.asyncio
async def test_mongo_thread_round_trip(mongo_store):
    created = datetime(2026, 5, 1, tzinfo=timezone.utc)
    thread = TemporalThread(
        user_id=USER,
        subject="Decision about leaving my job",
        temporal_type=TemporalType.DECISION,
        description="Deliberation about a career move.",
        origin_memory_id="mem_m_1",
        related_memory_ids=["mem_m_1"],
        importance=0.7,
        confidence=0.82,
        created_at=created,
        updated_at=created,
    )
    await mongo_store.save_thread(thread)

    fetched = await mongo_store.get_thread(thread.id, USER)
    assert fetched is not None
    assert fetched.model_dump() == thread.model_dump()   # ids/timestamps preserved
    assert fetched.created_at == created                 # timestamps preserved

    # Update persists.
    fetched.status = TemporalThreadStatus.ACTIVE
    fetched.related_memory_ids.append("mem_m_2")
    await mongo_store.save_thread(fetched)

    refetched = await mongo_store.get_thread(thread.id, USER)
    assert refetched.status is TemporalThreadStatus.ACTIVE
    assert refetched.related_memory_ids == ["mem_m_1", "mem_m_2"]
    assert await mongo_store.get_thread(thread.id, OTHER) is None   # user isolation


@pytest.mark.asyncio
async def test_mongo_event_round_trip_and_user_scoping(mongo_store):
    thread = TemporalThread(user_id=USER, subject="Learning guitar")
    await mongo_store.save_thread(thread)

    event = TemporalEvent(
        thread_id=thread.id,
        user_id=USER,
        temporal_type=TemporalType.GOAL,
        description="Picked up the guitar.",
        memory_id="mem_e_1",
        importance=0.65,
        confidence=0.77,
    )
    await mongo_store.save_event(event)

    events = await mongo_store.get_events_by_thread(thread.id, USER)
    assert len(events) == 1
    assert events[0].model_dump() == event.model_dump()
    assert events[0].memory_id == "mem_e_1"
    assert await mongo_store.get_events_by_thread(thread.id, OTHER) == []


@pytest.mark.asyncio
async def test_mongo_find_thread_by_origin_memory_is_targeted(mongo_store):
    thread = TemporalThread(user_id=USER, origin_memory_id="mem_dup_guard")
    await mongo_store.save_thread(thread)
    await mongo_store.save_thread(TemporalThread(user_id=OTHER, origin_memory_id="mem_x"))

    found = await mongo_store.find_thread_by_origin_memory(USER, "mem_dup_guard")
    assert found is not None and found.id == thread.id
    assert await mongo_store.find_thread_by_origin_memory(USER, "unknown") is None
    assert await mongo_store.find_thread_by_origin_memory(OTHER, "mem_dup_guard") is None


@pytest.mark.asyncio
async def test_mongo_candidates_live_only_bounded_sorted(mongo_store):
    base = datetime(2026, 2, 1, tzinfo=timezone.utc)
    for i in range(4):
        await mongo_store.save_thread(
            TemporalThread(user_id=USER, created_at=base + timedelta(hours=i))
        )
    await mongo_store.save_thread(
        TemporalThread(user_id=USER, status=TemporalThreadStatus.RESOLVED)
    )
    await mongo_store.save_thread(TemporalThread(user_id=OTHER))

    candidates = await mongo_store.get_candidate_threads(USER, limit=2)
    assert len(candidates) == 2
    assert candidates[0].created_at > candidates[1].created_at
    assert all(t.status in (TemporalThreadStatus.OPEN,) for t in candidates)


@pytest.mark.asyncio
async def test_mongo_reads_older_documents_with_missing_fields(mock_db, mongo_store):
    """Older documents written before optional fields existed remain readable:
    every model field has a safe default."""
    await mock_db["engine_temporal_threads"].insert_one(
        {
            "_id": "legacy-thread",
            "id": "legacy-thread",
            "user_id": USER,
            "subject": "An old thread",
            # no status / temporal_type / origin_memory_id / related ids / timestamps
        }
    )
    legacy = await mongo_store.get_thread("legacy-thread", USER)
    assert legacy is not None
    assert legacy.status is TemporalThreadStatus.OPEN
    assert legacy.temporal_type is None
    assert legacy.origin_memory_id is None
    assert legacy.related_memory_ids == []


@pytest.mark.asyncio
async def test_mongo_snapshot_round_trip(mongo_store):
    snapshot = TemporalSnapshot(user_id=USER, context_description="Where things stood.")
    await mongo_store.save_snapshot(snapshot)
    snapshots = await mongo_store.get_snapshots_by_user(USER)
    assert [s.id for s in snapshots] == [snapshot.id]
    assert await mongo_store.get_snapshots_by_user(OTHER) == []
