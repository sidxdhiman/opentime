"""Phase 3F tests: deterministic Past-Self Question planning.

Covers the required planning behavior: relation-driven question types
(RESOLVED/CHANGED/CONTRADICTED/EVOLVED/CONFIRMED/UNRESOLVED), temporal-type
specific focus and overrides, conservative gates (insufficient evidence,
single-moment histories, ambiguity, weak confidence, open stories without
continuity), WHAT/HOW separation (grounded focus + canonical template),
correct evidence mirroring, determinism, strict read-only behavior, and
end-to-end engine integration with honest trace entries and zero AI
invocation.

Deterministic and offline throughout — no AI, no embeddings.
"""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.interfaces import (
    BaseAIExecutor,
    BasePastSelfQuestionPlanner,
)
from chronos_engine.core.models import RetrievedContext, UserInput
from chronos_engine.state.builder import StateBuilder
from chronos_engine.storage import InMemoryTemporalStore
from chronos_engine.temporal.models import (
    PastSelfPerspective,
    PastSelfQuestionResult,
    PastSelfQuestionType,
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalLifecycleResult,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)
from chronos_engine.temporal.questions import PastSelfQuestionPlanner

USER = "user_3f"


def mk_event(
    description,
    ttype=None,
    memory_id=None,
    event_id=None,
    **kwargs,
) -> TemporalEvent:
    event = TemporalEvent(
        temporal_type=ttype, description=description, memory_id=memory_id, **kwargs
    )
    if event_id:
        event.id = event_id
    return event


def mk_thread(**kwargs) -> TemporalThread:
    kwargs.setdefault("user_id", USER)
    return TemporalThread(**kwargs)


def mk_comparison(
    relation=TemporalComparisonRelation.RESOLVED,
    confidence=0.80,
    thread_id=None,
    comparable=True,
    attempted=True,
    past_id="tevent_past",
    present_id="tevent_present",
    memories=("mem_1", "mem_2"),
    past_desc='I don\'t know if I should leave my job.',
    present_desc="I finally left my job.",
) -> TemporalComparisonResult:
    return TemporalComparisonResult(
        attempted=attempted,
        comparable=comparable,
        relation=relation,
        confidence=confidence,
        thread_id=thread_id,
        past_event_id=past_id if comparable else None,
        present_event_id=present_id if comparable else None,
        past_summary=f'Back then: "{past_desc}"' if comparable else "",
        present_summary=f'Now: "{present_desc}"' if comparable else "",
        evidence_memory_ids=list(memories) if comparable else [],
        evidence_event_ids=[past_id, present_id] if comparable else [],
        signals=["Shared topic tokens across moments: job, leave."],
        reason="test comparison",
    )


async def seeded_store(thread=None, events=()) -> InMemoryTemporalStore:
    store = InMemoryTemporalStore()
    if thread is not None:
        await store.save_thread(thread)
    for event in events:
        await store.save_event(event)
    return store


# ── Relation-driven question types ────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolved_decision_plans_outcome_reveal_question():
    thread = mk_thread(temporal_type=TemporalType.DECISION, subject="Leave my job")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.RESOLVED, thread_id=thread.id
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.attempted
    assert result.should_ask
    assert result.question_type is PastSelfQuestionType.OUTCOME_REVEAL
    assert result.comparison_relation is TemporalComparisonRelation.RESOLVED
    # WHAT vs HOW separation: grounded focus plus {subject} placeholder only.
    assert "feels now about the decision" in result.intent.focus
    assert "{subject}" in result.intent.canonical_template
    assert "leave my job" not in result.intent.canonical_template.replace(
        "{subject}", ""
    )
    assert result.intent.perspective is PastSelfPerspective.PAST_TO_PRESENT


@pytest.mark.asyncio
async def test_resolved_fear_plans_past_to_present_reflection():
    thread = mk_thread(temporal_type=TemporalType.FEAR, subject="Failing college")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.RESOLVED, thread_id=thread.id
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.should_ask
    assert result.question_type is PastSelfQuestionType.REFLECTION
    assert "tell their past self" in result.intent.focus
    assert "overcame" not in result.reason.lower()   # no unsupported claims


@pytest.mark.asyncio
async def test_changed_relation_plans_reflection():
    thread = mk_thread(temporal_type=TemporalType.GOAL, subject="Joining college")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.CHANGED,
        confidence=0.70,
        thread_id=thread.id,
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.should_ask
    assert result.question_type is PastSelfQuestionType.REFLECTION


@pytest.mark.asyncio
async def test_contradicted_relation_plans_perspective_reflection():
    thread = mk_thread(temporal_type=TemporalType.BELIEF, subject="Discipline first")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.CONTRADICTED,
        confidence=0.65,
        thread_id=thread.id,
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.should_ask
    assert result.question_type is PastSelfQuestionType.REFLECTION
    assert "perspective" in result.intent.focus.lower()


@pytest.mark.asyncio
async def test_evolved_relation_plans_check_in():
    thread = mk_thread(temporal_type=TemporalType.GOAL, subject="Running a marathon")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.EVOLVED,
        confidence=0.60,
        thread_id=thread.id,
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.should_ask
    assert result.question_type is PastSelfQuestionType.CHECK_IN


@pytest.mark.asyncio
async def test_confirmed_relation_plans_reassurance():
    thread = mk_thread(temporal_type=TemporalType.BELIEF, subject="Practice beats talent")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.CONFIRMED,
        confidence=0.66,
        thread_id=thread.id,
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.should_ask
    assert result.question_type is PastSelfQuestionType.REASSURANCE


@pytest.mark.asyncio
async def test_unresolved_with_rich_history_plans_cautious_revisit():
    thread = mk_thread(temporal_type=TemporalType.GOAL, subject="Learning guitar")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.UNRESOLVED,
        confidence=0.30,
        thread_id=thread.id,
    )
    events = [
        mk_event("I want to learn guitar.", event_id="tevent_past",
                 memory_id="mem_1"),
        mk_event("Bought a guitar this week.", event_id="tevent_mid",
                 memory_id="mem_x"),
        mk_event("Still practicing chords some nights.", event_id="tevent_present",
                 memory_id="mem_2"),
    ]
    result = PastSelfQuestionPlanner().plan(
        USER, thread, comparison, events=events
    )

    assert result.should_ask
    assert result.question_type is PastSelfQuestionType.REVISIT
    assert 0.5 <= result.confidence <= 0.70   # deliberately modest


@pytest.mark.asyncio
async def test_unresolved_with_shared_topic_continuity_plans_revisit():
    thread = mk_thread(temporal_type=TemporalType.QUESTION, subject="Leaving my job")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.UNRESOLVED,
        confidence=0.30,
        thread_id=thread.id,
        past_desc="I'm still thinking about leaving my job.",
        present_desc="Thinking about leaving my job again tonight.",
    )
    events = [
        mk_event("I'm still thinking about leaving my job.",
                 event_id="tevent_past", memory_id="mem_1"),
        mk_event("Thinking about leaving my job again tonight.",
                 event_id="tevent_present", memory_id="mem_2"),
    ]
    result = PastSelfQuestionPlanner().plan(
        USER, thread, comparison, events=events
    )

    assert result.should_ask
    assert result.question_type is PastSelfQuestionType.REVISIT


@pytest.mark.asyncio
async def test_unresolved_without_continuity_is_skipped():
    thread = mk_thread(subject="Leaving my job")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.UNRESOLVED,
        confidence=0.30,
        thread_id=thread.id,
        past_desc="I'm thinking about leaving my job.",
        present_desc="The garden tomatoes are finally ripe.",
    )
    events = [
        mk_event("I'm thinking about leaving my job.", event_id="tevent_past"),
        mk_event("The garden tomatoes are finally ripe.", event_id="tevent_present"),
    ]
    result = PastSelfQuestionPlanner().plan(
        USER, thread, comparison, events=events
    )

    assert not result.should_ask
    assert result.question_type is None
    assert "continuity" in result.reason.lower()


# ── Conservative gates ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_insufficient_evidence_relation_never_asks():
    thread = mk_thread(subject="Some story")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.INSUFFICIENT_EVIDENCE,
        confidence=0.0,
        thread_id=thread.id,
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.attempted
    assert not result.should_ask
    assert result.question_type is None


@pytest.mark.asyncio
async def test_single_moment_comparison_never_fabricates_question():
    thread = mk_thread(temporal_type=TemporalType.DECISION, subject="Leave my job")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.RESOLVED,
        comparable=False,          # 3E single-moment carve-out shape
        thread_id=thread.id,
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.attempted
    assert not result.should_ask
    assert "fabricat" in result.reason.lower()


@pytest.mark.asyncio
async def test_no_thread_reports_honest_skip():
    result = PastSelfQuestionPlanner().plan(USER, None, None)

    assert not result.attempted
    assert not result.should_ask
    assert "no temporal thread" in result.reason.lower()


@pytest.mark.asyncio
async def test_ambiguous_lifecycle_blocks_question():
    thread = mk_thread(subject="Leave my job")
    comparison = mk_comparison(thread_id=thread.id)
    lifecycle = TemporalLifecycleResult(attempted=True, ambiguous=True)
    result = PastSelfQuestionPlanner().plan(
        USER, thread, comparison, lifecycle_result=lifecycle
    )

    assert result.attempted
    assert not result.should_ask
    assert "ambiguous" in result.reason.lower()


@pytest.mark.asyncio
async def test_low_confidence_comparison_is_skipped_conservatively():
    thread = mk_thread(temporal_type=TemporalType.BELIEF, subject="Some belief")
    comparison = mk_comparison(
        relation=TemporalComparisonRelation.CONFIRMED,
        confidence=0.45,           # below the documented floor
        thread_id=thread.id,
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert not result.should_ask
    assert "threshold" in result.reason.lower()


@pytest.mark.asyncio
async def test_foreign_comparison_result_does_not_plan_a_question():
    thread = mk_thread(subject="Leave my job")
    comparison = mk_comparison(thread_id="thread_someone_else")
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert not result.should_ask
    assert "no applicable comparison" in result.reason.lower()


# ── Temporal-type behavior ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_different_temporal_types_produce_different_focus():
    focuses = {}
    for ttype in (
        TemporalType.DECISION,
        TemporalType.FEAR,
        TemporalType.GOAL,
        TemporalType.FUTURE_EXPECTATION,
        TemporalType.BELIEF,
        TemporalType.MILESTONE,
        TemporalType.PROMISE,
        TemporalType.QUESTION,
    ):
        thread = mk_thread(temporal_type=ttype, subject="Whatever story")
        comparison = mk_comparison(thread_id=thread.id)
        result = PastSelfQuestionPlanner().plan(USER, thread, comparison)
        assert result.should_ask
        focuses[ttype] = result.intent.focus

    assert len(set(focuses.values())) == len(focuses)
    assert "followed through" in focuses[TemporalType.PROMISE].lower()
    assert "reality compared" in focuses[TemporalType.FUTURE_EXPECTATION].lower()
    assert "sees the change now" in focuses[TemporalType.MILESTONE].lower()


@pytest.mark.asyncio
async def test_resolved_question_thread_prefers_reflection_over_outcome():
    thread = mk_thread(temporal_type=TemporalType.QUESTION, subject="Asking for a raise")
    comparison = mk_comparison(thread_id=thread.id)
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.question_type is PastSelfQuestionType.REFLECTION
    assert "answered" in result.intent.focus.lower()


# ── Evidence grounding ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_supporting_event_and_memory_ids_mirror_comparison_evidence():
    thread = mk_thread(subject="Leave my job")
    comparison = mk_comparison(
        thread_id=thread.id,
        past_id="tevent_alpha",
        present_id="tevent_omega",
        memories=("mem_a", "mem_b"),
    )
    result = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert result.past_event_id == "tevent_alpha"
    assert result.present_event_id == "tevent_omega"
    assert result.supporting_event_ids == ["tevent_alpha", "tevent_omega"]
    assert result.supporting_memory_ids == ["mem_a", "mem_b"]


@pytest.mark.asyncio
async def test_anchor_integrity_mismatch_skips_conservatively():
    thread = mk_thread(subject="Leave my job")
    comparison = mk_comparison(thread_id=thread.id)
    unrelated_events = [mk_event("Unrelated.", event_id="tevent_other")]
    result = PastSelfQuestionPlanner().plan(
        USER, thread, comparison, events=unrelated_events
    )

    assert not result.should_ask
    assert "conservatively skipped" in result.reason.lower()


@pytest.mark.asyncio
async def test_extra_recorded_moments_strengthen_confidence_with_cap():
    thread = mk_thread(subject="Leave my job")
    comparison = mk_comparison(confidence=0.80, thread_id=thread.id)
    two_events = [mk_event("a", event_id="tevent_past"),
                  mk_event("b", event_id="tevent_present")]
    four_events = two_events + [mk_event("c"), mk_event("d")]

    base = PastSelfQuestionPlanner().plan(USER, thread, comparison, events=two_events)
    richer = PastSelfQuestionPlanner().plan(USER, thread, comparison, events=four_events)

    assert richer.confidence > base.confidence
    assert richer.confidence <= 0.95


# ── Determinism & read-only behavior ─────────────────────────────────────


@pytest.mark.asyncio
async def test_repeated_execution_is_deterministic():
    thread = mk_thread(temporal_type=TemporalType.DECISION, subject="Leave my job")
    comparison = mk_comparison(thread_id=thread.id)
    first = PastSelfQuestionPlanner().plan(USER, thread, comparison)
    second = PastSelfQuestionPlanner().plan(USER, thread, comparison)

    assert first.model_dump() == second.model_dump()


@pytest.mark.asyncio
async def test_planner_never_mutates_threads_or_events_or_store():
    thread = mk_thread(temporal_type=TemporalType.DECISION, subject="Leave my job")
    past = mk_event("I don't know if I should leave my job.",
                    event_id="tevent_past", memory_id="mem_1",
                    thread_id=thread.id)
    present = mk_event("I finally left my job.", event_id="tevent_present",
                       memory_id="mem_2", thread_id=thread.id)
    store = await seeded_store(thread, [past, present])
    thread_before = (await store.get_thread(thread.id, USER)).model_dump()

    loaded = await store.get_thread(thread.id, USER)
    loaded_events = await store.get_events_by_thread(thread.id, USER)
    result = PastSelfQuestionPlanner().plan(USER, loaded, mk_comparison(
        thread_id=thread.id), events=loaded_events)

    assert result.should_ask
    assert (await store.get_thread(thread.id, USER)).model_dump() == thread_before
    stored_events = await store.get_events_by_thread(thread.id, USER)
    assert [e.model_dump() for e in stored_events] == [
        e.model_dump() for e in loaded_events
    ]
    assert len(await store.get_threads_by_user(USER)) == 1   # nothing created
    # The planner never mutates the handed-in models either.
    assert loaded.status is TemporalThreadStatus.OPEN


# ── State builder integration ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_state_builder_passes_question_result_through():
    user_input = UserInput(id="in_3f", user_id="u", content="x")
    question = PastSelfQuestionResult(attempted=True, should_ask=True)
    state = await StateBuilder().build(
        user_input, RetrievedContext(), past_self_question=question
    )
    assert state.past_self_question is question


@pytest.mark.asyncio
async def test_chronos_state_defaults_to_no_question_result():
    user_input = UserInput(id="in_3f", user_id="u", content="hello")
    state = await StateBuilder().build(user_input, RetrievedContext())
    assert state.past_self_question is None


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
async def test_engine_end_to_end_plans_flagship_outcome_reveal_question():
    recorder = RecordingAIExecutor()
    engine = ChronosEngine(ai_executor=recorder)
    user_id = "user_3f_e2e"

    # Input 1: thread creation -> single moment, no fabricated question.
    r1 = await engine.process_user_input(
        user_id=user_id,
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )
    q1 = r1.chronos_state.past_self_question
    assert q1 is not None
    assert q1.attempted and not q1.should_ask
    assert q1.question_type is None

    # Input 2: explicit outcome -> flagship past-self question.
    r2 = await engine.process_user_input(
        user_id=user_id,
        content="I finally left my job.",
        input_type="text",
        provider_key="chronos",
    )
    q2 = r2.chronos_state.past_self_question
    assert q2.attempted and q2.should_ask
    assert q2.question_type is PastSelfQuestionType.OUTCOME_REVEAL
    assert q2.thread_id == r1.chronos_state.temporal_comparison.thread_id
    assert q2.past_event_id and q2.present_event_id
    assert set(q2.supporting_event_ids) == {
        q2.past_event_id, q2.present_event_id,
    }
    memories = {m.id for m in await engine.get_memories(user_id)}
    assert set(q2.supporting_memory_ids) <= memories   # grounded references only

    trace2 = "\n".join(r2.reasoning_trace.reasoning_steps).lower()
    assert "past-self question planned -> outcome_reveal" in trace2

    # Read-only end state: exactly the lifecycle's own persisted artifacts.
    stored = await engine.temporal_store.get_thread(q2.thread_id, user_id)
    assert stored.status is TemporalThreadStatus.RESOLVED
    assert len(await engine.temporal_store.get_events_by_thread(q2.thread_id, user_id)) == 2
    assert isinstance(engine.ai_executor, RecordingAIExecutor)
    assert recorder.calls == 0                      # AI never invoked


@pytest.mark.asyncio
async def test_engine_trace_reports_skip_for_non_temporal_input():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_3f_quiet",
        content="What is Python?",
        input_type="text",
        provider_key="chronos",
    )
    question = response.chronos_state.past_self_question
    assert question is not None
    assert not question.attempted
    assert question.thread_id is None               # no invented history
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "past-self question skipped: no temporal thread available" in trace


@pytest.mark.asyncio
async def test_engine_trace_reports_skip_on_first_single_moment_thread():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_3f_first",
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )
    question = response.chronos_state.past_self_question
    assert question is not None
    assert question.attempted and not question.should_ask
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "past-self question skipped:" in trace
    assert "fewer than two distinct grounded moments" in trace


@pytest.mark.asyncio
async def test_engine_question_planner_injection_via_dependency_injection():
    calls = {"count": 0}

    class StubPlanner(BasePastSelfQuestionPlanner):
        def plan(self, user_id, thread, comparison, **kwargs):
            calls["count"] += 1
            return PastSelfQuestionResult(
                attempted=bool(thread),
                should_ask=True,
                question_type=PastSelfQuestionType.SURPRISE,
                reason="stub planner",
            )

    stub = StubPlanner()
    engine = ChronosEngine(past_self_question_planner=stub)
    response = await engine.process_user_input(
        user_id="user_3f_stub",
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )

    assert calls["count"] == 1
    assert response.chronos_state.past_self_question.question_type \
        is PastSelfQuestionType.SURPRISE
