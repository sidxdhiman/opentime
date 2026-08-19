"""Phase 2J tests: LIGHT-model execution integration.

The ``InferencePolicy`` decision now dictates the actual model executed by
``AIExecutor``:

* FAST  -> policy NONE, no provider call, deterministic response.
* INTERPRET / CLASSIFY -> policy LIGHT -> the configured light model
  (``qwen2.5:1.5b``), and ``qwen3:4b`` must NOT be called.
* REASON / REFLECT    -> policy DEEP -> the configured capable model
  (``qwen3:4b``), and ``qwen2.5:1.5b`` must NOT be called.
* LIGHT model unavailable / connection failure / timeout / validation
  failure -> deterministic fallback (never an automatic escalation to DEEP).

Model-selection logic is NOT duplicated in the executor: it only consumes the
policy decision. No real Ollama installation is required.
"""

import json

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.ai import (
    AIExecutionResult,
    AIExecutor,
    InferencePolicy,
    InferenceTier,
    ModelCapability,
    ReasoningMode,
    ReasoningPlan,
)
from chronos_engine.config import OllamaConfig
from chronos_engine.core.models import (
    RetrievedContext,
    UserInput,
    ValidationResult,
)
from chronos_engine.llm import LLMRegistry
from chronos_engine.llm.errors import (
    LLMConnectionError,
    LLMModelUnavailableError,
    LLMTimeoutError,
)
from chronos_engine.llm.result import LLMResult
from chronos_engine.routing import RoutingPath
from chronos_engine.routing.models import AIRoutingResult
from chronos_engine.state.models import ChronosState
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

FAST_INPUT = "What is Python?"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def make_policy(config=None) -> InferencePolicy:
    return InferencePolicy(
        config=config or make_config(),
        available_models=[LIGHT_CAPABILITY],
    )


def ok_result(text: str = "AI_2J_LIGHT_RESPONSE") -> LLMResult:
    return LLMResult(
        text=json.dumps(
            {
                "interpretation": None,
                "reasoning": None,
                "reflection": None,
                "answer": text,
                "uncertainties": [],
                "evidence_used": [],
            }
        ),
        provider="ollama",
        model=LIGHT_MODEL,
        latency_ms=8.0,
        success=True,
    )


class FakeOllama:
    """Fake provider recording the model name + options for every call."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.generate_calls = []  # [(model_name, inference_options)]

    def provider_name(self) -> str:
        return "Ollama Local"

    async def generate(self, prompt_context, model_name: str = "", inference_options=None):
        self.generate_calls.append((model_name, inference_options))
        if self.error is not None:
            raise self.error
        return self.result

    async def generate_response(self, prompt_context, model_name: str = ""):
        return self.result.text if self.result else ""

    @property
    def models_called(self):
        return [call[0] for call in self.generate_calls]


class RejectValidator:
    """Validator that always rejects — used to exercise validation failure."""

    async def validate_response(self, raw_response, prompt_context):
        return ValidationResult(
            is_valid=False,
            validated_response="",
            corrections_made=[],
            contradictions_detected=[],
            personalization_score=0.0,
        )


class DeepRouter:
    """Stub router: forces the DEEP path so the LIGHT/DEEP execution split
    can be exercised end-to-end without changing router semantics."""

    def route(self, state):
        return AIRoutingResult(
            use_ai=True,
            path=RoutingPath.DEEP,
            confidence=0.8,
            reason="stub deep routing",
            signals=[],
        )


def plan(*modes, primary=None) -> ReasoningPlan:
    return ReasoningPlan(
        modes=list(modes),
        primary_mode=primary or modes[-1],
        reason="test plan",
        confidence=0.6,
    )


def interpret_plan() -> ReasoningPlan:
    return plan(
        ReasoningMode.INTERPRET, ReasoningMode.GENERATE,
        primary=ReasoningMode.INTERPRET,
    )


def classify_plan() -> ReasoningPlan:
    return plan(
        ReasoningMode.CLASSIFY, ReasoningMode.GENERATE,
        primary=ReasoningMode.CLASSIFY,
    )


def reason_plan() -> ReasoningPlan:
    return plan(
        ReasoningMode.REASON, ReasoningMode.GENERATE,
        primary=ReasoningMode.REASON,
    )


def reflect_plan() -> ReasoningPlan:
    return plan(
        ReasoningMode.REFLECT, ReasoningMode.GENERATE,
        primary=ReasoningMode.REFLECT,
    )


def reason_reflect_plan() -> ReasoningPlan:
    return plan(
        ReasoningMode.REASON, ReasoningMode.REFLECT, ReasoningMode.GENERATE,
        primary=ReasoningMode.REASON,
    )


def deep_routing() -> AIRoutingResult:
    return AIRoutingResult(
        use_ai=True,
        path=RoutingPath.DEEP,
        confidence=0.8,
        reason="test routing",
        signals=[],
    )


def fast_routing() -> AIRoutingResult:
    return AIRoutingResult(
        use_ai=False,
        path=RoutingPath.FAST,
        confidence=0.7,
        reason="test routing",
        signals=[],
    )


def make_state(content: str = "I'm frustrated because I'm stuck.") -> ChronosState:
    return ChronosState(
        id="state_2j",
        user_id="user_2j",
        current_input=UserInput(id="in_2j", user_id="user_2j", content=content),
        context=RetrievedContext(),
    )


def make_executor(provider, config=None, validator=None) -> AIExecutor:
    config = config or make_config()
    registry = LLMRegistry()
    registry.register_provider("ollama", provider)
    return AIExecutor(
        llm_registry=registry,
        config=config,
        validator=validator or ResponseValidator(),
    )


async def run_executor(
    provider,
    *,
    plan=None,
    decision=None,
    config=None,
    validator=None,
) -> AIExecutionResult:
    """Run the executor with a policy decision derived from the given plan."""
    config = config or make_config()
    policy = make_policy(config)
    routing = deep_routing()
    decision = decision or policy.decide(routing, plan or interpret_plan())
    executor = make_executor(provider, config=config, validator=validator)
    return await executor.execute(
        routing,
        make_state(),
        _deterministic(),
        inference_policy_decision=decision,
    )


def _deterministic():
    from chronos_engine.response.models import (
        ChronosInterpretation,
        DeterministicResponse,
    )
    from chronos_engine.state.models import EngineStateResult

    return DeterministicResponse(
        user_signal="input",
        chronos_interpretation=ChronosInterpretation(
            user_state_summary="n", intent_summary="n", context_summary="n"
        ),
        chronos_state=EngineStateResult(),
        rendered="deterministic",
    )


def make_engine(provider, *, config=None, validator=None, router=None):
    config = config or make_config()
    registry = LLMRegistry()
    registry.register_provider("ollama", provider)
    executor = make_executor(provider, config=config, validator=validator)
    return ChronosEngine(
        ai_executor=executor,
        llm_registry=registry,
        ai_router=router,
    )


# ---------------------------------------------------------------------------
# Test 1 — FAST -> NONE -> no provider call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_never_calls_any_provider():
    provider = FakeOllama(result=ok_result())
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2j_fast", content=FAST_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.FAST
    assert response.inference_policy.tier == InferenceTier.NONE
    assert response.ai_execution.attempted is False
    assert response.ai_execution.tier == InferenceTier.NONE.value
    assert provider.models_called == []
    assert response.final_response == response.deterministic_response.rendered


# ---------------------------------------------------------------------------
# Test 2 — INTERPRET -> LIGHT -> qwen2.5:1.5b (and NOT qwen3:4b)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_interpret_executes_light_model_only():
    provider = FakeOllama(result=ok_result("AI_2J_INTERPRET"))
    result = await run_executor(provider, plan=interpret_plan())

    assert result.used is True
    assert result.success is True
    assert result.fallback_used is False
    assert result.tier == InferenceTier.LIGHT.value
    assert result.provider == "ollama"
    assert result.model == LIGHT_MODEL
    assert result.latency_ms is not None
    assert provider.models_called == [LIGHT_MODEL]
    assert DEEP_MODEL not in provider.models_called


@pytest.mark.asyncio
async def test_engine_interpret_end_to_end_executes_light_model():
    """The most important acceptance criterion: a LIGHT request calls the
    LIGHT model and never calls the DEEP model."""
    provider = FakeOllama(result=ok_result("AI_2J_ENGINE_LIGHT"))
    engine = make_engine(provider, router=DeepRouter())

    response = await engine.process_user_input(
        user_id="user_2j_e2e_light",
        content="I'm frustrated because I'm stuck.",
        provider_key="chronos",
    )

    assert response.ai_routing.use_ai is True
    assert response.inference_policy.tier == InferenceTier.LIGHT
    assert response.inference_policy.model == LIGHT_MODEL
    assert response.ai_execution.used is True
    assert response.ai_execution.tier == InferenceTier.LIGHT.value
    assert response.ai_execution.model == LIGHT_MODEL
    assert provider.models_called == [LIGHT_MODEL]
    assert DEEP_MODEL not in provider.models_called
    assert response.final_response == "AI_2J_ENGINE_LIGHT"
    assert response.model_name == LIGHT_MODEL


# ---------------------------------------------------------------------------
# Test 3 — CLASSIFY -> LIGHT -> qwen2.5:1.5b
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_executes_light_model_only():
    provider = FakeOllama(result=ok_result("AI_2J_CLASSIFY"))
    result = await run_executor(provider, plan=classify_plan())

    assert result.used is True
    assert result.tier == InferenceTier.LIGHT.value
    assert result.model == LIGHT_MODEL
    assert provider.models_called == [LIGHT_MODEL]
    assert DEEP_MODEL not in provider.models_called


# ---------------------------------------------------------------------------
# Tests 4–6 — REASON / REFLECT / REASON+REFLECT -> DEEP -> qwen3:4b
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reason_executes_deep_model_only():
    provider = FakeOllama(result=ok_result("AI_2J_REASON"))
    result = await run_executor(provider, plan=reason_plan())

    assert result.used is True
    assert result.tier == InferenceTier.DEEP.value
    assert result.model == DEEP_MODEL
    assert provider.models_called == [DEEP_MODEL]
    assert LIGHT_MODEL not in provider.models_called


@pytest.mark.asyncio
async def test_reflect_executes_deep_model_only():
    provider = FakeOllama(result=ok_result("AI_2J_REFLECT"))
    result = await run_executor(provider, plan=reflect_plan())

    assert result.used is True
    assert result.tier == InferenceTier.DEEP.value
    assert result.model == DEEP_MODEL
    assert provider.models_called == [DEEP_MODEL]
    assert LIGHT_MODEL not in provider.models_called


@pytest.mark.asyncio
async def test_reason_and_reflect_execute_deep_model_only():
    provider = FakeOllama(result=ok_result("AI_2J_REASON_REFLECT"))
    result = await run_executor(provider, plan=reason_reflect_plan())

    assert result.used is True
    assert result.tier == InferenceTier.DEEP.value
    assert result.model == DEEP_MODEL
    assert provider.models_called == [DEEP_MODEL]
    assert LIGHT_MODEL not in provider.models_called


# ---------------------------------------------------------------------------
# Tests 7–10 — LIGHT failures never escalate to DEEP; deterministic fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_light_model_unavailable_falls_back_deterministically():
    provider = FakeOllama(error=LLMModelUnavailableError("model missing"))
    engine = make_engine(provider, router=DeepRouter())

    response = await engine.process_user_input(
        user_id="user_2j_unavailable",
        content="I'm frustrated because I'm stuck.",
        provider_key="chronos",
    )

    ai = response.ai_execution
    assert ai.used is False
    assert ai.success is False
    assert ai.fallback_used is True
    assert ai.tier == InferenceTier.LIGHT.value
    assert ai.model == LIGHT_MODEL
    assert ai.error_type == "LLMModelUnavailableError"
    assert provider.models_called == [LIGHT_MODEL]
    assert DEEP_MODEL not in provider.models_called
    # Deterministic fallback — never a 100+ second DEEP request.
    assert response.final_response == response.deterministic_response.rendered


@pytest.mark.asyncio
async def test_light_connection_failure_falls_back_deterministically():
    provider = FakeOllama(error=LLMConnectionError("connection refused"))
    result = await run_executor(provider, plan=interpret_plan())

    assert result.fallback_used is True
    assert result.error_type == "LLMConnectionError"
    assert result.tier == InferenceTier.LIGHT.value
    assert result.model == LIGHT_MODEL
    assert provider.models_called == [LIGHT_MODEL]


@pytest.mark.asyncio
async def test_light_timeout_falls_back_deterministically():
    provider = FakeOllama(error=LLMTimeoutError("timed out"))
    result = await run_executor(provider, plan=interpret_plan())

    assert result.fallback_used is True
    assert result.error_type == "LLMTimeoutError"
    assert result.tier == InferenceTier.LIGHT.value
    assert result.model == LIGHT_MODEL
    assert provider.models_called == [LIGHT_MODEL]
    assert DEEP_MODEL not in provider.models_called


@pytest.mark.asyncio
async def test_light_validation_failure_falls_back_deterministically():
    provider = FakeOllama(result=ok_result("AI_2J_VALIDATION_REJECTED"))
    result = await run_executor(
        provider, plan=interpret_plan(), validator=RejectValidator()
    )

    assert result.used is False
    assert result.fallback_used is True
    assert result.error_type == "VALIDATION_FAILED"
    assert result.tier == InferenceTier.LIGHT.value
    assert result.model == LIGHT_MODEL
    assert provider.models_called == [LIGHT_MODEL]


# ---------------------------------------------------------------------------
# Test 11 — LIGHT never accidentally invokes qwen3:4b
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_light_never_invokes_deep_model_across_scenarios():
    calls: list[str] = []
    for error in (
        None,
        LLMModelUnavailableError("missing"),
        LLMConnectionError("down"),
        LLMTimeoutError("slow"),
    ):
        provider = FakeOllama(result=ok_result(), error=error)
        await run_executor(provider, plan=interpret_plan())
        await run_executor(provider, plan=classify_plan())
        calls.extend(provider.models_called)

    assert calls and set(calls) == {LIGHT_MODEL}
    assert DEEP_MODEL not in calls


# ---------------------------------------------------------------------------
# Test 12 — DEEP never accidentally invokes qwen2.5:1.5b
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deep_never_invokes_light_model_across_scenarios():
    calls: list[str] = []
    for p in (reason_plan(), reflect_plan(), reason_reflect_plan()):
        provider = FakeOllama(result=ok_result())
        await run_executor(provider, plan=p)
        calls.extend(provider.models_called)

    assert calls and set(calls) == {DEEP_MODEL}
    assert LIGHT_MODEL not in calls


# ---------------------------------------------------------------------------
# Test 13 — Execution metadata records the actual model + tier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_metadata_records_light_actuals():
    provider = FakeOllama(result=ok_result("AI_2J_META"))
    result = await run_executor(provider, plan=interpret_plan())

    assert result.tier == InferenceTier.LIGHT.value
    assert result.provider == "ollama"
    assert result.model == LIGHT_MODEL
    assert isinstance(result.latency_ms, (int, float))
    assert result.latency_ms >= 0
    assert result.success is True
    assert result.fallback_used is False
    assert result.error_type is None
    assert result.inference_options is not None
    assert result.prompt_chars is not None and result.prompt_chars > 0

    dumped = result.model_dump(mode="json")
    assert dumped["tier"] == "LIGHT"
    assert dumped["model"] == LIGHT_MODEL


@pytest.mark.asyncio
async def test_execution_metadata_records_deep_actuals():
    provider = FakeOllama(result=ok_result("AI_2J_META_DEEP"))
    result = await run_executor(provider, plan=reason_plan())

    assert result.tier == InferenceTier.DEEP.value
    assert result.model == DEEP_MODEL
    assert result.success is True
    assert result.fallback_used is False


# ---------------------------------------------------------------------------
# Test 14 — Inference options are model/tier appropriate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_light_inference_options_default_to_no_thinking_and_no_json():
    provider = FakeOllama(result=ok_result())
    result = await run_executor(provider, plan=interpret_plan())

    options = result.inference_options
    assert options.thinking_enabled is False  # light_thinking_enabled default
    assert options.format_json is False  # light_format_json default
    # The LIGHT tier must never inherit the DEEP model's thinking config.
    assert provider.generate_calls[0][1].thinking_enabled is False


@pytest.mark.asyncio
async def test_light_inference_options_respect_explicit_config():
    provider = FakeOllama(result=ok_result())
    config = make_config(light_thinking_enabled=True, light_format_json=True)
    result = await run_executor(provider, plan=interpret_plan(), config=config)

    assert result.inference_options.thinking_enabled is True
    assert result.inference_options.format_json is True


@pytest.mark.asyncio
async def test_deep_inference_options_keep_global_thinking_and_no_json_override():
    provider = FakeOllama(result=ok_result())
    result = await run_executor(provider, plan=reason_plan())

    options = result.inference_options
    assert options.thinking_enabled is True  # global default for DEEP
    assert options.format_json is None  # global default applies, not overridden


# ---------------------------------------------------------------------------
# Test 15 — the engine's recorded policy and executed model always agree
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_engine_policy_and_execution_agree():
    provider = FakeOllama(result=ok_result("AI_2J_AGREE"))
    engine = make_engine(provider, router=DeepRouter())

    response = await engine.process_user_input(
        user_id="user_2j_agree",
        content="I'm frustrated because I'm stuck.",
        provider_key="chronos",
    )

    assert response.inference_policy.tier.value == response.ai_execution.tier
    assert response.inference_policy.model == response.ai_execution.model
    assert response.inference_policy.tier == InferenceTier.LIGHT
    assert response.ai_execution.model == LIGHT_MODEL