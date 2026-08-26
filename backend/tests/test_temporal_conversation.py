"""Phase 3H tests: past-self conversation composition & surfacing.

Covers the required behavior: hard surface gating (SURFACE_NOW permission,
Phase 3F authority, grounded thread, meaningful comparison, no ambiguity),
per-question-type deterministic wording, evidence-ID propagation without ID
leakage into user-facing text, determinism, read-only guarantees, at most
one surfaced moment per request, and consistent preservation of the moment
across FAST / LIGHT / DEEP / fallback response paths.

Deterministic and offline throughout — no real AI, no embeddings.
"""

import json

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.ai import (
    AIExecutor,
    InferencePolicy,
    ModelCapability,
    ReasoningMode,
    ReasoningPlan,
)
from chronos_engine.config import OllamaConfig
from chronos_engine.llm import LLMRegistry
from chronos_engine.llm.errors import LLMConnectionError
from chronos_engine.llm.result import LLMResult
from chronos_engine.routing import RoutingPath
from chronos_engine.routing.models import AIRoutingResult
from chronos_engine.state.builder import StateBuilder
from chronos_engine.state.models import (
    RetrievedContext,
    UserInput,
)
from chronos_engine.storage import InMemoryTemporalStore
from chronos_engine.temporal.conversation import (
    SECTION_HEADING,
    PastSelfConversationComposer,
    render_past_self_section,
)
from chronos_engine.temporal.models import (
    PastSelfConversationMoment,
    PastSelfPerspective,
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
    TemporalType,
)

USER = "user_3h"

DEEP_MODEL = "qwen3:4b"
LIGHT_MODEL = "qwen2.5:1.5b"


# ── Fixture helpers ──────────────────────────────────────────────────────


def mk_input(content: str) -> UserInput:
    return UserInput(id="in_3h", user_id=USER, content=content)


def mk_job_thread(**kwargs) -> TemporalThread:
    kwargs.setdefault("user_id", USER)
    kwargs.setdefault("temporal_type", TemporalType.DECISION)
    kwargs.setdefault("subject", "Quit my job")
    kwargs.setdefault(
        "description", "I don't know if I should quit my job."
    )
    return TemporalThread(**kwargs)


def mk_events() -> list:
    return [
        TemporalEvent(
            id="tevent_past",
            user_id=USER,
            temporal_type=TemporalType.DECISION,
            description="I don't know if I should quit my job.",
            memory_id="mem_past",
        ),
        TemporalEvent(
            id="tevent_present",
            user_id=USER,
            temporal_type=TemporalType.LIFE_EVENT,
            description="I finally left my job.",
            memory_id="mem_present",
        ),
    ]


def mk_question(
    thread: TemporalThread,
    question_type: PastSelfQuestionType = PastSelfQuestionType.OUTCOME_REVEAL,
    confidence: float = 0.85,
    **kwargs,
) -> PastSelfQuestionResult:
    return PastSelfQuestionResult(
        attempted=True,
        should_ask=True,
        question_type=question_type,
        reason="planned by Phase 3F",
        confidence=confidence,
        thread_id=thread.id,
        comparison_relation=TemporalComparisonRelation.RESOLVED,
        past_event_id="tevent_past",
        present_event_id="tevent_present",
        supporting_memory_ids=["mem_past"],
        supporting_event_ids=["tevent_past", "tevent_present"],
        intent=PastSelfQuestionIntent(
            focus="How the user feels now about the decision",
            canonical_template="Back then, {subject}. How do you feel now?",
            perspective=PastSelfPerspective.PAST_TO_PRESENT,
        ),
        signals=[],
        **kwargs,
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
        past_summary='Back then you were weighing: '
        '"I don\'t know if I should quit my job."',
        present_summary='Now it has played out: "I finally left my job."',
        evidence_memory_ids=["mem_past", "mem_present"],
        evidence_event_ids=["tevent_past", "tevent_present"],
        signals=[],
        reason="test comparison",
    )


def mk_relevance(
    decision: TemporalRelevanceDecision = TemporalRelevanceDecision.SURFACE_NOW,
    confidence: float = 0.75,
) -> TemporalRelevanceResult:
    return TemporalRelevanceResult(
        attempted=True,
        decision=decision,
        should_surface=decision is TemporalRelevanceDecision.SURFACE_NOW,
        reason="test relevance",
        confidence=confidence,
        thread_id="thread_x",
        supporting_memory_ids=["mem_past"],
        supporting_event_ids=["tevent_past"],
    )


def compose(thread=None, question=None, **kwargs):
    """Convenience wrapper mirroring the composer call shape."""
    thread = thread if thread is not None else mk_job_thread()
    return PastSelfConversationComposer().compose(
        user_id=USER,
        past_self_question=(
            question if question is not None else mk_question(thread)
        ),
        relevance_result=kwargs.pop(
            "relevance_result", mk_relevance()
        ),
        thread=thread,
        comparison=kwargs.pop("comparison", mk_comparison(thread)),
        events=kwargs.pop("events", mk_events()),
        **kwargs,
    )


# ── 1–3. Valid moments per question type ─────────────────────────────────


def test_surface_now_outcome_reveal_composes_grounded_moment():
    thread = mk_job_thread()
    moment = compose(thread)
    assert moment.should_surface
    assert moment.attempted
    assert moment.question_type is PastSelfQuestionType.OUTCOME_REVEAL
    assert moment.relation is TemporalComparisonRelation.RESOLVED
    # Grounded reminder reuses the comparison's evidence quoting.
    assert 'weighing' in moment.context
    assert "quit my job" in moment.context.lower()
    # Bridge quotes the present evidence.
    assert "left my job" in moment.bridge.lower()
    # Question quotes the stored subject.
    assert '"Quit my job"' in moment.question
    assert moment.perspective is PastSelfPerspective.PAST_TO_PRESENT


def test_surface_now_reflection_uses_grounded_wording():
    thread = mk_job_thread()
    question = mk_question(
        thread,
        question_type=PastSelfQuestionType.REFLECTION,
        confidence=0.70,
    )
    moment = compose(thread, question=question)
    assert moment.should_surface
    assert moment.question_type is PastSelfQuestionType.REFLECTION
    assert '"Quit my job"' in moment.question
    assert moment.opening and moment.context


@pytest.mark.parametrize(
    "qtype", [PastSelfQuestionType.CHECK_IN, PastSelfQuestionType.REASSURANCE]
)
def test_surface_now_check_in_and_reassurance_compose(qtype):
    thread = mk_job_thread()
    question = mk_question(thread, question_type=qtype)
    moment = compose(thread, question=question)
    assert moment.should_surface
    assert moment.question_type is qtype
    assert moment.opening and moment.context and moment.question


# ── 4–10. Hard gates: honest empty results ───────────────────────────────


def test_deferred_relevance_does_not_surface():
    moment = compose(relevance_result=mk_relevance(TemporalRelevanceDecision.DEFER))
    assert not moment.should_surface
    assert moment.reason
    assert "DEFER" in moment.reason


def test_skipped_relevance_does_not_surface():
    moment = compose(relevance_result=mk_relevance(TemporalRelevanceDecision.SKIP))
    assert not moment.should_surface
    assert "SKIP" in moment.reason


def test_phase_3f_refusal_is_never_overridden():
    thread = mk_job_thread()
    refused = mk_question(thread).model_copy(update={"should_ask": False})
    moment = compose(thread, question=refused)
    assert not moment.should_surface
    assert moment.opening == "" and moment.question == ""
    assert "askable" in moment.reason.lower()


def test_insufficient_evidence_comparison_does_not_surface():
    thread = mk_job_thread()
    comparison = mk_comparison(thread).model_copy(
        update={
            "comparable": False,
            "relation": TemporalComparisonRelation.INSUFFICIENT_EVIDENCE,
        }
    )
    moment = compose(thread, comparison=comparison)
    assert not moment.should_surface


def test_ambiguous_lifecycle_does_not_surface():
    thread = mk_job_thread()
    lifecycle = TemporalLifecycleResult(
        attempted=True, updated=True, thread_id=thread.id, ambiguous=True
    )
    moment = compose(thread, lifecycle_result=lifecycle)
    assert not moment.should_surface
    assert "ambiguous" in moment.reason.lower()


def test_missing_thread_does_not_surface():
    question = mk_question(mk_job_thread())
    moment = PastSelfConversationComposer().compose(
        user_id=USER,
        past_self_question=question,
        relevance_result=mk_relevance(),
        thread=None,
    )
    assert not moment.should_surface


def test_missing_or_invalid_question_never_fabricates():
    composer = PastSelfConversationComposer()
    none_moment = composer.compose(
        user_id=USER,
        past_self_question=None,
        relevance_result=mk_relevance(),
    )
    assert not none_moment.should_surface

    thread = mk_job_thread()
    broken = mk_question(thread).model_copy(update={"intent": None})
    invalid_moment = compose(thread, question=broken)
    assert not invalid_moment.should_surface


def test_ungrounded_subject_cannot_be_composed():
    thread = mk_job_thread(subject="", description="", origin_memory_id="mem_o")
    bare_past = TemporalEvent(id="tevent_past", description="", memory_id="mem_o")
    question = mk_question(thread)
    moment = PastSelfConversationComposer().compose(
        user_id=USER,
        past_self_question=question,
        relevance_result=mk_relevance(),
        thread=thread,
        comparison=mk_comparison(thread),
        events=[bare_past],
    )
    assert not moment.should_surface
    assert "grounded subject" in moment.reason.lower()


# ── 11–12. Evidence IDs propagate; never leak into user-facing text ──────


def test_evidence_ids_propagate_and_dedupe():
    thread = mk_job_thread()
    question = mk_question(thread)
    question = question.model_copy(update={"supporting_memory_ids": ["mem_a", "mem_b"]})
    comparison = mk_comparison(thread).model_copy(
        update={"evidence_memory_ids": ["mem_b", "mem_c"]}
    )
    moment = compose(thread, question=question, comparison=comparison)
    assert moment.evidence_memory_ids == ["mem_a", "mem_b", "mem_c"]
    assert moment.evidence_event_ids[:2] == ["tevent_past", "tevent_present"]


def test_no_raw_ids_appear_in_user_facing_text():
    thread = mk_job_thread(id="thread_secret", user_id=USER)
    moment = compose(thread)
    section = render_past_self_section(moment)
    user_facing = "\n".join(
        [moment.opening, moment.context, moment.bridge, moment.question, section]
    )
    for leak in ("thread_secret", "mem_", "tevent_", "user_3h"):
        assert leak not in user_facing


# ── 13. Determinism ──────────────────────────────────────────────────────


def test_repeated_composition_is_identical():
    thread = mk_job_thread()
    first = compose(thread)
    second = compose(thread)
    assert first.model_dump() == second.model_dump()
    section_one = render_past_self_section(first)
    section_two = render_past_self_section(second)
    assert section_one == section_two


# ── 14. Read-only guarantees ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_composer_never_mutates_models_or_store():
    thread = mk_job_thread()
    events = mk_events()
    question = mk_question(thread)
    comparison = mk_comparison(thread)
    lifecycle = TemporalLifecycleResult(attempted=True, updated=True,
                                        thread_id=thread.id)
    before = {
        "thread": thread.model_dump(),
        "events": [e.model_dump() for e in events],
        "question": question.model_dump(),
        "comparison": comparison.model_dump(),
    }

    store = InMemoryTemporalStore()
    await store.save_thread(thread.model_copy(deep=True))
    threads_before = await store.get_threads_by_user(USER)

    compose(
        thread,
        question=question,
        comparison=comparison,
        lifecycle_result=lifecycle,
        events=events,
    )

    after = {
        "thread": thread.model_dump(),
        "events": [e.model_dump() for e in events],
        "question": question.model_dump(),
        "comparison": comparison.model_dump(),
    }
    assert after == before
    assert len(await store.get_threads_by_user(USER)) == len(threads_before)


def test_composer_takes_no_store_and_has_no_write_surface():
    composer = PastSelfConversationComposer()
    assert not hasattr(composer, "store")
    assert not hasattr(composer, "save")


# ── Section rendering ────────────────────────────────────────────────────


def test_rendered_section_shape_and_bridge_omission():
    thread = mk_job_thread()
    moment = compose(thread)
    section = render_past_self_section(moment)
    lines = [ln for ln in section.split("\n")]
    assert lines[0] == SECTION_HEADING
    assert moment.opening in section
    assert moment.context in section
    assert moment.bridge in section
    assert moment.question in section

    no_bridge = moment.model_copy(update={"bridge": ""})
    trimmed = render_past_self_section(no_bridge)
    assert moment.bridge not in trimmed
    assert trimmed.endswith(moment.question)


@pytest.mark.asyncio
async def test_state_builder_passes_conversation_through():
    moment = PastSelfConversationMoment(should_surface=False, reason="nope")
    state = await StateBuilder().build(
        UserInput(id="in_sb", user_id="u", content="x"),
        RetrievedContext(),
        past_self_conversation=moment,
    )
    assert state.past_self_conversation is moment


# ── Engine integration (FAST path) ───────────────────────────────────────


async def run_flagship(engine):
    r1 = await engine.process_user_input(
        user_id="user_3h_e2e",
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )
    r2 = await engine.process_user_input(
        user_id="user_3h_e2e",
        content="I finally left my job.",
        input_type="text",
        provider_key="chronos",
    )
    return r1, r2


@pytest.mark.asyncio
async def test_fast_path_surfaces_moment_without_ai():
    engine = ChronosEngine()
    r1, r2 = await run_flagship(engine)

    # Turn 1: nothing may be surfaced yet.
    assert r1.chronos_state.past_self_conversation is not None
    assert not r1.chronos_state.past_self_conversation.should_surface
    assert SECTION_HEADING not in r1.final_response

    # Turn 2: exactly one surfaced moment, appended after the answer.
    moment = r2.chronos_state.past_self_conversation
    assert moment.should_surface
    assert moment.thread_id == r2.chronos_state.past_self_question.thread_id
    assert r2.final_response.count(SECTION_HEADING) == 1
    assert r2.final_response.endswith(moment.question)

    # FAST path: the temporal layer caused NO AI execution.
    assert r2.ai_execution.attempted is False

    trace = "\n".join(r2.reasoning_trace.reasoning_steps).lower()
    assert "past-self conversation -> surfaced: outcome_reveal" in trace
    assert "Past-Self Conversation Composer" in r2.reasoning_trace.context_sources


@pytest.mark.asyncio
async def test_quiet_input_produces_no_temporal_block_and_honest_trace():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_3h_quiet",
        content="What is Python?",
        input_type="text",
        provider_key="chronos",
    )
    moment = response.chronos_state.past_self_conversation
    assert moment is not None
    assert not moment.should_surface
    assert SECTION_HEADING not in response.final_response
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "past-self conversation skipped:" in trace


# ── LIGHT / DEEP / fallback preservation ─────────────────────────────────


LIGHT_CAPABILITY = ModelCapability(
    provider="ollama",
    model=LIGHT_MODEL,
    parameter_count=1.5,
    quantization="Q4_K_M",
    estimated_memory_gb=1.1,
    disk_size_gb=1.1,
    context_length=32768,
    supports_json=True,
    supports_thinking=False,
    tier="LIGHT",
)


class FakeOllama:
    """Fake provider recording model calls; returns canned result/error."""

    def __init__(self, text: str = "", error: Exception | None = None):
        self.text = text
        self.error = error
        self.models_called: list = []

    def provider_name(self) -> str:
        return "Ollama Local"

    async def generate(self, prompt_context, model_name="", inference_options=None):
        self.models_called.append(model_name)
        if self.error is not None:
            raise self.error
        return LLMResult(
            text=json.dumps(
                {
                    "interpretation": None,
                    "reasoning": None,
                    "reflection": None,
                    "answer": self.text,
                    "uncertainties": [],
                    "evidence_used": [],
                }
            ),
            provider="ollama",
            model=model_name or DEEP_MODEL,
            latency_ms=5.0,
            success=True,
        )

    async def generate_response(self, prompt_context, model_name=""):
        return self.text


class DeepRouter:
    """Stub router forcing the DEEP AI path."""

    def route(self, state):
        return AIRoutingResult(
            use_ai=True,
            path=RoutingPath.DEEP,
            confidence=0.8,
            reason="stub deep routing",
            signals=[],
        )


class StubPlanner:
    """Stub reasoning planner pinning the inference tier under test."""

    def __init__(self, primary: ReasoningMode):
        self.plan_result = ReasoningPlan(
            modes=[primary, ReasoningMode.GENERATE],
            primary_mode=primary,
            reason="stub plan",
            confidence=0.6,
        )

    def plan(self, chronos_state, routing_result):
        return self.plan_result


def make_ai_engine(provider: FakeOllama, primary: ReasoningMode) -> ChronosEngine:
    config = OllamaConfig(
        base_url="http://ollama:11434",
        model=DEEP_MODEL,
        light_model=LIGHT_MODEL,
        timeout=2.0,
        enabled=True,
    )
    registry = LLMRegistry()
    registry.register_provider("ollama", provider)
    executor = AIExecutor(llm_registry=registry, config=config)
    return ChronosEngine(
        ai_executor=executor,
        llm_registry=registry,
        ai_router=DeepRouter(),
        reasoning_planner=StubPlanner(primary),
        inference_policy=InferencePolicy(
            config=config, available_models=[LIGHT_CAPABILITY]
        ),
    )


@pytest.mark.asyncio
async def test_light_ai_path_preserves_the_surfaced_moment():
    engine = make_ai_engine(FakeOllama(text="AI_LIGHT_ANSWER"), ReasoningMode.INTERPRET)
    _, r2 = await run_flagship(engine)
    assert r2.inference_policy.tier.value == "LIGHT"
    assert r2.ai_execution.used is True
    assert "AI_LIGHT_ANSWER" in r2.final_response
    assert r2.final_response.count(SECTION_HEADING) == 1


@pytest.mark.asyncio
async def test_deep_ai_path_preserves_the_surfaced_moment():
    engine = make_ai_engine(FakeOllama(text="AI_DEEP_ANSWER"), ReasoningMode.REASON)
    _, r2 = await run_flagship(engine)
    assert r2.inference_policy.tier.value == "DEEP"
    assert r2.ai_execution.used is True
    assert "AI_DEEP_ANSWER" in r2.final_response
    assert r2.final_response.count(SECTION_HEADING) == 1


@pytest.mark.asyncio
async def test_ai_failure_deterministic_fallback_preserves_the_moment():
    engine = make_ai_engine(
        FakeOllama(error=LLMConnectionError("ollama down")), ReasoningMode.REASON
    )
    _, r2 = await run_flagship(engine)
    assert r2.ai_execution.used is False
    assert r2.final_response.count(SECTION_HEADING) == 1
    moment = r2.chronos_state.past_self_conversation
    assert moment.should_surface
    assert moment.question in r2.final_response


# ── Serialization compatibility ──────────────────────────────────────────


def test_moment_serializes_cleanly_through_state():
    thread = mk_job_thread()
    moment = compose(thread)
    dumped = moment.model_dump_json()
    revived = PastSelfConversationMoment.model_validate_json(dumped)
    assert revived.model_dump() == moment.model_dump()
