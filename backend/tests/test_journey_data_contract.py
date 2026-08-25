"""Phase 4E tests: Journey data contract.

Verifies that the thread/event data exposed through the API is sufficient
for the Journey view, correctly ordered, user-isolated, and free of
fabricated data. Uses InMemoryTemporalStore directly for deterministic tests.
"""

from datetime import UTC, datetime, timedelta

from chronos_engine.storage import InMemoryTemporalStore
from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)

USER_J = "user_4e_journey"
OTHER_J = "user_4e_other"

BASE = datetime(2026, 1, 1, tzinfo=UTC)


# ── Helpers ─────────────────────────────────────────────────────────────


async def _make_thread(
    store, subject, status=TemporalThreadStatus.OPEN,
    ttype=TemporalType.DECISION,
):
    t = TemporalThread(user_id=USER_J, subject=subject, status=status, temporal_type=ttype)
    return await store.save_thread(t)


async def _make_event(
    store, thread_id, description, occurred_at,
    ttype=TemporalType.DECISION, user_id=USER_J,
):
    e = TemporalEvent(
        thread_id=thread_id,
        user_id=user_id,
        description=description,
        temporal_type=ttype,
        occurred_at=occurred_at,
    )
    return await store.save_event(e)


# ── 1. User isolation ──────────────────────────────────────────────────


class TestJourneyUserIsolation:
    """Threads and events from different users never mix."""

    async def test_threads_are_user_isolated(self):
        store = InMemoryTemporalStore()
        t1 = await _make_thread(store, "My story")
        await _make_event(store, t1.id, "Moment A", BASE)

        other = TemporalThread(user_id=OTHER_J, subject="Other story")
        await store.save_thread(other)

        my_threads = await store.get_threads_by_user(USER_J)
        other_threads = await store.get_threads_by_user(OTHER_J)
        assert len(my_threads) == 1
        assert len(other_threads) == 1
        assert my_threads[0].subject == "My story"
        assert other_threads[0].subject == "Other story"

    async def test_events_are_user_isolated(self):
        store = InMemoryTemporalStore()
        t1 = await _make_thread(store, "My thread")
        await _make_event(store, t1.id, "My event", BASE)

        other_thread = TemporalThread(user_id=OTHER_J, subject="Other thread")
        await store.save_thread(other_thread)
        await _make_event(
            store, other_thread.id, "Other event", BASE,
            ttype=TemporalType.GOAL, user_id=OTHER_J,
        )

        my_events = await store.get_events_by_thread(t1.id, USER_J)
        other_events = await store.get_events_by_thread(other_thread.id, OTHER_J)
        assert len(my_events) == 1
        assert my_events[0].description == "My event"
        assert other_events[0].description == "Other event"


# ── 2. Chronological ordering ──────────────────────────────────────────


class TestJourneyOrdering:
    """Thread and event ordering must be deterministic and chronological."""

    async def test_threads_newest_first(self):
        store = InMemoryTemporalStore()
        t1 = await _make_thread(store, "Early thread")
        t1.created_at = BASE
        await store.save_thread(t1)

        t2 = await _make_thread(store, "Late thread")
        t2.created_at = BASE + timedelta(days=10)
        await store.save_thread(t2)

        threads = await store.get_threads_by_user(USER_J)
        subjects = [t.subject for t in threads]
        assert subjects == ["Late thread", "Early thread"]

    async def test_events_chronological_order(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Timeline thread")

        await _make_event(store, t.id, "Third moment", BASE + timedelta(days=20))
        await _make_event(store, t.id, "First moment", BASE)
        await _make_event(store, t.id, "Second moment", BASE + timedelta(days=10))

        events = await store.get_events_by_thread(t.id, USER_J)
        descriptions = [e.description for e in events]
        assert descriptions == ["First moment", "Second moment", "Third moment"]


# ── 3. Event count accuracy ────────────────────────────────────────────


class TestJourneyEventCount:
    """Event count must reflect actual events, not related_memory_ids."""

    async def test_event_count_matches_actual_events(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Counted thread")
        await _make_event(store, t.id, "Event 1", BASE)
        await _make_event(store, t.id, "Event 2", BASE + timedelta(days=1))
        await _make_event(store, t.id, "Event 3", BASE + timedelta(days=2))

        events = await store.get_events_by_thread(t.id, USER_J)
        assert len(events) == 3

    async def test_empty_thread_has_zero_events(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Empty thread")
        events = await store.get_events_by_thread(t.id, USER_J)
        assert len(events) == 0


# ── 4. Thread statuses are grounded ────────────────────────────────────


class TestJourneyThreadStatuses:
    """Thread statuses reflect actual lifecycle states."""

    async def test_all_statuses_represented(self):
        store = InMemoryTemporalStore()
        statuses = [
            TemporalThreadStatus.OPEN,
            TemporalThreadStatus.ACTIVE,
            TemporalThreadStatus.RESOLVED,
            TemporalThreadStatus.CHANGED,
            TemporalThreadStatus.ABANDONED,
        ]
        for status in statuses:
            t = TemporalThread(user_id=USER_J, subject=f"Thread {status.value}", status=status)
            await store.save_thread(t)

        threads = await store.get_threads_by_user(USER_J)
        found = {t.status for t in threads}
        assert found == set(statuses)

    async def test_resolved_thread_preserves_status(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Resolved decision", status=TemporalThreadStatus.RESOLVED)
        fetched = await store.get_thread(t.id, USER_J)
        assert fetched.status == TemporalThreadStatus.RESOLVED


# ── 5. Single-event threads render honestly ────────────────────────────


class TestJourneySingleEvent:
    """Single-event threads are valid and should not be fabricated into stories."""

    async def test_single_event_thread_has_one_event(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Just one moment")
        await _make_event(store, t.id, "The only moment", BASE)

        events = await store.get_events_by_thread(t.id, USER_J)
        assert len(events) == 1
        assert events[0].description == "The only moment"

    async def test_multi_event_thread_preserves_all(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Multi-event story")
        for i in range(5):
            await _make_event(store, t.id, f"Event {i}", BASE + timedelta(days=i))

        events = await store.get_events_by_thread(t.id, USER_J)
        assert len(events) == 5


# ── 6. Temporal types preserved ────────────────────────────────────────


class TestJourneyTemporalTypes:
    """Temporal types on threads and events are preserved through storage."""

    async def test_thread_type_preserved(self):
        store = InMemoryTemporalStore()
        t = TemporalThread(user_id=USER_J, subject="Goal thread", temporal_type=TemporalType.GOAL)
        await store.save_thread(t)
        fetched = await store.get_thread(t.id, USER_J)
        assert fetched.temporal_type == TemporalType.GOAL

    async def test_event_type_preserved(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Typed thread")
        await _make_event(store, t.id, "Typed event", BASE, ttype=TemporalType.FEAR)
        fetched_events = await store.get_events_by_thread(t.id, USER_J)
        assert fetched_events[0].temporal_type == TemporalType.FEAR


# ── 7. No fabricated data ──────────────────────────────────────────────


class TestJourneyNoFabrication:
    """The journey data must not contain fabricated information."""

    async def test_empty_user_gets_empty_threads(self):
        store = InMemoryTemporalStore()
        threads = await store.get_threads_by_user("user_with_no_data")
        assert threads == []

    async def test_thread_without_events_has_empty_event_list(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Thread without events")
        events = await store.get_events_by_thread(t.id, USER_J)
        assert events == []

    async def test_description_and_subject_are_preserved(self):
        store = InMemoryTemporalStore()
        t = TemporalThread(
            user_id=USER_J,
            subject="Should I leave my job?",
            description="A decision thread about career change",
            temporal_type=TemporalType.DECISION,
        )
        await store.save_thread(t)
        fetched = await store.get_thread(t.id, USER_J)
        assert fetched.subject == "Should I leave my job?"
        assert fetched.description == "A decision thread about career change"
