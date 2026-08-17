"""Deterministic reasoning-mode planning for the ChronOS Engine.

The ``ReasoningPlanner`` translates an already-routed ``ChronOSState`` into the
minimum-sufficient set of reasoning modes for the single AI call. It is pure
computation over deterministic state — no LLM, no network. Identical states
always produce identical plans.

Mode selection (section 10 of the spec):

* ``CLASSIFY`` — the intent is unknown/ambiguous and the input is substantial
  enough to classify.
* ``INTERPRET`` — the state carries meaningful user-state signals or
  contradictions worth interpreting.
* ``REASON`` — the interaction involves a decision or explicit analysis:
  a ``DECISION`` intent with elevated complexity or multiple goals, a routed
  ``complex decision`` / ``explicit analysis request`` signal, or strong
  reason markers in the input.
* ``REFLECT`` — the interaction asks for reflection across past and present
  state (reflection intent, historical/pattern signals, or reflection markers).
* ``GENERATE`` — always engaged; the AI produces the final response.

A plan is minimal: modes are added only when their evidence is present.
"""


from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
from chronos_engine.core.interfaces import BaseReasoningPlanner
from chronos_engine.core.models import IntentType
from chronos_engine.routing.models import AIRoutingResult
from chronos_engine.state.models import ChronosState, GoalStatus

# Minimum input length before an ambiguous intent is worth CLASSIFYing.
CLASSIFY_MIN_LENGTH: int = 10

# Strong REASON language, independent of the intent detector's DECISION call.
_REASON_MARKERS: list[str] = [
    "analyze",
    "compare",
    "evaluate",
    "weighing",
    "pros and cons",
    "trade-offs",
    "tradeoffs",
    "decide whether",
    "decide between",
    "should i",
    "should we",
    "reason through",
    "help me decide",
]

# Strong REFLECT language (temporal / historical framing).
_REFLECT_MARKERS: list[str] = [
    "how have i changed",
    "how have i",
    "how did i",
    "priorities changed",
    "what changed",
    "changed over",
    "reflect",
    "looking back",
    "look back",
    "compared to before",
    "compared to earlier",
    "over the last few months",
    "over the past",
]

_REASON_SIGNALS = frozenset(
    {"explicit analysis request", "complex decision", "multiple relevant goals"}
)
_REFLECT_SIGNALS = frozenset({"historical reasoning", "pattern analysis", "reflection request"})

COMPLEXITY_CAP: float = 0.2


class ReasoningPlanner(BaseReasoningPlanner):
    """Builds the minimum-sufficient ``ReasoningPlan`` for one DEEP call."""

    def plan(
        self,
        state: ChronosState,
        routing_result: AIRoutingResult,
    ) -> ReasoningPlan:
        text = self._text(state)
        signals = routing_result.signals if routing_result is not None else []

        modes: list[ReasoningMode] = []
        reasons: list[str] = []

        if self._should_classify(state, text):
            modes.append(ReasoningMode.CLASSIFY)
            reasons.append("the intent is ambiguous or unknown")

        if self._should_interpret(state):
            modes.append(ReasoningMode.INTERPRET)
            reasons.append("there is meaningful user state to interpret")

        if self._should_reason(state, text, signals):
            modes.append(ReasoningMode.REASON)
            reasons.append("the interaction involves a decision or explicit analysis")

        if self._should_reflect(state, text, signals):
            modes.append(ReasoningMode.REFLECT)
            reasons.append("the interaction asks for reflection across past and present")

        modes.append(ReasoningMode.GENERATE)
        reasons.append("produce the final natural-language response")

        non_generate = len(modes) - 1
        return ReasoningPlan(
            modes=modes,
            primary_mode=self._primary_mode(state, modes),
            reason=("; ".join(reasons)).capitalize() + ".",
            confidence=round(min(0.95, 0.45 + 0.15 * non_generate), 2),
            requires_history=(
                ReasoningMode.REFLECT in modes or "historical reasoning" in signals
            ),
            requires_context=non_generate > 0,
        )

    # ------------------------------------------------------------------
    # Mode-selection rules
    # ------------------------------------------------------------------

    @staticmethod
    def _should_classify(state: ChronosState, text: str) -> bool:
        intent = state.intent
        intent_value = intent.intent if intent else None
        if intent_value is not None and intent_value != IntentType.UNKNOWN:
            return False
        return len(text.strip()) >= CLASSIFY_MIN_LENGTH

    @staticmethod
    def _meaningful_state(user_state) -> bool:
        if user_state is None:
            return False
        if (
            user_state.emotional_state is not None
            and user_state.emotional_state.value != "NEUTRAL"
        ):
            return True
        if user_state.cognitive_state is not None:
            return True
        if user_state.valence is not None and abs(user_state.valence) >= 0.2:
            return True
        if user_state.energy is not None:
            return True
        return False

    def _should_interpret(self, state: ChronosState) -> bool:
        if self._meaningful_state(state.user_state):
            return True
        if state.contradictions:
            return True
        goal = state.goal_analysis
        if (
            goal is not None
            and goal.status not in (None, GoalStatus.NONE)
            and self._meaningful_state(state.user_state)
        ):
            return True
        return False

    def _should_reason(
        self, state: ChronosState, text: str, signals: list[str]
    ) -> bool:
        intent = state.intent
        intent_value = intent.intent if intent else None

        if any(s in signals for s in _REASON_SIGNALS):
            return True

        if (
            intent_value == IntentType.DECISION
            and self._complexity(text) >= 0.12
        ):
            return True

        if self._multiple_relevant_goals(state):
            return True

        return any(marker in text for marker in _REASON_MARKERS)

    def _should_reflect(
        self, state: ChronosState, text: str, signals: list[str]
    ) -> bool:
        intent = state.intent
        intent_value = intent.intent if intent else None

        if intent_value == IntentType.REFLECTION:
            return True
        if any(s in signals for s in _REFLECT_SIGNALS):
            return True
        return any(marker in text for marker in _REFLECT_MARKERS)

    # ------------------------------------------------------------------
    # Primary mode
    # ------------------------------------------------------------------

    @staticmethod
    def _primary_mode(
        state: ChronosState, modes: list[ReasoningMode]
    ) -> ReasoningMode:
        intent = state.intent
        intent_value = intent.intent if intent else None
        if intent_value == IntentType.REFLECTION:
            return ReasoningMode.REFLECT
        if intent_value == IntentType.DECISION:
            return ReasoningMode.REASON
        for mode in (
            ReasoningMode.REASON,
            ReasoningMode.REFLECT,
            ReasoningMode.INTERPRET,
            ReasoningMode.CLASSIFY,
        ):
            if mode in modes:
                return mode
        return ReasoningMode.GENERATE

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _text(state: ChronosState) -> str:
        if state is None or state.current_input is None:
            return ""
        return (state.current_input.content or "").lower()

    @staticmethod
    def _multiple_relevant_goals(state: ChronosState) -> bool:
        goal = state.goal_analysis
        if goal is not None and goal.items and len(goal.items) >= 2:
            return True
        return len(state.goals) >= 3

    @staticmethod
    def _complexity(text: str) -> float:
        n_questions = text.count("?")
        n_sentences = max(1, sum(1 for c in text if c in ".!?;"))
        score = (
            0.06 * n_questions
            + 0.04 * min(n_sentences, 6)
            + 0.02 * (len(text) / 200)
        )
        return round(min(COMPLEXITY_CAP, score), 3)
