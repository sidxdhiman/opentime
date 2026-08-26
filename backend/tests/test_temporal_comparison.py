"""Phase 3E tests: deterministic Past-vs-Present comparison.

Covers the required comparison behavior: honest skipping when no temporal
thread is available, INSUFFICIENT_EVIDENCE for single-moment threads (with
the lifecycle-grounded resolution carve-out), anchor selection (origin
memory preferred, earliest event as fallback, newest event as present), the
documented relation policy (lifecycle-grounded RESOLVED / CHANGED / ABANDONED
mapping, fear realization/overcoming, deliberation outcome observation,
consistency corroboration, restatement vs development vs open stories),
deduplicated evidence ids, capped confidence, conservative template
summaries, strict read-only behavior and end-to-end engine integration with
honest trace entries.

Deterministic and offline throughout — no AI, no embeddings.
"""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.interfaces import (
    BaseAIExecutor,
    BaseTemporalComparisonEngine,
)
from chronos_engine.core.models import RetrievedContext, UserInput
from chronos_engine.state.builder import StateBuilder
from chronos_engine.state.models import ConsistencyResult, ContradictionResult
from chronos_engine.temporal.comparison import (
    MAX_COMPARISON_CONFIDENCE,
    TemporalComparisonEngine,
)
from chronos_engine.temporal.models import (
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalLifecycleResult,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)

USER = "user_3e"


def mk_event(
    description,
    ttype=None,
    memory_id=None,
    **kwargs,
) -> TemporalEvent:
    kwargs.setdefault("user_id", USER)
    return TemporalEvent(
        temporal_type=ttype, description=description, memory_id=memory_id, **kwargs
    )


def mk_thread(**kwargs) -> TemporalThread:
    kwargs.setdefault("user_id", USER)
    return TemporalThread(**kwargs)


def mk_lifecycle(
    thread_id=None, transitioned=False, status=None, confidence=0.8
) -> TemporalLifecycleResult:
    return TemporalLifecycleResult(
        attempted=True,
        updated=True,
        persisted=True,
        thread_id=thread_id,
        transitioned=transitioned,
        current_status=status,
        confidence=confidence,
    )


async def compare(thread=None, events=None, **kwargs) -> TemporalComparisonResult:
    engine = TemporalComparisonEngine()
    return await engine.compare(
        user_id=kwargs.pop("user_id", USER),
        thread=thread,
        events=events or [],
        **kwargs,
    )


# ── Honest skipping / insufficient history ───────────────────────────────


@pytest.mark.asyncio
async def test_no_thread_is_reported_as_honest_skip():
    result = await compare(thread=None)

    assert not result.attempted
    assert not result.comparable
    assert "no temporal thread available" in result.reason.lower()


@pytest.mark.asyncio
async def test_single_moment_thread_is_not_comparable():
    event = mk_event("I don't know if I should leave my job.", TemporalType.DECISION,
                     memory_id="mem_e2")
    result = await compare(thread=mk_thread(origin_memory_id="mem_e2"), events=[event])

    assert result.attempted
    assert not result.comparable
    assert result.relation is TemporalComparisonRelation.INSUFFICIENT_EVIDENCE
    assert result.present_event_id == event.id
    assert result.evidence_event_ids == [event.id]
    assert "fewer than two" in result.reason.lower()


@pytest.mark.asyncio
async def test_single_moment_with_grounded_lifecycle_resolution_still_reports():
    thread = mk_thread(origin_memory_id="mem_out")
    event = mk_event("I finally left my job.", TemporalType.LIFE_EVENT,
                     memory_id="mem_out")
    lifecycle = mk_lifecycle(
        thread_id=thread.id, transitioned=True,
        status=TemporalThreadStatus.RESOLVED,
    )
    result = await compare(thread=thread, events=[event], lifecycle_result=lifecycle)

    # The carve-out reports the grounded resolution WITHOUT claiming a
    # two-moment comparison happened.
    assert result.attempted
    assert not result.comparable
    assert result.relation is TemporalComparisonRelation.RESOLVED
    assert result.confidence == lifecycle.confidence
    assert any("lifecycle" in s.lower() for s in result.signals)


@pytest.mark.asyncio
async def test_empty_history_on_existing_thread_is_insufficient():
    result = await compare(thread=mk_thread(subject="Some story"), events=[])

    assert result.attempted
    assert not result.comparable
    assert result.relation is TemporalComparisonRelation.INSUFFICIENT_EVIDENCE


# ── Anchor selection ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_past_prefers_origin_memory_event_and_present_is_newest():
    past = mk_event("I'm thinking about leaving my job.", memory_id="mem_origin")
    present = mk_event("I finally left my job today.", memory_id="mem_now")
    thread = mk_thread(origin_memory_id="mem_origin", subject="Leave my job")

    # Events arrive out of chronological order on purpose.
    result = await compare(
        thread=thread, events=[present, past],
        lifecycle_result=mk_lifecycle(
            thread_id=thread.id, transitioned=True,
            status=TemporalThreadStatus.RESOLVED, confidence=0.7,
        ),
    )

    assert result.comparable
    assert result.past_event_id == past.id
    assert result.present_event_id == present.id


@pytest.mark.asyncio
async def test_origin_memory_beats_merely_earliest_event():
    from datetime import datetime

    first = mk_event("An unrelated earlier note.", memory_id="mem_a",
                     occurred_at=datetime(2026, 1, 1))
    origin = mk_event("I'm considering leaving my job.", memory_id="mem_origin",
                      occurred_at=datetime(2026, 1, 2))
    newest = mk_event("More thoughts about leaving my job.", memory_id="mem_c",
                      occurred_at=datetime(2026, 1, 3))
    thread = mk_thread(origin_memory_id="mem_origin", subject="Leaving my job")

    result = await compare(thread=thread, events=[first, origin, newest])

    assert result.comparable
    assert result.past_event_id == origin.id       # origin wins over earliest
    assert result.present_event_id == newest.id


@pytest.mark.asyncio
async def test_falls_back_to_earliest_event_without_origin_match():
    earliest = mk_event("First recorded moment about the move.",
                        memory_id="mem_x")
    present = mk_event("The move is done and we settled in.", memory_id="mem_y")
    thread = mk_thread(origin_memory_id="mem_missing", subject="The move")

    result = await compare(thread=thread, events=[earliest, present])

    assert result.comparable
    assert result.past_event_id == earliest.id


# ── Lifecycle-grounded relations ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_lifecycle_resolution_grounds_resolved_relation():
    past = mk_event("I don't know if I should leave my job.", memory_id="mem_o")
    present = mk_event("I finally left my job today.", memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.DECISION, origin_memory_id="mem_o")

    result = await compare(
        thread=thread, events=[past, present],
        lifecycle_result=mk_lifecycle(
            thread_id=thread.id, transitioned=True,
            status=TemporalThreadStatus.RESOLVED, confidence=0.80,
        ),
    )

    assert result.relation is TemporalComparisonRelation.RESOLVED
    assert result.confidence >= 0.65
    assert any("resolved" in s.lower() for s in result.signals)


@pytest.mark.asyncio
async def test_lifecycle_changed_transition_maps_to_changed_relation():
    past = mk_event("I want to become a software engineer.", TemporalType.GOAL,
                    memory_id="mem_o")
    present = mk_event("I've decided to pursue design instead.", memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.GOAL, origin_memory_id="mem_o")

    result = await compare(
        thread=thread, events=[past, present],
        lifecycle_result=mk_lifecycle(
            thread_id=thread.id, transitioned=True,
            status=TemporalThreadStatus.CHANGED, confidence=0.70,
        ),
    )

    assert result.relation is TemporalComparisonRelation.CHANGED
    assert result.confidence >= 0.60


@pytest.mark.asyncio
async def test_lifecycle_abandoned_transition_is_reported_as_changed():
    past = mk_event("I want to learn to play guitar.", TemporalType.GOAL,
                    memory_id="mem_o")
    present = mk_event("I'm giving up on learning guitar.", memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.GOAL, origin_memory_id="mem_o")

    result = await compare(
        thread=thread, events=[past, present],
        lifecycle_result=mk_lifecycle(
            thread_id=thread.id, transitioned=True,
            status=TemporalThreadStatus.ABANDONED, confidence=0.75,
        ),
    )

    assert result.relation is TemporalComparisonRelation.CHANGED
    assert any("withdrawal" in s.lower() or "abandoned" in s.lower()
               for s in result.signals)


@pytest.mark.asyncio
async def test_foreign_lifecycle_result_does_not_influence_relation():
    past = mk_event("I want to run a marathon.", TemporalType.GOAL,
                    memory_id="mem_o")
    present = mk_event("Marathon training update: making progress weekly.",
                       memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.GOAL, origin_memory_id="mem_o")

    # The lifecycle result refers to a DIFFERENT thread — it must be ignored.
    result = await compare(
        thread=thread, events=[past, present],
        lifecycle_result=mk_lifecycle(
            thread_id="thread_other", transitioned=True,
            status=TemporalThreadStatus.RESOLVED, confidence=0.9,
        ),
    )

    assert result.relation is not TemporalComparisonRelation.RESOLVED
    assert result.relation is TemporalComparisonRelation.EVOLVED


# ── Fear stories ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_realized_fear_contradicts_the_past():
    past = mk_event("I'm scared of losing my job.", TemporalType.FEAR,
                    memory_id="mem_o")
    present = mk_event("My fear came true this week.", TemporalType.LIFE_EVENT,
                       memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.FEAR, origin_memory_id="mem_o")

    result = await compare(thread=thread, events=[past, present])

    assert result.relation is TemporalComparisonRelation.CONTRADICTED
    assert result.present_summary  # grounded summary exists


@pytest.mark.asyncio
async def test_overcome_fear_resolves_the_story():
    past = mk_event("I'm afraid of public speaking.", TemporalType.FEAR,
                    memory_id="mem_o")
    present = mk_event("Honestly I am no longer afraid of speaking up.",
                       memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.FEAR, origin_memory_id="mem_o")

    result = await compare(thread=thread, events=[past, present])

    assert result.relation is TemporalComparisonRelation.RESOLVED


# ── Deliberation outcome observation ─────────────────────────────────────


@pytest.mark.asyncio
async def test_weak_outcome_observed_on_deliberation_without_transition():
    past = mk_event("I keep asking whether to take the offer.", TemporalType.QUESTION,
                    memory_id="mem_o")
    present = mk_event("It ended up fine after all.", memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.QUESTION, origin_memory_id="mem_o")

    # No lifecycle transition supplied: the sub-threshold outcome evidence
    # grounds a lower-confidence observational RESOLVED instead of silence.
    result = await compare(thread=thread, events=[past, present])

    assert result.relation is TemporalComparisonRelation.RESOLVED
    assert 0.5 < result.confidence <= 0.85
    assert any("outcome evidence" in s.lower() for s in result.signals)


@pytest.mark.asyncio
async def test_no_outcome_language_leaves_deliberation_unresolved():
    past = mk_event("Should I ask for a raise this year?", TemporalType.QUESTION,
                    memory_id="mem_o")
    present = mk_event("Work has been busy lately.", memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.QUESTION, origin_memory_id="mem_o")

    result = await compare(thread=thread, events=[past, present])

    assert result.relation is TemporalComparisonRelation.UNRESOLVED


# ── Consistency corroboration ────────────────────────────────────────────


def _related_consistency(entry_type: str) -> ConsistencyResult:
    return ConsistencyResult(
        changes=[
            ContradictionResult(
                type=entry_type,
                previous_value="becoming a software engineer",
                current_value="pursue music full time",
                supporting_memory_ids=["mem_goal"],
            )
        ],
    )


@pytest.mark.asyncio
async def test_related_statement_conflict_contradicts_thread():
    past = mk_event("I believe discipline beats motivation.", TemporalType.BELIEF,
                    memory_id="mem_goal")
    present = mk_event("Lately I mostly rely on motivation.", memory_id="mem_n")
    thread = mk_thread(
        temporal_type=TemporalType.BELIEF, subject="Discipline versus motivation",
        origin_memory_id="mem_goal", related_memory_ids=["mem_goal"],
    )

    consistency = ConsistencyResult(
        contradictions=[
            ContradictionResult(
                type="STATEMENT_CONFLICT",
                previous_value="discipline beats motivation",
                current_value="motivation matters more",
                supporting_memory_ids=["mem_goal"],
            )
        ],
    )
    result = await compare(
        thread=thread, events=[past, present], consistency_result=consistency,
    )

    assert result.relation is TemporalComparisonRelation.CONTRADICTED


@pytest.mark.asyncio
async def test_related_goal_change_supports_changed_relation():
    past = mk_event("I want to become a software engineer.", TemporalType.GOAL,
                    memory_id="mem_goal")
    present = mk_event("These days I dream about a different path.", memory_id="mem_n")
    thread = mk_thread(
        temporal_type=TemporalType.GOAL, subject="Becoming a software engineer",
        origin_memory_id="mem_goal", related_memory_ids=["mem_goal"],
    )

    result = await compare(
        thread=thread, events=[past, present],
        consistency_result=_related_consistency("GOAL_CHANGE"),
    )

    assert result.relation is TemporalComparisonRelation.CHANGED


@pytest.mark.asyncio
async def test_unrelated_consistency_entries_are_ignored():
    past = mk_event("I want to learn to play guitar.", TemporalType.GOAL,
                    memory_id="mem_o")
    present = mk_event("Still thinking about learning to play guitar.", memory_id="mem_n")
    thread = mk_thread(
        temporal_type=TemporalType.GOAL, subject="Learning to play guitar",
        origin_memory_id="mem_o",
    )

    unrelated = _related_consistency("GOAL_CHANGE")  # about software engineering
    result = await compare(
        thread=thread, events=[past, present], consistency_result=unrelated,
    )

    assert result.relation is TemporalComparisonRelation.CONFIRMED


# ── Continuation semantics ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_repeated_position_confirms_the_past():
    past = mk_event("I'm thinking about leaving my job.", memory_id="mem_o")
    present = mk_event("Still thinking about leaving my job.", memory_id="mem_n")
    thread = mk_thread(subject="Leaving my job", origin_memory_id="mem_o")

    result = await compare(thread=thread, events=[past, present])

    assert result.relation is TemporalComparisonRelation.CONFIRMED
    assert result.confidence > 0.5
    assert any("restates" in s.lower() for s in result.signals)


@pytest.mark.asyncio
async def test_development_markers_evolve_the_story():
    past = mk_event("I want to run a marathon someday.", TemporalType.GOAL,
                    memory_id="mem_o")
    present = mk_event("Marathon training update: making progress weekly.",
                       memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.GOAL, origin_memory_id="mem_o")

    result = await compare(thread=thread, events=[past, present])

    assert result.relation is TemporalComparisonRelation.EVOLVED
    assert any("development evidence" in s.lower() for s in result.signals)


@pytest.mark.asyncio
async def test_disjoint_moments_remain_unresolved_with_low_confidence():
    past = mk_event("I'm thinking about leaving my job.", memory_id="mem_o")
    present = mk_event("The garden tomatoes are finally ripe.", memory_id="mem_n")
    thread = mk_thread(subject="Leaving my job", origin_memory_id="mem_o")

    result = await compare(thread=thread, events=[past, present])

    assert result.relation is TemporalComparisonRelation.UNRESOLVED
    assert result.confidence <= 0.35


# ── Evidence, summaries, caps, read-only behavior ────────────────────────


@pytest.mark.asyncio
async def test_evidence_ids_are_exposed_and_deduplicated():
    past = mk_event("I'm thinking about leaving my job.", memory_id="mem_1")
    present = mk_event("Still thinking about leaving my job.", memory_id="mem_2")
    thread = mk_thread(origin_memory_id="mem_1", related_memory_ids=["mem_1"])

    result = await compare(thread=thread, events=[past, present])

    assert result.evidence_event_ids == [past.id, present.id]
    assert result.evidence_memory_ids == ["mem_1", "mem_2"]
    assert len(set(result.evidence_event_ids)) == len(result.evidence_event_ids)
    assert len(set(result.evidence_memory_ids)) == len(result.evidence_memory_ids)


@pytest.mark.asyncio
async def test_confidence_is_never_allowed_to_reach_one():
    past = mk_event("I don't know if I should leave my job.", memory_id="mem_o")
    present = mk_event("I finally left my job today.", memory_id="mem_n")
    thread = mk_thread(origin_memory_id="mem_o")

    result = await compare(
        thread=thread, events=[past, present],
        lifecycle_result=mk_lifecycle(
            thread_id=thread.id, transitioned=True,
            status=TemporalThreadStatus.RESOLVED, confidence=0.99,
        ),
    )

    assert result.confidence == MAX_COMPARISON_CONFIDENCE
    assert result.confidence < 1.0


@pytest.mark.asyncio
async def test_summaries_are_type_templated_and_quote_stored_text():
    past = mk_event("I don't know if I should leave my job.", TemporalType.DECISION,
                    memory_id="mem_o")
    present = mk_event("I finally left my job.", TemporalType.LIFE_EVENT,
                       memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.DECISION, origin_memory_id="mem_o")

    resolved = await compare(
        thread=thread, events=[past, present],
        lifecycle_result=mk_lifecycle(
            thread_id=thread.id, transitioned=True,
            status=TemporalThreadStatus.RESOLVED, confidence=0.8,
        ),
    )
    assert 'Back then you were weighing: "I don\'t know if I should leave my job."' \
        in resolved.past_summary
    assert "Now it has played out:" in resolved.present_summary

    unresolved = await compare(
        thread=thread,
        events=[
            past,
            mk_event("Totally different garden talk.", memory_id="mem_n"),
        ],
    )
    assert unresolved.relation is TemporalComparisonRelation.UNRESOLVED
    assert "As of now it remains open:" in unresolved.present_summary


@pytest.mark.asyncio
async def test_comparison_is_strictly_read_only_and_deterministic():
    from chronos_engine.storage import InMemoryTemporalStore

    store = InMemoryTemporalStore()
    past = mk_event("I don't know if I should leave my job.", TemporalType.DECISION,
                    memory_id="mem_o")
    present = mk_event("I finally left my job today.", memory_id="mem_n")
    thread = mk_thread(temporal_type=TemporalType.DECISION, origin_memory_id="mem_o")
    await store.save_thread(thread)
    await store.save_event(past)
    await store.save_event(present)
    thread_before = (await store.get_thread(thread.id, USER)).model_dump()
    events_before = [e.model_dump() for e in await store.get_events_by_thread(thread.id, USER)]

    loaded = await store.get_thread(thread.id, USER)
    loaded_events = await store.get_events_by_thread(thread.id, USER)
    engine = TemporalComparisonEngine()
    first = await engine.compare(USER, loaded, loaded_events)
    second = await engine.compare(USER, loaded, loaded_events)

    assert first.model_dump() == second.model_dump()   # deterministic
    assert (await store.get_thread(thread.id, USER)).model_dump() == thread_before
    assert [
        e.model_dump() for e in await store.get_events_by_thread(thread.id, USER)
    ] == events_before
    assert len(await store.get_threads_by_user(USER)) == 1   # nothing created


# ── State builder integration ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_state_builder_passes_comparison_result_through():
    user_input = UserInput(id="in_3e", user_id="u", content="x")
    comparison = TemporalComparisonResult(attempted=True, comparable=True)
    state = await StateBuilder().build(
        user_input, RetrievedContext(), temporal_comparison=comparison
    )
    assert state.temporal_comparison is comparison


@pytest.mark.asyncio
async def test_chronos_state_defaults_to_no_comparison_result():
    user_input = UserInput(id="in_3e", user_id="u", content="hello")
    state = await StateBuilder().build(user_input, RetrievedContext())
    assert state.temporal_comparison is None


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
async def test_engine_end_to_end_compares_then_resolves_flagship_story():
    engine = ChronosEngine(ai_executor=RecordingAIExecutor())
    user_id = "user_3e_e2e"

    r1 = await engine.process_user_input(
        user_id=user_id,
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )
    c1 = r1.chronos_state.temporal_comparison
    assert c1 is not None
    assert c1.attempted and not c1.comparable
    assert c1.relation is TemporalComparisonRelation.INSUFFICIENT_EVIDENCE
    trace1 = "\n".join(r1.reasoning_trace.reasoning_steps).lower()
    assert "temporal comparison -> insufficient_evidence" in trace1

    r2 = await engine.process_user_input(
        user_id=user_id,
        content="I finally left my job.",
        input_type="text",
        provider_key="chronos",
    )
    c2 = r2.chronos_state.temporal_comparison
    assert c2.attempted and c2.comparable
    assert c2.relation is TemporalComparisonRelation.RESOLVED
    assert c2.thread_id == c1.thread_id
    assert c2.past_event_id and c2.present_event_id
    trace2 = "\n".join(r2.reasoning_trace.reasoning_steps).lower()
    assert "temporal comparison -> resolved" in trace2
    assert isinstance(engine.ai_executor, RecordingAIExecutor)
    assert engine.ai_executor.calls == 0          # AI never invoked


@pytest.mark.asyncio
async def test_engine_trace_reports_skip_when_no_temporal_thread():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_3e_quiet",
        content="Hi there!",
        input_type="text",
        provider_key="chronos",
    )
    comparison = response.chronos_state.temporal_comparison
    assert comparison is not None
    assert not comparison.attempted
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "temporal comparison skipped: no temporal thread available" in trace


@pytest.mark.asyncio
async def test_engine_ambiguity_leaves_comparison_skipped():
    engine = ChronosEngine()
    user_id = "user_3e_amb"
    await engine.temporal_store.save_thread(
        TemporalThread(user_id=user_id, subject="Decision about leaving my job",
                       temporal_type=TemporalType.DECISION)
    )
    await engine.temporal_store.save_thread(
        TemporalThread(user_id=user_id, subject="Another decision about leaving my job soon",
                       temporal_type=TemporalType.DECISION)
    )

    response = await engine.process_user_input(
        user_id=user_id,
        content="I'm thinking about leaving my job.",
        input_type="text",
        provider_key="chronos",
    )

    state = response.chronos_state
    assert state.temporal_thread_match.ambiguous
    assert state.temporal_lifecycle.thread_id is None
    assert not state.temporal_comparison.attempted
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "temporal comparison skipped: no temporal thread available" in trace


@pytest.mark.asyncio
async def test_engine_comparison_engine_injection_via_dependency_injection():
    calls = {"count": 0}

    class StubComparison(BaseTemporalComparisonEngine):
        async def compare(self, user_id, thread, events, **kwargs):
            calls["count"] += 1
            return TemporalComparisonResult(
                attempted=True,
                comparable=bool(thread),
                relation=TemporalComparisonRelation.EVOLVED,
                confidence=0.6,
                reason="stub comparison",
            )

    stub = StubComparison()
    engine = ChronosEngine(temporal_comparison=stub)
    response = await engine.process_user_input(
        user_id="user_3e_stub",
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )

    assert calls["count"] == 1
    assert response.chronos_state.temporal_comparison.relation \
        is TemporalComparisonRelation.EVOLVED
