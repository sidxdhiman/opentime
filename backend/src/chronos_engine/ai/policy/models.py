"""Inference-policy models: tiers, latency classes, model capabilities.

Phase 2H: deterministic inference tiering for the ChronOS Engine.

``InferencePolicyDecision`` is what ``InferencePolicy`` returns for one
interaction. ``ModelCapability`` is a lightweight, honest description of a
locally installed model — unknown values stay ``None`` (they are never
fabricated). ``InferenceTier`` and ``LatencyClass`` are the deterministic
vocabulary the policy reasons with.

These models intentionally do not import ``chronos_engine.core.models`` so the
policy package stays out of the deferred-import cycle (same pattern as
``routing.models`` / ``ai.models``).
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class InferenceTier(StrEnum):
    """Which execution tier the policy selects for one interaction.

    * ``NONE``  — no AI inference is justified (FAST path, AI disabled, or no
      available model can meet the requested constraints).
    * ``LIGHT`` — a small, fast local model is sufficient.
    * ``DEEP``  — the capable local model is required.
    """

    NONE = "NONE"
    LIGHT = "LIGHT"
    DEEP = "DEEP"


class LatencyClass(StrEnum):
    """Coarse expected-latency class — a policy expectation, never a promise.

    * ``NONE`` — no inference will happen.
    * ``LOW``  — a lightweight model; expected to fit a tight budget.
    * ``HIGH`` — the capable model; longer generation is expected and allowed.
    """

    NONE = "NONE"
    LOW = "LOW"
    HIGH = "HIGH"


class ModelCapability(BaseModel):
    """Lightweight, honest capability metadata for one installed model.

    Only the identity pair ``provider``/``model`` is required. Every other
    value defaults to ``None`` when unknown — the policy treats ``None`` as
    "unknown" and never assumes a fabricated value.
    """

    provider: str
    model: str
    parameter_count: float | None = None  # billions of parameters (4.0 = 4B)
    quantization: str | None = None  # e.g. "Q4_K_M"
    estimated_memory_gb: float | None = None  # runtime memory estimate, if known
    disk_size_gb: float | None = None  # on-disk size, if known
    context_length: int | None = None  # max context tokens, if known
    supports_json: bool | None = None  # structured JSON output support
    supports_thinking: bool | None = None  # thinking-channel support
    tier: str | None = None  # optional pre-assigned tier label (LIGHT / DEEP)


class InferencePolicyDecision(BaseModel):
    """Deterministic output of the inference policy for one interaction.

    ``provider``/``model`` name the model the policy *would* use. They are a
    policy record — recording them never changes which model is actually
    invoked (execution stays on the configured DEEP model this phase).

    ``light_requested`` is ``True`` when the plan preferred a lightweight
    model but none was available, so the AI executor can later distinguish
    "LIGHT requested but unavailable" from "AI disabled".
    """

    tier: InferenceTier
    provider: str | None = None
    model: str | None = None
    reason: str
    confidence: float
    expected_latency_class: LatencyClass = LatencyClass.NONE
    latency_budget: float | None = None
    light_requested: bool = False
    signals: list[str] = Field(default_factory=list)