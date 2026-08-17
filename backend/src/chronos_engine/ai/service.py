"""AI execution orchestration for the ChronOS Engine.

The ``AIExecutor`` is the only component allowed to invoke an AI provider
(today: the ``OllamaProvider`` registered in ``LLMRegistry``). It turns a
routing decision + the structured ``ChronosState`` + the deterministic
response into either an AI result or an honest fallback.

Responsibilities (and only these):

* Build the DEEP-path prompt from deterministic state.
* Invoke the configured Ollama provider through ``LLMRegistry -> ollama``.
* Measure latency around the actual provider call — never fabricated.
* Run the existing ``ResponseValidator`` on the AI output.
* Catch every typed provider error and translate it into a structured
  ``AIExecutionResult`` with ``fallback_used=True``.

Non-responsibilities (kept out of this class by design):

* It never decides whether AI is needed — that is ``AIRouter``'s job.
* It never mutates ``ChronosState`` — the engine is the source of state.
* It never writes memory — AI memory behavior comes in a later phase.
* It never retries — retry policies are deliberately out of scope for now.
"""

import time

from chronos_engine.ai.models import AIExecutionResult
from chronos_engine.ai.prompts import ChronosAIPromptBuilder
from chronos_engine.config.ollama import OllamaConfig
from chronos_engine.core.interfaces import BaseAIExecutor, BaseResponseValidator
from chronos_engine.llm.errors import LLMProviderError
from chronos_engine.llm.providers import LLMRegistry
from chronos_engine.response.models import DeterministicResponse
from chronos_engine.state.models import ChronosState
from chronos_engine.validators.service import ResponseValidator


class AIExecutor(BaseAIExecutor):
    """Executes a DEEP routing decision through the configured AI provider."""

    def __init__(
        self,
        llm_registry: LLMRegistry = None,
        config: OllamaConfig = None,
        validator: BaseResponseValidator = None,
        prompt_builder: ChronosAIPromptBuilder = None,
    ):
        self.llm_registry = llm_registry or LLMRegistry()
        self.config = config or OllamaConfig()
        self.validator = validator or ResponseValidator()
        self.prompt_builder = prompt_builder or ChronosAIPromptBuilder()

    async def execute(
        self,
        routing_result,
        chronos_state: ChronosState,
        deterministic_response: DeterministicResponse,
    ) -> AIExecutionResult:
        """Execute the AI request for a routing decision.

        ``use_ai=False`` returns an ``attempted=False`` result without ever
        touching the provider. ``use_ai=True`` with a disabled or unavailable
        provider returns an honest ``fallback_used=True`` result — the engine
        is never allowed to crash because AI is unavailable.
        """
        if routing_result is None or not routing_result.use_ai:
            return AIExecutionResult(
                attempted=False, used=False, success=False, fallback_used=False
            )

        prompt_context = self.prompt_builder.build(chronos_state, deterministic_response)

        if not self.config.enabled:
            return AIExecutionResult(
                attempted=True,
                used=False,
                success=False,
                provider="ollama",
                model=self.config.model,
                prompt_context=prompt_context,
                fallback_used=True,
                error_type="LLMDisabledError",
            )

        provider = self.llm_registry.get_provider("ollama")
        model = self.config.model

        start = time.perf_counter()
        try:
            result = await provider.generate(prompt_context, model_name=model)
        except LLMProviderError as exc:
            return AIExecutionResult(
                attempted=True,
                used=False,
                success=False,
                provider="ollama",
                model=model,
                latency_ms=self._latency(start),
                prompt_context=prompt_context,
                fallback_used=True,
                error_type=type(exc).__name__,
            )
        latency_ms = self._latency(start)

        if not result.success:
            return AIExecutionResult(
                attempted=True,
                used=False,
                success=False,
                provider="ollama",
                model=model,
                latency_ms=latency_ms,
                response=result.text,
                prompt_context=prompt_context,
                fallback_used=True,
                error_type=result.error_type or "INVALID_LLM_RESULT",
            )

        validation = await self.validator.validate_response(result.text, prompt_context)

        if not validation.is_valid:
            return AIExecutionResult(
                attempted=True,
                used=False,
                success=False,
                provider="ollama",
                model=model,
                latency_ms=latency_ms,
                response=result.text,
                prompt_context=prompt_context,
                fallback_used=True,
                error_type="VALIDATION_FAILED",
                validation_result=validation,
            )

        return AIExecutionResult(
            attempted=True,
            used=True,
            success=True,
            provider="ollama",
            model=model,
            latency_ms=latency_ms,
            response=validation.validated_response,
            prompt_context=prompt_context,
            fallback_used=False,
            validation_result=validation,
        )

    @staticmethod
    def _latency(start: float) -> float:
        return round((time.perf_counter() - start) * 1000.0, 2)