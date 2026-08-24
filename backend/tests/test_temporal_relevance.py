"""Phase 3G tests: deterministic Temporal Relevance & Timing.

Covers the required behavior: hard gate on invalid / refused Phase 3F
results (never overridden), current-turn continuation surfacing,
same-topic reflection surfacing, urgency deferral, unrelated factual
requests never fabricating relevance, generic-overlap and marker-only
insufficiency, goal/consistency strengthening without fabrication,
negative-emotion non-blocking, frustration-based interruption protection,
resolution boosting timing, conservative low-confidence results,
ambiguity guards, determinism, serialization, signal transparency,
read-only guarantees, zero persistence, zero AI invocation and end-to-end
engine integration with honest trace entries.

Deterministic and offline throughout — no AI, no embeddings.
"""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.ai.models import AIExecutionResult
from chronos_engine.core.interfaces import (
    BaseAIExecutor,
    BaseTemporalRelevanceEngine,
)
from chronos_engine.core.models import (
    IntentType,
    RetrievedContext,
    UserInput,
)
from chronos_engine.state.builder import StateBuilder
from chronos_engine.state.models import (
    ConsistencyResult,
    ContradictionResult,
    GoalAnalysisResult,
    IntentResult,
    UserCognitiveState,
    UserEmotionState,
    UserStateResult,
)
from chronos_engine.storage import InMemoryTemporalStore
from chronos_engine.temporal.models import (
    PastSelfQuestionIntent,
    PastSelfQuestionResult,
    PastSelfQuestionType,
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalLifecycleResult,
    TemporalRelevanceDecision,
    TemporalRelevanceResult,
    TemporalThread,
    TemporalThreadMatchResult,
    TemporalType,
)
from chronos_engine.temporal.relevance import TemporalRelevanceEngine

USER = "user_3g"


# ── Fixture helpers ──────────────────────────────────────────────────────


def mk_input(content: str) -> UserInput:
    return UserInput(id="in_3g", user_id=USER, content=content)


def mk_thread(**kwargs) -> TemporalThread:
    kwargs.setdefault("user_id", USER)
    return TemporalThread(**kwargs)


def mk_job_thread() -> TemporalThread:
    """The flagship story: a once-open decision about quitting a job."""
    return mk_thread(
        temporal_type=TemporalType.DECISION,
        subject="Quit my job",
        description="I don't know if I should quit my job.",
        origin_memory_id="mem_past",
        related_memory_ids=["mem_past"],
    )


def mk_question(
    thread: TemporalThread,
    should_ask: bool = True,
    question_type: PastSelfQuestionType = PastSelfQuestionType.OUTCOME_REVEAL,
    confidence: float = 0.85,
    **kwargs,
) -> PastSelfQuestionResult:
    return PastSelfQuestionResult(
        attempted=True,
        should_ask=should_ask,
        question_type=question_type if should_ask else None,
        reason="planned by Phase 3F",
        confidence=confidence,
        thread_id=thread.id,
        comparison_relation=TemporalComparisonRelation.RESOLVED,
        past_event_id=kwargs.get("past_event_id", "tevent_past"),
        present_event_id=kwargs.get("present_event_id", "tevent_present"),
        supporting_memory_ids=["mem_past", "mem_present"],
        supporting_event_ids=["tevent_past", "tevent_present"],
        intent=PastSelfQuestionIntent(
            focus="How the user feels now about the decision",
            canonical_template="Back then, {subject}. How do you feel now?",
        ),
        signals=["test question"],
    )


def mk_events() -> list:
    return [
        TemporalEvent(
            id="tevent_past",
            thread_id=None,
            temporal_type=TemporalType.DECISION,
            description="I don't know if I should quit my job.",
            memory_id="mem_past",
        ),
        TemporalEvent(
            id="tevent_present",
            temporal_type=TemporalType.LIFE_EVENT,
            description="I finally left my job.",
            memory_id="mem_present",
        ),
    ]


def mk_match(thread: TemporalThread, matched: bool = True) -> TemporalThreadMatchResult:
    return TemporalThreadMatchResult(
        attempted=True,
        matched=matched,
        thread_id=thread.id if matched else None,
        confidence=0.70,
        reason="matched" if matched else "no match",
    )


def mk_lifecycle(
    thread: TemporalThread,
    updated: bool = True,
    transitioned: bool = False,
) -> TemporalLifecycleResult:
    return TemporalLifecycleResult(
        attempted=True,
        created=False,
        updated=updated,
        persisted=True,
        thread_id=thread.id,
        event_id="tevent_present",
        thread_subject=thread.subject,
        previous_status=thread.status,
        current_status=thread.status,
        transitioned=transitioned,
        reason="attached",
        confidence=0.80,
    )


def mk_comparison(thread: TemporalThread) -> TemporalComparisonResult:
    return TemporalComparisonResult(
        attempted=True,
        comparable=True,
        relation=TemporalComparisonRelation.RESOLVED,
        confidence=0.80,
        thread_id=thread.id,
        past_event_id="tevent_past",
        present_event_id="tevent_present",
        evidence_memory_ids=["mem_past", "mem_present"],
        evidence_event_ids=["tevent_past", "tevent_present"],
        signals=["Shared topic tokens across moments: job, quit."],
        reason="test comparison",
    )


def evaluate(thread, content, question=None, **kwargs):
    """Convenience wrapper mirroring the engine call shape."""
    return TemporalRelevanceEngine().evaluate(
        user_id=USER,
        user_input=mk_input(content),
        past_self_question=question if question is not None else mk_question(thread),
        thread=thread,
        events=kwargs.pop("events", mk_events()),
        **kwargs,
    )


# ── 1–2. Hard gate: no valid planned question can ever be overridden ────


def test_missing_question_result_skips():
    thread = mk_job_thread()
    result = TemporalRelevanceEngine().evaluate(
        USER, mk_input("I finally left my job."), None, thread=thread
    )
    assert not result.attempted
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert not result.should_surface


def test_unattempted_planning_skips_without_fabrication():
    thread = mk_job_thread()
    question = PastSelfQuestionResult(attempted=False, should_ask=False)
    result = TemporalRelevanceEngine().evaluate(
        USER, mk_input("What is Python?"), question, thread=thread
    )
    assert not result.attempted
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert result.question_type is None


def test_phase_3f_should_ask_false_cannot_be_overridden():
    thread = mk_job_thread()
    question = mk_question(thread, should_ask=False)
    # Even a perfectly continuing, calm, reflective turn may not override.
    result = evaluate(
        thread,
        "I finally left my job, and honestly I'm relieved.",
        question=question,
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, transitioned=True),
    )
    assert result.attempted
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert not result.should_surface
    assert "cannot override" in result.reason.lower()


def test_malformed_question_payload_skips_conservatively():
    thread = mk_job_thread()
    question = mk_question(thread)
    question = question.model_copy(update={"intent": None})  # unusable payload
    result = evaluate(thread, "I finally left my job.", question=question)
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert "conservatively skipped" in result.reason.lower()


def test_foreign_thread_question_skips_conservatively():
    thread = mk_job_thread()
    question = mk_question(thread)
    other = mk_thread(subject="Unrelated story")
    result = TemporalRelevanceEngine().evaluate(
        USER,
        mk_input("I finally left my job."),
        question,
        thread=other,
        events=[],
    )
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert "conservatively skipped" in result.reason.lower()


def test_insufficient_evidence_comparison_blocks_confident_surface():
    thread = mk_job_thread()
    comparison = mk_comparison(thread).model_copy(
        update={"relation": TemporalComparisonRelation.INSUFFICIENT_EVIDENCE}
    )
    result = evaluate(
        thread,
        "I finally left my job.",
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, transitioned=True),
        comparison=comparison,
    )
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert "ambiguity" in result.reason.lower()


def test_ambiguous_lifecycle_prevents_confident_surface():
    thread = mk_job_thread()
    lifecycle = mk_lifecycle(thread, transitioned=True).model_copy(
        update={"ambiguous": True}
    )
    result = evaluate(
        thread,
        "I finally left my job.",
        thread_match=mk_match(thread),
        lifecycle_result=lifecycle,
    )
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert "ambiguous" in result.reason.lower()


# ── 3–4. Current-turn continuation and reflection surface now ───────────


def test_direct_current_turn_continuation_surfaces_now():
    thread = mk_job_thread()
    result = evaluate(
        thread,
        "I finally left my job, and honestly I'm relieved.",
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, transitioned=True),
        comparison=mk_comparison(thread),
    )
    assert result.decision is TemporalRelevanceDecision.SURFACE_NOW
    assert result.should_surface
    assert result.relevance_score >= 0.55
    assert result.timing_score >= 0.45
    assert result.thread_id == thread.id
    assert result.question_type is PastSelfQuestionType.OUTCOME_REVEAL


def test_same_topic_reflection_surfaces_now():
    thread = mk_thread(
        temporal_type=TemporalType.FEAR,
        subject="Making it through college",
        description="I'm scared I won't make it through college.",
        origin_memory_id="mem_college",
    )
    events = [
        TemporalEvent(
            id="tevent_past",
            description="I'm scared I won't make it through college.",
            memory_id="mem_college",
        ),
        TemporalEvent(
            id="tevent_present",
            description="College finals are coming up.",
            memory_id="mem_now",
        ),
    ]
    question = mk_question(
        thread,
        question_type=PastSelfQuestionType.REFLECTION,
        confidence=0.75,
    )
    result = evaluate(
        thread,
        "Sometimes I think about how different I was when I first started "
        "college.",
        question=question,
        events=events,
    )
    assert result.decision is TemporalRelevanceDecision.SURFACE_NOW
    assert any("reflection markers" in s for s in result.signals)


# ── 5. Same topic but urgent immediate problem -> DEFER ──────────────────


def test_same_topic_with_urgent_problem_defers():
    thread = mk_job_thread()
    urgent_state = UserStateResult(
        emotional_state=UserEmotionState.ANXIOUS,
        confidence=0.8,
        urgency=0.85,
    )
    result = evaluate(
        thread,
        "My production server is down, this is urgent, I need help ASAP! "
        "Also I finally quit my job.",
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, transitioned=True),
        user_state=urgent_state,
    )
    assert result.decision is TemporalRelevanceDecision.DEFER
    assert not result.should_surface
    assert any("urgency" in b.lower() for b in result.blocking_signals)


# ── 6–8. Interruption protection: nothing fabricates relevance ──────────


def test_completely_unrelated_factual_request_skips_without_relevance():
    thread = mk_job_thread()
    result = evaluate(thread, "What is Python?")
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert not result.should_surface
    assert result.relevance_score < 0.30
    assert "no meaningful topical relation" in result.reason.lower()


def test_transactional_command_request_never_surfaces():
    thread = mk_job_thread()
    result = evaluate(thread, "Translate this sentence to French.")
    assert result.decision is not TemporalRelevanceDecision.SURFACE_NOW


def test_generic_token_overlap_does_not_create_relevance():
    # The ONLY lexical overlap is the generic token 'new'; it must never
    # open the topical-relevance door.
    thread = mk_thread(
        temporal_type=TemporalType.LIFE_EVENT,
        subject="A new beginning",
        description="I am starting a new chapter.",
    )
    result = evaluate(thread, "I want something new these days.")
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert result.relevance_score < 0.30
    assert any("generic token overlap" in s.lower() for s in result.signals)


def test_reflection_markers_alone_do_not_create_relevance():
    thread = mk_job_thread()
    result = evaluate(thread, "Looking back, I feel different about things.")
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert result.relevance_score < 0.30


def test_supporting_evidence_alone_cannot_fabricate_relevance():
    thread = mk_job_thread()
    goal_analysis = GoalAnalysisResult(
        goal="Learn guitar advanced chords",
        matched_existing_goal="Learn guitar advanced chords",
        confidence=0.9,
    )
    consistency = ConsistencyResult(
        changes=[
            ContradictionResult(
                type="DECISION_CHANGE",
                description="changed direction on guitar learning",
                supporting_memory_ids=["mem_past"],
                confidence=0.8,
            )
        ],
        supporting_memory_ids=["mem_past"],
    )
    result = evaluate(
        thread,
        "Looking back, I want to learn piano instead.",
        goal_analysis=goal_analysis,
        consistency_result=consistency,
    )
    assert result.decision is TemporalRelevanceDecision.SKIP
    assert result.relevance_score < 0.30


# ── 9–10. Goal and consistency continuity strengthen existing relevance ──


def _guitar_base_kwargs():
    thread = mk_thread(
        temporal_type=TemporalType.GOAL,
        subject="Learning guitar",
        description="I want to learn guitar properly.",
    )
    events = [
        TemporalEvent(
            id="tevent_past",
            description="I want to learn guitar properly.",
            memory_id="mem_g1",
        ),
        TemporalEvent(
            id="tevent_present",
            description="Practicing guitar most evenings.",
            memory_id="mem_g2",
        ),
    ]
    return thread, events


def test_goal_continuity_strengthens_topical_relevance():
    thread, events = _guitar_base_kwargs()
    base = evaluate(thread, "Playing guitar has been relaxing lately.", events=events)
    strengthened = evaluate(
        thread,
        "Playing guitar has been relaxing lately.",
        events=events,
        goal_analysis=GoalAnalysisResult(
            goal="Keep learning guitar every week",
            matched_existing_goal="Keep learning guitar every week",
            confidence=0.9,
        ),
    )
    assert strengthened.relevance_score > base.relevance_score
    assert any("Goal continuity" in s for s in strengthened.signals)


def test_consistency_change_evidence_strengthens_topical_relevance():
    thread, events = _guitar_base_kwargs()
    base = evaluate(thread, "Playing guitar has been relaxing lately.", events=events)
    strengthened = evaluate(
        thread,
        "Playing guitar has been relaxing lately.",
        events=events,
        consistency_result=ConsistencyResult(
            changes=[
                ContradictionResult(
                    type="GOAL_CHANGE",
                    description="refocused the guitar learning plan",
                    supporting_memory_ids=["mem_other"],
                    confidence=0.8,
                )
            ],
        ),
    )
    assert strengthened.relevance_score > base.relevance_score
    assert any("Consistency/change evidence" in s for s in strengthened.signals)


# ── 12–14. Emotion never blocks; task frustration does; resolution helps ─


def test_negative_emotion_about_the_topic_does_not_block():
    # Example D shape: the user revisits the very story they once told,
    # in a clearly negative emotional state — emotion alone never blocks.
    thread = mk_thread(
        temporal_type=TemporalType.DECISION,
        subject="Quitting my job",
        description="I've been thinking about quitting my job.",
        origin_memory_id="mem_past",
    )
    upset_state = UserStateResult(
        emotional_state=UserEmotionState.SAD,
        secondary_states=[UserEmotionState.ANXIOUS],
        valence=-0.5,
        confidence=0.8,
    )
    result = evaluate(
        thread,
        "I'm really upset because I keep wondering if quitting was a mistake.",
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread),
        user_state=upset_state,
    )
    assert result.decision is TemporalRelevanceDecision.SURFACE_NOW
    assert result.blocking_signals == []


def test_frustration_about_unrelated_task_blocks_interruption():
    thread = mk_job_thread()
    frustrated_state = UserStateResult(
        emotional_state=UserEmotionState.FRUSTRATED,
        cognitive_state=UserCognitiveState.FOCUSED,
        confidence=0.85,
    )
    problem_intent = IntentResult(intent=IntentType.PROBLEM_SOLVING, confidence=0.8)
    result = evaluate(
        thread,
        "This TypeScript error is so frustrating, I've been stuck for "
        "hours trying to fix it!",
        user_state=frustrated_state,
        intent=problem_intent,
    )
    assert result.decision is not TemporalRelevanceDecision.SURFACE_NOW
    assert any("Frustration" in b for b in result.blocking_signals)
    assert any("problem-solving" in b.lower() for b in result.blocking_signals)


def test_resolution_in_current_turn_boosts_timing():
    thread = mk_job_thread()
    continued_only = evaluate(
        thread,
        "I finally left my job.",
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, updated=True, transitioned=False),
    )
    resolved_this_turn = evaluate(
        thread,
        "I finally left my job.",
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, updated=True, transitioned=True),
    )
    assert (
        resolved_this_turn.timing_score > continued_only.timing_score
    )
    assert resolved_this_turn.decision is TemporalRelevanceDecision.SURFACE_NOW
    assert any("resolved or redirected" in s for s in resolved_this_turn.signals)


# ── 15–16. Conservative outcomes ─────────────────────────────────────────


def test_low_confidence_yields_conservative_defer():
    thread = mk_thread(temporal_type=TemporalType.GOAL, subject="Learning guitar")
    question = mk_question(thread, question_type=PastSelfQuestionType.CHECK_IN,
                           confidence=0.30)
    result = TemporalRelevanceEngine().evaluate(
        USER,
        mk_input("Playing guitar is relaxing."),
        question,
        thread=thread,
        events=[
            TemporalEvent(id="tevent_past", description="Learning guitar plans."),
        ],
    )
    assert result.decision is TemporalRelevanceDecision.DEFER
    assert not result.should_surface
    assert result.confidence < 0.50


# ── 17. Determinism ──────────────────────────────────────────────────────


def test_repeated_execution_is_deterministic():
    thread = mk_job_thread()
    kwargs = dict(
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, transitioned=True),
        comparison=mk_comparison(thread),
    )
    first = evaluate(thread, "I finally left my job.", **kwargs)
    second = evaluate(thread, "I finally left my job.", **kwargs)
    assert first.model_dump() == second.model_dump()


# ── 18. Serialization ────────────────────────────────────────────────────


def test_result_serialization_round_trip():
    thread = mk_job_thread()
    result = evaluate(
        thread,
        "I finally left my job.",
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, transitioned=True),
    )
    payload = result.model_dump()
    assert payload["decision"] == "SURFACE_NOW"
    revived = TemporalRelevanceResult.model_validate_json(result.model_dump_json())
    assert revived.model_dump() == payload


# ── 19. Signals reflect score contributions ──────────────────────────────


def test_positive_scores_have_supporting_signal_lines():
    thread = mk_job_thread()
    result = evaluate(
        thread,
        "I finally left my job.",
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, transitioned=True),
    )
    joined = "\n".join(result.signals)
    assert "Topical continuity via thread subject" in joined
    assert "Current-turn continuation" in joined
    assert "resolved or redirected" in joined
    assert result.blocking_signals == []


def test_blocking_signals_reflect_negative_contributions():
    thread = mk_job_thread()
    urgent = UserStateResult(emotional_state=None, urgency=0.90)
    transactional_intent = IntentResult(intent=IntentType.INFORMATION, confidence=0.8)
    result = evaluate(
        thread,
        "I finally left my job. Quick question: what is a 401k exactly?",
        thread_match=mk_match(thread),
        lifecycle_result=mk_lifecycle(thread, transitioned=True),
        user_state=urgent,
        intent=transactional_intent,
    )
    assert any("urgency" in b.lower() for b in result.blocking_signals)
    assert any("transactional" in b.lower() for b in result.blocking_signals)


# ── 20–21. Read-only guarantee & zero persistence ────────────────────────


@pytest.mark.asyncio
async def test_evaluation_never_mutates_handed_in_models_or_store():
    thread = mk_job_thread()
    events = mk_events()
    question = mk_question(thread)
    comparison = mk_comparison(thread)
    lifecycle = mk_lifecycle(thread, transitioned=True)
    match = mk_match(thread)

    before = {
        "thread": thread.model_dump(),
        "events": [e.model_dump() for e in events],
        "question": question.model_dump(),
        "comparison": comparison.model_dump(),
        "lifecycle": lifecycle.model_dump(),
        "match": match.model_dump(),
    }

    store = InMemoryTemporalStore()
    await store.save_thread(thread.model_copy(deep=True))
    for event in events:
        await store.save_event(event.model_copy(deep=True))
    threads_before = await store.get_threads_by_user(USER)
    events_before = await store.get_events_by_thread(thread.id, USER)

    TemporalRelevanceEngine().evaluate(
        USER,
        mk_input("I finally left my job."),
        question,
        thread=thread,
        events=events,
        thread_match=match,
        lifecycle_result=lifecycle,
        comparison=comparison,
    )

    after = {
        "thread": thread.model_dump(),
        "events": [e.model_dump() for e in events],
        "question": question.model_dump(),
        "comparison": comparison.model_dump(),
        "lifecycle": lifecycle.model_dump(),
        "match": match.model_dump(),
    }
    assert after == before

    # Nothing was written through any store either.
    assert len(await store.get_threads_by_user(USER)) == len(threads_before)
    assert len(await store.get_events_by_thread(thread.id, USER)) == len(events_before)
    stored_thread = await store.get_thread(thread.id, USER)
    assert stored_thread.model_dump() == before["thread"]


def test_relevance_engine_takes_no_store_and_has_no_write_surface():
    engine = TemporalRelevanceEngine()
    assert not hasattr(engine, "store")
    assert not hasattr(engine, "save")


# ── State builder integration ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_state_builder_passes_relevance_result_through():
    user_input = UserInput(id="in_3g_sb", user_id="u", content="x")
    relevance = TemporalRelevanceResult(
        attempted=True,
        decision=TemporalRelevanceDecision.DEFER,
        should_surface=False,
        reason="not now",
    )
    state = await StateBuilder().build(
        user_input, RetrievedContext(), temporal_relevance=relevance
    )
    assert state.temporal_relevance is relevance


@pytest.mark.asyncio
async def test_chronos_state_defaults_to_no_relevance_result():
    user_input = UserInput(id="in_3g_sb2", user_id="u", content="hello")
    state = await StateBuilder().build(user_input, RetrievedContext())
    assert state.temporal_relevance is None


# ── Engine integration (end-to-end) ──────────────────────────────────────


class RecordingAIExecutor(BaseAIExecutor):
    """Records whether AI execution was ever attempted."""

    def __init__(self):
        self.calls = 0

    async def execute(self, *args, **kwargs):
        self.calls += 1
        return AIExecutionResult(
            attempted=True, used=False, success=False, fallback_used=True
        )


@pytest.mark.asyncio
async def test_engine_end_to_end_flags_continuation_as_surface_now():
    recorder = RecordingAIExecutor()
    engine = ChronosEngine(ai_executor=recorder)
    user_id = "user_3g_e2e"

    r1 = await engine.process_user_input(
        user_id=user_id,
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )
    rel1 = r1.chronos_state.temporal_relevance
    assert rel1 is not None
    # Turn 1 has a single grounded moment: 3F refuses to plan, and 3G
    # must never override that refusal.
    assert rel1.decision is TemporalRelevanceDecision.SKIP
    assert not rel1.should_surface
    assert "cannot override" in rel1.reason.lower()

    r2 = await engine.process_user_input(
        user_id=user_id,
        content="I finally left my job.",
        input_type="text",
        provider_key="chronos",
    )
    rel2 = r2.chronos_state.temporal_relevance
    assert rel2 is not None
    assert rel2.attempted
    assert rel2.decision is TemporalRelevanceDecision.SURFACE_NOW
    assert rel2.should_surface
    assert rel2.thread_id == r2.chronos_state.past_self_question.thread_id
    assert rel2.supporting_event_ids
    assert rel2.supporting_memory_ids

    trace = "\n".join(r2.reasoning_trace.reasoning_steps).lower()
    assert "past-self relevance -> surface_now" in trace
    assert "Past-Self Relevance Engine" in r2.reasoning_trace.context_sources

    # Read-only + no AI: the relevance layer itself never invoked anything.
    assert isinstance(engine.ai_executor, RecordingAIExecutor)
    assert recorder.calls == 0


@pytest.mark.asyncio
async def test_engine_trace_reports_skip_for_non_temporal_input():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_3g_quiet",
        content="What is Python?",
        input_type="text",
        provider_key="chronos",
    )
    relevance = response.chronos_state.temporal_relevance
    assert relevance is not None
    assert relevance.decision is TemporalRelevanceDecision.SKIP
    assert not relevance.should_surface
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "past-self relevance skipped: no valid past-self question" in trace


@pytest.mark.asyncio
async def test_engine_relevance_engine_injection_via_dependency_injection():
    calls = {"count": 0}

    class StubRelevanceEngine(BaseTemporalRelevanceEngine):
        def evaluate(self, *args, **kwargs):
            calls["count"] += 1
            return TemporalRelevanceResult(
                attempted=True,
                decision=TemporalRelevanceDecision.DEFER,
                should_surface=False,
                reason="stub relevance",
            )

    stub = StubRelevanceEngine()
    engine = ChronosEngine(temporal_relevance_engine=stub)
    response = await engine.process_user_input(
        user_id="user_3g_stub",
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )

    assert calls["count"] == 1
    assert response.chronos_state.temporal_relevance.decision \
        is TemporalRelevanceDecision.DEFER
