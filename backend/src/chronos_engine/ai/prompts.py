"""Mode-gated, evidence-respecting AI prompt construction for the ChronOS Engine.

The DEEP path does not ask the model to rediscover the user's emotion, intent,
goals, or contradictions — ChronOS has already computed those deterministically.
This builder hands the model only the structured state ChronOS inferred, the
deterministic interpretation, and the reasoning plan, so the model can produce
a richer natural-language response that stays grounded in that evidence.

Prompt minimization (section 20): every CHRONOS STATE section is emitted only
when a reasoning mode actually needs it.

* ``INTENT``            — always.
* ``USER STATE``        — INTERPRET or REASON.
* ``GOAL ANALYSIS``     — INTERPRET or REASON.
* ``CONSISTENCY``       — INTERPRET or REASON.
* ``RELEVANT CONTEXT``  — INTERPRET, REASON, REFLECT or CLASSIFY.
* ``PATTERNS``          — REFLECT.
* ``GOAL CHANGES``      — REFLECT.
* ``ACTIVE GOALS``      — INTERPRET or REASON.

Evidence is tagged (``[memory:<id>]``, ``[timeline:<id>]``,
``[pattern:<id>]``) so the parser can reject invented citations. No MongoDB
ids beyond those tags, no internal implementation details, no stack traces,
and no provider metadata are included.
"""

from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
from chronos_engine.core.models import PromptContext, RetrievedContext
from chronos_engine.response.models import DeterministicResponse
from chronos_engine.state.models import (
    ChronosState,
    GoalStatus,
)

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
for any inferred user state.
- Do not diagnose the user.
- If the supplied context is insufficient, say so plainly.
- Keep any reasoning summary concise. Do not reveal a long chain of thought.

Generate a concise, useful response in the user's language."""

_MEMORY_EXCERPT_LIMIT: int = 5
_MEMORY_EXCERPT_CHARS: int = 140

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

    Pure string formatting: no LLM, no network, no retrieval. Identical
    states and plans produce identical prompts.
    """

    def build(
        self,
        chronos_state: ChronosState,
        deterministic_response: DeterministicResponse,
        plan: ReasoningPlan,
    ) -> PromptContext:
        context = chronos_state.context or RetrievedContext()
        user_prompt = self._format_user_prompt(
            chronos_state, deterministic_response, plan
        )

        return PromptContext(
            current_input=chronos_state.current_input,
            retrieved_context=context,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    def evidence_ids(self, chronos_state: ChronosState) -> set[str]:
        """Return the evidence ids the model is allowed to cite."""
        ids: set[str] = set()
        context = chronos_state.context
        if context is not None:
            ids.update(m.id for m in context.relevant_memories)
            ids.update(e.id for e in context.timeline_events)
        ids.update(p.id for p in chronos_state.patterns)
        return ids

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_user_prompt(
        self,
        state: ChronosState,
        deterministic_response: DeterministicResponse,
        plan: ReasoningPlan,
    ) -> str:
        lines: list[str] = []
        lines.append("REASONING PLAN:")
        lines.append(
            f"Modes engaged: {', '.join(m.value for m in plan.modes)}. "
            f"Primary mode: {plan.primary_mode.value}."
        )
        if plan.requires_history:
            lines.append("This interaction draws on the user's stored history.")
        lines.append("")
        lines.append("TASK:")
        lines.extend(self._task_lines(plan))
        lines.append("")
        lines.append("USER INPUT:")
        lines.append(f'"{state.current_input.content}"')
        lines.append("")
        lines.append("CHRONOS STATE:")
        lines.extend(self._state_lines(state, plan))
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

    def _state_lines(self, state: ChronosState, plan: ReasoningPlan) -> list[str]:
        lines: list[str] = []

        lines.append("INTENT:")
        intent = state.intent
        intent_value = intent.intent.value if intent and intent.intent else "UNKNOWN"
        lines.append(f"- Intent: {intent_value}")

        needs_context = any(
            m in plan.modes
            for m in (
                ReasoningMode.INTERPRET,
                ReasoningMode.REASON,
                ReasoningMode.REFLECT,
                ReasoningMode.CLASSIFY,
            )
        )

        if ReasoningMode.INTERPRET in plan.modes or ReasoningMode.REASON in plan.modes:
            lines.extend(self._interpret_lines(state))

        if plan.requires_context and needs_context:
            lines.extend(self._context_lines(state))

        if ReasoningMode.REFLECT in plan.modes:
            lines.extend(self._reflect_lines(state))

        if ReasoningMode.INTERPRET in plan.modes or ReasoningMode.REASON in plan.modes:
            if state.goals:
                lines.append("- Active goals: " + ", ".join(state.goals[:5]) + (
                    " (and more)" if len(state.goals) > 5 else ""
                ))

        return lines

    def _interpret_lines(self, state: ChronosState) -> list[str]:
        lines: list[str] = []

        user_state = state.user_state
        lines.append("USER STATE:")
        if user_state is not None:
            if user_state.emotional_state is not None:
                lines.append(
                    f"- The input suggests emotional state: "
                    f"{user_state.emotional_state.value}"
                )
            if user_state.cognitive_state is not None:
                lines.append(
                    f"- The input suggests cognitive state: "
                    f"{user_state.cognitive_state.value}"
                )
            if user_state.energy is not None:
                lines.append(
                    f"- The input suggests energy level: {user_state.energy.value}"
                )
            if user_state.valence is not None:
                lines.append(f"- Valence: {user_state.valence:+.2f}")
            if not any(
                [
                    user_state.emotional_state,
                    user_state.cognitive_state,
                    user_state.energy,
                    user_state.valence,
                ]
            ):
                lines.append("- User state: none detected.")
        else:
            lines.append("- User state: none detected.")

        goal = state.goal_analysis
        lines.append("GOAL ANALYSIS:")
        if goal is not None and goal.status not in (None, GoalStatus.NONE):
            goal_name = goal.goal or goal.matched_existing_goal
            lines.append(
                f"- Goal relationship: {goal.status.value}"
                + (f" (goal: {goal_name})" if goal_name else "")
            )
        else:
            lines.append("- Goal relationship: none detected.")

        contradictions = state.contradictions or []
        lines.append("CONSISTENCY:")
        if contradictions:
            labels = sorted({c.type for c in contradictions if c.type})
            detail = ", ".join(labels) if labels else "conflict"
            lines.append(
                f"- Consistency: ChronOS detected a {detail} with stored context."
            )
        else:
            lines.append("- Consistency: no conflict detected with stored context.")

        return lines

    def _context_lines(self, state: ChronosState) -> list[str]:
        lines: list[str] = []
        context = state.context
        memory_count = len(context.relevant_memories) if context else 0
        event_count = len(context.timeline_events) if context else 0
        pattern_count = len(state.patterns)

        lines.append("RELEVANT CONTEXT:")
        if not (memory_count or event_count or pattern_count):
            lines.append("- Relevant context: none retrieved.")
            return lines

        lines.append(
            f"- Relevant context: {memory_count} relevant memories, "
            f"{event_count} timeline events, {pattern_count} patterns."
        )
        if context is not None:
            for memory in context.relevant_memories[:_MEMORY_EXCERPT_LIMIT]:
                excerpt = memory.content[:_MEMORY_EXCERPT_CHARS]
                lines.append(f"  - {excerpt} [memory:{memory.id}]")
            for event in context.timeline_events[:_MEMORY_EXCERPT_LIMIT]:
                lines.append(
                    f"  - Timeline: {event.title} — "
                    f"{event.description[:_MEMORY_EXCERPT_CHARS]} [timeline:{event.id}]"
                )
        for pattern in state.patterns[:_MEMORY_EXCERPT_LIMIT]:
            lines.append(
                f"  - Pattern: {pattern.title} — "
                f"{pattern.description[:_MEMORY_EXCERPT_CHARS]} [pattern:{pattern.id}]"
            )
        return lines

    def _reflect_lines(self, state: ChronosState) -> list[str]:
        lines: list[str] = []

        patterns = state.patterns
        lines.append("PATTERNS:")
        if patterns:
            for pattern in patterns[:_MEMORY_EXCERPT_LIMIT]:
                lines.append(
                    f"- Pattern [{pattern.category.value}] ({pattern.title}): "
                    f"{pattern.description[:_MEMORY_EXCERPT_CHARS]} [pattern:{pattern.id}]"
                )
        else:
            lines.append("- Patterns: none detected.")

        context = state.context
        recent = context.recent_changes if context is not None else []
        lines.append("GOAL CHANGES:")
        if recent:
            for change in recent[:_MEMORY_EXCERPT_LIMIT]:
                lines.append(f"- Recent change: {change}")
        else:
            lines.append("- Goal changes: none detected.")

        return lines
