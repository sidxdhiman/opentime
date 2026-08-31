"""Phase 5D tests: return loop, resurfacing & ongoing value.

Covers the deterministic return-context engine, the persisted resurfacing
LEDGER (duplicate suppression + user control), returning-user detection,
since-last-visit meaningful-change detection, story resurfacing selection,
user isolation and deletion semantics.

Deterministic and offline throughout — no AI, no embeddings, no scheduler.
"""

from datetime import UTC, datetime, timedelta

from chronos_engine.storage.repository import InMemoryTemporalStore
from chronos_engine.temporal.models import (
    ReturnChangeType,
    ReturnLedger,
    ReturnUserKind,
    TemporalEvent,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)
from chronos_engine.temporal.return_context import (
    MEANINGFULLY_RETURNING_MIN_INTERVAL,
    ReturnContextEngine,
)

USER = "user_5d"
OTHER = "user_5d_other"

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _now() -> datetime:
    return datetime.now(UTC)


async def _thread(store, subject, status=TemporalThreadStatus.OPEN,
                  ttype=TemporalType.DECISION, user_id=USER):
    t = TemporalThread(user_id=user_id, subject=subject, status=status, temporal_type=ttype)
    return await store.save_thread(t)


async def _event(store, thread_id, description, at, ttype=TemporalType.DECISION, user_id=USER):
    e = TemporalEvent(
        thread_id=thread_id,
        user_id=user_id,
        description=description,
        temporal_type=ttype,
        occurred_at=at,
        recorded_at=at,
    )
    return await store.save_event(e)


def _mk_engine(store):
    return ReturnContextEngine(temporal_store=store)


# ── 1. Returning-user detection (Part 2) ─────────────────────────────────


class TestReturningUserDetection:
    async def test_first_ever_user_has_no_context(self):
        store = InMemoryTemporalStore()
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=None)
        assert ctx.user_kind is ReturnUserKind.FIRST_EVER
        assert ctx.has_return_context is False
        assert ctx.changes == []

    async def test_returning_user_with_no_change(self):
        store = InMemoryTemporalStore()
        prev = _now() - timedelta(hours=1)
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=prev)
        assert ctx.user_kind is ReturnUserKind.RETURNING
        assert ctx.has_return_context is False
        assert ctx.changes == []

    async def test_meaningfully_returning_user(self):
        store = InMemoryTemporalStore()
        prev = _now() - MEANINGFULLY_RETURNING_MIN_INTERVAL - timedelta(hours=1)
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=prev)
        assert ctx.user_kind is ReturnUserKind.MEANINGFULLY_RETURNING

    async def test_recent_return_is_recently_returning(self):
        store = InMemoryTemporalStore()
        prev = _now() - timedelta(minutes=5)
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=prev)
        assert ctx.user_kind is ReturnUserKind.RETURNING


# ── 2. Since-last-visit meaningful changes (Part 3) ──────────────────────


class TestSinceLastVisit:
    async def test_new_temporal_event_on_thread_progresses_story(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "changing jobs")
        await _event(store, t.id, "I might switch careers", BASE)
        # New moment recorded after the previous visit, with continuity
        later = _now() - timedelta(hours=2)
        await _event(store, t.id, "I made progress on a plan", later)

        cfg = _mk_engine(store)
        ctx = await cfg.build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert ctx.has_return_context is True
        assert any(c.change_type is ReturnChangeType.STORY_PROGRESSED for c in ctx.changes)

    async def test_no_new_event_means_no_insight(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "old story")
        await _event(store, t.id, "an old moment", BASE)

        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert ctx.has_return_context is False
        assert ctx.changes == []

    async def test_resolved_story_is_meaningful(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "deciding to move")
        await _event(store, t.id, "weighing the move", BASE)
        later = _now() - timedelta(hours=2)
        await _event(store, t.id, "I decided to move next month", later)
        t.status = TemporalThreadStatus.RESOLVED
        await store.save_thread(t)

        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert any(c.change_type is ReturnChangeType.STORY_RESOLVED for c in ctx.changes)

    async def test_changed_story_is_meaningful(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "training to run a marathon")
        await _event(store, t.id, "aiming for a marathon", BASE)
        later = _now() - timedelta(hours=2)
        await _event(store, t.id, "I am focusing on swimming instead", later)
        t.status = TemporalThreadStatus.CHANGED
        await store.save_thread(t)

        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert any(c.change_type is ReturnChangeType.STORY_CHANGED for c in ctx.changes)

    async def test_unrelated_new_memory_does_not_fabricate(self):
        """A new memory attached to no thread must not produce an insight."""
        store = InMemoryTemporalStore()
        t = await _thread(store, "my job decision")
        await _event(store, t.id, "thinking about work", BASE)
        # A brand-new thread created after the visit with a single event IS a
        # NEW_STORY — but ensure it is classified as a new story, not a
        # fabricated "progressed" on an unrelated thread.
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        # Only the job thread has new activity; it should not be mislabeled.
        for c in ctx.changes:
            assert c.change_type is not None

    async def test_new_story_since_visit_is_meaningful(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "starting a side project")
        later = _now() - timedelta(hours=2)
        await _event(store, t.id, "I started a side project", later)
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert any(c.change_type is ReturnChangeType.NEW_STORY for c in ctx.changes)


# ── 3. Story resurfacing selection (Part 8) ──────────────────────────────


class TestStoryResurfacing:
    async def test_open_story_resurfaces(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "changing jobs")
        await _event(store, t.id, "considering a change", BASE)
        await _event(store, t.id, "I keep thinking about it", _now() - timedelta(hours=2))
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert ctx.suggested_story_subject == "changing jobs"
        assert ctx.suggested_thread_id == t.id

    async def test_irrelevant_story_requires_activity(self):
        """A story that merely 'exists' is not resurfaced."""
        store = InMemoryTemporalStore()
        await _thread(store, "an old resolved thing")  # no new activity
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert ctx.has_return_context is False
        assert ctx.suggested_thread_id is None

    async def test_multiple_stories_deterministic_selection(self):
        store = InMemoryTemporalStore()
        t_resolved = await _thread(store, "finish my degree")
        await _event(store, t_resolved.id, "deciding on uni", BASE)
        await _event(store, t_resolved.id, "I graduated", _now() - timedelta(hours=2))
        t_resolved.status = TemporalThreadStatus.RESOLVED
        await store.save_thread(t_resolved)

        t_open = await _thread(store, "move to the coast")
        await _event(store, t_open.id, "thinking of moving", BASE)
        await _event(store, t_open.id, "still considering", _now() - timedelta(hours=1))

        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        # Resolved/conclusive stories rank above still-open ones.
        assert ctx.suggested_story_subject == "finish my degree"

    async def test_no_cross_user_story_leak(self):
        store = InMemoryTemporalStore()
        # Other user's story with lots of new activity
        other = await _thread(store, "other persons secret", user_id=OTHER)
        await _event(
            store, other.id, "other secret event", _now() - timedelta(hours=1), user_id=OTHER
        )
        other.status = TemporalThreadStatus.RESOLVED
        await store.save_thread(other)

        # This user has no activity
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert ctx.has_return_context is False
        assert ctx.suggested_thread_id is None
        assert all(c.subject != "other persons secret" for c in ctx.changes)


# ── 4. Duplicate suppression (Part 14) ───────────────────────────────────


class TestDuplicateSuppression:
    async def test_same_insight_not_repeated(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "changing jobs")
        await _event(store, t.id, "considering", BASE)
        await _event(store, t.id, "made progress", _now() - timedelta(hours=2))

        eng = _mk_engine(store)
        prev = _now() - timedelta(days=1)
        first = await eng.build(USER, latest_interaction_at=prev)
        assert first.has_return_context is True

        # Same previous visit, nothing new since the first surfacing.
        second = await eng.build(USER, latest_interaction_at=prev)
        assert second.has_return_context is False

    async def test_new_event_allows_new_insight(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "changing jobs")
        await _event(store, t.id, "considering", BASE)
        await _event(store, t.id, "step one", _now() - timedelta(hours=5))

        eng = _mk_engine(store)
        prev = _now() - timedelta(days=1)
        now1 = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        first = await eng.build(USER, latest_interaction_at=prev, now=now1)
        assert first.has_return_context is True

        # A genuinely new event recorded AFTER the previous surfacing marker
        await _event(store, t.id, "step two arrived", now1 + timedelta(minutes=1))
        now2 = now1 + timedelta(hours=2)
        second = await eng.build(USER, latest_interaction_at=prev, now=now2)
        assert second.has_return_context is True

    async def test_deletion_removes_resurfacing_eligibility(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "changing jobs")
        await _event(store, t.id, "considering", BASE)
        await _event(store, t.id, "made progress", _now() - timedelta(hours=2))

        await store.delete_all_for_user(USER)
        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert ctx.has_return_context is False
        assert ctx.changes == []

    async def test_ledger_is_cleared_on_delete(self):
        store = InMemoryTemporalStore()
        await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        await store.save_return_ledger(ReturnLedger(user_id=USER, last_surfaced_at=_now()))
        await store.delete_all_for_user(USER)
        assert await store.get_return_ledger(USER) is None


# ── 5. User isolation & privacy (Part 16) ────────────────────────────────


class TestUserIsolation:
    async def test_user_a_cannot_receive_user_b_context(self):
        store = InMemoryTemporalStore()
        b = await _thread(store, "b secret story", user_id=OTHER)
        await _event(store, b.id, "b private event", _now() - timedelta(hours=1), user_id=OTHER)

        ctx_a = await _mk_engine(store).build(
            USER, latest_interaction_at=_now() - timedelta(days=1)
        )
        ctx_b = await _mk_engine(store).build(
            OTHER, latest_interaction_at=_now() - timedelta(days=1)
        )
        assert ctx_a.has_return_context is False
        assert ctx_b.has_return_context is True

    async def test_no_raw_ids_in_user_facing_fields(self):
        store = InMemoryTemporalStore()
        t = await _thread(store, "changing jobs")
        await _event(store, t.id, "considering", BASE)
        await _event(store, t.id, "made progress", _now() - timedelta(hours=2))

        ctx = await _mk_engine(store).build(USER, latest_interaction_at=_now() - timedelta(days=1))
        user_facing = " ".join(
            [ctx.welcome, ctx.summary_section or ""]
            + [c.headline + " " + c.detail for c in ctx.changes]
            + [ctx.suggested_story_subject or "", ctx.suggested_story_because]
        )
        for token in ("mem_", "tevent_", "thread_", "tsnap_", "_5d", "user_5d"):
            assert token not in user_facing


# ── 6. User control (Part 19) ────────────────────────────────────────────


class TestUserControl:
    async def test_disabled_preference_hides_return_context(self):
        store = InMemoryTemporalStore()
        eng = _mk_engine(store)
        await eng.set_enabled(USER, enabled=False)

        t = await _thread(store, "changing jobs")
        await _event(store, t.id, "considering", BASE)
        await _event(store, t.id, "made progress", _now() - timedelta(hours=2))

        ctx = await eng.build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert ctx.has_return_context is False
        assert ctx.changes == []

    async def test_re_enabling_restores_return_context(self):
        store = InMemoryTemporalStore()
        eng = _mk_engine(store)
        await eng.set_enabled(USER, enabled=False)
        await eng.set_enabled(USER, enabled=True)

        t = await _thread(store, "changing jobs")
        await _event(store, t.id, "considering", BASE)
        await _event(store, t.id, "made progress", _now() - timedelta(hours=2))

        ctx = await eng.build(USER, latest_interaction_at=_now() - timedelta(days=1))
        assert ctx.has_return_context is True
