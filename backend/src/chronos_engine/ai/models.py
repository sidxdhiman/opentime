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


# Deferred imports: see module docstring. PromptContext and ValidationResult
# are defined above the deferred-import block in ``core.models``, so this is
# safe even while ``core.models`` is still partially initialized.
from chronos_engine.ai.reasoning.models import (  # noqa: E402
    AIReasoningResult,
    ReasoningPlan,
)
from chronos_engine.core.models import PromptContext, ValidationResult  # noqa: E402

AIExecutionResult.model_rebuild()