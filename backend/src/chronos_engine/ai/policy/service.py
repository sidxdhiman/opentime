"""Deterministic inference policy for the ChronOS Engine (Phase 2H).

The ``InferencePolicy`` answers one question:

    "For this routed interaction, which local model tier should be used?"

It is pure, deterministic computation over:

* the ``AIRoutingResult`` (FAST vs DEEP),
* the ``ReasoningPlan`` (which reasoning modes are engaged),
* the configured ``OllamaConfig`` (DEEP model + light-model thresholds),
* an optional catalog of installed ``ModelCapability`` entries,
* an optional latency budget.

It NEVER invokes a provider — model selection lives here, while
``OllamaProvider`` stays responsible only for HTTP / generation / health /
errors.

Current execution is NOT changed by the policy: FAST still returns the
deterministic response and DEEP still calls the configured DEEP model. The
policy decision is only recorded (``EngineResponse.inference_policy``) and
tested independently.

Deterministic rules (evaluated in order):

1. AI disabled (``OLLAMA_ENABLED=false``)          -> NONE.
2. ``use_ai=False`` (FAST)                          -> NONE.
3. Plan engages REASON or REFLECT                   -> DEEP (capable model
   required). A tight latency budget does not downgrade DEEP: higher latency
   is allowed for the capable model.
4. Otherwise (INTERPRET / CLASSIFY / GENERATE-only) -> LIGHT when a suitable
   lightweight model is configured (``OLLAMA_LIGHT_MODEL``) and installed;
   otherwise the policy falls back to DEEP with ``light_requested=True``.
5. A latency budget below the light-model threshold with no light model
   available means no available model can be expected to fit -> NONE.

Tier is derived from the plan's reasoning modes, which are themselves derived
deterministically from the state — never from emotion alone or prompt length.
"""

from chronos_engine.ai.policy.models import (
    InferencePolicyDecision,
    InferenceTier,
    LatencyClass,
    ModelCapability,
)
from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
from chronos_engine.config.ollama import OllamaConfig
from chronos_engine.routing.models import AIRoutingResult

# Deterministic confidence constants (documented policy defaults).
CONFIDENCE_NONE: float = 1.0
CONFIDENCE_LIGHT: float = 0.88
CONFIDENCE_DEEP: float = 0.94
CONFIDENCE_LIGHT_UNAVAILABLE: float = 1.0

# Modes that always require the capable (DEEP) model.
_DEEP_REASONING_MODES = frozenset({ReasoningMode.REASON, ReasoningMode.REFLECT})

# The only local provider today. The policy remains provider-keyed so a second
# provider can be added without touching the rules.
_LIGHT_PROVIDER = "ollama"


def capabilities_from_config(config: OllamaConfig) -> list[ModelCapability]:
    """Config-driven capability catalog for the DEEP + LIGHT models.

    Each configured model becomes a ``ModelCapability`` entry with the
    configured tier label. Metadata is intentionally NOT fabricated: parameter
    count, memory, context, and JSON/thinking support stay ``None`` unless a
    future phase verifies them against an installed model. The policy treats
    ``None`` as "unknown" and only disqualifies a model on definite evidence,
    so a configured LIGHT model still qualifies.
    """
    caps: list[ModelCapability] = []
    if config.model:
        caps.append(
            ModelCapability(provider=_LIGHT_PROVIDER, model=config.model, tier="DEEP")
        )
    if config.light_model and config.light_model != config.model:
        caps.append(
            ModelCapability(
                provider=_LIGHT_PROVIDER, model=config.light_model, tier="LIGHT"
            )
        )
    return caps


class InferencePolicy:
    """Deterministic local-model tier selection for one interaction."""

    def __init__(
        self,
        config: OllamaConfig | None = None,
        available_models: list[ModelCapability] | None = None,
    ):
        self.config = config or OllamaConfig()
        self.available_models = list(available_models or [])

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def decide(
        self,
        routing_result: AIRoutingResult | None = None,
        plan: ReasoningPlan | None = None,
        chronos_state=None,
        latency_budget: float | None = None,
    ) -> InferencePolicyDecision:
        """Select the tier/model for one interaction (never invokes a provider).

        ``chronos_state`` is accepted for future state-driven rules; the
        current deterministic rules derive the tier from the routing result
        and the reasoning plan.
        """
        if not self.config.enabled:
            return InferencePolicyDecision(
                tier=InferenceTier.NONE,
                reason="AI inference is disabled; no provider is available.",
                confidence=CONFIDENCE_NONE,
                expected_latency_class=LatencyClass.NONE,
                latency_budget=latency_budget,
                signals=["ai disabled"],
            )

        if routing_result is None or not routing_result.use_ai:
            return InferencePolicyDecision(
                tier=InferenceTier.NONE,
                reason="The FAST path is fully handled by the deterministic engine.",
                confidence=(
                    routing_result.confidence if routing_result else CONFIDENCE_NONE
                ),
                expected_latency_class=LatencyClass.NONE,
                latency_budget=latency_budget,
                signals=["fast path"],
            )

        if self._requires_deep(plan):
            return self._deep_decision(
                plan=plan,
                latency_budget=latency_budget,
                deep_required=True,
            )

        light = self._suitable_light_model()
        if (
            latency_budget is not None
            and latency_budget < self.config.light_max_latency_seconds
            and light is None
        ):
            # Only the capable model exists, and it cannot be expected to
            # complete within the requested budget.
            return InferencePolicyDecision(
                tier=InferenceTier.NONE,
                reason=(
                    "No available model can be expected to meet the requested "
                    "latency budget."
                ),
                confidence=CONFIDENCE_NONE,
                expected_latency_class=LatencyClass.NONE,
                latency_budget=latency_budget,
                light_requested=True,
                signals=[
                    "light requested",
                    "no light model",
                    "latency budget too tight",
                ],
            )

        if light is not None:
            return InferencePolicyDecision(
                tier=InferenceTier.LIGHT,
                provider=light.provider,
                model=light.model,
                reason="Interpretation does not require deep historical reasoning.",
                confidence=CONFIDENCE_LIGHT,
                expected_latency_class=LatencyClass.LOW,
                latency_budget=latency_budget,
                signals=["light requested", "light model available"],
            )

        # No lightweight model installed -> fall back to the capable model.
        return self._deep_decision(
            plan=plan,
            latency_budget=latency_budget,
            deep_required=False,
        )

    # ------------------------------------------------------------------
    # Deterministic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _requires_deep(plan: ReasoningPlan | None) -> bool:
        if plan is None:
            return False
        return bool(_DEEP_REASONING_MODES.intersection(plan.modes))

    def _deep_decision(
        self,
        plan: ReasoningPlan | None,
        latency_budget: float | None,
        deep_required: bool,
    ) -> InferencePolicyDecision:
        if deep_required:
            reason = (
                "The plan requires analytical or reflective reasoning beyond "
                "a lightweight model."
            )
            confidence = CONFIDENCE_DEEP
            signals = ["plan requires capable model"]
            light_requested = False
        else:
            reason = "No lightweight local model is available."
            confidence = CONFIDENCE_LIGHT_UNAVAILABLE
            signals = ["light requested", "no light model"]
            light_requested = True
        return InferencePolicyDecision(
            tier=InferenceTier.DEEP,
            provider="ollama",
            model=self.config.model,
            reason=reason,
            confidence=confidence,
            expected_latency_class=LatencyClass.HIGH,
            latency_budget=latency_budget,
            light_requested=light_requested,
            signals=signals,
        )

    def _suitable_light_model(self) -> ModelCapability | None:
        """The configured light model, if it is installed and passes criteria.

        Requires ``OLLAMA_LIGHT_MODEL`` to be set and distinct from the DEEP
        model. Capability metadata is used as a refinement, not a hard-coded
        model name.
        """
        target = self.config.light_model
        if not target or target == self.config.model:
            return None
        for cap in self.available_models:
            if cap.provider != _LIGHT_PROVIDER:
                continue
            if cap.model != target:
                continue
            if not self._passes_light_criteria(cap):
                return None
            return cap
        return None

    def _passes_light_criteria(self, cap: ModelCapability) -> bool:
        """Whether a model qualifies as a LIGHT candidate.

        Unknown values are tolerated (treated as "not provably disqualified");
        a definite ``False`` / too-large value disqualifies the model. The
        thresholds are configurable on ``OllamaConfig``.
        """
        if (
            cap.parameter_count is not None
            and cap.parameter_count > self.config.light_max_parameters
        ):
            return False
        if cap.estimated_memory_gb is not None:
            headroom = min(
                self.config.light_max_memory_gb, self.config.available_vram_gb
            )
            if cap.estimated_memory_gb > headroom:
                return False
        if (
            cap.context_length is not None
            and cap.context_length < self.config.light_min_context
        ):
            return False
        if cap.supports_json is False:
            return False
        return True