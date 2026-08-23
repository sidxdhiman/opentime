"""Phase 3A tests: temporal domain foundation.

Covers TemporalType / TemporalThreadStatus serialization, the
TemporalThread / TemporalEvent / TemporalSnapshot data shapes, JSON
round-trips, default handling, and the dormant InMemoryTemporalStore.
No live database and no engine behavior changes are involved — Phase 3A
creates no threads, events or snapshots automatically.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chronos_engine.storage import InMemoryStorageAdapter, InMemoryTemporalStore
from chronos_engine.temporal import (
    TemporalEvent,
    TemporalSnapshot,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)

# ── Enum vocabulary ───────────────────────────────────────────────────────


def test_temporal_type_values():
    assert {t.value for t in TemporalType} == {
        "FUTURE_EXPECTATION",
        "DECISION",
        "GOAL",
        "FEAR",
        "PREDICTION",
        "QUESTION",
        "PROMISE",
        "LIFE_EVENT",
        "BELIEF",
        "MILESTONE",
    }


def test_temporal_thread_status_values():
    assert {s.value for s in TemporalThreadStatus} == {
        "OPEN",
        "ACTIVE",
        "RESOLVED",
        "ABANDONED",
        "CHANGED",
        "ARCHIVED",
    }


@pytest.mark.parametrize(
    ("enum_cls", "value"),
    [
        (TemporalType, "FUTURE_EXPECTATION"),
        (TemporalType, "DECISION"),
        (TemporalType, "LIFE_EVENT"),
        (TemporalThreadStatus, "OPEN"),
        (TemporalThreadStatus, "RESOLVED"),
    ],
)
def test_enum_serialization_round_trip(enum_cls, value):
    """Enums serialize by value and re-hydrate from that value."""
    member = enum_cls(value)
    assert member.value == value
    assert enum_cls(value).name == member.name


# ── TemporalThread ────────────────────────────────────────────────────────


def test_thread_minimal_defaults():
    thread = TemporalThread(user_id="user_t1")
    assert thread.id.startswith("thread_")
    assert thread.status is TemporalThreadStatus.OPEN
    assert thread.temporal_type is None
    assert thread.subject == ""
    assert thread.description is None
    assert thread.origin_memory_id is None
    assert thread.related_memory_ids == []
    assert thread.importance == 0.5
    assert thread.confidence == 0.5
    assert isinstance(thread.created_at, datetime)
    assert isinstance(thread.updated_at, datetime)


def test_thread_with_related_memories():
    """A thread references existing memory IDs without copying content."""
    thread = TemporalThread(
        user_id="user_t1",
        temporal_type=TemporalType.DECISION,
        subject="Leaving my job",
        description="Deliberation about leaving, then the decision itself.",
        origin_memory_id="mem_001",
        related_memory_ids=["mem_001", "mem_145", "mem_290"],
    )
    assert thread.origin_memory_id == "mem_001"
    assert thread.related_memory_ids == ["mem_001", "mem_145", "mem_290"]
    assert thread.temporal_type is TemporalType.DECISION


def test_thread_ids_are_unique_per_instance():
    a, b = TemporalThread(user_id="u"), TemporalThread(user_id="u")
    assert a.id != b.id


# ── TemporalEvent ────────────────────────────────────────────────────────


def test_event_representation():
    occurred = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    event = TemporalEvent(
        thread_id="thread_abc123",
        temporal_type=TemporalType.DECISION,
        description="I actually left my job.",
        memory_id="mem_290",
        occurred_at=occurred,
    )
    assert event.thread_id == "thread_abc123"
    assert event.memory_id == "mem_290"
    assert event.occurred_at == occurred
    assert event.recorded_at >= occurred
    assert event.importance == 0.5
    assert event.confidence == 0.5
    assert event.id.startswith("tevent_")


def test_event_minimal_defaults():
    event = TemporalEvent(thread_id="thread_abc123")
    assert event.description == ""
    assert event.memory_id is None
    assert event.temporal_type is None


# ── TemporalSnapshot ─────────────────────────────────────────────────────


def test_snapshot_representation_with_serializable_user_state():
    """Snapshots carry a serializable state representation, not a typed
    ChronosState import — keeping the temporal package decoupled."""
    snapshot = TemporalSnapshot(
        user_id="user_t1",
        context_description="Moment of deliberation before quitting.",
        memory_id="mem_001",
        user_state={"emotional_state": "UNCERTAIN", "confidence": 0.7},
        relevant_goals=["Find meaningful work"],
        relevant_beliefs=["Stability matters more than passion"],
    )
    assert snapshot.user_state == {"emotional_state": "UNCERTAIN", "confidence": 0.7}
    assert snapshot.relevant_goals == ["Find meaningful work"]
    assert snapshot.relevant_beliefs == ["Stability matters more than passion"]
    assert snapshot.memory_id == "mem_001"
    assert snapshot.id.startswith("tsnap_")
    assert isinstance(snapshot.timestamp, datetime)


def test_snapshot_minimal_defaults():
    snapshot = TemporalSnapshot(user_id="user_t2")
    assert snapshot.context_description == ""
    assert snapshot.user_state is None
    assert snapshot.relevant_goals == []
    assert snapshot.relevant_beliefs == []


# ── Serialization round-trips ────────────────────────────────────────────


@pytest.mark.parametrize(
    "model",
    [
        TemporalThread(
            user_id="user_rt",
            temporal_type=TemporalType.FEAR,
            subject="Public speaking",
            related_memory_ids=["mem_a", "mem_b"],
        ),
        TemporalEvent(
            thread_id="thread_rt",
            temporal_type=TemporalType.PROMISE,
            description="Promised myself to try once.",
            memory_id="mem_c",
        ),
        TemporalSnapshot(
            user_id="user_rt",
            user_state={"valence": -0.2},
            relevant_goals=["G1"],
        ),
    ],
    ids=["thread", "event", "snapshot"],
)
def test_json_round_trip(model):
    payload = model.model_dump(mode="json")
    restored = type(model).model_validate(payload)
    assert restored == model


def test_invalid_enum_value_rejected():
    with pytest.raises(ValidationError):
        TemporalThread(user_id="u", temporal_type="NOT_A_TYPE")
    with pytest.raises(ValidationError):
        TemporalThread(user_id="u", status="FLOATING")


# ── Dormant store (no database) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_inmemory_temporal_store_round_trip_without_db():
    """The temporal contract works standalone — no Mongo, no engine wiring."""
    store = InMemoryTemporalStore()
    thread = TemporalThread(
        user_id="user_store",
        temporal_type=TemporalType.QUESTION,
        origin_memory_id="mem_001",
        related_memory_ids=["mem_001"],
    )

    await store.save_thread(thread)
    fetched = await store.get_thread(thread.id, "user_store")
    assert fetched == thread
    missing = await store.get_thread("thread_nope", "user_store")
    assert missing is None

    older = TemporalEvent(thread_id=thread.id, description="Earlier moment.")
    newer = TemporalEvent(thread_id=thread.id, description="Later moment.")
    newer.occurred_at = older.occurred_at.replace(year=older.occurred_at.year + 1)
    await store.save_event(newer)
    await store.save_event(older)
    events = await store.get_events_by_thread(thread.id, "user_store")
    assert [e.description for e in events] == ["Earlier moment.", "Later moment."]

    snapshot = TemporalSnapshot(user_id="user_store")
    await store.save_snapshot(snapshot)
    snapshots = await store.get_snapshots_by_user("user_store")
    assert snapshots == [snapshot]

    threads = await store.get_threads_by_user("user_store")
    assert threads == [thread]


@pytest.mark.asyncio
async def test_temporal_models_are_isolated_from_storage_and_engine():
    """Phase 3A adds nothing to engine behavior: the classic storage adapter
    still exposes only its original concerns, and temporal types are usable
    without importing the engine at all. (Phase 3D additively extends
    BaseTemporalStore with the lifecycle idempotency lookup.)"""
    adapter = InMemoryStorageAdapter()
    assert not hasattr(adapter, "save_thread")

    from chronos_engine.core.interfaces import BaseTemporalStore
    from chronos_engine.temporal.models import TemporalThread as DirectThread

    assert DirectThread is TemporalThread
    assert BaseTemporalStore.__abstractmethods__ == {
        "save_thread",
        "get_thread",
        "get_threads_by_user",
        "get_candidate_threads",
        "find_thread_by_origin_memory",
        "save_event",
        "get_events_by_thread",
        "save_snapshot",
        "get_snapshots_by_user",
    }
