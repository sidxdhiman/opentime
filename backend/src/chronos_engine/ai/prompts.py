"""Mode-gated, evidence-respecting AI prompt construction for the ChronOS Engine.

The DEEP path does not ask the model to rediscover the user's emotion, intent,
goals, or contradictions — ChronOS has already computed those deterministically.
The ``ReasoningContextBuilder`` filters and bounds the deterministic state by
reasoning mode; this builder is a pure formatter over that already-filtered
context.

Prompt minimization (Phase 2E, sections 6/8/9): every CHRONOS STATE section is
emitted only when a reasoning mode actually needs it, and evidence is bounded
by the configurable ``ContextBudget``.

* ``INTENT``            — always.
* ``USER STATE``        — INTERPRET, REASON or CLASSIFY (minimal).
* ``GOAL ANALYSIS``     — INTERPRET or REASON.
* ``CONSISTENCY``       — INTERPRET or REASON.
* ``RELEVANT CONTEXT``  — INTERPRET, REASON or REFLECT (bounded; CLASSIFY gets
  no historical context unless it requires it).
* ``PATTERNS``          — REFLECT.
* ``GOAL CHANGES``      — REFLECT.
* ``ACTIVE GOALS``      — INTERPRET or REASON.

Evidence is tagged (``[memory:<id>]``, ``[timeline:<id>]``,
``[pattern:<id>]``) so the parser can reject invented citations. No MongoDB
ids beyond those tags, no internal implementation details, no stack traces,
and no provider metadata are included.
"""

from chronos_engine.ai.context import (
    ContextBudget,
    ReasoningContext,
    ReasoningContextBuilder,
)
from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
from chronos_engine.core.models import PromptContext, RetrievedContext
from chronos_engine.response.models import DeterministicResponse
from chronos_engine.state.models import ChronosState

_SYSTEM_PROMPT = """\
You are the reasoning layer of ChronOS.

ChronOS has already analyzed the user's input deterministically. Use the \
supplied structured state as context; do not re-derive the user's emotion, \
intent, goals, or contradictions on your own.

Ground rules:
- Return only the JSON object requested in OUTPUT FORMAT, nothing else.
- Do not invent historical facts, goals, recurring patterns, or memories. \
Reference only evidence tagged in the CHRONOS STATE section.
- Do not claim that the user feels something as a fact; use cautious language \
for any inferred user state (a suggestion is never certainty).
- Do not diagnose the user.
- If the supplied context is insufficient, say so plainly.
- Keep any reasoning summary concise. Do not reveal a long chain of thought.

Generate a concise, useful response in the user's language."""

_OUTPUT_FORMAT = """\
Return ONLY a single JSON object with this schema:
{
  "interpretation": <string or null>,
  "reasoning": <string or null>,
  "reflection": <string or null>,
  "answer": <string>,           // required; your final response to the user
  "uncertainties": [<string>],  // optional list
  "evidence_used": [<string>]   // tags you actually cited, e.g. "[memory:<id>]"
}
Fill each field only when the corresponding reasoning mode was engaged. \
No markdown fences, no text before or after the JSON."""


class ChronosAIPromptBuilder:
    """Builds a ``PromptContext`` for the DEEP path from structured state.

    Pure string formatting over the filtered ``ReasoningContext``: no LLM, no
    network, no retrieval. Identical states and plans produce identical
    prompts.
    """

    def __init__(
        self,
        context_builder: ReasoningContextBuilder | None = None,
    ):
        self.context_builder = context_builder or ReasoningContextBuilder()

    def build(
        self,
        chronos_state: ChronosState,
        deterministic_response: DeterministicResponse,
        plan: ReasoningPlan,
        budget: ContextBudget | None = None,
    ) -> PromptContext:
        context = chronos_state.context or RetrievedContext()
        reasoning_context = self.context_builder.build(
            chronos_state, plan, budget=budget
        )
        user_prompt = self._format_user_prompt(
            reasoning_context, deterministic_response, plan
        )

        return PromptContext(
            current_input=chronos_state.current_input,
            retrieved_context=context,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    def context_for(
        self,
        chronos_state: ChronosState,
        plan: ReasoningPlan,
        budget: ContextBudget | None = None,
    ) -> ReasoningContext:
        """Build the filtered context without formatting a prompt."""
        return self.context_builder.build(chronos_state, plan, budget=budget)

    def evidence_ids(self, chronos_state: ChronosState) -> set[str]:
        """Return the evidence ids the model is allowed to cite."""
        return self.context_builder.evidence_ids(chronos_state)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_user_prompt(
        self,
        reasoning_context: ReasoningContext,
        deterministic_response: DeterministicResponse,
        plan: ReasoningPlan,
    ) -> str:
        lines: list[str] = []
        lines.append("REASONING PLAN:")
        lines.append(
            f"Modes engaged: {', '.join(m.value for m in plan.modes)}. "
            f"Primary mode: {plan.primary_mode.value}."
        )
        if reasoning_context.requires_history:
            lines.append("This interaction draws on the user's stored history.")
        lines.append("")
        lines.append("TASK:")
        lines.extend(self._task_lines(plan))
        lines.append("")
        lines.append("USER INPUT:")
        lines.append(f'"{reasoning_context.current_input}"')
        lines.append("")
        lines.append("CHRONOS STATE:")
        lines.extend(self._state_lines(reasoning_context))
        lines.append("")
        lines.append("DETERMINISTIC INTERPRETATION:")
        lines.append(deterministic_response.rendered)
        lines.append("")
        lines.append("OUTPUT FORMAT:")
        lines.append(_OUTPUT_FORMAT)
        return "\n".join(lines)

    def _task_lines(self, plan: ReasoningPlan) -> list[str]:
        tasks: dict[ReasoningMode, str] = {
            ReasoningMode.CLASSIFY: (
                "Briefly restate the user's likely intent in one short phrase."
            ),
            ReasoningMode.INTERPRET: (
                "Interpret what the input suggests about the user's current "
                "state, grounding any inference in the CHRONOS STATE section."
            ),
            ReasoningMode.REASON: (
                "Reason over the decision or analysis request. Keep the "
                "reasoning summary concise; state the key considerations and "
                "trade-offs, then conclude."
            ),
            ReasoningMode.REFLECT: (
                "Reflect on how the user's situation or priorities compare "
                "across the evidence provided. Note changes only if the "
                "evidence supports them."
            ),
            ReasoningMode.GENERATE: (
                "Produce the final natural-language response to the user in "
                "their language."
            ),
        }
        return [
            f"- {tasks[mode]}"
            for mode in plan.modes
            if mode in tasks
        ]

    def _state_lines(self, ctx: ReasoningContext) -> list[str]:
        lines: list[str] = []

        lines.append("INTENT:")
        lines.append(f"- Intent: {ctx.intent}")

        if ctx.show_user_state:
            lines.append("USER STATE:")
            lines.extend(ctx.user_state_lines)

        if ctx.show_goal_analysis:
            lines.append("GOAL ANALYSIS:")
            lines.extend(ctx.goal_lines)

        if ctx.show_consistency:
            lines.append("CONSISTENCY:")
            lines.extend(ctx.consistency_lines)

        if ctx.show_relevant_context:
            lines.append("RELEVANT CONTEXT:")
            if not (ctx.memory_excerpts or ctx.timeline_excerpts):
                lines.append("- Relevant context: none retrieved.")
            else:
                lines.append(
                    f"- Relevant context: {len(ctx.memory_excerpts)} relevant "
                    f"memories, {len(ctx.timeline_excerpts)} timeline events."
                )
                lines.extend(ctx.memory_excerpts)
                lines.extend(ctx.timeline_excerpts)

        if ctx.show_patterns:
            lines.append("PATTERNS:")
            lines.extend(ctx.pattern_excerpts or ["- Patterns: none detected."])

        if ctx.show_goal_changes:
            lines.append("GOAL CHANGES:")
            lines.extend(ctx.recent_changes or ["- Goal changes: none detected."])

        if ctx.active_goals:
            lines.append(
                "- Active goals: " + ", ".join(ctx.active_goals[:5])
                + (" (and more)" if len(ctx.active_goals) > 5 else "")
            )

        return lines