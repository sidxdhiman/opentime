"""Phase 2G tests: controlled local inference.

Covers the supported inference controls discovered by auditing the installed
Ollama 0.20.5 + ``qwen3:4b`` runtime:

* ``InferenceOptions`` — the model-agnostic per-call knobs assembled by the
  AI executor from the ``ReasoningPlan`` + ``OllamaConfig``.
* Thinking-channel control (``think`` request field) — verified to be the
  ONLY supported thinking control in the installed runtime; it changes the
  response channel, not the thinking-token count.
* Output-token configuration (``num_predict``) — per-mode and global.
* Timeout safety — a configured output budget can never be silently cut off
  by the client timeout.
* Parser robustness to the real Qwen3 evidence-tag shapes that previously
  rejected otherwise-valid REASON/REFLECT output (``memory:mem_x`` without
  brackets), while preserving the hallucinated-evidence guardrail.

No real Ollama installation is required: provider behavior is verified with
``httpx.MockTransport`` and the executor with a fake provider.
"""

import json

import httpx
import pytest

from chronos_engine.ai import AIExecutor
from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
from chronos_engine.ai.reasoning.parser import AIResponseParseError, AIResponseParser
from chronos_engine.config import OllamaConfig
from chronos_engine.core.models import PromptContext, RetrievedContext, UserInput
from chronos_engine.llm import InferenceOptions, LLMRegistry, OllamaProvider
from chronos_engine.llm.result import LLMResult


def make_prompt() -> PromptContext:
    return PromptContext(
        current_input=UserInput(id="in_2g", user_id="user_2g", content="Hello"),
        retrieved_context=RetrievedContext(),
        system_prompt="system prompt",
        user_prompt="user prompt",
    )


def make_provider(handler, **overrides) -> OllamaProvider:
    settings = dict(
        base_url="http://ollama:11434",
        model="qwen3:4b",
        timeout=2.0,
        enabled=True,
    )
    settings.update(overrides)
    config = OllamaConfig(**settings)
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, timeout=2.0)
    return OllamaProvider(config=config, client=client)


def capturing_handler(captured: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content)
        captured["timeout"] = request.extensions.get("timeout")
        return httpx.Response(
            200, json={"model": "qwen3:4b", "response": "OK", "done": True}
        )

    return handler


# ---------------------------------------------------------------------------
# InferenceOptions model
# ---------------------------------------------------------------------------


def test_inference_options_default_to_none():
    opts = InferenceOptions()

    assert opts.thinking_enabled is None
    assert opts.num_predict is None
    assert opts.num_ctx is None
    assert opts.temperature is None


# ---------------------------------------------------------------------------
# Configuration defaults + env loading
# ---------------------------------------------------------------------------


def test_thinking_enabled_defaults_true():
    config = OllamaConfig()

    assert config.thinking_enabled is True


def test_thinking_enabled_loads_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_THINKING_ENABLED", "false")

    config = OllamaConfig()

    assert config.thinking_enabled is False


def test_mode_overrides_load_from_env(monkeypatch):
    monkeypatch.setenv(
        "OLLAMA_MODE_NUM_PREDICT", '{"REASON": 2048, "REFLECT": 3072}'
    )
    monkeypatch.setenv("OLLAMA_MODE_THINKING_ENABLED", '{"INTERPRET": false}')

    config = OllamaConfig()

    assert config.mode_num_predict == {"REASON": 2048, "REFLECT": 3072}
    assert config.mode_thinking_enabled == {"INTERPRET": False}


def test_mode_overrides_default_empty():
    config = OllamaConfig()

    assert config.mode_num_predict == {}
    assert config.mode_thinking_enabled == {}


def test_timeout_safety_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_MIN_TOKENS_PER_SEC", "15.0")
    monkeypatch.setenv("OLLAMA_TIMEOUT_MARGIN", "45.0")

    config = OllamaConfig()

    assert config.min_tokens_per_sec == 15.0
    assert config.timeout_margin == 45.0


# ---------------------------------------------------------------------------
# Provider: think field + inference-option override of global settings
# ---------------------------------------------------------------------------


async def test_provider_sends_think_field_by_default():
    captured: dict = {}

    provider = make_provider(capturing_handler(captured))
    await provider.generate(make_prompt())

    assert captured["json"]["think"] is True


async def test_provider_sends_think_false_when_configured():
    captured: dict = {}

    provider = make_provider(capturing_handler(captured))
    await provider.generate(
        make_prompt(), inference_options=InferenceOptions(thinking_enabled=False)
    )

    assert captured["json"]["think"] is False


async def test_inference_options_override_global_generation_options():
    captured: dict = {}

    provider = make_provider(
        capturing_handler(captured), num_predict=256, num_ctx=4096, temperature=0.7
    )
    await provider.generate(
        make_prompt(),
        inference_options=InferenceOptions(num_predict=512),
    )

    assert captured["json"]["options"] == {
        "num_predict": 512,
        "num_ctx": 4096,
        "temperature": 0.7,
    }


# ---------------------------------------------------------------------------
# Timeout safety: budget-derived effective timeout
# ---------------------------------------------------------------------------


async def test_effective_timeout_covers_output_budget():
    captured: dict = {}
    # 4096-token budget at the conservative 10 tok/s floor = 409.6s + 30s margin.
    provider = make_provider(
        capturing_handler(captured),
        timeout=2.0,
        min_tokens_per_sec=10.0,
        timeout_margin=30.0,
    )
    await provider.generate(
        make_prompt(), inference_options=InferenceOptions(num_predict=4096)
    )

    timeout = captured["timeout"]
    assert timeout["read"] >= 439.0


async def test_timeout_untouched_without_budget():
    captured: dict = {}

    provider = make_provider(capturing_handler(captured), timeout=2.0)
    await provider.generate(make_prompt())

    timeout = captured["timeout"]
    assert timeout["read"] == 2.0


# ---------------------------------------------------------------------------
# Mode-specific inference policy: ReasoningPlan -> InferenceOptions
# ---------------------------------------------------------------------------


def test_executor_resolves_mode_specific_inference_options():
    config = OllamaConfig(
        base_url="http://ollama:11434",
        model="qwen3:4b",
        timeout=2.0,
        enabled=True,
        thinking_enabled=True,
        num_ctx=4096,
        temperature=0.4,
        mode_num_predict={"REASON": 2048, "REFLECT": 3072},
        mode_thinking_enabled={"INTERPRET": False},
    )
    executor = AIExecutor(config=config, llm_registry=LLMRegistry())

    reason_plan = ReasoningPlan(
        modes=[ReasoningMode.REASON, ReasoningMode.GENERATE],
        primary_mode=ReasoningMode.REASON,
        reason="r",
        confidence=0.6,
    )
    opts = executor._inference_options(reason_plan)
    assert opts.num_predict == 2048
    assert opts.thinking_enabled is True  # REASON has no thinking override -> global True
    assert opts.num_ctx == 4096
    assert opts.temperature == 0.4

    reflect_plan = ReasoningPlan(
        modes=[ReasoningMode.REFLECT, ReasoningMode.GENERATE],
        primary_mode=ReasoningMode.REFLECT,
        reason="r",
        confidence=0.6,
        requires_history=True,
    )
    assert executor._inference_options(reflect_plan).num_predict == 3072

    interpret_plan = ReasoningPlan(
        modes=[ReasoningMode.INTERPRET, ReasoningMode.GENERATE],
        primary_mode=ReasoningMode.INTERPRET,
        reason="r",
        confidence=0.6,
    )
    opts = executor._inference_options(interpret_plan)
    assert opts.thinking_enabled is False
    assert opts.num_predict is None  # INTERPRET has no budget -> global (None)


def test_executor_falls_back_to_global_when_no_mode_override():
    config = OllamaConfig(
        base_url="http://ollama:11434",
        model="qwen3:4b",
        timeout=2.0,
        enabled=True,
        num_predict=768,
    )
    executor = AIExecutor(config=config, llm_registry=LLMRegistry())

    plan = ReasoningPlan(
        modes=[ReasoningMode.REASON, ReasoningMode.GENERATE],
        primary_mode=ReasoningMode.REASON,
        reason="r",
        confidence=0.6,
    )
    opts = executor._inference_options(plan)

    assert opts.num_predict == 768  # global value, mode overrides empty


async def test_executor_passes_inference_options_to_provider():
    received: dict = {}

    class CaptureProvider:
        def provider_name(self) -> str:
            return "Ollama Local"

        async def generate(self, prompt_context, model_name="", inference_options=None):
            received["options"] = inference_options
            return LLMResult(
                text=json.dumps(
                    {
                        "interpretation": None,
                        "reasoning": "r",
                        "reflection": None,
                        "answer": "A",
                        "uncertainties": [],
                        "evidence_used": [],
                    }
                ),
                provider="ollama",
                model="qwen3:4b",
                latency_ms=1.0,
                success=True,
            )

        async def generate_response(self, prompt_context, model_name=""):
            return ""

    config = OllamaConfig(
        base_url="http://ollama:11434",
        model="qwen3:4b",
        timeout=2.0,
        enabled=True,
        num_predict=4321,
    )
    registry = LLMRegistry()
    registry.register_provider("ollama", CaptureProvider())
    executor = AIExecutor(llm_registry=registry, config=config)

    from chronos_engine.response.models import ChronosInterpretation, DeterministicResponse
    from chronos_engine.routing import RoutingPath
    from chronos_engine.state.models import ChronosState, EngineStateResult
    from chronos_engine.routing.models import AIRoutingResult

    state = ChronosState(
        id="state_2g",
        user_id="user_2g",
        current_input=UserInput(id="in_2g", user_id="user_2g", content="input"),
    )
    routing = AIRoutingResult(
        use_ai=True, path=RoutingPath.DEEP, confidence=0.8, reason="test"
    )
    deterministic = DeterministicResponse(
        user_signal="input",
        chronos_interpretation=ChronosInterpretation(
            user_state_summary="n",
            intent_summary="n",
            context_summary="n",
        ),
        chronos_state=EngineStateResult(),
        rendered="deterministic",
    )
    await executor.execute(routing, state, deterministic)

    assert received["options"] is not None
    assert received["options"].num_predict == 4321
    assert received["options"].thinking_enabled is True


# ---------------------------------------------------------------------------
# Parser robustness to real Qwen3 evidence-tag shapes (root cause of the
# Phase 2F REASON/REFLECT failures: evidence emitted as ``memory:mem_x``
# without brackets, or with brackets, mixed within the same response).
# ---------------------------------------------------------------------------


def test_parser_accepts_real_qwen3_evidence_formats():
    parser = AIResponseParser()
    text = json.dumps(
        {
            "interpretation": None,
            "reasoning": "r",
            "reflection": None,
            "answer": "A",
            "uncertainties": [],
            "evidence_used": [
                "memory:mem_x",
                "[memory:mem_y]",
                "[timeline:evt_z]",
                "pattern:p1",
            ],
        }
    )

    result = parser.parse(text, allowed_evidence_ids={"mem_x", "mem_y", "evt_z", "p1"})

    assert result.answer == "A"


def test_parser_accepts_bare_evidence_ids():
    parser = AIResponseParser()
    text = json.dumps(
        {
            "interpretation": None,
            "reasoning": "r",
            "reflection": None,
            "answer": "A",
            "uncertainties": [],
            "evidence_used": ["mem_x", "[mem_y]"],
        }
    )

    result = parser.parse(text, allowed_evidence_ids={"mem_x", "mem_y"})

    assert result.answer == "A"


def test_parser_still_rejects_fabricated_evidence():
    parser = AIResponseParser()
    text = json.dumps(
        {
            "interpretation": None,
            "reasoning": "r",
            "reflection": None,
            "answer": "A",
            "uncertainties": [],
            "evidence_used": ["memory:fake_999", "[memory:mem_real]"],
        }
    )

    with pytest.raises(AIResponseParseError) as exc_info:
        parser.parse(text, allowed_evidence_ids={"mem_real"})

    assert exc_info.value.reason == "HALLUCINATED_EVIDENCE"