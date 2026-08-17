"""Real Ollama HTTP provider for the ChronOS Engine.

Connects ChronOS to a local Ollama instance over its HTTP API. The provider
is fully offline-capable: when Ollama is unavailable it raises typed provider
errors instead of crashing the engine, and it never hangs indefinitely.

The provider is DISABLED by default (``OLLAMA_ENABLED=false``) and reads all
connection settings from ``OllamaConfig``. It is model-agnostic: the model
name comes from configuration (``OLLAMA_MODEL``), never hard-coded.
"""

import time
from typing import Optional

import httpx

from chronos_engine.config.ollama import OllamaConfig
from chronos_engine.core.interfaces import BaseLLMProvider
from chronos_engine.core.models import PromptContext
from chronos_engine.llm.errors import (
    LLMConnectionError,
    LLMDisabledError,
    LLMInvalidResponseError,
    LLMModelUnavailableError,
    LLMTimeoutError,
)
from chronos_engine.llm.result import LLMResult


class OllamaProvider(BaseLLMProvider):
    """A real Ollama provider speaking to the local Ollama HTTP API.

    All settings come from :class:`OllamaConfig` (env-prefixed ``OLLAMA_``).
    An optional ``httpx.AsyncClient`` may be injected (e.g. a mocked client
    in tests); otherwise a shared client with connection reuse is created.
    """

    def __init__(
        self,
        config: Optional[OllamaConfig] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.config = config or OllamaConfig()
        self._client = client
        self._owns_client = client is None

    def provider_name(self) -> str:
        return "Ollama Local"

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(self.config.timeout)
            self._client = httpx.AsyncClient(timeout=timeout)
            self._owns_client = True
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate_response(self, prompt_context: PromptContext, model_name: str = "") -> str:
        result = await self.generate(prompt_context, model_name=model_name)
        return result.text

    async def generate(self, prompt_context: PromptContext, model_name: str = "") -> LLMResult:
        """Generate a response from the configured Ollama model.

        Returns a structured :class:`LLMResult` on success and raises a typed
        error (from :mod:`chronos_engine.llm.errors`) on any failure.
        """
        if not self.config.enabled:
            raise LLMDisabledError(
                "Ollama provider is disabled (OLLAMA_ENABLED=false)."
            )

        model = model_name or self.config.model
        url = f"{self.config.base_url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt_context.user_prompt,
            "stream": False,
            "format": "json",
        }

        start = time.perf_counter()
        try:
            response = await self.client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Ollama request timed out after {self.config.timeout}s."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMConnectionError(
                f"Could not reach Ollama at {self.config.base_url}: {exc.__class__.__name__}."
            ) from exc
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)

        if response.status_code == 404:
            raise LLMModelUnavailableError(
                f"Model '{model}' is not available on Ollama."
            )
        if response.status_code != 200:
            raise LLMInvalidResponseError(
                f"Ollama returned HTTP {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMInvalidResponseError("Ollama returned malformed JSON.") from exc

        text = data.get("response")
        if not isinstance(text, str) or not text.strip():
            raise LLMInvalidResponseError(
                "Ollama response is missing the generated text."
            )

        return LLMResult(
            text=text,
            provider="ollama",
            model=model,
            latency_ms=latency_ms,
            success=True,
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> dict:
        """Check whether Ollama is reachable and the configured model exists.

        Uses the cheaper ``/api/tags`` list endpoint rather than generating.
        Returns a structured dict:

        ``{"reachable": bool, "model_available": bool, "model": str}``
        """
        model = self.config.model
        url = f"{self.config.base_url.rstrip('/')}/api/tags"
        try:
            response = await self.client.get(url)
        except (httpx.TimeoutException, httpx.HTTPError):
            return {"reachable": False, "model_available": False, "model": model}

        if response.status_code != 200:
            return {"reachable": False, "model_available": False, "model": model}

        try:
            data = response.json()
        except ValueError:
            return {"reachable": True, "model_available": False, "model": model}

        models = data.get("models", []) or []
        model_names = {m.get("name", "") for m in models}
        available = model in model_names
        return {"reachable": True, "model_available": available, "model": model}
