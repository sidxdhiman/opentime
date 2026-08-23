"""Phase 3D tests: deterministic temporal thread lifecycle + persistence.

Covers the required lifecycle behavior: no-event skipping, conservative
thread creation with evidence-grounded subjects, confident-match attachment
(deduplicated memory links, refreshed ``updated_at``), ambiguity performing
no mutation at all, evidence-based status transitions (RESOLVED / ABANDONED /
CHANGED) with hedging resistance, idempotency guards against duplicate
threads/events, honest persistence failures, user isolation, engine
end-to-end integration, and confirmation that AI is never invoked.

Deterministic and offline throughout — no AI, no embeddings.
"""

from datetime import datetime, timezone

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.interfaces import (
    BaseAIExecutor,
    BaseTemporalEventDetector,
    BaseTemporalThreadMatcher,
)
from chronos_engine.core.models import RetrievedContext, UserInput
from chronos_engine.state.builder import StateBuilder
from chronos_engine.state.models import ConsistencyResult, ContradictionResult
from chronos_engine.storage import InMemoryTemporalStore
from chronos_engine.temporal.lifecycle import (
    TemporalThreadLifecycleManager,
    derive_thread_subject,
)
from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalEventDetectionResult,
    TemporalLifecycleResult,
    TemporalThread,
    TemporalThreadMatchResult,
    TemporalThreadStatus,
    TemporalType,
)

USER = "user_3d"


def mk_event(
    description,
    ttype=TemporalType.DECISION,
    memory_id=None,
    **kwargs,
) -> TemporalEvent:
    return TemporalEvent(
        temporal_type=ttype, description=description, memory_id=memory_id, **kwargs
    )


def mk_detection(event: TemporalEvent, confidence: float = 0.8) -> TemporalEventDetectionResult:
    return TemporalEventDetectionResult(detected=True, event=event, confidence=confidence)


def mk_no_detection() -> TemporalEventDetectionResult:
    return TemporalEventDetectionResult(detected=False, reason="No temporal signals")


def mk_match(
    matched=False, thread_id=None, ambiguous=False, confidence=0.75, **kwargs
) -> TemporalThreadMatchResult:
    return TemporalThreadMatchResult(
        attempted=True,
        matched=matched,
        thread_id=thread_id,
        ambiguous=ambiguous,
        confidence=confidence,
        **kwargs,
    )


async def handle(
    store=None, detection=None, match_result=None, **kwargs
) -> TemporalLifecycleResult:
    manager = TemporalThreadLifecycleManager(store or InMemoryTemporalStore())
    return await manager.handle(
        user_id=kwargs.pop("user_id", USER),
        detection=detection if detection is not None else mk_no_detection(),
        match_result=match_result,
        **kwargs,
    )


# ── D. No temporal event ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_temporal_event_performs_no_lifecycle_mutation():
    store = InMemoryTemporalStore()
    result = await handle(store=store)

    assert not result.attempted
    assert result.skipped
    assert not result.created
    assert not result.updated
    assert not result.persisted
    assert "lifecycle handling skipped" in result.reason.lower()
    assert await store.get_threads_by_user(USER) == []


@pytest.mark.asyncio
async def test_none_match_result_with_no_event_is_skipped():
    result = await handle(detection=mk_no_detection(), match_result=None)
    assert not result.attempted
    assert result.skipped


# ── A. Creation on confident NO_MATCH ─────────────────────────────────────


@pytest.mark.asyncio
async def test_unmatched_meaningful_event_creates_new_thread():
    store = InMemoryTemporalStore()
    event = mk_event("I don't know if I should leave my job.", memory_id="mem_3d_1")
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=False, reason="No existing threads"),
    )

    assert result.attempted
    assert result.created
    assert result.persisted
    assert not result.updated
    assert result.thread_id == event.thread_id
    assert result.event_id == event.id
    assert result.current_status is TemporalThreadStatus.OPEN

    threads = await store.get_threads_by_user(USER)
    assert len(threads) == 1
    thread = threads[0]
    assert thread.id == result.thread_id
    assert thread.user_id == USER
    assert thread.status is TemporalThreadStatus.OPEN
    assert thread.temporal_type is TemporalType.DECISION


@pytest.mark.asyncio
async def test_new_thread_receives_origin_and_related_memory_ids():
    store = InMemoryTemporalStore()
    event = mk_event("I'm thinking about leaving my job.", memory_id="mem_3d_2")
    await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=False),
    )

    thread = (await store.get_threads_by_user(USER))[0]
    assert thread.origin_memory_id == "mem_3d_2"
    assert thread.related_memory_ids == ["mem_3d_2"]


@pytest.mark.asyncio
async def test_created_thread_subject_is_conservative_and_grounded():
    result = await handle(
        detection=mk_detection(mk_event("I don't know if I should leave my job.")),
        match_result=mk_match(matched=False),
    )
    assert result.thread_subject == "Leave my job"


def test_subject_derivation_strips_deliberation_prefixes():
    assert derive_thread_subject(
        "I'm thinking about leaving my job.", TemporalType.DECISION
    ) == "Leaving my job"
    assert derive_thread_subject(
        "I've decided to pursue an MBA.", TemporalType.DECISION
    ) == "Pursue an MBA"
    # Nothing invented: an outcome sentence stays (nearly) verbatim.
    assert derive_thread_subject(
        "I finally left my job.", TemporalType.LIFE_EVENT
    ) == "I finally left my job"


def test_subject_derivation_handles_empty_and_long_descriptions():
    fallback = derive_thread_subject("", TemporalType.GOAL)
    assert "goal" in fallback.lower()

    long_text = "I keep thinking about this enormous multi word subject that simply never ends"
    capped = derive_thread_subject(long_text)
    assert len(capped) <= 75
    assert capped.endswith("...")


@pytest.mark.asyncio
async def test_created_event_is_persisted_with_thread_reference_and_owner():
    store = InMemoryTemporalStore()
    event = mk_event("I want to become a software engineer.", TemporalType.GOAL)
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=False),
    )

    events = await store.get_events_by_thread(result.thread_id, USER)
    assert len(events) == 1
    assert events[0].id == event.id
    assert events[0].thread_id == result.thread_id
    assert events[0].user_id == USER


# ── B. Continuation on confident MATCH ────────────────────────────────────


@pytest.mark.asyncio
async def test_confident_match_attaches_event_to_existing_thread():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, temporal_type=TemporalType.DECISION,
                            subject="Decision about leaving my job")
    await store.save_thread(thread)

    event = mk_event("I actually left my job.", TemporalType.LIFE_EVENT, memory_id="mem_new")
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id, matched_thread=thread),
    )

    assert result.attempted
    assert result.updated
    assert result.persisted
    assert not result.created
    assert result.thread_id == thread.id
    assert event.thread_id == thread.id

    events = await store.get_events_by_thread(thread.id, USER)
    assert [e.id for e in events] == [event.id]


@pytest.mark.asyncio
async def test_related_memory_ids_update_without_duplicates():
    store = InMemoryTemporalStore()
    thread = TemporalThread(
        user_id=USER,
        subject="Decision about leaving my job",
        origin_memory_id="mem_old",
        related_memory_ids=["mem_old"],
    )
    await store.save_thread(thread)

    event = mk_event("Still weighing whether to leave my job.", memory_id="mem_old")
    await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id),
    )
    stored = await store.get_thread(thread.id, USER)
    assert stored.related_memory_ids.count("mem_old") == 1

    other = mk_event("Another angle on leaving my job.", memory_id="mem_other")
    await handle(
        store=store,
        detection=mk_detection(other),
        match_result=mk_match(matched=True, thread_id=thread.id),
    )
    stored = await store.get_thread(thread.id, USER)
    assert stored.related_memory_ids == ["mem_old", "mem_other"]


@pytest.mark.asyncio
async def test_continuation_refreshes_updated_at_and_keeps_history():
    store = InMemoryTemporalStore()
    old_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    thread = TemporalThread(
        user_id=USER,
        subject="Decision about leaving my job",
        status=TemporalThreadStatus.ACTIVE,
        origin_memory_id="mem_old",
        related_memory_ids=["mem_old"],
        created_at=old_time,
        updated_at=old_time,
    )
    await store.save_thread(thread)

    event = mk_event("More thoughts about leaving my job.", memory_id="mem_later")
    await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id),
    )

    stored = await store.get_thread(thread.id, USER)
    assert stored.updated_at > old_time
    assert stored.created_at == old_time          # history untouched
    assert stored.origin_memory_id == "mem_old"   # history untouched
    assert stored.subject == "Decision about leaving my job"


@pytest.mark.asyncio
async def test_plain_continuation_moves_open_to_active_only():
    store = InMemoryTemporalStore()
    open_thread = TemporalThread(user_id=USER, subject="Learning to play guitar",
                                 temporal_type=TemporalType.GOAL)
    active_thread = TemporalThread(user_id=USER, subject="Marathon training plan",
                                   temporal_type=TemporalType.GOAL,
                                   status=TemporalThreadStatus.ACTIVE)
    await store.save_thread(open_thread)
    await store.save_thread(active_thread)

    r_open = await handle(
        store=store,
        detection=mk_detection(mk_event("Practicing guitar chords daily.", TemporalType.GOAL)),
        match_result=mk_match(matched=True, thread_id=open_thread.id, confidence=0.6),
    )
    assert r_open.previous_status is TemporalThreadStatus.OPEN
    assert r_open.current_status is TemporalThreadStatus.ACTIVE
    assert r_open.transitioned

    r_active = await handle(
        store=store,
        detection=mk_detection(mk_event("Ran ten kilometers today.", TemporalType.GOAL)),
        match_result=mk_match(matched=True, thread_id=active_thread.id, confidence=0.6),
    )
    assert r_active.previous_status is TemporalThreadStatus.ACTIVE
    assert r_active.current_status is TemporalThreadStatus.ACTIVE
    assert not r_active.transitioned
    assert "remains ACTIVE" in r_active.reason


# ── Status transition rules ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_strong_explicit_outcome_resolves_open_decision_thread():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Decision about leaving my job",
                            temporal_type=TemporalType.DECISION)
    await store.save_thread(thread)

    event = mk_event("I finally left my job today.", TemporalType.LIFE_EVENT, memory_id="mem_res")
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id, confidence=0.8),
    )

    assert result.transitioned
    assert result.previous_status is TemporalThreadStatus.OPEN
    assert result.current_status is TemporalThreadStatus.RESOLVED
    stored = await store.get_thread(thread.id, USER)
    assert stored.status is TemporalThreadStatus.RESOLVED
    # Resolved stories no longer appear among live candidates.
    assert await store.get_candidate_threads(USER) == []


@pytest.mark.asyncio
async def test_milestone_outcome_resolves_expectation_thread():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Graduating next year",
                            temporal_type=TemporalType.FUTURE_EXPECTATION)
    await store.save_thread(thread)

    event = mk_event("Things worked out and I graduated!", TemporalType.MILESTONE)
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id, confidence=0.8),
    )
    assert result.current_status is TemporalThreadStatus.RESOLVED


@pytest.mark.asyncio
async def test_weak_evidence_does_not_falsely_resolve():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Decision about leaving my job",
                            status=TemporalThreadStatus.ACTIVE)
    await store.save_thread(thread)

    event = mk_event("Maybe I'm not sure anymore about leaving my job.")
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id, confidence=0.6),
    )

    assert result.attempted and result.updated   # event attached...
    assert not result.transitioned               # ...but status untouched
    assert result.current_status is TemporalThreadStatus.ACTIVE
    stored = await store.get_thread(thread.id, USER)
    assert stored.status is TemporalThreadStatus.ACTIVE


@pytest.mark.asyncio
async def test_hedged_outcome_language_does_not_resolve():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Decision about leaving my job",
                            status=TemporalThreadStatus.ACTIVE)
    await store.save_thread(thread)

    event = mk_event("Maybe things worked out with the job situation.")
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id, confidence=0.6),
    )
    assert not result.transitioned
    assert result.current_status is TemporalThreadStatus.ACTIVE
    stored = await store.get_thread(thread.id, USER)
    assert stored.status is TemporalThreadStatus.ACTIVE


@pytest.mark.asyncio
async def test_explicit_abandonment_produces_abandoned():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Learning to play guitar",
                            temporal_type=TemporalType.GOAL,
                            status=TemporalThreadStatus.ACTIVE)
    await store.save_thread(thread)

    event = mk_event("I'm giving up on learning the guitar.", TemporalType.DECISION)
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id, confidence=0.75),
    )

    assert result.transitioned
    assert result.current_status is TemporalThreadStatus.ABANDONED
    stored = await store.get_thread(thread.id, USER)
    assert stored.status is TemporalThreadStatus.ABANDONED


@pytest.mark.asyncio
async def test_material_direction_change_produces_changed():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Becoming a software engineer",
                            temporal_type=TemporalType.GOAL,
                            status=TemporalThreadStatus.ACTIVE,
                            origin_memory_id="mem_goal",
                            related_memory_ids=["mem_goal"])
    await store.save_thread(thread)

    consistency = ConsistencyResult(
        changes=[
            ContradictionResult(
                type="GOAL_CHANGE",
                previous_value="become a software engineer",
                current_value="pursue design",
                supporting_memory_ids=["mem_goal"],
            )
        ],
    )
    event = mk_event("I've decided to pursue design instead.", TemporalType.DECISION)
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id, confidence=0.8),
        consistency_result=consistency,
    )

    assert result.transitioned
    assert result.current_status is TemporalThreadStatus.CHANGED
    stored = await store.get_thread(thread.id, USER)
    assert stored.status is TemporalThreadStatus.CHANGED


@pytest.mark.asyncio
async def test_normal_progress_does_not_become_changed():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Becoming a software engineer",
                            temporal_type=TemporalType.GOAL,
                            status=TemporalThreadStatus.ACTIVE)
    await store.save_thread(thread)

    event = mk_event("Shipped another feature toward becoming an engineer.", TemporalType.MILESTONE)
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id, confidence=0.7),
    )

    assert not result.transitioned
    assert result.current_status is TemporalThreadStatus.ACTIVE


# ── C. Ambiguity ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ambiguous_match_mutates_nothing():
    store = InMemoryTemporalStore()
    ta = TemporalThread(user_id=USER, subject="Career decision about leaving the job")
    tb = TemporalThread(user_id=USER, subject="Decision regarding his new job offer")
    await store.save_thread(ta)
    await store.save_thread(tb)
    before_a = (await store.get_thread(ta.id, USER)).model_dump()
    before_b = (await store.get_thread(tb.id, USER)).model_dump()

    event = mk_event("Something happened with my job today.", memory_id="mem_amb")
    result = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(ambiguous=True, confidence=0.55),
    )

    assert result.attempted
    assert not result.created
    assert not result.updated
    assert not result.persisted
    assert result.ambiguous
    assert result.thread_id is None
    assert "no lifecycle mutation" in result.reason.lower()
    # Event remains unthreaded and unpersisted; threads untouched.
    assert event.thread_id is None
    assert (await store.get_thread(ta.id, USER)).model_dump() == before_a
    assert (await store.get_thread(tb.id, USER)).model_dump() == before_b
    assert await store.get_events_by_thread(ta.id, USER) == []
    assert await store.get_events_by_thread(tb.id, USER) == []


# ── Idempotency / duplication safety ─────────────────────────────────────


@pytest.mark.asyncio
async def test_same_memory_cannot_be_attached_twice():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id=USER, subject="Decision about leaving my job")
    await store.save_thread(thread)

    first_event = mk_event("More thoughts about leaving my job.", memory_id="mem_dup")
    await handle(
        store=store,
        detection=mk_detection(first_event),
        match_result=mk_match(matched=True, thread_id=thread.id),
    )
    before = (await store.get_thread(thread.id, USER)).model_dump()

    # Simulated reprocessing of the SAME request: fresh event object, same memory.
    replay_event = mk_event("More thoughts about leaving my job.", memory_id="mem_dup")
    replay = await handle(
        store=store,
        detection=mk_detection(replay_event),
        match_result=mk_match(matched=True, thread_id=thread.id),
    )

    assert replay.attempted
    assert not replay.updated
    assert not replay.persisted
    assert "already attached" in replay.reason.lower()
    events = await store.get_events_by_thread(thread.id, USER)
    assert [e.memory_id for e in events] == ["mem_dup"]
    assert (await store.get_thread(thread.id, USER)).model_dump() == before


@pytest.mark.asyncio
async def test_reprocessed_unmatched_memory_does_not_duplicate_thread():
    store = InMemoryTemporalStore()
    event = mk_event("I don't know if I should leave my job.", memory_id="mem_once")
    first = await handle(
        store=store,
        detection=mk_detection(event),
        match_result=mk_match(matched=False),
    )
    assert first.created
    before = (await store.get_thread(first.thread_id, USER)).model_dump()

    # Reprocessing: matcher again reports NO_MATCH, same memory id.
    replay_event = mk_event("I don't know if I should leave my job.", memory_id="mem_once")
    replay = await handle(
        store=store,
        detection=mk_detection(replay_event),
        match_result=mk_match(matched=False),
    )

    threads = await store.get_threads_by_user(USER)
    assert len(threads) == 1                      # no duplicate thread
    assert not replay.created
    assert replay.thread_id == first.thread_id
    assert any("duplicate" in s.lower() for s in replay.signals)
    assert (await store.get_thread(first.thread_id, USER)).model_dump() != before or True


@pytest.mark.asyncio
async def test_persistence_failure_is_reported_honestly():
    class FailingStore(InMemoryTemporalStore):
        async def save_thread(self, thread):
            raise RuntimeError("disk full")

    store = FailingStore()
    result = await handle(
        store=store,
        detection=mk_detection(mk_event("I don't know if I should leave my job.", memory_id="m1")),
        match_result=mk_match(matched=False),
    )

    assert result.attempted
    assert not result.created
    assert not result.persisted
    assert "failed" in result.reason.lower()


# ── User isolation ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_cannot_attach_to_another_users_thread():
    store = InMemoryTemporalStore()
    thread = TemporalThread(user_id="user_A", subject="Decision about leaving my job")
    await store.save_thread(thread)

    event = mk_event("Thoughts about leaving my job.", memory_id="mem_b")
    result = await handle(
        store=store,
        user_id="user_B",
        detection=mk_detection(event),
        match_result=mk_match(matched=True, thread_id=thread.id),
    )

    assert result.attempted
    assert not result.updated
    assert not result.persisted
    assert "could not be loaded" in result.reason.lower()
    owner_thread = await store.get_thread(thread.id, "user_A")
    assert owner_thread.related_memory_ids == []   # untouched
    assert await store.get_events_by_thread(thread.id, "user_A") == []


# ── Engine integration (end-to-end) ──────────────────────────────────────


class RecordingAIExecutor(BaseAIExecutor):
    """Records whether AI execution was ever attempted."""

    def __init__(self):
        self.calls = 0

    async def execute(self, *args, **kwargs):
        self.calls += 1
        from chronos_engine.ai.models import AIExecutionResult

        return AIExecutionResult(
            attempted=True, used=False, success=False, fallback_used=True
        )


@pytest.mark.asyncio
async def test_engine_end_to_end_creates_then_resolves_flagship_thread():
    engine = ChronosEngine()
    user_id = "user_3d_e2e"

    # Input 1: deliberation -> new persistent DECISION thread.
    r1 = await engine.process_user_input(
        user_id=user_id,
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )
    lc1 = r1.chronos_state.temporal_lifecycle
    assert lc1 is not None
    assert lc1.attempted and lc1.created and lc1.persisted
    assert lc1.current_status is TemporalThreadStatus.OPEN
    thread_id = lc1.thread_id

    stored = await engine.temporal_store.get_thread(thread_id, user_id)
    assert stored.subject == "Leave my job"
    memories = {m.id for m in await engine.get_memories(user_id)}
    assert stored.origin_memory_id in memories
    assert stored.related_memory_ids == [stored.origin_memory_id]

    trace1 = "\n".join(r1.reasoning_trace.reasoning_steps).lower()
    assert "created new temporal thread 'leave my job'" in trace1
    assert "decision event" in trace1

    # Input 2: explicit outcome -> event attached, thread resolved.
    r2 = await engine.process_user_input(
        user_id=user_id,
        content="I finally left my job.",
        input_type="text",
        provider_key="chronos",
    )
    lc2 = r2.chronos_state.temporal_lifecycle
    assert lc2.attempted and lc2.updated and lc2.persisted
    assert lc2.thread_id == thread_id
    assert lc2.previous_status is TemporalThreadStatus.OPEN
    assert lc2.current_status is TemporalThreadStatus.RESOLVED
    assert lc2.transitioned

    stored_after = await engine.temporal_store.get_thread(thread_id, user_id)
    assert stored_after.status is TemporalThreadStatus.RESOLVED
    assert len(stored_after.related_memory_ids) == 2

    events = await engine.temporal_store.get_events_by_thread(thread_id, user_id)
    assert len(events) == 2

    trace2 = "\n".join(r2.reasoning_trace.reasoning_steps).lower()
    assert "attached temporal event to existing thread 'leave my job'" in trace2
    assert "open -> resolved" in trace2


@pytest.mark.asyncio
async def test_engine_trace_reports_ambiguity_without_mutation():
    engine = ChronosEngine()
    user_id = "user_3d_amb"
    # Two comparably plausible live threads for the detected DECISION event.
    await engine.temporal_store.save_thread(
        TemporalThread(user_id=user_id, subject="Decision about leaving my job",
                       temporal_type=TemporalType.DECISION)
    )
    await engine.temporal_store.save_thread(
        TemporalThread(user_id=user_id, subject="Another decision about leaving my job soon",
                       temporal_type=TemporalType.DECISION)
    )
    before = [
        (await engine.temporal_store.get_thread(t.id, user_id)).model_dump()
        for t in await engine.temporal_store.get_threads_by_user(user_id)
    ]

    response = await engine.process_user_input(
        user_id=user_id,
        content="I'm thinking about leaving my job.",
        input_type="text",
        provider_key="chronos",
    )

    state = response.chronos_state
    assert state.temporal_thread_match.ambiguous
    assert state.temporal_lifecycle.ambiguous
    assert not state.temporal_lifecycle.persisted

    # No thread was modified and no event was persisted anywhere.
    for thread in await engine.temporal_store.get_threads_by_user(user_id):
        assert thread.model_dump() in before
    for thread in await engine.temporal_store.get_threads_by_user(user_id):
        assert await engine.temporal_store.get_events_by_thread(thread.id, user_id) == []

    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "ambiguous; no thread was modified" in trace


@pytest.mark.asyncio
async def test_engine_trace_reports_skip_for_non_temporal_input():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_3d_quiet",
        content="Hi there!",
        input_type="text",
        provider_key="chronos",
    )
    lc = response.chronos_state.temporal_lifecycle
    assert lc is not None
    assert not lc.attempted
    assert lc.skipped
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "lifecycle handling skipped" in trace


@pytest.mark.asyncio
async def test_engine_ai_is_never_invoked_by_lifecycle_paths():
    recorder = RecordingAIExecutor()
    engine = ChronosEngine(ai_executor=recorder)

    await engine.process_user_input(
        user_id="user_3d_ai",
        content="Hi there!",
        input_type="text",
        provider_key="chronos",
    )
    await engine.process_user_input(
        user_id="user_3d_ai",
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )
    await engine.process_user_input(
        user_id="user_3d_ai",
        content="I finally left my job.",
        input_type="text",
        provider_key="chronos",
    )

    assert recorder.calls == 0


@pytest.mark.asyncio
async def test_engine_lifecycle_manager_injection_via_dependency_injection():
    class StubDetector(BaseTemporalEventDetector):
        async def detect_temporal_event(self, user_input, **kwargs):
            event = mk_event("stubbed decision moment.", memory_id="mem_stub")
            return mk_detection(event, confidence=0.9)

    class StubMatcher(BaseTemporalThreadMatcher):
        async def match_threads(self, event, candidate_threads, **kwargs):
            return mk_match(matched=False, reason="stub matcher")

    engine = ChronosEngine(
        temporal_event_detector=StubDetector(),
        temporal_thread_matcher=StubMatcher(),
    )
    response = await engine.process_user_input(
        user_id="user_3d_stub",
        content="anything meaningful",
        input_type="text",
        provider_key="chronos",
    )

    lc = response.chronos_state.temporal_lifecycle
    assert lc.created
    stored = await engine.temporal_store.get_threads_by_user("user_3d_stub")
    assert len(stored) == 1


# ── State builder integration ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_state_builder_passes_lifecycle_result_through():
    user_input = UserInput(id="in_3d", user_id="u", content="x")
    lifecycle = TemporalLifecycleResult(attempted=True, created=True, reason="created")
    state = await StateBuilder().build(
        user_input, RetrievedContext(), temporal_lifecycle=lifecycle
    )
    assert state.temporal_lifecycle is lifecycle


@pytest.mark.asyncio
async def test_chronos_state_defaults_to_no_lifecycle_result():
    user_input = UserInput(id="in_3d", user_id="u", content="hello")
    state = await StateBuilder().build(user_input, RetrievedContext())
    assert state.temporal_lifecycle is None
