"""Minimal, evidence-respecting AI prompt construction for the ChronOS Engine.

The DEEP path does not ask the model to rediscover the user's emotion, intent,
goals, or contradictions — ChronOS has already computed those deterministically.
This builder hands the model only the structured state ChronOS inferred, plus
the deterministic interpretation, so the model can produce a richer
natural-language response that stays grounded in that evidence.

Only information necessary for the response is sent:

* current input
* intent
* user state (cautious phrasing)
* goal analysis
* consistency result
* relevant context (counts + brief excerpts of already-retrieved memories)
* deterministic interpretation

No MongoDB ids, internal implementation details, stack traces, or provider
metadata are included.
"""


from chronos_engine.core.models import PromptContext, RetrievedContext
from chronos_engine.response.models import DeterministicResponse
from chronos_engine.state.models import (
    ChronosState,
    GoalStatus,
)

_SYSTEM_PROMPT = """\
You are the language layer of ChronOS.

ChronOS has already analyzed the user's input deterministically. Use the \
supplied structured state as context; do not re-derive the user's emotion, \
intent, goals, or contradictions on your own.

Ground rules:
- Do not invent historical facts, goals, recurring patterns, or memories.
- Do not claim that the user feels something as a fact; use cautious language \
for any inferred user state.
- Do not diagnose the user.
- Use only the information provided in the CHRONOS STATE and DETERMINISTIC \
INTERPRETATION sections.
- If the supplied context is insufficient, say so plainly.

Generate a concise, useful response in the user's language."""

_MEMORY_EXCERPT_LIMIT: int = 5
_MEMORY_EXCERPT_CHARS: int = 140


class ChronosAIPromptBuilder:
    """Builds a ``PromptContext`` for the DEEP path from structured state.

    Pure string formatting: no LLM, no network, no retrieval. Identical
    states produce identical prompts.
    """

    def build(
        self,
        chronos_state: ChronosState,
        deterministic_response: DeterministicResponse,
    ) -> PromptContext:
        context = chronos_state.context or RetrievedContext()
        user_prompt = self._format_user_prompt(chronos_state, deterministic_response)

        return PromptContext(
            current_input=chronos_state.current_input,
            retrieved_context=context,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_user_prompt(
        self, state: ChronosState, deterministic_response: DeterministicResponse
    ) -> str:
        lines: list[str] = []
        lines.append("USER INPUT:")
        lines.append(f'"{state.current_input.content}"')
        lines.append("")
        lines.append("CHRONOS STATE:")
        lines.extend(self._state_lines(state))
        lines.append("")
        lines.append("DETERMINISTIC INTERPRETATION:")
        lines.append(deterministic_response.rendered)
        return "\n".join(lines)

    def _state_lines(self, state: ChronosState) -> list[str]:
        lines: list[str] = []

        intent = state.intent
        if intent is not None and intent.intent is not None:
            lines.append(f"- Intent: {intent.intent.value}")
        else:
            lines.append("- Intent: UNKNOWN")

        user_state = state.user_state
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

        goal = state.goal_analysis
        if goal is not None and goal.status not in (None, GoalStatus.NONE):
            goal_name = goal.goal or goal.matched_existing_goal
            lines.append(
                f"- Goal relationship: {goal.status.value}"
                + (f" (goal: {goal_name})" if goal_name else "")
            )

        contradictions = state.contradictions or []
        if contradictions:
            labels = sorted({c.type for c in contradictions if c.type})
            detail = ", ".join(labels) if labels else "conflict"
            lines.append(
                f"- Consistency: ChronOS detected a {detail} with stored context."
            )
        else:
            lines.append("- Consistency: no conflict detected with stored context.")

        context = state.context
        if context is not None:
            memory_count = len(context.relevant_memories)
            event_count = len(context.timeline_events)
            if memory_count or event_count:
                lines.append(
                    f"- Relevant context: {memory_count} relevant memories, "
                    f"{event_count} timeline events."
                )
            for memory in context.relevant_memories[:_MEMORY_EXCERPT_LIMIT]:
                excerpt = memory.content[:_MEMORY_EXCERPT_CHARS]
                lines.append(f"  - {excerpt}")

        if state.goals:
            lines.append(
                f"- Active goals: {', '.join(state.goals[:5])}"
                + (" (and more)" if len(state.goals) > 5 else "")
            )

        return lines