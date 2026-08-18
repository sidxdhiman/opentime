"""AI execution orchestration for the ChronOS Engine.

The ``AIExecutor`` is the only component allowed to invoke an AI provider
(today: the ``OllamaProvider`` registered in ``LLMRegistry``). It turns a
routing decision + the structured ``ChronosState`` + the deterministic
response into either an AI result or an honest fallback.

Responsibilities (and only these):

* Build a reasoning plan and the mode-filtered DEEP-path prompt.
* Invoke the configured Ollama provider through ``LLMRegistry -> ollama``.
* Measure every stage of the DEEP path with monotonic timing — never
  fabricated (Phase 2E): reasoning planning, prompt construction, provider
  call, response parsing, response validation, and the total wall time.
* Measure the actual prompt size sent to the provider (characters) plus a
  clearly-labeled token estimate and a diagnostic context hash.
* Run the existing ``ResponseValidator`` on the AI output.
* Catch every typed provider error and translate it into a structured
  ``AIExecutionResult`` with ``fallback_used=True``.

Non-responsibilities (kept out of this class by design):

* It never decides whether AI is needed — that is ``AIRouter``'s job.
* It never mutates ``ChronosState`` — the engine is the source of state.
* It never writes memory — AI memory behavior comes in a later phase.
* It never retries — retry policies are deliberately out of scope for now.
"""

import hashlib
import time

from chronos_engine.ai.context import ContextBudget
from chronos_engine.ai.models import AIExecutionResult
from chronos_engine.ai.prompts import ChronosAIPromptBuilder
from chronos_engine.ai.reasoning.parser import AIResponseParseError, AIResponseParser
from chronos_engine.ai.reasoning.planner import ReasoningPlanner
from chronos_engine.config.ollama import OllamaConfig
from chronos_engine.core.interfaces import BaseAIExecutor, BaseResponseValidator
from chronos_engine.llm.errors import LLMProviderError
from chronos_engine.llm.inference import InferenceOptions
from chronos_engine.llm.providers import LLMRegistry
from chronos_engine.response.models import DeterministicResponse
from chronos_engine.state.models import ChronosState
from chronos_engine.validators.service import ResponseValidator


def _estimate_tokens(chars: int) -> int:
    """Deterministic token estimate (chars / 4) — an ESTIMATE, clearly labeled."""
    return max(1, round(chars / 4))


def _prompt_hash(prompt_context) -> str:
    """Short deterministic hash of the actual prompt (diagnostics only)."""
    return hashlib.sha256(prompt_context.full_prompt().encode("utf-8")).hexdigest()[:16]


class AIExecutor(BaseAIExecutor):
    """Executes a DEEP routing decision through the configured AI provider."""

    def __init__(
        self,
        llm_registry: LLMRegistry = None,
        config: OllamaConfig = None,
        validator: BaseResponseValidator = None,
        prompt_builder: ChronosAIPromptBuilder = None,
        planner: ReasoningPlanner = None,
        parser: AIResponseParser = None,
        budget: ContextBudget = None,
    ):
        self.llm_registry = llm_registry or LLMRegistry()
        self.config = config or OllamaConfig()
        self.validator = validator or ResponseValidator()
        self.prompt_builder = prompt_builder or ChronosAIPromptBuilder()
        self.planner = planner or ReasoningPlanner()
        self.parser = parser or AIResponseParser()
        self.budget = budget or ContextBudget()

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

        Exactly one provider call happens per DEEP request: the reasoning plan
        is built deterministically, the prompt targets that plan, and the
        provider's single response is parsed into the structured output
        contract before validation.
        """
        if routing_result is None or not routing_result.use_ai:
            return AIExecutionResult(
                attempted=False, used=False, success=False, fallback_used=False
            )

        total_start = time.perf_counter()

        plan_start = time.perf_counter()
        plan = self.planner.plan(chronos_state, routing_result)
        reasoning_plan_ms = self._latency(plan_start)

        inference_options = self._inference_options(plan)

        build_start = time.perf_counter()
        allowed_evidence_ids = self.prompt_builder.evidence_ids(chronos_state)
        prompt_context = self.prompt_builder.build(
            chronos_state, deterministic_response, plan, budget=self.budget
        )
        prompt_build_ms = self._latency(build_start)

        prompt_chars = len(prompt_context.full_prompt())
        prompt_tokens_estimate = _estimate_tokens(prompt_chars)
        prompt_context_hash = _prompt_hash(prompt_context)

        def result(**overrides) -> AIExecutionResult:
            fields: dict = {
                "attempted": True,
                "used": False,
                "success": False,
                "provider": "ollama",
                "model": self.config.model,
                "prompt_context": prompt_context,
                "prompt_chars": prompt_chars,
                "prompt_tokens_estimate": prompt_tokens_estimate,
                "prompt_context_hash": prompt_context_hash,
                "reasoning_plan_ms": reasoning_plan_ms,
                "prompt_build_ms": prompt_build_ms,
                "total_ai_ms": self._latency(total_start),
                "reasoning_plan": plan,
                "inference_options": inference_options,
            }
            fields.update(overrides)
            return AIExecutionResult(**fields)

        if not self.config.enabled:
            return result(fallback_used=True, error_type="LLMDisabledError")

        provider = self.llm_registry.get_provider("ollama")
        model = self.config.model

        provider_start = time.perf_counter()
        try:
            llm_result = await provider.generate(
                prompt_context,
                model_name=model,
                inference_options=inference_options,
            )
        except LLMProviderError as exc:
            provider_latency_ms = self._latency(provider_start)
            return result(
                latency_ms=provider_latency_ms,
                provider_latency_ms=provider_latency_ms,
                fallback_used=True,
                error_type=type(exc).__name__,
            )
        provider_latency_ms = self._latency(provider_start)

        if not llm_result.success:
            return result(
                latency_ms=provider_latency_ms,
                provider_latency_ms=provider_latency_ms,
                response=llm_result.text,
                fallback_used=True,
                error_type=llm_result.error_type or "INVALID_LLM_RESULT",
            )

        parse_start = time.perf_counter()
        try:
            parsed = self.parser.parse(
                llm_result.text, allowed_evidence_ids=allowed_evidence_ids
            )
        except AIResponseParseError as exc:
            parse_ms = self._latency(parse_start)
            return result(
                latency_ms=provider_latency_ms,
                provider_latency_ms=provider_latency_ms,
                parse_ms=parse_ms,
                response=llm_result.text,
                fallback_used=True,
                error_type=exc.reason,
            )
        parse_ms = self._latency(parse_start)

        validation_start = time.perf_counter()
        validation = await self.validator.validate_response(
            parsed.answer, prompt_context
        )
        validation_ms = self._latency(validation_start)

        if not validation.is_valid:
            return result(
                latency_ms=provider_latency_ms,
                provider_latency_ms=provider_latency_ms,
                parse_ms=parse_ms,
                validation_ms=validation_ms,
                response=parsed.answer,
                fallback_used=True,
                error_type="VALIDATION_FAILED",
                validation_result=validation,
                ai_reasoning=parsed,
            )

        return result(
            used=True,
            success=True,
            latency_ms=provider_latency_ms,
            provider_latency_ms=provider_latency_ms,
            parse_ms=parse_ms,
            validation_ms=validation_ms,
            response=validation.validated_response,
            fallback_used=False,
            validation_result=validation,
            ai_reasoning=parsed,
        )

    @staticmethod
    def _latency(start: float) -> float:
        return round((time.perf_counter() - start) * 1000.0, 2)

    def _inference_options(self, plan: ReasoningPlan) -> InferenceOptions:
        """Resolve per-call inference knobs from the plan + configuration.

        Mode-specific overrides (``mode_thinking_enabled`` /
        ``mode_num_predict``) take precedence over the global settings; the
        plan's ``primary_mode`` selects the override. Falls back to global
        configuration when no mode override is configured, preserving current
        behavior unless explicitly configured.
        """
        primary = plan.primary_mode.value
        return InferenceOptions(
            thinking_enabled=self.config.mode_thinking_enabled.get(
                primary, self.config.thinking_enabled
            ),
            num_predict=self.config.mode_num_predict.get(
                primary, self.config.num_predict
            ),
            num_ctx=self.config.num_ctx,
            temperature=self.config.temperature,
        )