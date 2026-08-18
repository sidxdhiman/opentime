"""Phase 2C tests: AI Router connected to Ollama via the AIExecutor.

The routing decision is now operational:

* FAST  -> deterministic response, the AI executor is never invoked, and
  Ollama is never called.
* DEEP  -> the AIExecutor invokes the configured Ollama provider through
  ``LLMRegistry -> ollama``; the AI output passes through the existing
  ``ResponseValidator``.
* DEEP + disabled/unavailable/invalid/validation-failure -> graceful,
  observable deterministic fallback. The engine must never crash because AI
  is unavailable, must never hide the failure, must never mutate
  ``ChronosState``, and must never write memory.

All provider failures are simulated with typed provider errors; no real
Ollama installation is required.
"""

import json

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.ai import AIExecutionResult, AIExecutor
from chronos_engine.config import OllamaConfig
from chronos_engine.core.models import (
    PromptContext,
    RetrievedContext,
    ValidationResult,
)
from chronos_engine.llm import LLMRegistry
from chronos_engine.llm.errors import (
    LLMConnectionError,
    LLMInvalidResponseError,
    LLMModelUnavailableError,
    LLMTimeoutError,
)
from chronos_engine.llm.result import LLMResult
from chronos_engine.routing import RoutingPath
from chronos_engine.validators.service import ResponseValidator

DEEP_INPUT = (
    "Considering everything I've told you about ChronOS, "
    "do you think I should continue investing my time in it?"
)
FAST_INPUT = "What is Python?"


def ok_result(text: str = "CHRONOS_AI_RESPONSE") -> LLMResult:
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
        model="qwen3:4b",
        latency_ms=12.5,
        success=True,
    )


class FakeOllama:
    """Fake provider with the same surface the executor touches."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.generate_calls = []
        self.generate_response_calls = []
        self.last_inference_options = None

    def provider_name(self) -> str:
        return "Ollama Local"

    async def generate(self, prompt_context, model_name: str = "", inference_options=None):
        self.generate_calls.append((prompt_context, model_name))
        self.last_inference_options = inference_options
        if self.error is not None:
            raise self.error
        return self.result

    async def generate_response(self, prompt_context, model_name: str = ""):
        self.generate_response_calls.append((prompt_context, model_name))
        if self.error is not None:
            raise self.error
        return self.result.text if self.result else ""


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


class NoopExecutor:
    """Executor that returns a fallback without touching any provider."""

    async def execute(self, routing_result, chronos_state, deterministic_response):
        prompt_context = PromptContext(
            current_input=chronos_state.current_input,
            retrieved_context=chronos_state.context or RetrievedContext(),
            system_prompt="",
            user_prompt="",
        )
        return AIExecutionResult(
            attempted=True,
            used=False,
            success=False,
            model="qwen3:4b",
            prompt_context=prompt_context,
            fallback_used=True,
            error_type="OLLAMA_UNAVAILABLE",
        )


def make_engine(provider, *, enabled=True, validator=None, model="qwen3:4b"):
    config = OllamaConfig(
        base_url="http://ollama:11434", model=model, timeout=2.0, enabled=enabled
    )
    registry = LLMRegistry()
    registry.register_provider("ollama", provider)
    executor = AIExecutor(
        llm_registry=registry,
        config=config,
        validator=validator or ResponseValidator(),
    )
    return ChronosEngine(ai_executor=executor, llm_registry=registry)


def core_state(state):
    """The deterministic-state slice that AI must never rewrite."""
    return {
        "intent": state.intent.model_dump() if state.intent else None,
        "user_state": state.user_state.model_dump() if state.user_state else None,
        "goal_analysis": state.goal_analysis.model_dump()
        if state.goal_analysis
        else None,
        "contradictions": [c.model_dump() for c in (state.contradictions or [])],
        "goals": state.goals,
        "patterns": [p.model_dump() for p in state.patterns],
        "engine_state": state.engine_state.model_dump() if state.engine_state else None,
        "confidence": state.confidence,
    }


# ---------------------------------------------------------------------------
# Test 1 — FAST never calls Ollama
# ---------------------------------------------------------------------------


async def test_fast_never_calls_ollama():
    provider = FakeOllama(result=ok_result())
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_fast", content=FAST_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.FAST
    assert provider.generate_calls == []
    assert provider.generate_response_calls == []
    assert response.ai_execution.attempted is False
    assert response.ai_execution.used is False
    assert response.final_response == response.deterministic_response.rendered


# ---------------------------------------------------------------------------
# Test 2 — DEEP calls Ollama
# ---------------------------------------------------------------------------


async def test_deep_calls_ollama_success():
    provider = FakeOllama(result=ok_result("AI_RESPONSE_TEXT"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_deep", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.DEEP
    assert len(provider.generate_calls) == 1
    ai_execution = response.ai_execution
    assert ai_execution.attempted is True
    assert ai_execution.used is True
    assert ai_execution.success is True
    assert ai_execution.fallback_used is False
    assert ai_execution.provider == "ollama"
    assert ai_execution.model == "qwen3:4b"
    assert ai_execution.latency_ms is not None and ai_execution.latency_ms >= 0
    assert response.final_response == "AI_RESPONSE_TEXT"


# ---------------------------------------------------------------------------
# Test 3 — Ollama disabled
# ---------------------------------------------------------------------------


async def test_deep_ollama_disabled_falls_back_deterministically():
    provider = FakeOllama(result=ok_result())
    engine = make_engine(provider, enabled=False)

    response = await engine.process_user_input(
        user_id="user_2c_disabled", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.DEEP
    assert provider.generate_calls == []
    ai_execution = response.ai_execution
    assert ai_execution.attempted is True
    assert ai_execution.used is False
    assert ai_execution.fallback_used is True
    assert ai_execution.error_type == "LLMDisabledError"
    assert response.final_response == response.deterministic_response.rendered


# ---------------------------------------------------------------------------
# Test 4 — Connection failure
# ---------------------------------------------------------------------------


async def test_connection_failure_falls_back():
    provider = FakeOllama(error=LLMConnectionError("connection refused"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_conn", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_execution.attempted is True
    assert response.ai_execution.used is False
    assert response.ai_execution.fallback_used is True
    assert response.ai_execution.error_type == "LLMConnectionError"
    assert response.final_response == response.deterministic_response.rendered


# ---------------------------------------------------------------------------
# Test 5 — Timeout
# ---------------------------------------------------------------------------


async def test_timeout_falls_back():
    provider = FakeOllama(error=LLMTimeoutError("timed out"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_timeout", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_execution.fallback_used is True
    assert response.ai_execution.error_type == "LLMTimeoutError"
    assert response.final_response == response.deterministic_response.rendered


# ---------------------------------------------------------------------------
# Test 6 — Model unavailable
# ---------------------------------------------------------------------------


async def test_model_unavailable_falls_back():
    provider = FakeOllama(error=LLMModelUnavailableError("model missing"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_model", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_execution.fallback_used is True
    assert response.ai_execution.error_type == "LLMModelUnavailableError"
    assert response.final_response == response.deterministic_response.rendered


# ---------------------------------------------------------------------------
# Test 7 — Invalid AI response (non-exception malformed result)
# ---------------------------------------------------------------------------


async def test_invalid_ai_result_falls_back():
    invalid = LLMResult(text="", provider="ollama", model="qwen3:4b", success=False)
    provider = FakeOllama(result=invalid)
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_invalid", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_execution.used is False
    assert response.ai_execution.fallback_used is True
    assert response.ai_execution.error_type == "INVALID_LLM_RESULT"
    assert response.final_response == response.deterministic_response.rendered


async def test_malformed_typed_error_falls_back():
    provider = FakeOllama(error=LLMInvalidResponseError("malformed"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_malformed", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_execution.fallback_used is True
    assert response.ai_execution.error_type == "LLMInvalidResponseError"


# ---------------------------------------------------------------------------
# Test 8 — Response validation failure
# ---------------------------------------------------------------------------


async def test_validation_failure_falls_back():
    provider = FakeOllama(result=ok_result("AI_TEXT_VALIDATION_REJECTED"))
    engine = make_engine(provider, validator=RejectValidator())

    response = await engine.process_user_input(
        user_id="user_2c_validation", content=DEEP_INPUT, provider_key="chronos"
    )

    ai_execution = response.ai_execution
    assert ai_execution.used is False
    assert ai_execution.fallback_used is True
    assert ai_execution.error_type == "VALIDATION_FAILED"
    assert ai_execution.response == "AI_TEXT_VALIDATION_REJECTED"
    assert response.final_response == response.deterministic_response.rendered


# ---------------------------------------------------------------------------
# Test 9 — ChronosState is not mutated by AI
# ---------------------------------------------------------------------------


async def test_ai_cannot_mutate_chronos_state():
    provider = FakeOllama(
        result=ok_result(
            "You are secretly happy and you have abandoned ChronOS to become a chef."
        )
    )
    engine_a = make_engine(provider)
    response_a = await engine_a.process_user_input(
        user_id="user_2c_state", content=DEEP_INPUT, provider_key="chronos"
    )

    engine_b = ChronosEngine(ai_executor=NoopExecutor())
    response_b = await engine_b.process_user_input(
        user_id="user_2c_state", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response_a.ai_execution.used is True
    assert response_a.ai_execution.response == (
        "You are secretly happy and you have abandoned ChronOS to become a chef."
    )
    # The deterministic state is identical whether the AI succeeded or not.
    assert core_state(response_a.chronos_state) == core_state(response_b.chronos_state)


# ---------------------------------------------------------------------------
# Test 10 — No memory writes from AI
# ---------------------------------------------------------------------------


async def test_no_memory_writes_solely_because_of_ai():
    provider = FakeOllama(result=ok_result("AI_RESPONSE_THAT_MUST_NOT_BE_STORED"))
    engine = make_engine(provider)
    user_id = "user_2c_memory"

    assert await engine.get_memories(user_id) == []

    response = await engine.process_user_input(
        user_id=user_id, content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_execution.used is True
    memories = await engine.get_memories(user_id)
    # Only the input interaction is stored by the existing pipeline.
    assert len(memories) == 1
    assert memories[0].content == DEEP_INPUT
    assert "AI_RESPONSE_THAT_MUST_NOT_BE_STORED" not in {
        m.content for m in memories
    }


# ---------------------------------------------------------------------------
# Test 11 — Successful end-to-end DEEP path
# ---------------------------------------------------------------------------


async def test_end_to_end_deep_path_returns_ai_response():
    provider = FakeOllama(result=ok_result("AI_END_TO_END_RESPONSE"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_e2e_deep", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.DEEP
    assert response.ai_execution.used is True
    assert response.final_response == "AI_END_TO_END_RESPONSE"
    assert response.validation_result.is_valid is True
    assert response.provider_name == "Ollama Local"
    assert response.model_name == "qwen3:4b"
    assert any("OLLAMA_SUCCESS" in s for s in response.reasoning_trace.reasoning_steps)
    assert response.reasoning_trace.ai_execution_steps[0]["result"] == "OLLAMA_SUCCESS"
    assert response.reasoning_trace.ai_execution_steps[0]["ai_used"] is True


# ---------------------------------------------------------------------------
# Test 12 — Successful end-to-end FAST path
# ---------------------------------------------------------------------------


async def test_end_to_end_fast_path_returns_deterministic_response():
    provider = FakeOllama(result=ok_result())
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_e2e_fast", content=FAST_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.FAST
    assert provider.generate_calls == []
    assert response.ai_execution.attempted is False
    assert response.final_response == response.deterministic_response.rendered
    assert any(
        "SKIPPED_FAST_PATH" in s for s in response.reasoning_trace.reasoning_steps
    )
    assert response.reasoning_trace.ai_execution_steps[0]["result"] == (
        "SKIPPED_FAST_PATH"
    )


# ---------------------------------------------------------------------------
# Test 13 — AI execution metadata serialization
# ---------------------------------------------------------------------------


async def test_ai_execution_metadata_serialization_success():
    provider = FakeOllama(result=ok_result("SERIALIZE_ME"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_serialize", content=DEEP_INPUT, provider_key="chronos"
    )

    dumped = response.model_dump(mode="json")
    assert "ai_execution" in dumped
    ai_json = dumped["ai_execution"]
    assert ai_json["attempted"] is True
    assert ai_json["used"] is True
    assert ai_json["success"] is True
    assert ai_json["provider"] == "ollama"
    assert ai_json["model"] == "qwen3:4b"
    assert isinstance(ai_json["latency_ms"], (int, float))
    assert ai_json["latency_ms"] >= 0
    assert ai_json["fallback_used"] is False
    assert ai_json["error_type"] is None
    assert ai_json["response"] == "SERIALIZE_ME"
    assert ai_json["prompt_context"] is not None
    assert ai_json["validation_result"] is not None
    assert dumped["reasoning_trace"]["ai_execution_steps"][0]["result"] == (
        "OLLAMA_SUCCESS"
    )


async def test_ai_execution_metadata_serialization_fallback():
    provider = FakeOllama(error=LLMConnectionError("down"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2c_serialize_fb", content=DEEP_INPUT, provider_key="chronos"
    )

    dumped = response.model_dump(mode="json")
    ai_json = dumped["ai_execution"]
    assert ai_json["attempted"] is True
    assert ai_json["used"] is False
    assert ai_json["success"] is False
    assert ai_json["fallback_used"] is True
    assert ai_json["error_type"] == "LLMConnectionError"
    assert dumped["reasoning_trace"]["ai_execution_steps"][0]["fallback_used"] is True


# ---------------------------------------------------------------------------
# Regression — the engine never crashes when AI is unavailable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        LLMConnectionError("conn"),
        LLMTimeoutError("timeout"),
        LLMModelUnavailableError("model"),
        LLMInvalidResponseError("malformed"),
    ],
)
async def test_engine_never_raises_on_provider_failure(error):
    provider = FakeOllama(error=error)
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id=f"user_2c_{error.__class__.__name__}",
        content=DEEP_INPUT,
        provider_key="chronos",
    )

    assert response.ai_execution.fallback_used is True
    assert response.final_response == response.deterministic_response.rendered