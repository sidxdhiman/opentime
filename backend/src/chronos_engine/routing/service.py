"""Deterministic, offline AI routing for the ChronOS Engine.

The ``AIRouter`` answers one question about a ``ChronosState``:

    "Can the deterministic engine adequately handle this interaction,
     or would an AI model materially improve the result?"

The router NEVER calls an LLM. It never touches the network. It only reads
the structured state and returns a routing decision (``FAST`` or ``DEEP``).

Design
------
* **Default to FAST.** AI is an escalation mechanism; the router only routes
  to ``DEEP`` when explicit evidence shows the deterministic state is
  insufficient.
* **Scoring, not if/else chains.** ``deep_score`` and ``fast_score`` are
  accumulated from deterministic signal groups. A ``DEEP`` decision requires
  ``deep_score`` to clear a minimum threshold AND to beat ``fast_score``.
* **Emotion alone never routes to AI.** ``"I'm frustrated."`` is FAST.
  Frustration plus historical reasoning ("considering everything I've told
  you...") is DEEP.
* **Zero dependencies.** Pure computation over existing in-memory state.
"""

from typing import Dict, List, Set, Tuple

from chronos_engine.core.interfaces import BaseAIRouter
from chronos_engine.core.models import IntentType
from chronos_engine.routing.models import AIRoutingResult, RoutingPath
from chronos_engine.state.models import ChronosState, GoalStatus

# Minimum deep_score required before the router will escalate to AI. Keeping
# this meaningful means a lone weak signal never triggers an AI call.
DEEP_MIN_SCORE: float = 0.45

# ---------------------------------------------------------------------------
# Deep-path signal tables
# ---------------------------------------------------------------------------

# Explicit temporal / personal reasoning requests (section 12). These are the
# strongest signal: the user is asking ChronOS to reason across its history.
HISTORICAL_SIGNALS: List[Tuple[str, str]] = [
    ("previously", "historical reasoning"),
    ("everything i've told you", "historical reasoning"),
    ("everything you know about", "historical reasoning"),
    ("based on our conversations", "historical reasoning"),
    ("based on my history", "historical reasoning"),
    ("based on everything", "historical reasoning"),
    ("over the last", "historical reasoning"),
    ("over the past", "historical reasoning"),
    ("over the last few months", "historical reasoning"),
    ("in the past", "historical reasoning"),
    ("a few months ago", "historical reasoning"),
    ("last few months", "historical reasoning"),
    ("compared to before", "historical reasoning"),
    ("compared to earlier", "historical reasoning"),
    ("have i changed", "historical reasoning"),
    ("what patterns do you see", "historical reasoning"),
    ("looking back", "historical reasoning"),
    ("look back", "historical reasoning"),
    ("remember when", "historical reasoning"),
    ("you've known", "historical reasoning"),
    ("you know about", "historical reasoning"),
]

# Pattern-interpretation requests (section 15). Only count when there is
# relevant historical evidence to interpret.
PATTERN_SIGNALS: List[Tuple[str, str]] = [
    ("why do i keep", "pattern analysis"),
    ("why do i always", "pattern analysis"),
    ("keep ending up", "pattern analysis"),
    ("keep getting stuck", "pattern analysis"),
    ("same type of problem", "pattern analysis"),
    ("same kind of problem", "pattern analysis"),
    ("same problem", "pattern analysis"),
    ("recurring", "pattern analysis"),
    ("pattern", "pattern analysis"),
    ("going in circles", "pattern analysis"),
    ("in a loop", "pattern analysis"),
    ("stuck again", "pattern analysis"),
    ("the same thing", "pattern analysis"),
]

# Explicit requests for analysis / reasoning (sections 8 & 16).
REASONING_SIGNALS: List[Tuple[str, str]] = [
    ("analyze", "explicit analysis request"),
    ("compare", "explicit analysis request"),
    ("evaluate", "explicit analysis request"),
    ("reason through", "explicit analysis request"),
    ("reasoning", "explicit analysis request"),
    ("think about", "explicit analysis request"),
    ("help me decide", "explicit analysis request"),
    ("help me understand why", "explicit analysis request"),
    ("explain why", "explicit analysis request"),
    ("detailed analysis", "explicit analysis request"),
    ("deep dive", "explicit analysis request"),
    ("pros and cons", "explicit analysis request"),
    ("trade-offs", "explicit analysis request"),
    ("tradeoffs", "explicit analysis request"),
    ("weighing", "explicit analysis request"),
    ("considering everything", "explicit analysis request"),
    ("considering all", "explicit analysis request"),
    ("what this says about", "explicit analysis request"),
    ("tell me what this says", "explicit analysis request"),
]

# Ambiguous opinion-seeking phrases that only escalate when ChronOS has
# relevant history to ground them. "What do you think?" with no history is
# a plain question; with history it asks ChronOS to reason over stored state.
REASONING_HISTORY_SIGNALS: List[Tuple[str, str]] = [
    ("what do you think", "explicit analysis request"),
    ("think about this", "explicit analysis request"),
    ("what's your take", "explicit analysis request"),
]

# Reflection language (sections 8 & 19).
REFLECTION_SIGNALS: List[Tuple[str, str]] = [
    ("priorities changed", "reflection request"),
    ("how have i changed", "reflection request"),
    ("how have i", "reflection request"),
    ("how did i", "reflection request"),
    ("what changed", "reflection request"),
    ("changed over the", "reflection request"),
    ("changed over time", "reflection request"),
    ("reflect", "reflection request"),
    ("my priorities", "reflection request"),
]

# Complex-decision language (section 8). ``vs``/``versus`` and the
# ``decide between`` family strongly signal a decision even when the
# intent detector stays quiet.
DECISION_MARKERS: List[Tuple[str, str]] = [
    ("should i", "complex decision"),
    ("should we", "complex decision"),
    ("deciding whether", "complex decision"),
    ("decide whether", "complex decision"),
    ("choose between", "complex decision"),
    ("choosing between", "complex decision"),
    ("decide between", "complex decision"),
    ("is it better", "complex decision"),
    ("versus", "complex decision"),
    (" vs ", "complex decision"),
    ("or should i", "complex decision"),
]

# ---------------------------------------------------------------------------
# Fast-path signal tables
# ---------------------------------------------------------------------------

# Simple intents that the deterministic engine handles comfortably.
SIMPLE_INTENT_FAST: Dict[IntentType, str] = {
    IntentType.INFORMATION: "simple information request",
    IntentType.STATUS_UPDATE: "simple status update",
    IntentType.COMMAND: "simple command",
    IntentType.JOURNAL_ENTRY: "simple journal entry",
}

TRIVIAL_LENGTH: int = 30
SHORT_LENGTH: int = 60

# ---------------------------------------------------------------------------
# Weights (documented in the AIRouter docstring / this table)
# ---------------------------------------------------------------------------

#   Signal group                     deep   fast
HISTORICAL_WEIGHT = 0.5
PATTERN_WEIGHT = 0.4
REASONING_WEIGHT = 0.4
REFLECTION_WEIGHT = 0.4
DECISION_WEIGHT = 0.4
MULTI_GOAL_WEIGHT = 0.3
AMBIGUOUS_WEIGHT = 0.3
COMPLEXITY_CAP = 0.2

SIMPLE_INTENT_WEIGHT = 0.3
SIMPLE_STATUS_WEIGHT = 0.4
SIMPLE_PROGRESS_WEIGHT = 0.3
SIMPLE_PROBLEM_WEIGHT = 0.2
GOAL_CHANGE_WEIGHT = 0.25
STRONG_STATE_WEIGHT = 0.2
SHORT_INPUT_WEIGHT = 0.15
TRIVIAL_WEIGHT = 0.3


class AIRouter(BaseAIRouter):
    """Classifies whether a ``ChronosState`` needs an AI model.

    Deterministic and fully offline. Identical states always produce
    identical routing decisions. No LLM, no network, no retrieval.
    """

    def route(self, state: ChronosState) -> AIRoutingResult:
        text = self._text(state)
        signals: List[str] = []

        deep_score = 0.0
        fast_score = 0.0

        has_history = self._has_history(state)
        has_contradiction = bool(state.contradictions)

        # ---- Deep-path signals ----------------------------------------
        deep_signal_matches = self._match_deep_signals(text, has_history, state)
        deep_score += deep_signal_matches["score"]
        signals.extend(deep_signal_matches["labels"])

        # ---- Fast-path signals ----------------------------------------
        fast_blocks = self._match_fast_signals(
            state, text, has_contradiction, deep_signal_matches["has_deep_language"]
        )
        fast_score += fast_blocks["score"]
        signals.extend(fast_blocks["labels"])

        if not has_contradiction:
            signals.append("no unresolved contradiction")

        deep_score = round(deep_score, 3)
        fast_score = round(fast_score, 3)

        if deep_score >= DEEP_MIN_SCORE and deep_score > fast_score:
            path = RoutingPath.DEEP
            confidence = self._deep_confidence(deep_score)
            reason = self._deep_reason(deep_signal_matches["labels"])
        else:
            path = RoutingPath.FAST
            confidence = self._fast_confidence(fast_score)
            reason = (
                "The current interaction can be sufficiently interpreted "
                "using deterministic ChronOS state."
            )

        return AIRoutingResult(
            use_ai=path == RoutingPath.DEEP,
            path=path,
            confidence=confidence,
            reason=reason,
            signals=signals,
        )

    # ------------------------------------------------------------------
    # Deep-path scoring
    # ------------------------------------------------------------------

    def _match_deep_signals(
        self, text: str, has_history: bool, state: ChronosState
    ) -> Dict[str, object]:
        labels: List[str] = []
        score = 0.0

        historical = self._matched_labels(text, HISTORICAL_SIGNALS)
        if historical:
            score += HISTORICAL_WEIGHT
            labels.extend(historical)

        pattern = self._matched_labels(text, PATTERN_SIGNALS)
        if pattern and has_history:
            score += PATTERN_WEIGHT
            labels.extend(pattern)

        reasoning = self._matched_labels(text, REASONING_SIGNALS)
        if reasoning:
            score += REASONING_WEIGHT
            labels.extend(reasoning)

        reasoning_history = self._matched_labels(text, REASONING_HISTORY_SIGNALS)
        if reasoning_history and has_history:
            score += REASONING_WEIGHT
            labels.extend(reasoning_history)

        reflection = self._matched_labels(text, REFLECTION_SIGNALS)
        if reflection:
            score += REFLECTION_WEIGHT
            labels.extend(reflection)

        intent = state.intent
        intent_label = intent.intent if intent else None
        decision = self._matched_labels(text, DECISION_MARKERS)
        if decision and (intent_label == IntentType.DECISION or decision):
            score += DECISION_WEIGHT
            labels.extend(decision)

        if self._multiple_relevant_goals(state):
            score += MULTI_GOAL_WEIGHT
            labels.append("multiple relevant goals")

        if (
            intent_label in (None, IntentType.UNKNOWN)
            and len(text) >= 80
            and has_history
        ):
            score += AMBIGUOUS_WEIGHT
            labels.append("ambiguous intent")

        complexity = self._complexity(text)
        score += complexity
        if complexity > 0:
            labels.append("elevated complexity")

        return {
            "score": min(score, 1.8),
            "labels": self._dedupe(labels),
            "has_deep_language": bool(historical or pattern or reasoning or reflection),
        }

    @staticmethod
    def _matched_labels(text: str, table: List[Tuple[str, str]]) -> List[str]:
        labels: List[str] = []
        for marker, label in table:
            if marker in text:
                labels.append(label)
        return labels

    @staticmethod
    def _multiple_relevant_goals(state: ChronosState) -> bool:
        goal = state.goal_analysis
        if goal is not None and goal.items:
            if len(goal.items) >= 2:
                return True
        return len(state.goals) >= 3

    def _complexity(self, text: str) -> float:
        n_questions = text.count("?")
        n_sentences = max(1, sum(1 for c in text if c in ".!?;"))
        score = 0.06 * n_questions + 0.04 * min(n_sentences, 6) + 0.02 * (len(text) / 200)
        return round(min(COMPLEXITY_CAP, score), 3)

    # ------------------------------------------------------------------
    # Fast-path scoring
    # ------------------------------------------------------------------

    def _match_fast_signals(
        self,
        state: ChronosState,
        text: str,
        has_contradiction: bool,
        has_deep_language: bool,
    ) -> Dict[str, object]:
        labels: List[str] = []
        score = 0.0

        intent = state.intent
        intent_label = intent.intent if intent else None

        if intent_label is not None and not has_deep_language:
            if intent_label in SIMPLE_INTENT_FAST:
                if intent_label == IntentType.STATUS_UPDATE:
                    score += SIMPLE_STATUS_WEIGHT
                else:
                    score += SIMPLE_INTENT_WEIGHT
                labels.append(SIMPLE_INTENT_FAST[intent_label])
            elif intent_label == IntentType.PROBLEM_SOLVING:
                score += SIMPLE_PROBLEM_WEIGHT
                labels.append("simple problem report")
            elif intent_label == IntentType.CREATION:
                score += SIMPLE_INTENT_WEIGHT
                labels.append("simple creation request")
            elif intent_label == IntentType.REQUEST:
                score += SIMPLE_INTENT_WEIGHT
                labels.append("simple request")

        goal = state.goal_analysis
        goal_status = goal.status if goal else GoalStatus.NONE
        if not has_deep_language:
            if goal_status in (GoalStatus.PROGRESS, GoalStatus.COMPLETED):
                score += SIMPLE_PROGRESS_WEIGHT
                labels.append("simple progress update")
            if (
                goal_status in (GoalStatus.ABANDONED, GoalStatus.CHANGED)
                or any(c.type == "GOAL_CHANGE" for c in state.contradictions or [])
            ):
                score += GOAL_CHANGE_WEIGHT
                labels.append("deterministic goal change")

        if self._strong_state(state):
            score += STRONG_STATE_WEIGHT
            labels.append("strong deterministic state")

        length = len(text)
        if length < SHORT_LENGTH:
            score += SHORT_INPUT_WEIGHT
            labels.append("concise input")

        if intent_label in (None, IntentType.UNKNOWN) and length < TRIVIAL_LENGTH:
            score += TRIVIAL_WEIGHT
            labels.append("trivial input")

        return {"score": min(score, 1.5), "labels": self._dedupe(labels)}

    @staticmethod
    def _strong_state(state: ChronosState) -> bool:
        confidence_values: List[float] = []
        intent = state.intent
        if intent is not None and intent.confidence:
            confidence_values.append(intent.confidence)
        user_state = state.user_state
        if user_state is not None and user_state.confidence:
            confidence_values.append(user_state.confidence)
        goal = state.goal_analysis
        if goal is not None and goal.confidence:
            confidence_values.append(goal.confidence)
        if state.contradictions:
            return False
        return bool(confidence_values) and max(confidence_values) >= 0.6

    # ------------------------------------------------------------------
    # Confidence & reason
    # ------------------------------------------------------------------

    @staticmethod
    def _deep_confidence(deep_score: float) -> float:
        return round(min(0.95, 0.45 + 0.4 * deep_score), 2)

    @staticmethod
    def _fast_confidence(fast_score: float) -> float:
        return round(min(0.95, 0.45 + 0.4 * fast_score), 2)

    @staticmethod
    def _deep_reason(labels: List[str]) -> str:
        if "historical reasoning" in labels:
            return "Historical personal reasoning is required."
        if "pattern analysis" in labels:
            return "The request asks for pattern interpretation across stored history."
        if "complex decision" in labels and "multiple relevant goals" in labels:
            return "The request requires nuanced reasoning across multiple goals."
        if "complex decision" in labels:
            return "The request involves a complex decision with tradeoffs."
        if "explicit analysis request" in labels:
            return "The request explicitly asks for analysis."
        if "reflection request" in labels:
            return "The request requires reflection across past and present state."
        if "ambiguous intent" in labels:
            return "The intent is ambiguous and substantial enough that AI could clarify it."
        return "The deterministic state is insufficient to fully address this interaction."

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _text(state: ChronosState) -> str:
        if state is None or state.current_input is None:
            return ""
        return (state.current_input.content or "").lower()

    @staticmethod
    def _has_history(state: ChronosState) -> bool:
        context = state.context
        if context is None:
            return False
        return bool(
            context.relevant_memories or context.timeline_events or state.patterns
        )

    @staticmethod
    def _dedupe(labels: List[str]) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                out.append(label)
        return out
