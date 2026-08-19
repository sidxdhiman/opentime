"""Phase 2H tests: deterministic inference policy + local model audit.

Covers the ``InferencePolicy`` (tier / provider / model selection), the
``ModelCapability`` abstraction, latency-budget handling, and the guarantee
that the policy itself is pure selection logic:

* It never invokes a provider.
* It never changes ``AIRouter`` / ``ReasoningPlanner`` behavior.
* Execution follows the decision: FAST -> deterministic, LIGHT -> the
  configured light model, DEEP -> the configured capable model (Phase 2J).
"""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.ai import (
    AIExecutor,
    InferencePolicy,
    InferenceTier,
    LatencyClass,
    ModelCapability,
    ReasoningMode,
    ReasoningPlan,
    ReasoningPlanner,
)
from chronos_engine.config import OllamaConfig
from chronos_engine.core.models import (
    IntentType,
    RetrievedContext,
    UserInput,
)
from chronos_engine.llm import LLMRegistry
from chronos_engine.llm.result import LLMResult
from chronos_engine.routing import RoutingPath
from chronos_engine.routing.models import AIRoutingResult
from chronos_engine.state.models import (
    ChronosState,
    GoalAnalysisResult,
    GoalStatus,
    IntentResult,
)
from chronos_engine.validators.service import ResponseValidator

DEEP_MODEL = "qwen3:4b"
LIGHT_MODEL = "qwen2.5:1.5b"

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def routing(use_ai: bool = True, confidence: float = 0.9) -> AIRoutingResult:
    return AIRoutingResult(
        use_ai=use_ai,
        path=RoutingPath.DEEP if use_ai else RoutingPath.FAST,
        confidence=confidence,
        reason="test routing",
        signals=[],
    )


def plan(*modes, primary=None) -> ReasoningPlan:
    return ReasoningPlan(
        modes=list(modes),
        primary_mode=primary or modes[-1],
        reason="test plan",
        confidence=0.6,
    )


def reflect_plan() -> ReasoningPlan:
    return plan(
        ReasoningMode.REFLECT,
        ReasoningMode.GENERATE,
        primary=ReasoningMode.REFLECT,
    )


def interpret_plan() -> ReasoningPlan:
    return plan(
        ReasoningMode.INTERPRET,
        ReasoningMode.GENERATE,
        primary=ReasoningMode.INTERPRET,
    )


def reason_plan() -> ReasoningPlan:
    return plan(
        ReasoningMode.REASON,
        ReasoningMode.GENERATE,
        primary=ReasoningMode.REASON,
    )


def make_policy(
    *,
    enabled: bool = True,
    deep_model: str = DEEP_MODEL,
    light_model: str = "",
    catalog=None,
) -> InferencePolicy:
    config = OllamaConfig(
        enabled=enabled, model=deep_model, light_model=light_model
    )
    return InferencePolicy(config=config, available_models=catalog or [])


def make_state(content: str) -> ChronosState:
    return ChronosState(
        id="state_2h",
        user_id="user_2h",
        current_input=UserInput(id="in_2h", user_id="user_2h", content=content),
        context=RetrievedContext(),
    )


# ---------------------------------------------------------------------------
# Test 1 — FAST -> NONE
# ---------------------------------------------------------------------------


def test_fast_path_returns_none():
    policy = make_policy()
    decision = policy.decide(routing(use_ai=False, confidence=0.7), plan(ReasoningMode.GENERATE))

    assert decision.tier == InferenceTier.NONE
    assert decision.provider is None
    assert decision.model is None
    assert decision.expected_latency_class == LatencyClass.NONE
    assert decision.light_requested is False
    assert "fast path" in decision.signals


# ---------------------------------------------------------------------------
# Test 2 — INTERPRET + GENERATE -> LIGHT when a light model exists
# ---------------------------------------------------------------------------


def test_interpret_generate_uses_light_model_when_available():
    policy = make_policy(light_model=LIGHT_MODEL, catalog=[LIGHT_CAPABILITY])

    decision = policy.decide(
        routing(), interpret_plan()
    )

    assert decision.tier == InferenceTier.LIGHT
    assert decision.provider == "ollama"
    assert decision.model == LIGHT_MODEL
    assert decision.confidence == 0.88
    assert decision.expected_latency_class == LatencyClass.LOW
    assert decision.light_requested is False
    assert "light model available" in decision.signals


# ---------------------------------------------------------------------------
# Test 3 — INTERPRET + GENERATE with NO light model -> DEEP fallback policy
# ---------------------------------------------------------------------------


def test_interpret_generate_falls_back_to_deep_without_light_model():
    policy = make_policy()

    decision = policy.decide(
        routing(), interpret_plan()
    )

    assert decision.tier == InferenceTier.DEEP
    assert decision.provider == "ollama"
    assert decision.model == DEEP_MODEL
    assert decision.confidence == 1.0
    assert decision.expected_latency_class == LatencyClass.HIGH
    assert decision.light_requested is True
    assert "No lightweight local model is available." in decision.reason
    assert "no light model" in decision.signals


# ---------------------------------------------------------------------------
# Test 4 — REASON -> DEEP
# ---------------------------------------------------------------------------


def test_reason_requires_deep():
    policy = make_policy(light_model=LIGHT_MODEL, catalog=[LIGHT_CAPABILITY])

    decision = policy.decide(
        routing(), reason_plan()
    )

    assert decision.tier == InferenceTier.DEEP
    assert decision.model == DEEP_MODEL
    assert decision.confidence == 0.94
    assert decision.expected_latency_class == LatencyClass.HIGH
    assert decision.light_requested is False
    # A light model existing must never downgrade REASON.
    assert "plan requires capable model" in decision.signals


# ---------------------------------------------------------------------------
# Test 5 — REFLECT -> DEEP
# ---------------------------------------------------------------------------


def test_reflect_requires_deep():
    policy = make_policy()

    decision = policy.decide(
        routing(), reflect_plan()
    )

    assert decision.tier == InferenceTier.DEEP
    assert decision.model == DEEP_MODEL
    assert decision.expected_latency_class == LatencyClass.HIGH


# ---------------------------------------------------------------------------
# Test 6 — REASON + REFLECT -> DEEP
# ---------------------------------------------------------------------------


def test_reason_and_reflect_require_deep():
    policy = make_policy()

    decision = policy.decide(
        routing(),
        plan(
            ReasoningMode.REASON,
            ReasoningMode.REFLECT,
            ReasoningMode.GENERATE,
            primary=ReasoningMode.REASON,
        ),
    )

    assert decision.tier == InferenceTier.DEEP
    assert decision.model == DEEP_MODEL


# ---------------------------------------------------------------------------
# Test 7 — AI disabled -> NONE
# ---------------------------------------------------------------------------


def test_ai_disabled_returns_none():
    policy = make_policy(enabled=False)

    decision = policy.decide(
        routing(), reason_plan()
    )

    assert decision.tier == InferenceTier.NONE
    assert decision.provider is None
    assert decision.model is None
    assert "ai disabled" in decision.signals


# ---------------------------------------------------------------------------
# Test 8 — Qwen3:4B remains DEEP
# ---------------------------------------------------------------------------


def test_qwen3_remains_deep_model():
    config = OllamaConfig(enabled=True, model=DEEP_MODEL, light_model=LIGHT_MODEL)
    policy = InferencePolicy(config=config, available_models=[LIGHT_CAPABILITY])

    # Even when a light model is configured AND installed, REASON stays DEEP
    # on the configured capable model.
    reason_decision = policy.decide(
        routing(), reason_plan()
    )
    assert reason_decision.tier == InferenceTier.DEEP
    assert reason_decision.model == DEEP_MODEL

    # And when no light model is configured, DEEP is the only tier.
    bare = make_policy(deep_model=DEEP_MODEL)
    deep_decision = bare.decide(
        routing(), interpret_plan()
    )
    assert deep_decision.tier == InferenceTier.DEEP
    assert deep_decision.model == DEEP_MODEL


# ---------------------------------------------------------------------------
# Test 9 — Unknown model metadata does not crash the policy
# ---------------------------------------------------------------------------


def test_unknown_model_metadata_does_not_crash_policy():
    unknown = ModelCapability(provider="ollama", model="some-small-model")
    policy = make_policy(light_model="some-small-model", catalog=[unknown])

    decision = policy.decide(
        routing(), interpret_plan()
    )

    # Unknown values are tolerated (not fabricated) — the model still counts
    # as a LIGHT candidate and the decision is deterministic.
    assert decision.tier == InferenceTier.LIGHT
    assert decision.model == "some-small-model"


def test_unknown_metadata_never_reports_known_values():
    unknown = ModelCapability(provider="ollama", model="m")
    dumped = unknown.model_dump()
    assert dumped["parameter_count"] is None
    assert dumped["quantization"] is None
    assert dumped["estimated_memory_gb"] is None
    assert dumped["context_length"] is None
    assert dumped["supports_json"] is None


# ---------------------------------------------------------------------------
# Test 10 — Model capability serialization
# ---------------------------------------------------------------------------


def test_model_capability_serialization_round_trip():
    dumped = LIGHT_CAPABILITY.model_dump()
    assert dumped["provider"] == "ollama"
    assert dumped["model"] == LIGHT_MODEL
    assert dumped["parameter_count"] == 1.5
    assert dumped["quantization"] == "Q4_K_M"
    assert dumped["estimated_memory_gb"] == 1.1
    assert dumped["context_length"] == 32768
    assert dumped["supports_json"] is True
    assert dumped["supports_thinking"] is False
    assert dumped["tier"] == "LIGHT"

    restored = ModelCapability.model_validate(dumped)
    assert restored == LIGHT_CAPABILITY


# ---------------------------------------------------------------------------
# Test 11 — Latency budget handling
# ---------------------------------------------------------------------------


def test_latency_budget_too_tight_without_light_model_returns_none():
    policy = make_policy()  # no light model configured
    decision = policy.decide(
        routing(),
        plan(ReasoningMode.INTERPRET, ReasoningMode.GENERATE, primary=ReasoningMode.INTERPRET),
        latency_budget=10.0,  # below light_max_latency_seconds (30.0)
    )

    assert decision.tier == InferenceTier.NONE
    assert decision.latency_budget == 10.0
    assert decision.light_requested is True
    assert "latency budget too tight" in decision.signals


def test_latency_budget_tight_with_light_model_stays_light():
    policy = make_policy(light_model=LIGHT_MODEL, catalog=[LIGHT_CAPABILITY])
    decision = policy.decide(
        routing(),
        plan(ReasoningMode.INTERPRET, ReasoningMode.GENERATE, primary=ReasoningMode.INTERPRET),
        latency_budget=10.0,
    )

    assert decision.tier == InferenceTier.LIGHT
    assert decision.model == LIGHT_MODEL
    assert decision.latency_budget == 10.0
    assert decision.expected_latency_class == LatencyClass.LOW


def test_latency_budget_does_not_downgrade_deep_reasoning():
    policy = make_policy()
    decision = policy.decide(
        routing(),
        plan(ReasoningMode.REASON, ReasoningMode.GENERATE, primary=ReasoningMode.REASON),
        latency_budget=10.0,  # DEEP tolerates higher latency
    )

    assert decision.tier == InferenceTier.DEEP
    assert decision.model == DEEP_MODEL
    assert decision.latency_budget == 10.0


def test_latency_budget_adequate_without_light_model_stays_deep():
    policy = make_policy()
    decision = policy.decide(
        routing(),
        plan(ReasoningMode.INTERPRET, ReasoningMode.GENERATE, primary=ReasoningMode.INTERPRET),
        latency_budget=60.0,  # at/above the light threshold
    )

    assert decision.tier == InferenceTier.DEEP
    assert decision.model == DEEP_MODEL
    assert decision.expected_latency_class == LatencyClass.HIGH


# ---------------------------------------------------------------------------
# Test 12 — Policy never invokes any provider
# ---------------------------------------------------------------------------


def test_policy_never_invokes_provider(monkeypatch):
    from chronos_engine.llm.providers.ollama import OllamaProvider

    def boom(self, *args, **kwargs):
        raise AssertionError("The inference policy must never call a provider.")

    monkeypatch.setattr(OllamaProvider, "generate", boom)
    monkeypatch.setattr(OllamaProvider, "generate_response", boom)
    monkeypatch.setattr(OllamaProvider, "health_check", boom)

    policy = make_policy(light_model=LIGHT_MODEL, catalog=[LIGHT_CAPABILITY])

    policy.decide(
        routing(), interpret_plan()
    )
    policy.decide(
        routing(), reason_plan()
    )
    policy.decide(routing(use_ai=False), plan(ReasoningMode.GENERATE))


# ---------------------------------------------------------------------------
# Test 13 — Existing AIRouter behavior unchanged
# ---------------------------------------------------------------------------


def test_policy_does_not_change_airouter_decision():
    state = make_state(
        "Should I continue building ChronOS or focus on interview preparation?"
    )
    state.intent = IntentResult(intent=IntentType.DECISION, confidence=0.8)
    state.goal_analysis = GoalAnalysisResult(
        status=GoalStatus.ACTIVE, goal="Build ChronOS", confidence=0.7
    )

    from chronos_engine.routing.service import AIRouter

    router = AIRouter()
    before = router.route(state)
    assert before.path == RoutingPath.DEEP

    # The policy is a pure consumer of the routing result — evaluating it must
    # not alter the router's output.
    policy = make_policy()
    policy.decide(before, ReasoningPlanner().plan(state, before))
    after = router.route(state)

    assert after.model_dump() == before.model_dump()


@pytest.mark.asyncio
async def test_engine_records_policy_without_changing_routing():
    engine = ChronosEngine(
        inference_policy=make_policy(),
    )

    fast = await engine.process_user_input(
        user_id="user_2h_fast", content="What is MongoDB?", provider_key="chronos"
    )
    assert fast.ai_routing.path == RoutingPath.FAST
    assert fast.inference_policy is not None
    assert fast.inference_policy.tier == InferenceTier.NONE

    deep = await engine.process_user_input(
        user_id="user_2h_deep",
        content="Should I continue building ChronOS or focus on interviews?",
        provider_key="chronos",
    )
    assert deep.ai_routing.path == RoutingPath.DEEP
    assert deep.ai_routing.use_ai is True
    assert deep.inference_policy is not None
    assert deep.inference_policy.tier == InferenceTier.DEEP


# ---------------------------------------------------------------------------
# Test 14 — Existing ReasoningPlanner behavior unchanged
# ---------------------------------------------------------------------------


def test_policy_consumes_planner_plan_deterministically():
    state = make_state(
        "Should I continue building ChronOS or focus on interview preparation?"
    )
    state.intent = IntentResult(intent=IntentType.DECISION, confidence=0.8)
    state.goal_analysis = GoalAnalysisResult(
        status=GoalStatus.ACTIVE, goal="Build ChronOS", confidence=0.7
    )
    routing_result = routing()

    planner = ReasoningPlanner()
    plan_one = planner.plan(state, routing_result)
    plan_two = planner.plan(state, routing_result)
    assert plan_one.model_dump() == plan_two.model_dump()

    policy = make_policy()
    decision = policy.decide(routing_result, plan_one)
    assert decision.tier == InferenceTier.DEEP
    assert decision.model == DEEP_MODEL


# ---------------------------------------------------------------------------
# Execution follows the decision — policy never invokes a provider itself
# ---------------------------------------------------------------------------


class FakeOllama:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.generate_calls = []

    def provider_name(self):
        return "Ollama Local"

    async def generate(self, prompt_context, model_name: str = "", inference_options=None):
        self.generate_calls.append((model_name, inference_options))
        if self.error is not None:
            raise self.error
        return self.result

    async def generate_response(self, prompt_context, model_name: str = ""):
        return self.result.text if self.result else ""


def ok_result(text: str = "AI_2H_RESPONSE") -> LLMResult:
    import json

    return LLMResult(
        text=json.dumps(
            {
                "interpretation": None,
                "reasoning": "ChronOS weighed the deterministic state.",
                "reflection": None,
                "answer": text,
                "uncertainties": [],
                "evidence_used": [],
            }
        ),
        provider="ollama",
        model=DEEP_MODEL,
        latency_ms=12.5,
        success=True,
    )


@pytest.mark.asyncio
async def test_engine_execution_follows_policy_for_deep():
    """The executor executes exactly the model the policy decision selects."""
    config = OllamaConfig(
        base_url="http://ollama:11434",
        model=DEEP_MODEL,
        light_model=LIGHT_MODEL,
        timeout=2.0,
        enabled=True,
    )
    policy = InferencePolicy(config=config, available_models=[LIGHT_CAPABILITY])
    provider = FakeOllama(result=ok_result())
    registry = LLMRegistry()
    registry.register_provider("ollama", provider)
    executor = AIExecutor(
        llm_registry=registry, config=config, validator=ResponseValidator()
    )
    engine = ChronosEngine(
        ai_executor=executor,
        llm_registry=registry,
        inference_policy=policy,
        reasoning_planner=ReasoningPlanner(),
    )

    response = await engine.process_user_input(
        user_id="user_2h_obs",
        content="Considering everything I've told you about ChronOS, "
        "do you think I should continue investing my time in it?",
        provider_key="chronos",
    )

    # This input routes DEEP (historical reasoning), so the policy decision
    # and the executed model are the capable DEEP model — even though a light
    # model is configured and available. LIGHT must never run a REASON/REFLECT
    # request.
    assert response.inference_policy is not None
    assert response.inference_policy.tier == InferenceTier.DEEP
    assert response.ai_routing.use_ai is True
    assert response.ai_execution.used is True
    assert response.ai_execution.tier == InferenceTier.DEEP.value
    assert response.ai_execution.model == DEEP_MODEL
    assert provider.generate_calls and provider.generate_calls[0][0] == DEEP_MODEL
    assert response.final_response == "AI_2H_RESPONSE"