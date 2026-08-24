"""Phase 3I tests: bounded AI temporal reflection over a valid moment.

Covers: strict eligibility gating (no surfaced moment / DEFER / SKIP /
Phase 3F refusal / ambiguous lifecycle / insufficient comparison -> the
provider is never touched), additive InferencePolicy tier selection
(LIGHT preferred, DEEP only for deterministically complex relations),
model separation, the strict output contract (malformed JSON, missing
reflection, hallucinated evidence ids, leaked identifiers -> safe
fallback), the single-call/no-retry guarantee, and end-to-end
preservation of the deterministic past-self moment on every path
(FAST, LIGHT, DEEP, AI disabled, provider failure).

Deterministic and offline throughout — no real Ollama is contacted.
"""

import json

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.ai import (
    AIExecutor,
    InferencePolicy,
    ReasoningMode,
    ReasoningPlan,
)
from chronos_engine.ai.policy.models import (
    InferenceTier,
    LatencyClass,
    ModelCapability,
)
from chronos_engine.config.ollama import OllamaConfig
from chronos_engine.llm import LLMRegistry
from chronos_engine.llm.errors import (
    LLMConnectionError,
    LLMTimeoutError,
)
from chronos_engine.llm.result import LLMResult
from chronos_engine.routing.models import AIRoutingResult
from chronos_engine.routing.service import RoutingPath
from chronos_engine.state.models import RetrievedContext, UserInput
from chronos_engine.temporal.conversation import SECTION_HEADING as MOMENT_HEADING
from chronos_engine.temporal.models import (
    PastSelfConversationMoment,
    PastSelfPerspective,
    PastSelfQuestionIntent,
    PastSelfQuestionResult,
    PastSelfQuestionType,
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalLifecycleResult,
    TemporalRelevanceDecision,
    TemporalRelevanceResult,
)
from chronos_engine.temporal.reflection import (
    SECTION_HEADING as REFLECTION_HEADING,
)
from chronos_engine.temporal.reflection import (
    TemporalReflectionGenerator,
    render_temporal_reflection_section,
)

USER = "user_3i"

DEEP_MODEL = "qwen3:4b"
LIGHT_MODEL = "qwen2.5:1.5b"

REFLECTION_MARKER = "AUTHORITATIVE TEMPORAL FACTS"

GOOD_REFLECTION = (
    "The uncertainty you carried earlier and the decision you eventually "
    "made now sit side by side."
)


# ── Fixture helpers ──────────────────────────────────────────────────────


def make_config(**overrides) -> OllamaConfig:
    params = dict(
        base_url="http://ollama:11434",
        model=DEEP_MODEL,
        light_model=LIGHT_MODEL,
        timeout=2.0,
        enabled=True,
    )
    params.update(overrides)
    return OllamaConfig(**params)


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


def mk_moment(**overrides) -> PastSelfConversationMoment:
    fields = dict(
        attempted=True,
        should_surface=True,
        thread_id="thread_x",
        perspective=PastSelfPerspective.PAST_TO_PRESENT,
        question_type=PastSelfQuestionType.OUTCOME_REVEAL,
        relation=TemporalComparisonRelation.RESOLVED,
        opening="Earlier, you were weighing this.",
        context='Back then you were weighing: "I don\'t know if I should quit my job."',
        bridge='Now it has played out: "I finally left my job."',
        question='"Quit my job" — how do you feel about it now?',
        confidence=0.75,
        evidence_memory_ids=["mem_past"],
        evidence_event_ids=["tevent_past", "tevent_present"],
        reason="all gates passed",
    )
    fields.update(overrides)
    return PastSelfConversationMoment(**fields)


def mk_question() -> PastSelfQuestionResult:
    return PastSelfQuestionResult(
        attempted=True,
        should_ask=True,
        question_type=PastSelfQuestionType.OUTCOME_REVEAL,
        reason="planned",
        confidence=0.85,
        thread_id="thread_x",
        comparison_relation=TemporalComparisonRelation.RESOLVED,
        supporting_memory_ids=["mem_past"],
        supporting_event_ids=["tevent_past"],
        intent=PastSelfQuestionIntent(
            focus="feelings now",
            canonical_template="How do you feel now?",
            perspective=PastSelfPerspective.PAST_TO_PRESENT,
        ),
    )


def mk_relevance(
    decision: TemporalRelevanceDecision = TemporalRelevanceDecision.SURFACE_NOW,
) -> TemporalRelevanceResult:
    return TemporalRelevanceResult(
        attempted=True,
        decision=decision,
        should_surface=decision is TemporalRelevanceDecision.SURFACE_NOW,
        reason="test",
        confidence=0.8,
    )


def mk_comparison(
    relation: TemporalComparisonRelation = TemporalComparisonRelation.RESOLVED,
    comparable: bool = True,
) -> TemporalComparisonResult:
    return TemporalComparisonResult(
        attempted=True,
        comparable=comparable,
        relation=relation,
        confidence=0.8,
        thread_id="thread_x",
        past_summary="back then summary",
        present_summary="now summary",
        evidence_memory_ids=["mem_past"],
        evidence_event_ids=["tevent_past", "tevent_present"],
    )


class ScriptedProvider:
    """Fake Ollama provider: serves the reflection contract on temporal
    prompts and the main-answer contract otherwise; records every model
    call and every temporal-reflection call separately."""

    def __init__(
        self,
        reflection_text=None,
        error=None,
        raw_reflection=None,
        cite_event=None,
    ):
        self.reflection_text = reflection_text
        self.raw_reflection = raw_reflection
        self.error = error
        self.cite_event = cite_event
        self.models_called: list = []
        self.reflection_calls = 0

    def provider_name(self) -> str:
        return "Ollama Local"

    @staticmethod
    def _main_payload() -> str:
        return json.dumps(
            {
                "interpretation": None,
                "reasoning": None,
                "reflection": None,
                "answer": "MAIN_ANSWER",
                "uncertainties": [],
                "evidence_used": [],
            }
        )

    def _reflection_payload(self) -> str:
        if self.raw_reflection is not None:
            return self.raw_reflection
        return json.dumps(
            {
                "reflection": self.reflection_text or GOOD_REFLECTION,
                "evidence_used": (
                    [f"[timeline:{self.cite_event}]"] if self.cite_event else []
                ),
                "uncertainties": [],
            }
        )

    async def generate(self, prompt_context, model_name="", inference_options=None):
        self.models_called.append(model_name)
        if self.error is not None:
            raise self.error
        if REFLECTION_MARKER in prompt_context.full_prompt():
            self.reflection_calls += 1
            return LLMResult(
                text=self._reflection_payload(),
                provider="ollama",
                model=model_name or DEEP_MODEL,
                latency_ms=5.0,
                success=True,
            )
        return LLMResult(
            text=self._main_payload(),
            provider="ollama",
            model=model_name or DEEP_MODEL,
            latency_ms=5.0,
            success=True,
        )

    async def generate_response(self, prompt_context, model_name=""):
        return "MAIN_ANSWER"


def make_generator(provider=None, **config_overrides) -> TemporalReflectionGenerator:
    config = make_config(**config_overrides)
    registry = LLMRegistry()
    registry.register_provider("ollama", provider or ScriptedProvider())
    return TemporalReflectionGenerator(
        llm_registry=registry,
        config=config,
        inference_policy=InferencePolicy(
            config=config, available_models=[LIGHT_CAPABILITY]
        ),
    )


async def generate_with(
    provider=None, moment=None, comparison=None, lifecycle=None, **kwargs
) -> tuple[TemporalReflectionGenerator, object]:
    generator = make_generator(provider, **kwargs.pop("config_overrides", {}))
    result = await generator.generate(
        user_id=USER,
        moment=moment if moment is not None else mk_moment(),
        past_self_question=mk_question(),
        relevance_result=kwargs.pop(
            "relevance", mk_relevance()
        ),
        comparison=(
            comparison
            if comparison is not None
            else mk_comparison()
        ),
        lifecycle_result=lifecycle,
    )
    return generator, result


async def run_flagship(engine):
    await engine.process_user_input(
        user_id="user_3i_e2e",
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )
    return await engine.process_user_input(
        user_id="user_3i_e2e",
        content="I finally left my job.",
        input_type="text",
        provider_key="chronos",
    )


# ── Unit: successful reflection ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_moment_produces_validated_reflection():
    provider = ScriptedProvider(reflection_text=GOOD_REFLECTION, cite_event="tevent_past")
    _, result = await generate_with(provider=provider)

    assert result.attempted and result.used and result.success
    assert not result.fallback_used
    assert result.tier == InferenceTier.LIGHT.value
    assert result.model == LIGHT_MODEL
    assert result.reflection == GOOD_REFLECTION
    assert result.evidence_used == ["tevent_past"]
    assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_light_selected_for_simple_relations_and_separation_holds():
    provider = ScriptedProvider()
    _, result = await generate_with(provider=provider)
    # LIGHT tier ran the configured LIGHT model, never the DEEP model.
    assert result.tier == InferenceTier.LIGHT.value
    assert result.model == LIGHT_MODEL
    assert provider.models_called == [LIGHT_MODEL]


@pytest.mark.parametrize(
    "relation",
    [
        TemporalComparisonRelation.CHANGED,
        TemporalComparisonRelation.EVOLVED,
        TemporalComparisonRelation.CONTRADICTED,
    ],
)
def test_deep_only_for_deterministically_complex_relations(relation):
    config = make_config()
    policy = InferencePolicy(config=config, available_models=[LIGHT_CAPABILITY])
    decision = policy.decide_temporal_reflection(comparison=mk_comparison(relation))
    assert decision.tier is InferenceTier.DEEP
    assert decision.model == DEEP_MODEL


def test_light_preferred_when_available():
    config = make_config()
    policy = InferencePolicy(config=config, available_models=[LIGHT_CAPABILITY])
    decision = policy.decide_temporal_reflection(
        comparison=mk_comparison(TemporalComparisonRelation.RESOLVED)
    )
    assert decision.tier is InferenceTier.LIGHT
    assert decision.model == LIGHT_MODEL
    assert decision.expected_latency_class is LatencyClass.LOW


def test_no_light_model_falls_back_to_deep_flagged_not_escalated():
    config = make_config()
    policy = InferencePolicy(
        config=config,
        available_models=[
            ModelCapability(provider="ollama", model=DEEP_MODEL, tier="DEEP")
        ],
    )
    decision = policy.decide_temporal_reflection(
        comparison=mk_comparison(TemporalComparisonRelation.RESOLVED)
    )
    assert decision.tier is InferenceTier.DEEP
    assert decision.light_requested is True


def test_disabled_config_selects_none():
    config = make_config(enabled=False)
    policy = InferencePolicy(config=config, available_models=[LIGHT_CAPABILITY])
    decision = policy.decide_temporal_reflection(comparison=mk_comparison())
    assert decision.tier is InferenceTier.NONE


# ── Unit: eligibility gating (the provider is never touched) ─────────────


@pytest.mark.asyncio
async def test_no_surfaced_moment_skips_without_provider_call():
    provider = ScriptedProvider()
    generator, result = await generate_with(
        provider=provider, moment=mk_moment(should_surface=False)
    )
    assert not result.attempted
    assert "no surfaced temporal moment" in result.reason
    assert provider.models_called == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "decision_label",
    [TemporalRelevanceDecision.DEFER, TemporalRelevanceDecision.SKIP],
)
async def test_defer_or_skip_relevance_never_invokes_ai(decision_label):
    provider = ScriptedProvider()
    _, result = await generate_with(
        provider=provider, relevance=mk_relevance(decision_label)
    )
    assert not result.attempted
    assert provider.models_called == []


@pytest.mark.asyncio
async def test_phase_3f_refusal_never_invokes_ai():
    provider = ScriptedProvider()
    refused = mk_question().model_copy(update={"should_ask": False})
    generator = make_generator(provider)
    result = await generator.generate(
        user_id=USER,
        moment=mk_moment(),
        past_self_question=refused,
        relevance_result=mk_relevance(),
        comparison=mk_comparison(),
    )
    assert not result.attempted
    assert provider.models_called == []


@pytest.mark.asyncio
async def test_ambiguous_lifecycle_never_invokes_ai():
    provider = ScriptedProvider()
    ambiguous = TemporalLifecycleResult(
        attempted=True, updated=True, thread_id="thread_x", ambiguous=True
    )
    _, result = await generate_with(provider=provider, lifecycle=ambiguous)
    assert not result.attempted
    assert provider.models_called == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "comparison",
    [
        mk_comparison(comparable=False),
        mk_comparison(relation=TemporalComparisonRelation.INSUFFICIENT_EVIDENCE),
    ],
)
async def test_insufficient_or_missing_comparison_never_invokes_ai(comparison):
    provider = ScriptedProvider()
    _, result = await generate_with(provider=provider, comparison=comparison)
    assert not result.attempted
    assert provider.models_called == []


@pytest.mark.asyncio
async def test_missing_comparison_never_invokes_ai():
    provider = ScriptedProvider()
    generator = make_generator(provider)
    result = await generator.generate(
        user_id=USER,
        moment=mk_moment(),
        past_self_question=mk_question(),
        relevance_result=mk_relevance(),
        comparison=None,
    )
    assert not result.attempted
    assert provider.models_called == []


@pytest.mark.asyncio
async def test_missing_evidence_identifiers_skip():
    provider = ScriptedProvider()
    bare = mk_moment(evidence_memory_ids=[], evidence_event_ids=[])
    _, result = await generate_with(provider=provider, moment=bare)
    assert not result.attempted
    assert provider.models_called == []


# ── Unit: failures fall back safely, once ────────────────────────────────


@pytest.mark.asyncio
async def test_connection_failure_preserves_deterministic_moment():
    provider = ScriptedProvider(error=LLMConnectionError("down"))
    _, result = await generate_with(provider=provider)
    assert result.attempted and not result.used
    assert result.fallback_used
    assert result.error_type == "LLMConnectionError"
    assert provider.reflection_calls == 0


@pytest.mark.asyncio
async def test_timeout_failure_falls_back_without_retry():
    provider = ScriptedProvider(error=LLMTimeoutError("too slow"))
    generator = make_generator(provider)
    result = await generator.generate(
        user_id=USER,
        moment=mk_moment(),
        past_self_question=mk_question(),
        relevance_result=mk_relevance(),
        comparison=mk_comparison(),
    )
    retry = await generator.generate(
        user_id=USER,
        moment=mk_moment(),
        past_self_question=mk_question(),
        relevance_result=mk_relevance(),
        comparison=mk_comparison(),
    )
    assert result.fallback_used and retry.fallback_used
    assert result.error_type == "LLMTimeoutError"
    # No retry: each attempt made exactly one doomed provider call.
    assert provider.reflection_calls == 0
    assert len(provider.models_called) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw,expected_error",
    [
        ("this is not json at all", "MALFORMED_JSON"),
        (json.dumps({"reflection": ""}), "MISSING_REFLECTION"),
        (json.dumps({"reflection": "   "}), "MISSING_REFLECTION"),
        (json.dumps({"reflection": "x" * 1300}), "VALIDATION_FAILED"),
        (
            json.dumps(
                {
                    "reflection": GOOD_REFLECTION,
                    "evidence_used": ["[memory:mem_invented]"],
                }
            ),
            "HALLUCINATED_EVIDENCE",
        ),
        (
            json.dumps({"reflection": "See tevent_past for what happened."}),
            "LEAKED_IDENTIFIER",
        ),
        (
            json.dumps(
                {"reflection": f"Quoting mem_past directly: {GOOD_REFLECTION}"}
            ),
            "LEAKED_IDENTIFIER",
        ),
        ('{"reflection": 42}', "MALFORMED_JSON"),
    ],
)
async def test_invalid_output_contract_fails_safely(raw, expected_error):
    provider = ScriptedProvider(raw_reflection=raw)
    _, result = await generate_with(provider=provider)
    assert result.attempted and not result.used
    assert result.fallback_used
    assert result.error_type == expected_error
    assert result.reflection == ""


@pytest.mark.asyncio
async def test_disabled_provider_records_honest_skip():
    provider = ScriptedProvider()
    generator = make_generator(provider, enabled=False)
    result = await generator.generate(
        user_id=USER,
        moment=mk_moment(),
        past_self_question=mk_question(),
        relevance_result=mk_relevance(),
        comparison=mk_comparison(),
    )
    assert not result.attempted
    assert "disabled" in result.reason.lower()
    assert provider.models_called == []


@pytest.mark.asyncio
async def test_repeated_fallback_behavior_is_stable():
    provider = ScriptedProvider(raw_reflection="not json")
    first = await make_generator(provider).generate(
        user_id=USER,
        moment=mk_moment(),
        past_self_question=mk_question(),
        relevance_result=mk_relevance(),
        comparison=mk_comparison(),
    )
    second = await make_generator(ScriptedProvider(raw_reflection="not json")).generate(
        user_id=USER,
        moment=mk_moment(),
        past_self_question=mk_question(),
        relevance_result=mk_relevance(),
        comparison=mk_comparison(),
    )
    assert first.error_type == second.error_type == "MALFORMED_JSON"
    assert first.reflection == second.reflection == ""


def test_render_section_none_when_unused_and_shape_when_used():
    from chronos_engine.temporal.models import TemporalReflectionResult

    assert render_temporal_reflection_section(None) is None

    failed = TemporalReflectionResult(attempted=True, fallback_used=True)
    assert render_temporal_reflection_section(failed) is None

    ok = TemporalReflectionResult(
        attempted=True, used=True, success=True, reflection=GOOD_REFLECTION
    )
    section = render_temporal_reflection_section(ok)
    assert section.startswith(REFLECTION_HEADING)
    assert GOOD_REFLECTION in section


# ── Engine integration ───────────────────────────────────────────────────


def make_engine(provider: ScriptedProvider) -> ChronosEngine:
    config = make_config()
    registry = LLMRegistry()
    registry.register_provider("ollama", provider)
    return ChronosEngine(
        ai_executor=AIExecutor(llm_registry=registry, config=config),
        llm_registry=registry,
    )


@pytest.mark.asyncio
async def test_end_to_end_success_appends_reflection_after_moment():
    provider = ScriptedProvider(reflection_text=GOOD_REFLECTION)
    engine = make_engine(provider)
    response = await run_flagship(engine)

    moment = response.chronos_state.past_self_conversation
    reflection = response.chronos_state.temporal_reflection
    assert moment.should_surface
    assert reflection.used and reflection.success
    assert reflection.tier == InferenceTier.LIGHT.value

    # Order and uniqueness: answer -> deterministic moment -> reflection.
    assert response.final_response.startswith("MAIN_ANSWER") or (
        MOMENT_HEADING in response.final_response
    )
    assert response.final_response.count(MOMENT_HEADING) == 1
    assert response.final_response.count(REFLECTION_HEADING) == 1
    assert response.final_response.index(MOMENT_HEADING) < response.final_response.index(
        REFLECTION_HEADING
    )
    # The deterministic past-self question remains visible, untouched.
    assert moment.question in response.final_response
    assert response.final_response.index(moment.question) < response.final_response.index(
        REFLECTION_HEADING
    )
    assert GOOD_REFLECTION in response.final_response

    # Exactly ONE bounded temporal provider call for this request.
    assert provider.reflection_calls == 1

    # Honest trace + context source.
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "temporal ai reflection -> light success" in trace
    assert "Temporal Reflection Generator" in response.reasoning_trace.context_sources

    # No raw evidence identifiers anywhere in user-facing text.
    for leak in ("mem_", "tevent_", "thread_"):
        assert leak not in response.final_response


@pytest.mark.asyncio
async def test_turn_without_moment_makes_no_temporal_call():
    provider = ScriptedProvider()
    engine = make_engine(provider)
    first = await engine.process_user_input(
        user_id="user_3i_e2e_b",
        content="I don't know if I should leave my job.",
        input_type="text",
        provider_key="chronos",
    )
    assert not first.chronos_state.past_self_conversation.should_surface
    assert not first.chronos_state.temporal_reflection.attempted
    assert provider.reflection_calls == 0
    assert REFLECTION_HEADING not in first.final_response


@pytest.mark.asyncio
async def test_provider_failure_preserves_deterministic_moment_end_to_end():
    provider = ScriptedProvider(error=LLMConnectionError("down"))
    engine = make_engine(provider)
    response = await run_flagship(engine)

    moment = response.chronos_state.past_self_conversation
    reflection = response.chronos_state.temporal_reflection
    assert moment.should_surface
    assert reflection.attempted and reflection.fallback_used
    # The deterministic section still surfaces exactly once; no reflection.
    assert response.final_response.count(MOMENT_HEADING) == 1
    assert REFLECTION_HEADING not in response.final_response
    assert moment.question in response.final_response
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert (
        "temporal ai reflection failed -> deterministic moment preserved"
        in trace
    )


@pytest.mark.asyncio
async def test_default_engine_disabled_ai_never_attempts_reflection():
    engine = ChronosEngine()
    response = await run_flagship(engine)
    reflection = response.chronos_state.temporal_reflection
    assert reflection is not None
    assert not reflection.attempted
    # The deterministic moment surfaces unchanged (default OllamaConfig
    # ships disabled, so Phase 3H behavior is fully preserved).
    assert response.final_response.count(MOMENT_HEADING) == 1
    assert REFLECTION_HEADING not in response.final_response


@pytest.mark.asyncio
async def test_ordinary_input_unchanged_and_no_ai_call():
    provider = ScriptedProvider()
    engine = make_engine(provider)
    response = await engine.process_user_input(
        user_id="user_3i_quiet",
        content="What is Python?",
        input_type="text",
        provider_key="chronos",
    )
    assert not response.chronos_state.temporal_reflection.attempted
    assert provider.reflection_calls == 0
    assert MOMENT_HEADING not in response.final_response
    assert REFLECTION_HEADING not in response.final_response
    trace = "\n".join(response.reasoning_trace.reasoning_steps).lower()
    assert "temporal ai reflection skipped:" in trace


# ── Coexistence with the main AI paths (LIGHT/DEEP) ──────────────────────


class ForceAIRouter:
    def route(self, state):
        return AIRoutingResult(
            use_ai=True,
            path=RoutingPath.DEEP,
            confidence=0.8,
            reason="stub",
            signals=[],
        )


class StubPlanner:
    def __init__(self, primary: ReasoningMode):
        self.plan_result = ReasoningPlan(
            modes=[primary, ReasoningMode.GENERATE],
            primary_mode=primary,
            reason="stub plan",
            confidence=0.6,
        )

    def plan(self, chronos_state, routing_result):
        return self.plan_result


def make_ai_engine(provider: ScriptedProvider, primary: ReasoningMode) -> ChronosEngine:
    config = make_config()
    registry = LLMRegistry()
    registry.register_provider("ollama", provider)
    return ChronosEngine(
        ai_executor=AIExecutor(llm_registry=registry, config=config),
        llm_registry=registry,
        ai_router=ForceAIRouter(),
        reasoning_planner=StubPlanner(primary),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "primary,tier",
    [
        (ReasoningMode.INTERPRET, "LIGHT"),
        (ReasoningMode.REASON, "DEEP"),
    ],
)
async def test_main_ai_path_regression_and_single_temporal_call(primary, tier):
    provider = ScriptedProvider(reflection_text=GOOD_REFLECTION)
    engine = make_ai_engine(provider, primary)
    response = await run_flagship(engine)

    # Main-path behavior did not regress.
    assert response.inference_policy.tier.value == tier
    assert response.ai_execution.used is True
    assert "MAIN_ANSWER" in response.final_response
    assert response.final_response.count(MOMENT_HEADING) == 1

    # Per the implemented architecture the temporal reflection is a
    # separate bounded execution domain: exactly ONE additional,
    # explicitly observable provider call — never more.
    assert provider.reflection_calls == 1
    assert response.chronos_state.temporal_reflection.success
    assert GOOD_REFLECTION in response.final_response
    assert response.final_response.count(REFLECTION_HEADING) == 1

    # Model separation holds across both executions: LIGHT goes to the
    # light model, DEEP to the capable model.
    expected_models = {LIGHT_MODEL if tier == "LIGHT" else DEEP_MODEL}
    assert set(provider.models_called) == expected_models | {LIGHT_MODEL}


@pytest.mark.asyncio
async def test_fast_path_stays_deterministic_except_explicit_reflection_call():
    provider = ScriptedProvider(reflection_text=GOOD_REFLECTION)
    engine = make_engine(provider)
    response = await run_flagship(engine)

    # FAST: the MAIN response path never touched the provider...
    assert response.ai_execution.attempted is False
    # ...and the only provider traffic is the single explicit temporal
    # reflection call for the surfaced moment.
    assert len(provider.models_called) == 1
    assert provider.models_called[0] == LIGHT_MODEL


# ── State wiring ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chronos_state_carries_reflection_result():
    from chronos_engine.state.builder import StateBuilder
    from chronos_engine.temporal.models import TemporalReflectionResult

    result = TemporalReflectionResult(
        attempted=True, used=True, success=True, reflection=GOOD_REFLECTION
    )
    state = await StateBuilder().build(
        UserInput(id="in_sb", user_id="u", content="x"),
        RetrievedContext(),
        temporal_reflection=result,
    )
    assert state.temporal_reflection is result
