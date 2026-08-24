"""Deterministic Temporal Relevance & Timing for the ChronOS Engine
(Phase 3G).

A meaningful past-self question existing does NOT mean ChronOS should
interrupt the user with it. Given the already-planned Phase 3F
``PastSelfQuestionResult`` and the evidence of the current interaction,
this module answers exactly one question: should that question be surfaced
NOW, deferred ("not now"), or skipped?

Strictly read-only pure computation over handed-in objects. It never
mutates threads or events, never persists anything, never schedules or
resurfaces anything, never creates notifications, never marks a question as
shown and never scans memory history. It never invents a past-self question
and never overrides Phase 3F: without a valid ``should_ask=True`` result it
returns SKIP immediately.

Relevance policy (deterministic, explainable)
---------------------------------------------
A. Direct topical continuity   Meaningful shared tokens (stopwords removed,
                               light stemming — the SAME normalization the
                               matcher uses) between the current input and
                               the thread subject / thread description /
                               PAST event description. The PRESENT event is
                               deliberately excluded: its description is
                               derived from the current input itself, so
                               overlap with it would be circular evidence.
B. Current-turn continuity     The Phase 3C matcher already matched THIS
                               turn's event to this very thread through its
                               own conservative topic-gated scoring. That
                               validated connection can open the relevance
                               door when independent tokens alone would not.
C. Goal continuity             Existing GoalDetector evidence clearly
                               relating to the thread. Supports relevance;
                               can never fabricate it.
D. Consistency / change        GOAL_CHANGE / DECISION_CHANGE / conflict
                               evidence relating to this specific thread
                               (shared meaningful tokens or explicit memory
                               links). Supports; can never fabricate.
E. Explicit reflection markers "looking back", "back then", "remember when"
                               ... strengthen relevance ONLY on top of
                               topical continuity; they never make an
                               unrelated thread relevant.

Generic-token-only overlap is documented as insufficient: it cannot open
the relevance door.

Timing / interruption policy (deterministic, explainable)
---------------------------------------------------------
Positive: current-turn continuation or resolution of THIS thread, explicit
reflection language, reflective/calm/curious interaction state, reflection
intent. Negative: high urgency, immediate problem-solving focus, clearly
transactional/factual requests, frustration directed at an unrelated task.

Emotion alone NEVER blocks: negative emotion about the thread's own topic
("I'm really upset because I keep wondering if quitting was a mistake") can
be the single most appropriate moment to surface the past-self question.
No clinical or psychological rules are applied — only contextual
interruption logic over already-computed state.

Decision policy:

- SKIP    no valid planned question, no meaningful topical relation,
          ambiguous/insufficient temporal evidence, or confidence too low
          to ground any surface decision.
- DEFER   the question is meaningful and topically related, but the current
          moment is not appropriate (urgent unrelated request, active
          problem-solving, transactional conversation). DEFER is a decision
          label only — nothing is scheduled or persisted.
- SURFACE_NOW meaningful relevance + appropriate timing + sufficient
          confidence.

Every score contribution is recorded as an explainable line in ``signals``
(positive) or ``blocking_signals`` (negative); there is no hidden scoring.
No AI, no Ollama, no embeddings: works fully with AI disabled. The engine
is synchronous because it performs no I/O (mirroring the planner/router
conventions).
"""


from chronos_engine.core.interfaces import BaseTemporalRelevanceEngine
from chronos_engine.core.models import UserInput
from chronos_engine.state.models import (
    ConsistencyResult,
    GoalAnalysisResult,
    IntentResult,
    UserCognitiveState,
    UserEmotionState,
    UserStateResult,
)
from chronos_engine.temporal.matcher import (
    _CHANGE_TYPES,
    _normalize,
    _split_meaningful,
)
from chronos_engine.temporal.models import (
    PastSelfQuestionResult,
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalLifecycleResult,
    TemporalRelevanceDecision,
    TemporalRelevanceResult,
    TemporalThread,
    TemporalThreadMatchResult,
)

# --- Calibration -------------------------------------------------------------
# Conservative on purpose. These values are implementation-defined, documented
# and tested — they are not claimed to be statistically calibrated.

MAX_RELEVANCE_SCORE = 0.95
MAX_TIMING_SCORE = 0.95
MAX_RELEVANCE_CONFIDENCE = 0.95

# Minimum topical continuity before ANY surfacing consideration. Below this
# the input simply is not about the thread's story.
RELEVANCE_FLOOR = 0.30
# Relevance required for SURFACE_NOW (single distinctive shared subject token
# plus one corroborating signal clears it; generic overlap never can).
RELEVANCE_SURFACE_MIN = 0.55

# Neutral starting point: an ordinary conversational moment has nothing
# against it. Positives add; blockers subtract; floored at zero.
TIMING_BASE = 0.35
# Timing required for SURFACE_NOW.
TIMING_SURFACE_MIN = 0.45

# Overall confidence required for SURFACE_NOW.
CONFIDENCE_SURFACE_MIN = 0.50

_TOPIC_BASE = 0.40          # >=1 meaningful shared token in thread.subject
_TOPIC_EXTRA = 0.08         # each additional meaningful shared subject token
_TOPIC_CAP = 0.60           # subject overlap alone stays below certainty
_DESCRIPTION_BASE = 0.28    # meaningful tokens found only in description/past
_DESCRIPTION_EXTRA = 0.06
_DESCRIPTION_CAP = 0.40     # prose-only overlap is weaker evidence
_GENERIC_ONLY_OVERLAP = 0.10
_MATCH_DOOR_BASE = 0.30     # door opened only by this turn's validated match

_CONTINUATION_RELEVANCE_BONUS = 0.20
_GOAL_CONTINUITY_BONUS = 0.15
_CONSISTENCY_RELEVANCE_BONUS = 0.15
_REFLECTION_RELEVANCE_BONUS = 0.20

_TRANSITION_TIMING_BONUS = 0.50     # this turn resolved/changed the thread
_CONTINUATION_TIMING_BONUS = 0.25   # this turn continued the thread
_REFLECTION_TIMING_BONUS = 0.15
_RECEPTIVE_STATE_TIMING_BONUS = 0.10  # calm / curious / exploratory language
_REFLECTION_INTENT_TIMING_BONUS = 0.10

_URGENCY_HIGH_THRESHOLD = 0.60
_URGENCY_HIGH_PENALTY = 0.45
_URGENCY_MODERATE_THRESHOLD = 0.30
_URGENCY_MODERATE_PENALTY = 0.25
_PROBLEM_SOLVING_PENALTY = 0.30
_TRANSACTIONAL_PENALTY = 0.35      # information/command intent
_UNRELATED_FRUSTRATION_PENALTY = 0.30

# Explicit look-back language. Phrase-specific so neutral sentences never
# fabricate reflection evidence.
_REFLECTION_MARKERS: list[str] = [
    "looking back",
    "look back",
    "in retrospect",
    "used to think",
    "used to believe",
    "used to feel",
    "remember when",
    "back then",
    "now i realize",
    "now i realise",
    "when i first started",
    "how far i",
    "i've changed",
    "i have changed",
    "since then",
]

# Interaction states whose language reads as receptive to reflection. This is
# contextual interruption logic over existing detector output, not psychology:
# negative emotions are intentionally absent here AND absent from blockers.
_RECEPTIVE_EMOTIONS = frozenset({UserEmotionState.CALM, UserEmotionState.CURIOUS})

# Intents describing an immediate task focus that should not be interrupted.
_TRANSACTIONAL_INTENTS = frozenset({"INFORMATION", "COMMAND"})

_PROBLEM_SOLVING_INTENT = "PROBLEM_SOLVING"
_REFLECTION_INTENT = "REFLECTION"

# Frustration/anger labels from the existing user-state detector; they only
# ever contribute when combined with problem-solving intent (frustration at a
# task), never on their own.
_TASK_FRUSTRATION_STATES = frozenset(
    {UserEmotionState.FRUSTRATED, UserEmotionState.ANGRY}
)


def _contains_any(text: str, patterns: list[str]) -> list[str]:
    return [p for p in patterns if p in text]


class TemporalRelevanceEngine(BaseTemporalRelevanceEngine):
    """Default deterministic implementation of BaseTemporalRelevanceEngine."""

    def evaluate(
        self,
        user_id: str,
        user_input: UserInput,
        past_self_question: PastSelfQuestionResult | None,
        thread: TemporalThread | None = None,
        events: list[TemporalEvent] | None = None,
        thread_match: TemporalThreadMatchResult | None = None,
        lifecycle_result: TemporalLifecycleResult | None = None,
        comparison: TemporalComparisonResult | None = None,
        intent: IntentResult | None = None,
        user_state: UserStateResult | None = None,
        goal_analysis: GoalAnalysisResult | None = None,
        consistency_result: ConsistencyResult | None = None,
    ) -> TemporalRelevanceResult:
        gate = self._hard_gate(past_self_question, thread, comparison, lifecycle_result)
        if gate is not None:
            return gate

        assert past_self_question is not None and thread is not None  # narrowed
        question = past_self_question

        events = events or []
        past_event, _present_event = self._anchor_events(question, events)
        text = (user_input.content or "").lower()

        # ---- Relevance -------------------------------------------------
        signals: list[str] = []
        blocking_signals: list[str] = []

        thread_memories = set(thread.related_memory_ids)
        if thread.origin_memory_id:
            thread_memories.add(thread.origin_memory_id)

        continuation_this_turn = self._continued_this_turn(
            question.thread_id, thread_match, lifecycle_result
        )
        transitioned_this_turn = self._transitioned_this_turn(
            question.thread_id, lifecycle_result
        )

        relevance_raw, door_open, relevance_signals = self._relevance(
            text=text,
            thread=thread,
            past_event=past_event,
            continuation_this_turn=continuation_this_turn,
            goal_analysis=goal_analysis,
            consistency_result=consistency_result,
            thread_memories=thread_memories,
        )
        signals.extend(relevance_signals)

        timing_raw, timing_signals, new_blockers = self._timing(
            text=text,
            intent=intent,
            user_state=user_state,
            transitioned_this_turn=transitioned_this_turn,
            continuation_this_turn=continuation_this_turn,
        )
        signals.extend(timing_signals)
        blocking_signals.extend(new_blockers)

        relevance_score = round(min(MAX_RELEVANCE_SCORE, max(0.0, relevance_raw)), 2)
        timing_score = round(min(MAX_TIMING_SCORE, max(0.0, timing_raw)), 2)
        confidence = round(
            min(
                MAX_RELEVANCE_CONFIDENCE,
                0.4 * relevance_score
                + 0.4 * timing_score
                + 0.2 * question.confidence,
            ),
            2,
        )

        decision, reason = self._decide(
            door_open=door_open,
            relevance=relevance_score,
            timing=timing_score,
            confidence=confidence,
        )

        return TemporalRelevanceResult(
            attempted=True,
            decision=decision,
            should_surface=decision is TemporalRelevanceDecision.SURFACE_NOW,
            reason=reason,
            confidence=confidence,
            relevance_score=relevance_score,
            timing_score=timing_score,
            thread_id=question.thread_id,
            question_type=question.question_type,
            signals=signals,
            blocking_signals=blocking_signals,
            supporting_memory_ids=list(question.supporting_memory_ids),
            supporting_event_ids=list(question.supporting_event_ids),
        )

    # ------------------------------------------------------------------
    # Hard gate — Phase 3F authority is never overridden
    # ------------------------------------------------------------------

    def _hard_gate(
        self,
        question: PastSelfQuestionResult | None,
        thread: TemporalThread | None,
        comparison: TemporalComparisonResult | None,
        lifecycle_result: TemporalLifecycleResult | None,
    ) -> TemporalRelevanceResult | None:
        if question is None:
            return TemporalRelevanceResult(
                attempted=False,
                reason=(
                    "No past-self question result was available; relevance "
                    "evaluation skipped."
                ),
            )
        if not question.attempted:
            return TemporalRelevanceResult(
                attempted=False,
                thread_id=question.thread_id,
                question_type=question.question_type,
                reason=(
                    "No temporal thread was touched, so no past-self "
                    "question exists to evaluate."
                ),
            )
        if not question.should_ask:
            return TemporalRelevanceResult(
                attempted=True,
                thread_id=question.thread_id,
                question_type=question.question_type,
                reason=(
                    "Past-self question planning decided not to ask "
                    f"({question.reason}); relevance evaluation cannot "
                    "override that decision."
                ),
            )
        if question.question_type is None or question.intent is None:
            return TemporalRelevanceResult(
                attempted=True,
                thread_id=question.thread_id,
                question_type=question.question_type,
                reason=(
                    "The planned past-self question lacks a usable type or "
                    "intent payload; conservatively skipped."
                ),
            )
        if thread is None or question.thread_id != thread.id:
            return TemporalRelevanceResult(
                attempted=True,
                thread_id=question.thread_id,
                question_type=question.question_type,
                reason=(
                    "The planned past-self question does not belong to the "
                    "current temporal thread; conservatively skipped."
                ),
            )
        if (
            comparison is not None
            and comparison.comparable
            and comparison.relation is TemporalComparisonRelation.INSUFFICIENT_EVIDENCE
        ):
            return TemporalRelevanceResult(
                attempted=True,
                thread_id=question.thread_id,
                question_type=question.question_type,
                reason=(
                    "The underlying temporal comparison reported "
                    "insufficient evidence; ambiguity prevents a confident "
                    "surface decision."
                ),
            )
        if lifecycle_result is not None and lifecycle_result.ambiguous:
            return TemporalRelevanceResult(
                attempted=True,
                thread_id=question.thread_id,
                question_type=question.question_type,
                reason=(
                    "The temporal thread relationship was ambiguous; "
                    "ambiguity prevents a confident surface decision."
                ),
            )
        return None

    # ------------------------------------------------------------------
    # Relevance scoring — every contribution logged as a signal line
    # ------------------------------------------------------------------

    def _relevance(
        self,
        text: str,
        thread: TemporalThread,
        past_event: TemporalEvent | None,
        continuation_this_turn: bool,
        goal_analysis: GoalAnalysisResult | None,
        consistency_result: ConsistencyResult | None,
        thread_memories: set[str],
    ) -> tuple[float, bool, list[str]]:
        """Return (score, door_open, signal lines).

        The present event is deliberately excluded from continuity: its
        description derives from the current input, so overlap with it would
        be circular rather than independent evidence.
        """
        signals: list[str] = []

        input_tokens = _normalize(text)
        subject_tokens = _normalize(thread.subject)
        body_tokens = _normalize(thread.description)
        if past_event is not None:
            body_tokens = body_tokens | _normalize(past_event.description)

        subject_shared = input_tokens & subject_tokens
        meaningful_subject = _split_meaningful(subject_shared)[0]
        body_only_shared = (input_tokens & body_tokens) - subject_shared
        meaningful_body = _split_meaningful(body_only_shared)[0]

        markers = _contains_any(text, _REFLECTION_MARKERS)

        if meaningful_subject:
            relevance = min(
                _TOPIC_CAP,
                _TOPIC_BASE + _TOPIC_EXTRA * (len(meaningful_subject) - 1),
            )
            detail = ", ".join(sorted(meaningful_subject))
            extras: list[str] = []
            generic_subject = subject_shared - meaningful_subject
            if generic_subject:
                extras.append(f"generic: {', '.join(sorted(generic_subject))}")
            if meaningful_body:
                extras.append(f"description/past: {', '.join(sorted(meaningful_body))}")
            if extras:
                detail += f" ({'; '.join(extras)})"
            signals.append(f"Topical continuity via thread subject: {detail}.")
            door_open = True
        elif meaningful_body:
            relevance = min(
                _DESCRIPTION_CAP,
                _DESCRIPTION_BASE + _DESCRIPTION_EXTRA * (len(meaningful_body) - 1),
            )
            signals.append(
                "Weak topical continuity (description/past event only): "
                f"{', '.join(sorted(meaningful_body))}."
            )
            door_open = True
        elif continuation_this_turn:
            relevance = _MATCH_DOOR_BASE
            signals.append(
                "Continuity via this turn's validated thread match (the "
                "matcher already confirmed this input belongs to this story)."
            )
            door_open = True
        elif subject_shared or body_only_shared:
            relevance = _GENERIC_ONLY_OVERLAP
            shared_all = sorted(subject_shared | body_only_shared)
            signals.append(
                "Only generic token overlap; insufficient for topical "
                f"relevance ({', '.join(shared_all)})."
            )
            door_open = False
        else:
            relevance = 0.0
            signals.append(
                "No meaningful shared topic tokens between the input and "
                "the thread's story."
            )
            door_open = False

        # Supporting evidence strengthens existing topical relevance but can
        # never fabricate it: every bonus below requires door_open.
        if door_open:
            if continuation_this_turn and meaningful_subject:
                relevance += _CONTINUATION_RELEVANCE_BONUS
                signals.append(
                    "Current-turn continuation of this very thread "
                    "strengthens relevance."
                )
            goal_bonus_applied = self._apply_goal_continuity(
                goal_analysis, subject_tokens | body_tokens, signals
            )
            if goal_bonus_applied:
                relevance += _GOAL_CONTINUITY_BONUS
            consistency_applied = self._apply_consistency_continuity(
                consistency_result, subject_tokens | body_tokens,
                thread_memories, signals,
            )
            if consistency_applied:
                relevance += _CONSISTENCY_RELEVANCE_BONUS
            if markers:
                relevance += _REFLECTION_RELEVANCE_BONUS
                signals.append(
                    f"Explicit reflection markers with topical continuity: "
                    f"{', '.join(markers)}."
                )

        return relevance, door_open, signals

    @staticmethod
    def _apply_goal_continuity(
        goal_analysis: GoalAnalysisResult | None,
        thread_tokens: set[str],
        signals: list[str],
    ) -> bool:
        if goal_analysis is None:
            return False
        goal_texts: list[str] = []
        if goal_analysis.goal:
            goal_texts.append(goal_analysis.goal)
        if goal_analysis.matched_existing_goal and (
            not goal_analysis.goal
            or goal_analysis.matched_existing_goal != goal_analysis.goal
        ):
            goal_texts.append(goal_analysis.matched_existing_goal)
        for goal_text in goal_texts:
            shared = _split_meaningful(_normalize(goal_text) & thread_tokens)[0]
            if shared:
                snippet = goal_text if len(goal_text) <= 60 else goal_text[:57] + "..."
                signals.append(
                    f"Goal continuity: current goal relates to this thread "
                    f"({snippet})."
                )
                return True
        return False

    @staticmethod
    def _apply_consistency_continuity(
        consistency_result: ConsistencyResult | None,
        thread_tokens: set[str],
        thread_memories: set[str],
        signals: list[str],
    ) -> bool:
        """Same relation notion the matcher/lifecycle use for change evidence."""
        if consistency_result is None:
            return False
        for entry in list(consistency_result.changes) + list(
            consistency_result.contradictions
        ):
            if (entry.type or "") not in _CHANGE_TYPES:
                continue
            entry_text = " ".join(
                part
                for part in (entry.description, entry.previous_value, entry.current_value)
                if part
            )
            related_by_text = bool(
                _split_meaningful(_normalize(entry_text) & thread_tokens)[0]
            )
            related_by_memory = bool(set(entry.supporting_memory_ids) & thread_memories)
            if related_by_text or related_by_memory:
                label = (entry.type or "change").lower().replace("_", " ")
                signals.append(
                    f"Consistency/change evidence relates to this thread "
                    f"({label})."
                )
                return True
        return False

    # ------------------------------------------------------------------
    # Timing scoring — contextual interruption policy, never emotion alone
    # ------------------------------------------------------------------

    def _timing(
        self,
        text: str,
        intent: IntentResult | None,
        user_state: UserStateResult | None,
        transitioned_this_turn: bool,
        continuation_this_turn: bool,
    ) -> tuple[float, list[str], list[str]]:
        signals: list[str] = []
        blockers: list[str] = []

        timing = TIMING_BASE

        if transitioned_this_turn:
            timing += _TRANSITION_TIMING_BONUS
            signals.append(
                "This interaction just resolved or redirected this very "
                "thread; reacting to the outcome is invited."
            )
        elif continuation_this_turn:
            timing += _CONTINUATION_TIMING_BONUS
            signals.append(
                "This interaction directly continues this very thread."
            )

        markers = _contains_any(text, _REFLECTION_MARKERS)
        if markers:
            timing += _REFLECTION_TIMING_BONUS
            signals.append(
                f"The user is explicitly reflecting on the past "
                f"({', '.join(markers)})."
            )

        receptive = False
        if user_state is not None:
            receptive = (
                user_state.emotional_state in _RECEPTIVE_EMOTIONS
                or user_state.cognitive_state is UserCognitiveState.EXPLORATORY
            )
        if receptive:
            timing += _RECEPTIVE_STATE_TIMING_BONUS
            signals.append(
                "Interaction language reads calm/curious/exploratory."
            )

        intent_label = intent.intent.value if intent is not None and intent.intent else None

        if intent_label == _REFLECTION_INTENT:
            timing += _REFLECTION_INTENT_TIMING_BONUS
            signals.append("Reflection intent invites a past-self exchange.")

        urgency = user_state.urgency if user_state is not None else None
        if urgency is not None and urgency >= _URGENCY_HIGH_THRESHOLD:
            timing -= _URGENCY_HIGH_PENALTY
            blockers.append(
                f"High urgency in the current request ({urgency}); do not "
                "interrupt time-sensitive tasks."
            )
        elif urgency is not None and urgency >= _URGENCY_MODERATE_THRESHOLD:
            timing -= _URGENCY_MODERATE_PENALTY
            blockers.append(
                f"Elevated urgency in the current request ({urgency})."
            )

        if intent_label == _PROBLEM_SOLVING_INTENT:
            timing -= _PROBLEM_SOLVING_PENALTY
            blockers.append(
                "Active problem-solving requires immediate focus."
            )

        if intent_label in _TRANSACTIONAL_INTENTS:
            timing -= _TRANSACTIONAL_PENALTY
            blockers.append(
                "Clearly transactional/factual request; keep the exchange "
                "on task."
            )

        frustrated_on_task = (
            user_state is not None
            and user_state.emotional_state in _TASK_FRUSTRATION_STATES
            and intent_label == _PROBLEM_SOLVING_INTENT
        )
        if frustrated_on_task:
            timing -= _UNRELATED_FRUSTRATION_PENALTY
            blockers.append(
                "Frustration is directed at an immediate task; interrupting "
                "with a reflection would add friction."
            )

        return timing, signals, blockers

    # ------------------------------------------------------------------
    # Decision policy
    # ------------------------------------------------------------------

    @staticmethod
    def _decide(
        door_open: bool,
        relevance: float,
        timing: float,
        confidence: float,
    ) -> tuple[TemporalRelevanceDecision, str]:
        if not door_open or relevance < RELEVANCE_FLOOR:
            return (
                TemporalRelevanceDecision.SKIP,
                "No meaningful topical relation between the current input "
                "and the thread's story; surfacing would be an unfounded "
                "interruption.",
            )
        if (
            relevance >= RELEVANCE_SURFACE_MIN
            and timing >= TIMING_SURFACE_MIN
            and confidence >= CONFIDENCE_SURFACE_MIN
        ):
            return (
                TemporalRelevanceDecision.SURFACE_NOW,
                "Strong topical relation and an appropriate moment: the "
                "planned past-self question fits this exchange.",
            )
        if confidence < CONFIDENCE_SURFACE_MIN:
            return (
                TemporalRelevanceDecision.DEFER,
                "The question is topically related but overall evidence "
                "confidence is too low to justify surfacing right now.",
            )
        if relevance < RELEVANCE_SURFACE_MIN:
            return (
                TemporalRelevanceDecision.DEFER,
                "The question relates to the thread, but topical evidence "
                "this turn is too weak for a confident surface.",
            )
        return (
            TemporalRelevanceDecision.DEFER,
            "The question relates to the thread, but the current moment is "
            "not appropriate (urgent, focused or transactional exchange); "
            "not now.",
        )

    # ------------------------------------------------------------------
    # Evidence helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _anchor_events(
        question: PastSelfQuestionResult, events: list[TemporalEvent]
    ) -> tuple[TemporalEvent | None, TemporalEvent | None]:
        by_id = {event.id: event for event in events}
        past = (
            by_id.get(question.past_event_id) if question.past_event_id else None
        )
        present = (
            by_id.get(question.present_event_id)
            if question.present_event_id
            else None
        )
        return past, present

    @staticmethod
    def _continued_this_turn(
        thread_id: str | None,
        thread_match: TemporalThreadMatchResult | None,
        lifecycle_result: TemporalLifecycleResult | None,
    ) -> bool:
        if thread_match is not None and thread_match.matched:
            if thread_id and thread_match.thread_id == thread_id:
                return True
        if (
            lifecycle_result is not None
            and lifecycle_result.updated
            and thread_id
            and lifecycle_result.thread_id == thread_id
        ):
            return True
        return False

    @staticmethod
    def _transitioned_this_turn(
        thread_id: str | None,
        lifecycle_result: TemporalLifecycleResult | None,
    ) -> bool:
        return bool(
            lifecycle_result is not None
            and lifecycle_result.transitioned
            and thread_id
            and lifecycle_result.thread_id == thread_id
        )


__all__ = [
    "TemporalRelevanceEngine",
    "RELEVANCE_FLOOR",
    "RELEVANCE_SURFACE_MIN",
    "TIMING_BASE",
    "TIMING_SURFACE_MIN",
    "CONFIDENCE_SURFACE_MIN",
]
