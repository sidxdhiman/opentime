"""Deterministic context building for AI prompts (Phase 2E).

``ReasoningContextBuilder`` is a deterministic filtering layer between the
already-retrieved context and the AI prompt (spec section 7). It:

* applies the ``ReasoningPlan``'s mode-specific context preferences (section 6),
* bounds the number of evidence items sent to the model (section 8),
* computes the evidence ids the model is allowed to cite,
* and produces only the fields the requested reasoning actually needs.

It never performs another retrieval pass, never generates embeddings, and
never touches the network. Identical states and plans produce identical
contexts.
"""

from pydantic import BaseModel, Field

from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
from chronos_engine.core.models import RetrievedContext
from chronos_engine.state.models import ChronosState, GoalStatus

_MEMORY_EXCERPT_CHARS: int = 140

_INTERPRET_REASON_MODES = (ReasoningMode.INTERPRET, ReasoningMode.REASON)


class ContextBudget(BaseModel):
    """Bounded evidence counts for one AI prompt (spec section 8).

    The retrieved context already arrives relevance-ordered; these limits cap
    how many items are forwarded, preserving the existing ordering.
    """

    max_memories: int = 5
    max_timeline_events: int = 3
    max_patterns: int = 3
    max_recent_changes: int = 3


class ReasoningContext(BaseModel):
    """The mode-specific, bounded slice of state forwarded to the AI prompt.

    Excerpt strings are pre-formatted with their evidence tags so the prompt
    builder stays a pure formatter over already-filtered content.
    """

    current_input: str
    intent: str
    requires_history: bool

    user_state_lines: list[str] = Field(default_factory=list)
    goal_lines: list[str] = Field(default_factory=list)
    consistency_lines: list[str] = Field(default_factory=list)

    memory_excerpts: list[str] = Field(default_factory=list)
    timeline_excerpts: list[str] = Field(default_factory=list)
    pattern_excerpts: list[str] = Field(default_factory=list)
    recent_changes: list[str] = Field(default_factory=list)
    active_goals: list[str] = Field(default_factory=list)

    # Phase 4F: bounded active thread context for thread continuation
    active_thread_lines: list[str] = Field(default_factory=list)

    show_user_state: bool = False
    show_goal_analysis: bool = False
    show_consistency: bool = False
    show_relevant_context: bool = False
    show_patterns: bool = False
    show_goal_changes: bool = False
    show_active_thread: bool = False

    evidence_ids: set[str] = Field(default_factory=set)


class ReasoningContextBuilder:
    """Filters + bounds deterministic state into a ``ReasoningContext``."""

    def build(
        self,
        state: ChronosState,
        plan: ReasoningPlan,
        budget: ContextBudget | None = None,
    ) -> ReasoningContext:
        budget = budget or ContextBudget()
        modes = plan.modes
        context = state.context or RetrievedContext()

        show_interpret = ReasoningMode.INTERPRET in modes
        show_reason = ReasoningMode.REASON in modes
        show_classify = ReasoningMode.CLASSIFY in modes
        show_reflect = ReasoningMode.REFLECT in modes

        thread_lines = self._active_thread_lines(state.active_temporal_context)

        return ReasoningContext(
            current_input=state.current_input.content,
            intent=(
                state.intent.intent.value if state.intent and state.intent.intent else "UNKNOWN"
            ),
            requires_history=plan.requires_history,
            user_state_lines=self._user_state_lines(state.user_state),
            goal_lines=self._goal_lines(state.goal_analysis),
            consistency_lines=self._consistency_lines(state.contradictions or []),
            memory_excerpts=self._memory_excerpts(context, budget.max_memories),
            timeline_excerpts=self._timeline_excerpts(context, budget.max_timeline_events),
            pattern_excerpts=self._pattern_excerpts(state, budget.max_patterns),
            recent_changes=self._recent_changes(context, budget.max_recent_changes),
            active_goals=list(state.goals) if (show_interpret or show_reason) else [],
            active_thread_lines=thread_lines,
            show_user_state=show_interpret or show_reason or show_classify,
            show_goal_analysis=show_interpret or show_reason,
            show_consistency=show_interpret or show_reason,
            show_relevant_context=show_interpret or show_reason or show_reflect,
            show_patterns=show_reflect,
            show_goal_changes=show_reflect,
            show_active_thread=bool(thread_lines),
            evidence_ids=self.evidence_ids(state),
        )

    # ------------------------------------------------------------------
    # Evidence ids
    # ------------------------------------------------------------------

    @staticmethod
    def evidence_ids(state: ChronosState) -> set[str]:
        """Return every evidence id the model is allowed to cite."""
        ids: set[str] = set()
        context = state.context
        if context is not None:
            ids.update(m.id for m in context.relevant_memories)
            ids.update(e.id for e in context.timeline_events)
        ids.update(p.id for p in state.patterns)
        return ids

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    @staticmethod
    def _user_state_lines(user_state) -> list[str]:
        if user_state is None:
            return ["- User state: none detected."]
        lines: list[str] = []
        if user_state.emotional_state is not None:
            lines.append(
                f"- The input suggests emotional state: "
                f"{user_state.emotional_state.value}"
                f" (confidence {user_state.confidence})"
            )
        if user_state.cognitive_state is not None:
            lines.append(
                f"- The input suggests cognitive state: "
                f"{user_state.cognitive_state.value}"
                f" (confidence {user_state.confidence})"
            )
        if user_state.energy is not None:
            lines.append(
                f"- The input suggests energy level: {user_state.energy.value}"
            )
        if user_state.valence is not None:
            lines.append(f"- Valence: {user_state.valence:+.2f}")
        if not lines:
            lines.append("- User state: none detected.")
        return lines

    @staticmethod
    def _goal_lines(goal) -> list[str]:
        if goal is not None and goal.status not in (None, GoalStatus.NONE):
            goal_name = goal.goal or goal.matched_existing_goal
            line = f"- Goal relationship: {goal.status.value}"
            if goal_name:
                line += f" (goal: {goal_name})"
            return [line]
        return ["- Goal relationship: none detected."]

    @staticmethod
    def _consistency_lines(contradictions) -> list[str]:
        if contradictions:
            labels = sorted({c.type for c in contradictions if c.type})
            detail = ", ".join(labels) if labels else "conflict"
            return [
                f"- Consistency: ChronOS detected a {detail} with stored context."
            ]
        return ["- Consistency: no conflict detected with stored context."]

    def _memory_excerpts(self, context: RetrievedContext, limit: int) -> list[str]:
        lines: list[str] = []
        for memory in context.relevant_memories[:limit]:
            excerpt = memory.content[:_MEMORY_EXCERPT_CHARS]
            lines.append(f"  - {excerpt} [memory:{memory.id}]")
        return lines

    def _timeline_excerpts(self, context: RetrievedContext, limit: int) -> list[str]:
        lines: list[str] = []
        for event in context.timeline_events[:limit]:
            lines.append(
                f"  - Timeline: {event.title} — "
                f"{event.description[:_MEMORY_EXCERPT_CHARS]} [timeline:{event.id}]"
            )
        return lines

    def _pattern_excerpts(self, state: ChronosState, limit: int) -> list[str]:
        lines: list[str] = []
        for pattern in state.patterns[:limit]:
            lines.append(
                f"- Pattern [{pattern.category.value}] ({pattern.title}): "
                f"{pattern.description[:_MEMORY_EXCERPT_CHARS]} [pattern:{pattern.id}]"
            )
        return lines

    @staticmethod
    def _recent_changes(context: RetrievedContext, limit: int) -> list[str]:
        return [f"- Recent change: {change}" for change in (context.recent_changes or [])[:limit]]

    @staticmethod
    def _active_thread_lines(ctx) -> list[str]:
        """Format bounded active thread context for the AI prompt.

        Produces a read-only, user-safe section: subject, status, type,
        origin, and up to 10 recent event descriptions.  When no context is
        provided, returns an empty list (section is omitted entirely).
        """
        if ctx is None:
            return []
        lines: list[str] = []
        lines.append(f"- Thread: \"{ctx.subject}\" (status: {ctx.status})")
        if ctx.temporal_type:
            lines.append(f"- Temporal type: {ctx.temporal_type}")
        if ctx.description:
            lines.append(f"- Description: {ctx.description[:200]}")
        if ctx.origin_description:
            lines.append(f"- Origin: {ctx.origin_description[:200]}")
        if ctx.recent_events:
            lines.append(f"- Recent events ({len(ctx.recent_events)}):")
            for ev in ctx.recent_events:
                ev_type = f" [{ev.temporal_type}]" if ev.temporal_type else ""
                lines.append(f"  - {ev.description[:150]}{ev_type}")
        return lines