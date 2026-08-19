"""Structured AI-execution models for the ChronOS Engine.

``AIExecutionResult`` describes what actually happened when the engine
executed the DEEP path through an AI provider (today: Ollama). Every field
must accurately represent reality — never a fabricated latency, provider, or
response.

A result can be in exactly one of three observable states:

* **Not attempted** (``attempted=False``) — the FAST path, or the executor
  was never invoked.
* **Used** (``attempted=True, used=True, success=True``) — the provider
  returned a valid, validated response that became the final output.
* **Attempted but not used** (``attempted=True, used=False``) — disabled,
  unreachable, timed out, invalid, or failed validation. ``fallback_used``
  is True in this state and the deterministic response became the final
  output.

``tier`` names the inference tier that was actually executed (``LIGHT`` /
``DEEP`` / ``NONE``) and ``provider`` / ``model`` name the actual provider and
model that were called — the executor resolves these from the
``InferencePolicy`` decision and records reality, never a fabricated target.

These models intentionally avoid importing ``chronos_engine.core.models`` at
module top: ``core.models`` defers its own cross-package imports to the end of
the module, so the deferred import below keeps this package out of that cycle
(the same pattern as ``response.models`` and ``routing.models``).
"""

from pydantic import BaseModel


class AIExecutionResult(BaseModel):
    """Structured record of one AI (DEEP-path) execution attempt."""

    attempted: bool = False
    used: bool = False
    success: bool = False
    tier: str | None = None
    provider: str | None = None
    model: str | None = None
    latency_ms: float | None = None
    response: str | None = None
    fallback_used: bool = False
    error_type: str | None = None

    prompt_context: "PromptContext | None" = None
    validation_result: "ValidationResult | None" = None

    reasoning_plan: "ReasoningPlan | None" = None
    ai_reasoning: "AIReasoningResult | None" = None

    # Resolved per-call inference knobs (thinking channel, output budget, ...).
    inference_options: "InferenceOptions | None" = None

    # Prompt sizing (measured, never fabricated). The token count is a
    # deterministic ESTIMATE (characters / 4), clearly labeled as such.
    prompt_chars: int | None = None
    prompt_tokens_estimate: int | None = None
    prompt_context_hash: str | None = None

    # Monotonic timing breakdown of the DEEP path (milliseconds).
    reasoning_plan_ms: float | None = None
    prompt_build_ms: float | None = None
    provider_latency_ms: float | None = None
    parse_ms: float | None = None
    validation_ms: float | None = None
    total_ai_ms: float | None = None

    def latency_report(self) -> dict[str, float | int | str | None]:
        """Structured latency + prompt-size breakdown for one AI attempt.

        Every value comes from an actual monotonic measurement recorded during
        execution — nothing is fabricated. ``provider_latency_ms`` falls back to
        ``latency_ms`` (which measures the same provider call) when the newer
        field was not populated.
        """
        return {
            "reasoning_plan_ms": self.reasoning_plan_ms,
            "prompt_build_ms": self.prompt_build_ms,
            "provider_latency_ms": (
                self.provider_latency_ms
                if self.provider_latency_ms is not None
                else self.latency_ms
            ),
            "parse_ms": self.parse_ms,
            "validation_ms": self.validation_ms,
            "total_ai_ms": self.total_ai_ms,
            "prompt_chars": self.prompt_chars,
            "prompt_tokens_estimate": self.prompt_tokens_estimate,
            "prompt_context_hash": self.prompt_context_hash,
        }


# Deferred imports: see module docstring. PromptContext and ValidationResult
# are defined above the deferred-import block in ``core.models``, so this is
# safe even while ``core.models`` is still partially initialized.
from chronos_engine.ai.reasoning.models import (  # noqa: E402
    AIReasoningResult,
    ReasoningPlan,
)
from chronos_engine.core.models import PromptContext, ValidationResult  # noqa: E402
from chronos_engine.llm.inference import InferenceOptions  # noqa: E402

AIExecutionResult.model_rebuild()