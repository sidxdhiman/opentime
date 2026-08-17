"""Phase 2B tests: real Ollama HTTP provider.

The OllamaProvider talks to a local Ollama instance over its HTTP API. These
tests use ``httpx.MockTransport`` so no real Ollama installation is required —
they run identically on machines where Ollama is not installed.

Key properties verified:

* Successful generation returns a structured ``LLMResult`` with provider/model
  metadata and measured latency.
* Connection failures, timeouts, missing models and malformed responses raise
  typed errors — never application crashes.
* The provider is registered in ``LLMRegistry`` under ``"ollama"`` but is NOT
  the default provider.
* Configuration values (base_url, model, timeout, enabled) load correctly from
  the ``OLLAMA_*`` environment.
"""

import json

import httpx
import pytest

from chronos_engine.config import OllamaConfig
from chronos_engine.core.models import PromptContext, RetrievedContext, UserInput
from chronos_engine.llm import LLMRegistry, OllamaProvider
from chronos_engine.llm.errors import (
    LLMConnectionError,
    LLMDisabledError,
    LLMInvalidResponseError,
    LLMModelUnavailableError,
    LLMTimeoutError,
)


def make_prompt() -> PromptContext:
    return PromptContext(
        current_input=UserInput(id="in_2b", user_id="user_2b", content="Hello"),
        retrieved_context=RetrievedContext(),
        system_prompt="system prompt",
        user_prompt="user prompt",
    )


def make_provider(
    handler,
    *,
    enabled: bool = True,
    model: str = "qwen3:4b",
) -> OllamaProvider:
    config = OllamaConfig(
        base_url="http://ollama:11434",
        model=model,
        timeout=2.0,
        enabled=enabled,
    )
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, timeout=2.0)
    return OllamaProvider(config=config, client=client)


def ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"model": "qwen3:4b", "response": "CHRONOS_OLLAMA_OK", "done": True},
    )


# ---------------------------------------------------------------------------
# Test 1 — Successful generation
# ---------------------------------------------------------------------------


async def test_successful_generation():
    provider = make_provider(ok_handler)

    result = await provider.generate(make_prompt())

    assert result.success is True
    assert result.provider == "ollama"
    assert result.model == "qwen3:4b"
    assert result.text == "CHRONOS_OLLAMA_OK"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


async def test_generate_response_returns_plain_text():
    provider = make_provider(ok_handler)

    text = await provider.generate_response(make_prompt())

    assert text == "CHRONOS_OLLAMA_OK"


# ---------------------------------------------------------------------------
# Test 2 — Connection failure
# ---------------------------------------------------------------------------


def connection_refused_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused")


async def test_connection_failure_raises_typed_error():
    provider = make_provider(connection_refused_handler)

    with pytest.raises(LLMConnectionError):
        await provider.generate(make_prompt())


# ---------------------------------------------------------------------------
# Test 3 — Timeout
# ---------------------------------------------------------------------------


def timeout_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("read timed out")


async def test_timeout_raises_typed_error():
    provider = make_provider(timeout_handler)

    with pytest.raises(LLMTimeoutError):
        await provider.generate(make_prompt())


# ---------------------------------------------------------------------------
# Test 4 — Model unavailable
# ---------------------------------------------------------------------------


def model_not_found_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(404, json={"error": "model 'qwen3:4b' not found"})


async def test_model_unavailable_raises_typed_error():
    provider = make_provider(model_not_found_handler)

    with pytest.raises(LLMModelUnavailableError) as exc_info:
        await provider.generate(make_prompt())

    assert "qwen3:4b" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 5 — Malformed response
# ---------------------------------------------------------------------------


def malformed_json_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=b"not-json", headers={"content-type": "application/json"})


def missing_text_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"model": "qwen3:4b", "done": True})


async def test_malformed_json_raises_typed_error():
    provider = make_provider(malformed_json_handler)

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate(make_prompt())


async def test_missing_generated_text_raises_typed_error():
    provider = make_provider(missing_text_handler)

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate(make_prompt())


# ---------------------------------------------------------------------------
# Test 6 — Registry resolution
# ---------------------------------------------------------------------------


def test_registry_resolves_ollama():
    registry = LLMRegistry()

    provider = registry.get_provider("ollama")

    assert isinstance(provider, OllamaProvider)
    assert registry.get_provider() is not provider  # default is NOT ollama
    assert registry.get_provider().provider_name() == "ChronOS Native Engine Model"


# ---------------------------------------------------------------------------
# Test 7 — Disabled configuration
# ---------------------------------------------------------------------------


async def test_disabled_provider_refuses_generation():
    provider = make_provider(ok_handler, enabled=False)

    with pytest.raises(LLMDisabledError):
        await provider.generate(make_prompt())


def test_disabled_by_default_in_registry(monkeypatch):
    monkeypatch.delenv("OLLAMA_ENABLED", raising=False)
    provider = OllamaProvider()

    assert provider.config.enabled is False


# ---------------------------------------------------------------------------
# Test 7b — Prompt payload: safety system prompt is always sent
# ---------------------------------------------------------------------------


def capturing_ok_handler(request: httpx.Request, captured: dict) -> httpx.Response:
    captured["json"] = json.loads(request.content)
    return httpx.Response(
        200,
        json={"model": "qwen3:4b", "response": "CHRONOS_OLLAMA_OK", "done": True},
    )


async def test_generation_sends_full_prompt_with_safety_instructions():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return capturing_ok_handler(request, captured)

    provider = make_provider(handler)
    await provider.generate(make_prompt())

    sent = captured["json"]["prompt"]
    assert sent == "system prompt\n\nuser prompt"
    assert "system prompt" in sent
    assert "user prompt" in sent


async def test_generation_omits_options_by_default():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return capturing_ok_handler(request, captured)

    provider = make_provider(handler)
    await provider.generate(make_prompt())

    assert "options" not in captured["json"]
    assert "format" not in captured["json"]


async def test_generation_sends_format_json_when_configured():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return capturing_ok_handler(request, captured)

    config = OllamaConfig(
        base_url="http://ollama:11434",
        model="qwen3:4b",
        timeout=2.0,
        enabled=True,
        format_json=True,
    )
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, timeout=2.0)
    provider = OllamaProvider(config=config, client=client)
    await provider.generate(make_prompt())

    assert captured["json"]["format"] == "json"


async def test_generation_sends_configured_options():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return capturing_ok_handler(request, captured)

    config = OllamaConfig(
        base_url="http://ollama:11434",
        model="qwen3:4b",
        timeout=2.0,
        enabled=True,
        temperature=0.7,
        num_ctx=4096,
        num_predict=256,
    )
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, timeout=2.0)
    provider = OllamaProvider(config=config, client=client)
    await provider.generate(make_prompt())

    assert captured["json"]["options"] == {
        "temperature": 0.7,
        "num_ctx": 4096,
        "num_predict": 256,
    }


# ---------------------------------------------------------------------------
# Test 8 — Configuration loading
# ---------------------------------------------------------------------------


def test_configuration_defaults():
    config = OllamaConfig(
        base_url="http://localhost:11434",
        model="llama3:latest",
        timeout=60.0,
        enabled=False,
    )

    assert config.base_url == "http://localhost:11434"
    assert config.model == "llama3:latest"
    assert config.timeout == 60.0
    assert config.enabled is False


def test_configuration_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "5.5")
    monkeypatch.setenv("OLLAMA_ENABLED", "true")

    config = OllamaConfig()

    assert config.base_url == "http://127.0.0.1:11435"
    assert config.model == "qwen3:4b"
    assert config.timeout == 5.5
    assert config.enabled is True


def test_generation_options_load_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_TEMPERATURE", "0.4")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "8192")
    monkeypatch.setenv("OLLAMA_NUM_PREDICT", "128")

    config = OllamaConfig()

    assert config.temperature == 0.4
    assert config.num_ctx == 8192
    assert config.num_predict == 128


def test_generation_options_default_to_none():
    config = OllamaConfig()
    assert config.temperature is None
    assert config.num_ctx is None
    assert config.num_predict is None
    assert config.format_json is False


def test_format_json_loads_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORMAT_JSON", "true")

    config = OllamaConfig()

    assert config.format_json is True


# ---------------------------------------------------------------------------
# Health check (cheap /api/tags, no generation)
# ---------------------------------------------------------------------------


def tags_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/api/tags"
    return httpx.Response(
        200,
        json={"models": [{"name": "qwen3:4b", "model": "qwen3:4b"}]},
    )


async def test_health_check_available():
    provider = make_provider(tags_handler)

    health = await provider.health_check()

    assert health["reachable"] is True
    assert health["model_available"] is True
    assert health["model"] == "qwen3:4b"


async def test_health_check_unreachable():
    provider = make_provider(connection_refused_handler)

    health = await provider.health_check()

    assert health["reachable"] is False
    assert health["model_available"] is False
