"""Bounded AI reflection over an already-valid temporal moment (Phase 3I).

The deterministic pipeline (Phases 3A–3H) remains the sole source of truth
for WHAT happened temporally. This module adds an optional ENHANCEMENT
layer: when a valid ``PastSelfConversationMoment`` exists, a small local
model may re-express the grounded facts as one thoughtful reflection.

Hard boundaries (enforced here, not trusted to the model):

* Eligibility is deterministic and mirrors the Phase 3H surface gates —
  no surfaced moment, non-``SURFACE_NOW`` relevance, insufficient
  comparison, ambiguous lifecycle or missing grounding means the provider
  is never touched.
* The prompt carries ONLY curated, already-grounded temporal facts
  (subject quotes inside the deterministic lines, anchored event
  descriptions, lifecycle transition label, comparison relation and its
  two summaries, the planned question and the deterministic moment).
  No raw database dumps, no unrelated memories, no internal traces.
* Output must be a single JSON object matching the strict contract;
  parsing reuses the existing ``AIResponseParser`` JSON extraction,
  evidence-id normalization and stable error reasons. Cited evidence ids
  outside the curated allowed set fail safely (hallucination guard), raw
  identifiers leaking into user-facing text fail safely, and oversized
  output fails safely.
* Exactly ONE provider call per attempt, through the existing
  ``LLMRegistry``/``OllamaProvider`` infrastructure and the existing
  ``InferencePolicy`` (extended with a temporal-reflection rule). No
  retry, no automatic LIGHT→DEEP escalation. On any failure the
  deterministic moment surfaces unchanged.
"""

import re
import time

from pydantic import BaseModel, Field

from chronos_engine.ai.policy.models import InferencePolicyDecision, InferenceTier
from chronos_engine.ai.policy.service import InferencePolicy
from chronos_engine.ai.reasoning.parser import (
    HALLUCINATED_EVIDENCE,
    AIResponseParseError,
    AIResponseParser,
    _normalize_evidence_id,
)
from chronos_engine.config.ollama import OllamaConfig
from chronos_engine.core.interfaces import BaseTemporalReflectionGenerator
from chronos_engine.core.models import (
    PromptContext,
    RetrievedContext,
    UserInput,
)
from chronos_engine.llm.errors import LLMDisabledError, LLMProviderError
from chronos_engine.llm.inference import InferenceOptions
from chronos_engine.llm.providers import LLMRegistry
from chronos_engine.temporal.models import (
    PastSelfConversationMoment,
    PastSelfQuestionResult,
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalLifecycleResult,
    TemporalReflectionResult,
    TemporalRelevanceDecision,
    TemporalRelevanceResult,
)

SECTION_HEADING = "REFLECTION"

# A generated reflection is a short interpretive paragraph, never an essay.
_MAX_REFLECTION_CHARS = 1200

# Stable validation-failure reasons (extend the parser's vocabulary).
MISSING_REFLECTION = "MISSING_REFLECTION"
LEAKED_IDENTIFIER = "LEAKED_IDENTIFIER"
VALIDATION_FAILED = "VALIDATION_FAILED"

# Any raw internal identifier pattern found in USER-FACING text is a hard
# failure: ids live in metadata fields only (Phase 3H honesty contract).
_RAW_ID_PATTERN = re.compile(
    r"\b(?:mem|tevent|thread|user|tsnap)_[A-Za-z0-9_-]+\b"
)

_SYSTEM_PROMPT = """\
You are refining an already-determined reflection for ChronOS.

ChronOS has already decided — deterministically — what temporal event \
occurred, which story it belongs to, how it changed, and what question to \
ask. Your ONLY job is to express these established facts more naturally.

Ground rules:
- The supplied facts are authoritative and complete. Do not add facts.
- Do not change, soften or reinterpret the story outcome.
- Do not invent emotions, motivations, durations or history.
- Use cautious language; if evidence is limited, say so conservatively.
- Do not diagnose the user and do not give instructions.
- Return only the JSON object requested in OUTPUT FORMAT, nothing else."""

_OUTPUT_FORMAT = """\
Return ONLY a single JSON object with this schema:
{
  "reflection": <string>,       // required; one short paragraph
  "evidence_used": [<string>],  // tags you actually cited, e.g. "[timeline:<id>]"
  "uncertainties": [<string>]   // optional list
}
No markdown fences, no text before or after the JSON."""


class TemporalReflectionOutput(BaseModel):
    """Strict structured contract for one temporal reflection response."""

    reflection: str | None = None
    uncertainties: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)


def render_temporal_reflection_section(
    result: TemporalReflectionResult | None,
) -> str | None:
    """Render the additive REFLECTION section, or ``None`` when unused.

    The section is appended AFTER the deterministic past-self section and
    never replaces or rewrites it.
    """
    if result is None or not result.used or not result.success:
        return None
    text = (result.reflection or "").strip()
    if not text:
        return None
    return "\n\n".join([SECTION_HEADING, text])


class TemporalReflectionGenerator(BaseTemporalReflectionGenerator):
    """Default Phase 3I implementation of BaseTemporalReflectionGenerator.

    Orchestrates existing infrastructure only: tier/model selection comes
    exclusively from ``InferencePolicy.decide_temporal_reflection``, the
    single provider call goes through the registered Ollama provider, and
    output validation reuses the ``AIResponseParser`` machinery.
    """

    def __init__(
        self,
        llm_registry: LLMRegistry | None = None,
        config: OllamaConfig | None = None,
        inference_policy: InferencePolicy | None = None,
    ):
        self.llm_registry = llm_registry or LLMRegistry()
        self.config = config or OllamaConfig()
        self.inference_policy = inference_policy or InferencePolicy(config=self.config)
        self.parser = AIResponseParser()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def generate(
        self,
        user_id: str,
        moment: PastSelfConversationMoment,
        past_self_question: PastSelfQuestionResult | None = None,
        relevance_result: TemporalRelevanceResult | None = None,
        comparison: TemporalComparisonResult | None = None,
        lifecycle_result: TemporalLifecycleResult | None = None,
    ) -> TemporalReflectionResult:
        """Attempt at most ONE bounded reflection call for a valid moment."""
        skip_reason = self._eligibility_reason(
            moment,
            relevance_result,
            comparison,
            lifecycle_result,
            past_self_question,
        )
        if skip_reason is not None:
            return TemporalReflectionResult(
                attempted=False, reason=skip_reason
            )

        assert moment is not None and comparison is not None
        assert relevance_result is not None

        decision = self.inference_policy.decide_temporal_reflection(
            comparison=comparison
        )
        if decision.tier is InferenceTier.NONE:
            return TemporalReflectionResult(
                attempted=False,
                reason=f"No inference target available: {decision.reason}",
                evidence_allowed=self._allowed_evidence(moment),
            )

        total_start = time.perf_counter()

        allowed = self._allowed_evidence(moment)
        prompt_context = self._build_prompt(user_id, moment, comparison)

        if not self.config.enabled:
            return self._fallback(
                decision=decision,
                allowed=allowed,
                error_type="LLMDisabledError",
                latency_ms=self._latency(total_start),
                reason="AI inference is disabled; deterministic moment preserved.",
            )

        provider_key = decision.provider or "ollama"
        model = decision.model or self.config.model
        provider = self.llm_registry.get_provider(provider_key)

        # Exactly one provider call. No retry, no tier escalation: any
        # failure keeps the deterministic moment untouched.
        try:
            llm_result = await provider.generate(
                prompt_context,
                model_name=model,
                inference_options=self._inference_options(decision.tier.value),
            )
        except LLMDisabledError as exc:
            return self._fallback(
                decision=decision,
                allowed=allowed,
                error_type=type(exc).__name__,
                latency_ms=self._latency(total_start),
                reason="AI inference is disabled; deterministic moment preserved.",
            )
        except LLMProviderError as exc:
            return self._fallback(
                decision=decision,
                allowed=allowed,
                error_type=type(exc).__name__,
                latency_ms=self._latency(total_start),
                reason="Provider call failed; deterministic moment preserved.",
            )
        latency_ms = self._latency(total_start)

        if not llm_result.success or not (llm_result.text or "").strip():
            return self._fallback(
                decision=decision,
                allowed=allowed,
                error_type=llm_result.error_type or "INVALID_LLM_RESULT",
                latency_ms=latency_ms,
                reason="Empty or invalid provider result; deterministic "
                "moment preserved.",
            )

        try:
            validated = self._validate_output(llm_result.text, allowed)
        except AIResponseParseError as exc:
            return self._fallback(
                decision=decision,
                allowed=allowed,
                error_type=exc.reason,
                latency_ms=latency_ms,
                reason="Reflection failed validation; deterministic moment "
                "preserved.",
            )

        evidence_used = [
            entry
            for entry in (
                _normalize_evidence_id(tag) for tag in validated.evidence_used
            )
            if entry in set(allowed)
        ]
        return TemporalReflectionResult(
            attempted=True,
            used=True,
            success=True,
            fallback_used=False,
            reason="Validated temporal reflection produced.",
            tier=decision.tier.value,
            provider=provider_key,
            model=model,
            latency_ms=latency_ms,
            reflection=validated.reflection or "",
            uncertainties=validated.uncertainties,
            evidence_allowed=allowed,
            evidence_used=evidence_used,
        )

    # ------------------------------------------------------------------
    # Deterministic eligibility gate (mirrors the Phase 3H surface gates)
    # ------------------------------------------------------------------

    @staticmethod
    def _eligibility_reason(
        moment: PastSelfConversationMoment | None,
        relevance_result: TemporalRelevanceResult | None,
        comparison: TemporalComparisonResult | None,
        lifecycle_result: TemporalLifecycleResult | None,
        past_self_question: PastSelfQuestionResult | None,
    ) -> str | None:
        """Return why reflection may not run, or ``None`` when eligible."""
        if moment is None or not moment.should_surface:
            return "no surfaced temporal moment."
        if relevance_result is None or (
            relevance_result.decision is not TemporalRelevanceDecision.SURFACE_NOW
        ):
            return "relevance was not SURFACE_NOW."
        if past_self_question is None or not past_self_question.attempted or (
            not past_self_question.should_ask
        ):
            return "no askable past-self question."
        if comparison is None or not comparison.comparable or (
            comparison.relation is TemporalComparisonRelation.INSUFFICIENT_EVIDENCE
        ):
            return "comparison is not meaningful."
        if lifecycle_result is not None and lifecycle_result.ambiguous:
            return "temporal lifecycle was ambiguous."
        if not (moment.evidence_memory_ids or moment.evidence_event_ids):
            return "no grounded evidence identifiers."
        return None

    # ------------------------------------------------------------------
    # Prompt construction (strictly bounded, curated facts only)
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        user_id: str,
        moment: PastSelfConversationMoment,
        comparison: TemporalComparisonResult,
    ) -> PromptContext:
        lines: list[str] = []
        lines.append("TASK:")
        lines.append(
            "- Write ONE short reflection paragraph that connects the "
            "earlier moment below with the present one."
        )
        lines.append("- Interpret only; do not add anything new.")
        lines.append("")
        lines.append("AUTHORITATIVE TEMPORAL FACTS:")
        if comparison.past_event_id:
            lines.append(
                f"- Earlier moment [timeline:{comparison.past_event_id}]: "
                f"{(moment.context or '').strip()}"
            )
        else:
            lines.append(f"- Earlier moment: {(moment.context or '').strip()}")
        if (moment.bridge or "").strip():
            lines.append(f"- Present moment: {moment.bridge.strip()}")
        relation_value = (
            moment.relation.value if moment.relation is not None else "UNRESOLVED"
        )
        lines.append(f"- Deterministic outcome: {self._lifecycle_label(relation_value)}.")
        lines.append(
            f"- Planned past-self question: {(moment.question or '').strip()}"
        )
        lines.append("")
        lines.append("OUTPUT FORMAT:")
        lines.append(_OUTPUT_FORMAT)

        return PromptContext(
            # Structural placeholder only: the reflection task has no new
            # user input, and providers receive ``full_prompt()`` (system +
            # user prompt), never this field on its own.
            current_input=UserInput(
                id="in_temporal_reflection",
                user_id=user_id,
                content="[internal] temporal reflection enhancement task",
            ),
            retrieved_context=RetrievedContext(),
            system_prompt=_SYSTEM_PROMPT,
            user_prompt="\n".join(lines),
        )

    @staticmethod
    def _lifecycle_label(relation_value: str) -> str:
        labels: dict[str, str] = {
            "CONFIRMED": "the present reaffirms the earlier direction",
            "CHANGED": "the present moved away from the earlier direction",
            "RESOLVED": "the story reached an explicit outcome",
            "EVOLVED": "the story keeps developing without closure yet",
            "CONTRADICTED": "the present conflicts with the earlier stance",
            "UNRESOLVED": "the story is still open",
        }
        return labels.get(relation_value, f"relation: {relation_value}")

    # ------------------------------------------------------------------
    # Validation (reuses the existing parser infrastructure)
    # ------------------------------------------------------------------

    def _validate_output(
        self, text: str, allowed: list[str]
    ) -> TemporalReflectionOutput:
        payload = self.parser._extract_json(text)
        if payload is None:
            raise AIResponseParseError("MALFORMED_JSON")
        try:
            output = TemporalReflectionOutput.model_validate(payload)
        except ValueError:
            raise AIResponseParseError("MALFORMED_JSON") from None

        reflection = (output.reflection or "").strip()
        if not reflection:
            raise AIResponseParseError(MISSING_REFLECTION)
        if len(reflection) > _MAX_REFLECTION_CHARS:
            raise AIResponseParseError(VALIDATION_FAILED)

        allowed_set = set(allowed)
        cited = {
            _normalize_evidence_id(tag) for tag in output.evidence_used
        }
        if cited and not cited.issubset(allowed_set):
            raise AIResponseParseError(HALLUCINATED_EVIDENCE)

        user_facing = "\n".join([reflection, *output.uncertainties])
        if _RAW_ID_PATTERN.search(user_facing):
            raise AIResponseParseError(LEAKED_IDENTIFIER)
        if any(eid and eid in user_facing for eid in allowed_set):
            raise AIResponseParseError(LEAKED_IDENTIFIER)

        return output

    @staticmethod
    def _allowed_evidence(moment: PastSelfConversationMoment) -> list[str]:
        seen: list[str] = []
        for eid in [*moment.evidence_event_ids, *moment.evidence_memory_ids]:
            if eid and eid not in seen:
                seen.append(eid)
        return seen

    # ------------------------------------------------------------------
    # Provider-call plumbing (mirrors AIExecutor conventions)
    # ------------------------------------------------------------------

    def _inference_options(self, tier: str) -> InferenceOptions:
        """Resolve per-tier knobs exactly like the main executor does.

        LIGHT uses its own model-specific knobs so the small model never
        inherits DEEP thinking configuration; DEEP uses the global settings.
        """
        if tier == InferenceTier.LIGHT.value:
            thinking_enabled = self.config.light_thinking_enabled
            format_json = self.config.light_format_json
        else:
            thinking_enabled = self.config.thinking_enabled
            format_json = None
        return InferenceOptions(
            thinking_enabled=thinking_enabled,
            num_predict=self.config.num_predict,
            num_ctx=self.config.num_ctx,
            temperature=self.config.temperature,
            format_json=format_json,
        )

    def _fallback(
        self,
        decision: InferencePolicyDecision,
        allowed: list[str],
        error_type: str,
        latency_ms: float,
        reason: str,
    ) -> TemporalReflectionResult:
        """Honest failure record — the deterministic moment is untouched."""
        return TemporalReflectionResult(
            attempted=True,
            used=False,
            success=False,
            fallback_used=True,
            error_type=error_type,
            reason=reason,
            tier=decision.tier.value,
            provider=decision.provider or "ollama",
            model=decision.model or self.config.model,
            latency_ms=latency_ms,
            evidence_allowed=allowed,
        )

    @staticmethod
    def _latency(start: float) -> float:
        return round((time.perf_counter() - start) * 1000.0, 2)
