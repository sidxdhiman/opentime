"""Deterministic, AI-free response generation for the ChronOS Engine.

The ``ResponseGenerator`` takes a fully structured ``ChronosState`` (intent,
user state, goals, consistency, context) and produces a concise,
human-readable interpretation of the interaction.

Everything here is pure template / rule logic:

* No LLM calls.
* No network calls.
* No retrieval changes.
* No AI reasoning.

The generator only mentions information that is actually present in the
state. Missing evidence yields neutral phrases or ``None``, never a
fabricated emotion, goal, memory or pattern.

Emotional language is deliberately cautious: the generator says "the input
suggests frustration", never "you are frustrated".
"""

from typing import Dict, List, Optional, Set

from chronos_engine.core.interfaces import BaseResponseGenerator
from chronos_engine.core.models import IntentType
from chronos_engine.response.models import ChronosInterpretation, DeterministicResponse
from chronos_engine.state.models import (
    ChronosState,
    EngineStateResult,
    EngineStatus,
    GoalStatus,
    UserCognitiveState,
    UserEmotionState,
)

# ---------------------------------------------------------------------------
# Intent → natural-language summary (section 7)
# ---------------------------------------------------------------------------

INTENT_SUMMARIES: Dict[IntentType, str] = {
    IntentType.QUESTION: "You appear to be looking for an answer.",
    IntentType.REQUEST: "You appear to be asking ChronOS to perform an action.",
    IntentType.DECISION: "You appear to be evaluating a decision.",
    IntentType.PLANNING: "You appear to be planning a course of action.",
    IntentType.PROBLEM_SOLVING: "You appear to be trying to solve a problem.",
    IntentType.REFLECTION: "You appear to be reflecting on your situation.",
    IntentType.CREATION: "You appear to be asking for something to be created.",
    IntentType.STATUS_UPDATE: "You appear to be reporting progress or a current state.",
    IntentType.EMOTIONAL_SUPPORT: (
        "You appear to be looking for support around your current situation."
    ),
    IntentType.JOURNAL_ENTRY: (
        "This appears to be a personal reflection or journal-style entry."
    ),
    IntentType.COMMAND: "You appear to be giving ChronOS a direct instruction.",
    IntentType.INFORMATION: "You appear to be looking for information.",
    IntentType.UNKNOWN: "ChronOS is not yet confident about what you are trying to accomplish.",
}

# ---------------------------------------------------------------------------
# Operational-state rules (section 13)
# ---------------------------------------------------------------------------

NEGATIVE_EMOTIONS: Set[UserEmotionState] = {
    UserEmotionState.FRUSTRATED,
    UserEmotionState.ANGRY,
    UserEmotionState.ANXIOUS,
    UserEmotionState.OVERWHELMED,
    UserEmotionState.SAD,
    UserEmotionState.TIRED,
}

STRONG_NEGATIVE_EMOTIONS: Set[UserEmotionState] = {
    UserEmotionState.FRUSTRATED,
    UserEmotionState.ANGRY,
    UserEmotionState.ANXIOUS,
    UserEmotionState.OVERWHELMED,
    UserEmotionState.SAD,
}

POSITIVE_EMOTIONS: Set[UserEmotionState] = {
    UserEmotionState.RELIEVED,
    UserEmotionState.POSITIVE,
    UserEmotionState.EXCITED,
    UserEmotionState.MOTIVATED,
    UserEmotionState.CONFIDENT,
}

UNCERTAIN_COGNITIVE: Set[UserCognitiveState] = {
    UserCognitiveState.UNCERTAIN,
    UserCognitiveState.CONFUSED,
}

# Important intents that benefit from more context before interpretation.
IMPORTANT_INTENTS: Set[IntentType] = {
    IntentType.DECISION,
    IntentType.REQUEST,
    IntentType.CREATION,
    IntentType.PLANNING,
    IntentType.PROBLEM_SOLVING,
}

EXPLORATORY_INTENTS: Set[IntentType] = {
    IntentType.QUESTION,
    IntentType.INFORMATION,
    IntentType.PLANNING,
}

CONFLICT_TYPES: Set[str] = {
    "GOAL_CONFLICT",
    "DECISION_CHANGE",
    "PREFERENCE_CONFLICT",
    "STATEMENT_CONFLICT",
    "IDENTITY_CONFLICT",
}

# Emotion label → natural noun, so "suggests relief" reads better than
# "suggests relieved".
EMOTION_NOUNS: Dict[UserEmotionState, str] = {
    UserEmotionState.CALM: "calm",
    UserEmotionState.POSITIVE: "positivity",
    UserEmotionState.EXCITED: "excitement",
    UserEmotionState.CONFIDENT: "confidence",
    UserEmotionState.CURIOUS: "curiosity",
    UserEmotionState.NEUTRAL: "neutrality",
    UserEmotionState.UNCERTAIN: "uncertainty",
    UserEmotionState.OVERWHELMED: "feeling overwhelmed",
    UserEmotionState.FRUSTRATED: "frustration",
    UserEmotionState.ANXIOUS: "anxiety",
    UserEmotionState.SAD: "sadness",
    UserEmotionState.TIRED: "tiredness",
    UserEmotionState.ANGRY: "anger",
    UserEmotionState.MOTIVATED: "motivation",
    UserEmotionState.FOCUSED: "focus",
    UserEmotionState.RELIEVED: "relief",
}

# Rendered-text status emojis (section 16 / 17).
STATUS_EMOJIS: Dict[EngineStatus, str] = {
    EngineStatus.NEUTRAL: "⚪",
    EngineStatus.CURIOUS: "🔵",
    EngineStatus.CONFIDENT: "🟢",
    EngineStatus.CAUTIOUS: "🟠",
    EngineStatus.CONCERNED: "🟡",
    EngineStatus.UNCERTAIN: "🟠",
    EngineStatus.ALERT: "🔴",
    EngineStatus.POSITIVE: "🟢",
    EngineStatus.FOCUSED: "🟢",
    EngineStatus.WAITING_FOR_CONTEXT: "⚪",
}


class ResponseGenerator(BaseResponseGenerator):
    """Builds a deterministic, human-readable interpretation from a state.

    Pure computation over ``ChronosState``: identical states always produce
    identical responses. No AI is used anywhere in this path.
    """

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def generate(self, state: ChronosState) -> DeterministicResponse:
        interpretation = self._interpret(state)
        op_state, next_step = self._operational(state, interpretation)
        observations = self._observations(state)
        rendered = self._render(state, interpretation, op_state, observations, next_step)

        return DeterministicResponse(
            user_signal=interpretation.user_state_summary,
            chronos_interpretation=interpretation,
            observations=observations,
            chronos_state=op_state,
            suggested_next_step=next_step,
            rendered=rendered,
        )

    # ------------------------------------------------------------------
    # Chronos interpretation (section 5)
    # ------------------------------------------------------------------

    def _interpret(self, state: ChronosState) -> ChronosInterpretation:
        return ChronosInterpretation(
            user_state_summary=self._user_state_summary(state),
            intent_summary=self._intent_summary(state),
            goal_summary=self._goal_summary(state),
            context_summary=self._context_summary(state),
            pattern_summary=self._pattern_summary(state),
            consistency_summary=self._consistency_summary(state),
        )

    def _user_state_summary(self, state: ChronosState) -> str:
        user_state = state.user_state
        if user_state is None:
            return (
                "ChronOS does not yet have enough evidence to confidently "
                "interpret the current interaction."
            )

        phrases: List[str] = []
        if user_state.emotional_state and user_state.emotional_state != UserEmotionState.NEUTRAL:
            noun = EMOTION_NOUNS.get(
                user_state.emotional_state, user_state.emotional_state.value.lower()
            )
            phrases.append(f"suggests {noun}")
        if user_state.cognitive_state in UNCERTAIN_COGNITIVE:
            phrases.append(f"signals {user_state.cognitive_state.value.lower()}")
        if user_state.valence is not None and user_state.valence >= 0.4:
            phrases.append("carries a positive tone")
        elif user_state.valence is not None and user_state.valence <= -0.4:
            phrases.append("carries a negative tone")

        if not phrases:
            return "The input does not carry a clear emotional or cognitive signal."
        return "The input " + " and ".join(phrases) + "."

    def _intent_summary(self, state: ChronosState) -> str:
        intent_result = state.intent
        if intent_result is None or intent_result.intent is None:
            return INTENT_SUMMARIES[IntentType.UNKNOWN]
        return INTENT_SUMMARIES[intent_result.intent]

    def _goal_summary(self, state: ChronosState) -> Optional[str]:
        goal = state.goal_analysis
        if goal is None or goal.status in (None, GoalStatus.NONE):
            return None
        name = goal.goal or goal.matched_existing_goal

        if goal.status == GoalStatus.NEW:
            return f"ChronOS detected a possible new goal: {name}."
        if goal.status == GoalStatus.ACTIVE:
            return f"This appears related to your active goal of {name}."
        if goal.status == GoalStatus.PROGRESS:
            return f"This appears to represent progress toward your goal of {name}."
        if goal.status == GoalStatus.COMPLETED:
            return f"This appears to indicate completion of the goal: {name}."
        if goal.status == GoalStatus.BLOCKED:
            return f"The current goal ({name}) appears to be blocked."
        if goal.status == GoalStatus.ABANDONED:
            return "The current input suggests that you may no longer be pursuing this goal."
        if goal.status == GoalStatus.CHANGED:
            return "The current input suggests that this goal has changed direction."
        return None

    def _context_summary(self, state: ChronosState) -> str:
        context = state.context
        parts: List[str] = []
        if context and context.relevant_memories:
            n = len(context.relevant_memories)
            parts.append(f"{n} relevant past {'memory' if n == 1 else 'memories'}")
        if context and context.timeline_events:
            n = len(context.timeline_events)
            parts.append(f"{n} timeline {'event' if n == 1 else 'events'}")
        if state.goals:
            n = len(state.goals)
            parts.append(f"{n} active {'goal' if n == 1 else 'goals'}")

        if not parts:
            return "No significant historical context was available for this interaction."
        return "ChronOS drew on " + ", ".join(parts) + " to inform this interpretation."

    def _pattern_summary(self, state: ChronosState) -> Optional[str]:
        if not state.patterns:
            return None
        categories = ", ".join(sorted({p.category.value for p in state.patterns})[:3])
        return (
            f"ChronOS has previously identified recurring {categories} "
            "patterns related to this context."
        )

    def _consistency_summary(self, state: ChronosState) -> Optional[str]:
        contradictions = state.contradictions or []
        if not contradictions:
            if self._has_context(state):
                return "ChronOS found no significant conflict with the available context."
            return None
        for ctype, text in (
            ("GOAL_CHANGE", "ChronOS noticed a change from a previously stated goal."),
            (
                "DECISION_CHANGE",
                "ChronOS noticed that a previously stated decision appears to have changed.",
            ),
            (
                "PREFERENCE_CONFLICT",
                "ChronOS detected a possible change in an established preference.",
            ),
        ):
            if any(c.type == ctype for c in contradictions):
                return text
        return "ChronOS detected a possible conflict with previously stored context."

    # ------------------------------------------------------------------
    # Observations (WHAT CHRONOS NOTICED)
    # ------------------------------------------------------------------

    def _observations(self, state: ChronosState) -> List[str]:
        observations: List[str] = []
        goal = state.goal_analysis
        if goal is not None and goal.status not in (None, GoalStatus.NONE):
            name = goal.goal or goal.matched_existing_goal
            status_text = {
                GoalStatus.NEW: f"ChronOS detected a possible new goal: {name}.",
                GoalStatus.ACTIVE: f"The input relates to the active goal: {name}.",
                GoalStatus.PROGRESS: f"The input reflects progress toward the goal: {name}.",
                GoalStatus.COMPLETED: f"The goal appears to be completed: {name}.",
                GoalStatus.BLOCKED: f"The current goal appears to be blocked: {name}.",
                GoalStatus.ABANDONED: "The input suggests a goal may no longer be pursued.",
                GoalStatus.CHANGED: "The current input suggests a goal has changed direction.",
            }.get(goal.status)
            if status_text:
                observations.append(status_text)

        for c in state.contradictions or []:
            text = self._contradiction_observation(c)
            if text and text not in observations:
                observations.append(text)

        pattern_summary = self._pattern_summary(state)
        if pattern_summary and pattern_summary not in observations:
            observations.append(pattern_summary)

        return observations

    @staticmethod
    def _contradiction_observation(c) -> str:
        if c.type == "GOAL_CHANGE":
            return "ChronOS noticed a change from a previously stated goal."
        if c.type == "DECISION_CHANGE":
            return "A previously stated decision appears to have changed."
        if c.type == "PREFERENCE_CONFLICT":
            return "A possible change in an established preference was detected."
        return "A possible conflict with previously stored context was detected."

    # ------------------------------------------------------------------
    # Operational state (sections 12-14)
    # ------------------------------------------------------------------

    def _operational(
        self, state: ChronosState, interpretation: ChronosInterpretation
    ) -> tuple[EngineStateResult, Optional[str]]:
        user_state = state.user_state
        intent = state.intent

        emotion = user_state.emotional_state if user_state else None
        cognitive = user_state.cognitive_state if user_state else None
        valence = user_state.valence if user_state else None
        urgency = user_state.urgency if user_state else None
        us_conf = user_state.confidence if user_state else 0.0

        intent_label = intent.intent if intent else None
        intent_conf = intent.confidence if intent else 0.0
        has_intent = intent_label is not None and intent_label != IntentType.UNKNOWN

        goal = state.goal_analysis
        goal_status = goal.status if goal else GoalStatus.NONE
        goal_conf = goal.confidence if goal else 0.0

        contradictions = state.contradictions or []
        has_context = self._has_context(state)

        evidence = self._evidence(
            intent_conf, us_conf, goal_conf, contradictions
        )
        op_state: EngineStateResult
        next_step: Optional[str]

        # --- ALERT: high urgency combined with a meaningful conflict/blocker.
        if (
            urgency is not None
            and urgency >= 0.5
            and (contradictions or goal_status == GoalStatus.BLOCKED)
        ):
            op_state = EngineStateResult(
                status=EngineStatus.ALERT,
                confidence=self._confidence(evidence),
                reason="High urgency is combined with a meaningful conflict or blocker.",
            )
            next_step = "Prioritize the blocker before continuing."
            return op_state, next_step

        # --- CONCERNED: strong negative signal + blocked goal, or a real
        # --- conflict / high-confidence contradiction.
        negative_plus_blocked = (
            emotion in STRONG_NEGATIVE_EMOTIONS
            and goal_status == GoalStatus.BLOCKED
        )
        strong_negative = emotion in STRONG_NEGATIVE_EMOTIONS and us_conf >= 0.5
        meaningful_conflict = any(c.type in CONFLICT_TYPES for c in contradictions)
        high_confidence_contradiction = any(c.confidence >= 0.8 for c in contradictions)

        if (
            negative_plus_blocked
            or strong_negative
            or meaningful_conflict
            or high_confidence_contradiction
        ):
            reason = self._concerned_reason(state, emotion, goal_status, contradictions)
            op_state = EngineStateResult(
                status=EngineStatus.CONCERNED,
                confidence=self._confidence(evidence),
                reason=reason,
            )
            if goal_status == GoalStatus.BLOCKED:
                next_step = (
                    "Identify the specific blocker before deciding whether "
                    "to change the goal."
                )
            else:
                next_step = "Clarify whether the earlier context still holds before proceeding."
            return op_state, next_step

        # --- POSITIVE: clear positive signal, strong positive tone, or
        # --- a completed goal.
        positive_emotion = emotion in POSITIVE_EMOTIONS and us_conf >= 0.3
        positive_tone = valence is not None and valence >= 0.4 and us_conf >= 0.3
        if positive_emotion or positive_tone or goal_status == GoalStatus.COMPLETED:
            reason = self._positive_reason(state, emotion, goal_status)
            op_state = EngineStateResult(
                status=EngineStatus.POSITIVE,
                confidence=self._confidence(evidence),
                reason=reason,
            )
            next_step = "Continue tracking progress toward the current goal."
            return op_state, next_step

        # --- FOCUSED: high engagement + focused cognitive state + clear intent.
        if (
            user_state is not None
            and user_state.engagement is not None
            and user_state.engagement >= 0.6
            and cognitive == UserCognitiveState.FOCUSED
            and has_intent
        ):
            op_state = EngineStateResult(
                status=EngineStatus.FOCUSED,
                confidence=self._confidence(evidence),
                reason=(
                    "The input shows high engagement and a focused cognitive "
                    "state with a clear intent."
                ),
            )
            next_step = "Continue tracking progress toward the current goal."
            return op_state, next_step

        # --- WAITING_FOR_CONTEXT: important intent or genuinely ambiguous
        # --- input with no stored context to draw on.
        empty_state = (
            user_state is None
            and not has_intent
            and not has_context
        )
        important_without_context = (
            intent_label in IMPORTANT_INTENTS and not has_context
        )
        ambiguous_without_context = (
            not has_intent and us_conf > 0 and not has_context
        )
        if empty_state or important_without_context or ambiguous_without_context:
            op_state = EngineStateResult(
                status=EngineStatus.WAITING_FOR_CONTEXT,
                confidence=self._confidence(evidence, cap=0.5),
                reason=(
                    "ChronOS does not yet have enough context to interpret "
                    "this interaction."
                ),
            )
            next_step = (
                "Provide more context if you want ChronOS to make a more "
                "informed assessment."
            )
            return op_state, next_step

        # --- CONFIDENT: clear intent + strong evidence + no contradictions.
        no_negative = emotion is None or emotion not in NEGATIVE_EMOTIONS
        no_uncertainty = (
            emotion != UserEmotionState.UNCERTAIN
            and cognitive not in UNCERTAIN_COGNITIVE
        )
        if (
            has_intent
            and intent_conf >= 0.6
            and us_conf >= 0.4
            and no_negative
            and no_uncertainty
            and not contradictions
        ):
            op_state = EngineStateResult(
                status=EngineStatus.CONFIDENT,
                confidence=self._confidence(evidence),
                reason=(
                    "The intent is clear, the evidence is strong, and no "
                    "contradiction was detected."
                ),
            )
            next_step = "Continue tracking progress toward the current goal."
            return op_state, next_step

        # --- CAUTIOUS: high uncertainty, moderate/low evidence, or a goal
        # --- that appears to have changed direction.
        high_uncertainty = (
            emotion == UserEmotionState.UNCERTAIN or cognitive in UNCERTAIN_COGNITIVE
        )
        goal_changed = (
            goal_status == GoalStatus.CHANGED
            or any(c.type == "GOAL_CHANGE" for c in contradictions)
        )
        low_evidence_with_context = (
            0 < self._max_evidence(evidence) < 0.5 and has_context
        )
        if high_uncertainty or goal_changed or low_evidence_with_context:
            reason = self._cautious_reason(state, goal_changed, has_context)
            op_state = EngineStateResult(
                status=EngineStatus.CAUTIOUS,
                confidence=self._confidence(evidence),
                reason=reason,
            )
            if goal_changed:
                next_step = (
                    "Confirm whether the new direction should replace the "
                    "previous goal."
                )
            elif intent_label == IntentType.DECISION:
                next_step = "Clarify the missing information before making the decision."
            else:
                next_step = (
                    "Provide more context if you want ChronOS to make a more "
                    "informed assessment."
                )
            return op_state, next_step

        # --- UNCERTAIN: an intent/emotion signal is absent while stored
        # --- context exists but yields no clear reading.
        if not has_intent and us_conf == 0 and has_context:
            op_state = EngineStateResult(
                status=EngineStatus.UNCERTAIN,
                confidence=self._confidence(evidence, cap=0.5),
                reason=(
                    "ChronOS has insufficient evidence to interpret the "
                    "current interaction."
                ),
            )
            next_step = (
                "Provide more context if you want ChronOS to make a more "
                "informed assessment."
            )
            return op_state, next_step

        # --- CURIOUS: an exploratory intent paired with curiosity.
        if (
            intent_label in EXPLORATORY_INTENTS
            and (emotion == UserEmotionState.CURIOUS or cognitive == UserCognitiveState.EXPLORATORY)
        ):
            op_state = EngineStateResult(
                status=EngineStatus.CURIOUS,
                confidence=self._confidence(evidence),
                reason=(
                    "The input shows curiosity and an intent to learn or explore."
                ),
            )
            next_step = None
            return op_state, next_step

        # --- NEUTRAL: nothing else applies.
        op_state = EngineStateResult(
            status=EngineStatus.NEUTRAL,
            confidence=self._confidence(evidence),
            reason=(
                "The interaction does not present strong signals in any direction."
            ),
        )
        return op_state, None

    # ------------------------------------------------------------------
    # Operational-state reasons (section 14)
    # ------------------------------------------------------------------

    @staticmethod
    def _concerned_reason(
        state: ChronosState,
        emotion: Optional[UserEmotionState],
        goal_status: GoalStatus,
        contradictions: list,
    ) -> str:
        if emotion is not None and goal_status == GoalStatus.BLOCKED:
            return (
                f"The current input suggests {EMOTION_NOUNS.get(emotion, emotion.value.lower())} "
                "and the associated goal appears blocked."
            )
        if emotion is not None and emotion in STRONG_NEGATIVE_EMOTIONS:
            noun = EMOTION_NOUNS.get(emotion, emotion.value.lower())
            return (
                f"The current input contains strong {noun} signals that "
                "ChronOS treats as significant."
            )
        if any(c.type == "GOAL_CONFLICT" for c in contradictions):
            return (
                "ChronOS detected a possible conflict with a previously "
                "stated goal."
            )
        if any(c.confidence >= 0.8 for c in contradictions):
            return (
                "ChronOS detected a high-confidence contradiction with "
                "previously stored context."
            )
        return (
            "ChronOS detected a possible conflict with previously stored "
            "context."
        )

    @staticmethod
    def _positive_reason(
        state: ChronosState,
        emotion: Optional[UserEmotionState],
        goal_status: GoalStatus,
    ) -> str:
        parts: List[str] = []
        if emotion in POSITIVE_EMOTIONS:
            parts.append(
                f"the input suggests {EMOTION_NOUNS.get(emotion, emotion.value.lower())}"
            )
        if goal_status == GoalStatus.COMPLETED:
            parts.append("the associated goal appears to be completed")
        if not parts:
            return "The input carries a clearly positive tone."
        return "The interaction reads positively: " + " and ".join(parts) + "."

    @staticmethod
    def _cautious_reason(state: ChronosState, goal_changed: bool, has_context: bool) -> str:
        if goal_changed:
            return (
                "The current input suggests that a previously stated goal "
                "has changed direction."
            )
        if not has_context:
            return (
                "The available context is incomplete, so ChronOS interprets "
                "this cautiously."
            )
        return (
            "The available evidence is moderate or low, so ChronOS interprets "
            "this cautiously."
        )

    # ------------------------------------------------------------------
    # Evidence & confidence
    # ------------------------------------------------------------------

    @staticmethod
    def _evidence(
        intent_conf: float, us_conf: float, goal_conf: float, contradictions: list
    ) -> List[float]:
        components: List[float] = []
        for value in (intent_conf, us_conf, goal_conf):
            if value and value > 0:
                components.append(value)
        for c in contradictions:
            if c.confidence and c.confidence > 0:
                components.append(c.confidence)
        return components

    @staticmethod
    def _max_evidence(evidence: List[float]) -> float:
        return max(evidence, default=0.0)

    @staticmethod
    def _confidence(evidence: List[float], cap: float = 0.95) -> float:
        if not evidence:
            return round(min(cap, 0.2), 2)
        value = 0.40 + 0.40 * max(evidence) + 0.04 * (len(evidence) - 1)
        return round(min(cap, value), 2)

    # ------------------------------------------------------------------
    # Rendering (section 16 / 17)
    # ------------------------------------------------------------------

    def _render(
        self,
        state: ChronosState,
        interpretation: ChronosInterpretation,
        op_state: EngineStateResult,
        observations: List[str],
        next_step: Optional[str],
    ) -> str:
        lines: List[str] = []
        lines.append("USER SIGNAL")
        lines.append("")
        lines.append(interpretation.user_state_summary)
        lines.append("")
        lines.append("WHAT CHRONOS UNDERSTANDS")
        lines.append("")
        lines.append(interpretation.intent_summary)
        if interpretation.goal_summary:
            lines.append(interpretation.goal_summary)
        lines.append("")
        lines.append("WHAT CHRONOS NOTICED")
        lines.append("")
        if observations:
            lines.extend(observations)
        elif interpretation.consistency_summary:
            lines.append(interpretation.consistency_summary)
        else:
            lines.append("No significant observations were made for this interaction.")
        if (
            interpretation.consistency_summary
            and interpretation.consistency_summary not in observations
        ):
            lines.append(interpretation.consistency_summary)
        lines.append(interpretation.context_summary)
        if interpretation.pattern_summary and interpretation.pattern_summary not in observations:
            lines.append(interpretation.pattern_summary)
        lines.append("")
        lines.append("CHRONOS STATE")
        lines.append("")
        emoji = STATUS_EMOJIS.get(op_state.status, "⚪")
        lines.append(f"{emoji} {op_state.status.value.replace('_', ' ').title()}")
        lines.append("")
        lines.append(op_state.reason or "")
        lines.append("")
        lines.append("SUGGESTED NEXT STEP")
        lines.append("")
        lines.append(next_step or "No next step is suggested yet.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _has_context(state: ChronosState) -> bool:
        context = state.context
        if context is None:
            return False
        return bool(
            context.relevant_memories
            or context.timeline_events
            or state.goals
            or state.patterns
        )
