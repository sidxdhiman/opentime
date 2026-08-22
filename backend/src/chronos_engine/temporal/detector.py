"""Deterministic, offline temporal event detection for the ChronOS engine.

Phase 3B scope
--------------
Answers one question about the current input: *is this a meaningful moment
that ChronOS should recognize as a TemporalEvent?* Detection only — the
detector never persists events, never creates or searches TemporalThreads,
never compares against history, and never calls an LLM.

Design (house style shared with IntentDetector / GoalDetector /
UserStateDetector)
------
* **Weighted signal tables** — every ``TemporalType`` scores the lowercased
  input via ``(pattern, weight, description)`` substring signals.
* **Score-primary selection with documented tie-break** — the highest-scoring
  type wins; ties resolve by ``TYPE_PRIORITY``, which prefers concrete,
  durable moments (milestones, life events, decisions) over tentative ones
  (fears, questions).
* **Significance filter** — ChronOS must not store everyday activity. Input
  is rejected when it lacks first-person self-reference, hits a trivial-topic
  pattern without strong evidence, or never clears the score floor. Fear,
  belief and question types additionally require meaningful-domain contact so
  bare emotions and generic questions never become events.
* **Existing evidence reuse** — a NEW-goal result provides GOAL evidence (no
  goal re-classification), an ANXIOUS user state supports FEAR, a DECISIVE
  cognitive state supports DECISION, and a DECISION intent supports DECISION.
  Supporting evidence strengthens but can never single-handedly create a
  type score out of nothing.
* **One input → zero or one event** — mixed inputs yield one event whose
  primary type is the strongest-scoring one; every matched type is recorded
  in the result's ``signals``.
* **Grounded descriptions** — the description is derived from the input's
  strongest matching sentence; nothing is invented.

Identical inputs always produce identical results.
"""

import re
from typing import Dict, List, Optional, Tuple

from chronos_engine.core.interfaces import BaseTemporalEventDetector
from chronos_engine.core.models import UserInput
from chronos_engine.state.models import (
    GoalAnalysisResult,
    IntentResult,
    UserEmotionState,
    UserStateResult,
)
from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalEventDetectionResult,
    TemporalType,
)

# (substring pattern, weight, human-readable description)
Signal = Tuple[str, float, str]

# ---------------------------------------------------------------------------
# Significance gates
# ---------------------------------------------------------------------------

# The input must reference the user themselves; general questions ("what is
# python?"), commands ("fix the login button") and third-party content are
# never temporal events about the user's life.
FIRST_PERSON_RE = re.compile(
    r"\b(i|i'm|i've|i'll|i am|i have|i will|my|me|mine|myself|we|our)\b"
)

# Mundane, low-stakes topics that must not become temporal events even when a
# weak type signal fires. Strong evidence (>= STRONG_SCORE) may override —
# e.g. "exhausted from this job and thinking about quitting".
TRIVIAL_TOPICS: List[str] = [
    "hungry",
    "thirsty",
    "sleepy",
    "pizza",
    "lunch",
    "dinner",
    "breakfast",
    "coffee",
    "netflix",
    "watched a movie",
    "laundry",
    "dishes",
    "wi-fi",
    "wifi",
    "good morning",
    "good night",
    "good evening",
]

# Winning scores below this never produce an event.
MIN_EVENT_SCORE: float = 0.45
# Above this, signal evidence outweighs a trivial-topic match.
STRONG_SCORE: float = 0.85

# ---------------------------------------------------------------------------
# Per-type signal tables
# ---------------------------------------------------------------------------

TYPE_SIGNALS: Dict[TemporalType, List[Signal]] = {
    TemporalType.MILESTONE: [
        ("graduated", 0.60, "graduation milestone language"),
        ("finally launched", 0.55, "completed-launch milestone"),
        ("just launched", 0.45, "completed-launch milestone"),
        ("completed my degree", 0.55, "degree completion milestone"),
        ("finished my degree", 0.55, "degree completion milestone"),
        ("got my first job", 0.60, "first-job milestone"),
        ("landed my first", 0.55, "first-achievement milestone"),
        ("defended my thesis", 0.55, "thesis milestone"),
        ("passed my final", 0.45, "exam completion milestone"),
        ("finally shipped", 0.50, "shipped milestone"),
        ("got married", 0.65, "marriage milestone"),
    ],
    TemporalType.LIFE_EVENT: [
        ("got accepted", 0.60, "acceptance life event"),
        ("accepted into", 0.55, "acceptance life event"),
        ("started my first job", 0.55, "first-job life event"),
        ("start college", 0.50, "college transition"),
        ("starting college", 0.55, "college transition"),
        ("i'm moving to", 0.50, "relocation life event"),
        ("moving to another city", 0.55, "relocation life event"),
        ("got engaged", 0.55, "engagement life event"),
        ("having a baby", 0.60, "family life event"),
        ("broke up", 0.50, "relationship change"),
        ("lost my job", 0.55, "job loss life event"),
        ("got laid off", 0.55, "job loss life event"),
        ("quit my job", 0.55, "job exit life event"),
        ("left my job", 0.50, "job exit life event"),
        ("new job", 0.40, "job change life event"),
    ],
    TemporalType.DECISION: [
        ("i've decided to", 0.70, "settled decision language"),
        ("i have decided to", 0.70, "settled decision language"),
        ("i decided to", 0.65, "settled decision language"),
        ("decided to", 0.55, "decision language"),
        ("thinking about leaving", 0.55, "leaving deliberation"),
        ("thinking of leaving", 0.55, "leaving deliberation"),
        ("considering leaving", 0.60, "leaving deliberation"),
        ("thinking about quitting", 0.55, "quitting deliberation"),
        ("thinking of quitting", 0.55, "quitting deliberation"),
        ("considering quitting", 0.60, "quitting deliberation"),
        ("seriously considering", 0.55, "serious deliberation"),
        ("i'm going to do it", 0.60, "resolved intention"),
        ("going to do it", 0.50, "resolved intention"),
        ("chose to", 0.55, "choice language"),
        ("made up my mind", 0.55, "settled decision language"),
        ("don't know if i should", 0.55, "uncertain deliberation"),
        ("not sure if i should", 0.55, "uncertain deliberation"),
        ("i should leave", 0.45, "leave/stay deliberation"),
        ("if i should", 0.35, "weighing options"),
        ("should i leave", 0.40, "leave/stay deliberation"),
        ("whether i should", 0.40, "weighing options"),
    ],
    TemporalType.PROMISE: [
        ("i promise", 0.60, "self-promise language"),
        ("promise myself", 0.60, "self-commitment language"),
        ("from now on i", 0.50, "commitment going forward"),
        ("i won't give up", 0.50, "persistence commitment"),
        ("no matter what i", 0.40, "unconditional commitment"),
        ("committing to", 0.45, "explicit commitment"),
    ],
    TemporalType.GOAL: [
        ("my goal is to", 0.60, "explicit goal statement"),
        ("my dream is to", 0.55, "aspiration statement"),
        ("i want to become", 0.55, "identity goal language"),
    ],
    TemporalType.FUTURE_EXPECTATION: [
        ("next month", 0.35, "near-future time marker"),
        ("next year", 0.35, "future time marker"),
        ("next week", 0.30, "near-future time marker"),
        ("next semester", 0.35, "future time marker"),
        ("this summer", 0.30, "future time marker"),
        ("in a few months", 0.30, "future time marker"),
        ("soon", 0.25, "near-future marker"),
        ("i'll be", 0.30, "anticipated future self-state"),
        ("i will be", 0.30, "anticipated future self-state"),
        ("working abroad", 0.45, "anticipated relocation"),
        ("i'm moving", 0.40, "anticipated relocation"),
    ],
    TemporalType.PREDICTION: [
        ("i'll regret", 0.60, "regret prediction"),
        ("i will regret", 0.60, "regret prediction"),
        ("will make me miserable", 0.60, "negative outcome prediction"),
        ("feel like i'll", 0.45, "personal forecast"),
        ("could become my biggest", 0.55, "significant outcome forecast"),
        ("probably end up", 0.50, "outcome forecast"),
        ("won't work out", 0.50, "negative outcome prediction"),
        ("will fail", 0.45, "failure prediction"),
    ],
    TemporalType.BELIEF: [
        ("i believe", 0.35, "belief statement"),
        ("matters more than", 0.50, "value hierarchy statement"),
        ("more important than", 0.45, "value comparison"),
        ("i value", 0.45, "stated personal value"),
        ("i've realised", 0.45, "belief realisation"),
        ("i've realized", 0.45, "belief realisation"),
        ("i realized", 0.40, "belief shift"),
        ("i used to think", 0.50, "belief change"),
        ("what really matters", 0.45, "worldview reflection"),
    ],
    TemporalType.FEAR: [
        ("scared i'll fail", 0.60, "fear of failing"),
        ("afraid i'll fail", 0.60, "fear of failing"),
        ("scared of failing", 0.60, "fear of failing"),
        ("afraid of failing", 0.60, "fear of failing"),
        ("i'm scared", 0.35, "fear statement"),
        ("i am scared", 0.35, "fear statement"),
        ("scared to", 0.25, "fear framing"),
        ("afraid", 0.45, "fear statement"),
        ("terrified", 0.55, "strong fear statement"),
        ("what if i never", 0.55, "identity fear"),
        ("my biggest fear", 0.55, "named fear"),
    ],
    # A QUESTION becomes a temporal event only when it exposes the user's
    # own crossroads — never factual/informational questions.
    TemporalType.QUESTION: [
        ("should i leave", 0.45, "life-direction question"),
        ("should i quit", 0.45, "life-direction question"),
        ("should i move", 0.45, "life-direction question"),
        ("should i stay", 0.40, "life-direction question"),
        ("do i even want", 0.45, "desire question"),
        ("what do i want", 0.45, "direction question"),
        ("who am i", 0.45, "identity question"),
        ("am i making a mistake", 0.50, "doubt question"),
        ("will i ever", 0.40, "future doubt question"),
    ],
}

# Tie-break order when type scores are equal: concrete/durable moments carry
# more evidential weight than tentative ones.
TYPE_PRIORITY: List[TemporalType] = [
    TemporalType.MILESTONE,
    TemporalType.LIFE_EVENT,
    TemporalType.DECISION,
    TemporalType.PROMISE,
    TemporalType.GOAL,
    TemporalType.FUTURE_EXPECTATION,
    TemporalType.PREDICTION,
    TemporalType.BELIEF,
    TemporalType.FEAR,
    TemporalType.QUESTION,
]

# Fear / belief / question inputs must also touch something meaningful — a
# life domain, identity, direction or the future — otherwise they stay
# ordinary statements and are zeroed out by the significance gate.
MEANINGFUL_DOMAINS: frozenset = frozenset(
    {
        "job", "work", "career", "college", "school", "university", "exam",
        "degree", "mba", "married", "marriage", "relationship", "moving",
        "city", "country", "abroad", "family", "health", "money", "business",
        "startup", "project", "quit", "quitting", "leaving", "leave",
        "fail", "failing", "freedom", "success", "stability", "risk",
        "future", "life", "dreams", "purpose", "regret",
    }
)

# Supporting evidence from existing detectors can add at most this much.
SUPPORT_CAP: float = 0.15

_WORD_RE = re.compile(r"[a-z']+")


def _words(text: str) -> set:
    """Lowercased word tokens; naive singular normalization for domain checks."""
    words = set()
    for token in _WORD_RE.findall(text):
        words.add(token)
        if len(token) > 3 and token.endswith("s"):
            words.add(token[:-1])
    return words


class TemporalEventDetector(BaseTemporalEventDetector):
    """Detects whether the current input is a meaningful temporal moment.

    Deterministic and fully offline: weighted substring signals plus already-
    computed ChronOS evidence. Conservative by design — most everyday input
    produces no event.
    """

    async def detect_temporal_event(
        self,
        user_input: UserInput,
        intent: Optional[IntentResult] = None,
        user_state: Optional[UserStateResult] = None,
        goal_analysis: Optional[GoalAnalysisResult] = None,
        memory_id: Optional[str] = None,
    ) -> TemporalEventDetectionResult:
        """Return zero or one detected TemporalEvent with detector metadata."""
        content = (user_input.content or "").strip()
        if not content:
            return TemporalEventDetectionResult(
                detected=False,
                reason="Empty input",
                confidence=0.0,
            )

        text = content.lower()

        if not FIRST_PERSON_RE.search(text):
            return TemporalEventDetectionResult(
                detected=False,
                confidence=0.0,
                reason="No first-person self-reference; not about the user's life",
            )

        scores, matched = self._score_types(text)
        self._apply_supporting_evidence(
            text,
            scores,
            intent=intent,
            user_state=user_state,
            goal_analysis=goal_analysis,
        )
        self._apply_domain_gates(text, scores)

        best_score = max(scores.values())
        if best_score < MIN_EVENT_SCORE:
            return TemporalEventDetectionResult(
                detected=False,
                confidence=round(min(0.95, best_score), 2),
                reason="No temporal signals above significance threshold",
                signals=self._all_signals(matched),
            )

        if any(topic in text for topic in TRIVIAL_TOPICS) and best_score < STRONG_SCORE:
            return TemporalEventDetectionResult(
                detected=False,
                confidence=round(min(0.95, best_score), 2),
                reason="Trivial everyday topic, not a temporal event",
                signals=self._all_signals(matched),
            )

        primary, secondary_signals = self._select_primary(scores, matched)

        event = TemporalEvent(
            temporal_type=primary,
            description=self._describe(content, primary),
            memory_id=memory_id,
            importance=self._importance(primary),
        )
        detection_confidence = round(
            min(
                0.95,
                0.30
                + 0.45 * min(1.5, best_score)
                + 0.05 * min(3, len(secondary_signals)),
            ),
            2,
        )
        event.confidence = detection_confidence
        return TemporalEventDetectionResult(
            detected=True,
            event=event,
            confidence=detection_confidence,
            reason=f"Meaningful {primary.value} evidence in current input",
            signals=secondary_signals,
        )

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _score_types(
        text: str,
    ) -> Tuple[Dict[TemporalType, float], Dict[TemporalType, List[str]]]:
        scores: Dict[TemporalType, float] = {t: 0.0 for t in TemporalType}
        matched: Dict[TemporalType, List[str]] = {t: [] for t in TemporalType}
        for ttype, signals in TYPE_SIGNALS.items():
            for pattern, weight, desc in signals:
                if pattern in text:
                    scores[ttype] += weight
                    if desc not in matched[ttype]:
                        matched[ttype].append(desc)
        return scores, matched

    @staticmethod
    def _apply_supporting_evidence(
        text: str,
        scores: Dict[TemporalType, float],
        intent: Optional[IntentResult],
        user_state: Optional[UserStateResult],
        goal_analysis: Optional[GoalAnalysisResult],
    ) -> None:
        """Fold in already-computed ChronOS detector output."""
        if (
            goal_analysis is not None
            and goal_analysis.status is not None
            and goal_analysis.status.value == "NEW"
            and goal_analysis.goal
        ):
            scores[TemporalType.GOAL] += round(
                0.6 * min(1.0, goal_analysis.confidence), 2
            )

        if user_state is not None:
            anxious = (
                user_state.emotional_state is UserEmotionState.ANXIOUS
                or UserEmotionState.ANXIOUS in (user_state.secondary_states or [])
            )
            if anxious and MEANINGFUL_DOMAINS & _words(text):
                scores[TemporalType.FEAR] += SUPPORT_CAP
            if (
                user_state.cognitive_state is not None
                and user_state.cognitive_state.value == "DECISIVE"
            ):
                scores[TemporalType.DECISION] += SUPPORT_CAP

        if intent is not None and intent.intent is not None:
            if intent.intent.value == "DECISION":
                scores[TemporalType.DECISION] += SUPPORT_CAP

    @staticmethod
    def _apply_domain_gates(text: str, scores: Dict[TemporalType, float]) -> None:
        """Fear / belief / question require meaningful-domain contact."""
        if not (MEANINGFUL_DOMAINS & _words(text)):
            scores[TemporalType.FEAR] = 0.0
            scores[TemporalType.BELIEF] = 0.0
            scores[TemporalType.QUESTION] = 0.0

    @staticmethod
    def _select_primary(
        scores: Dict[TemporalType, float],
        matched: Dict[TemporalType, List[str]],
    ) -> Tuple[TemporalType, List[str]]:
        candidates = [t for t in scores if scores[t] >= MIN_EVENT_SCORE]
        candidates.sort(key=lambda t: (-scores[t], TYPE_PRIORITY.index(t)))
        primary = candidates[0]
        secondary = [
            f"{t.value} evidence" + (f" ({', '.join(matched[t])})" if matched[t] else "")
            for t in candidates
        ]
        return primary, secondary

    # ------------------------------------------------------------------
    # Description & metadata
    # ------------------------------------------------------------------

    @staticmethod
    def _describe(content: str, primary: TemporalType) -> str:
        """Grounded description: the sentence containing the strongest
        primary-type signal, lightly normalized. Never invents content."""
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", content) if s.strip()]
        chosen = sentences[0] if sentences else content

        lowered = content.lower()
        positions = [
            lowered.find(pattern)
            for pattern, _, _ in TYPE_SIGNALS.get(primary, [])
            if lowered.find(pattern) != -1
        ]
        if positions:
            earliest = min(positions)
            cursor = 0
            for sentence in sentences:
                start = content.find(sentence, cursor)
                end = start + len(sentence)
                cursor = end
                if start <= earliest < end:
                    chosen = sentence
                    break

        description = re.sub(r"\s+", " ", chosen).strip()
        if len(description) > 140:
            description = description[:137].rstrip() + "..."
        if description and description[0].islower():
            description = description[0].upper() + description[1:]
        if description and description[-1] not in ".!?":
            description += "."
        return description

    @staticmethod
    def _importance(primary: TemporalType) -> float:
        coarse = {
            TemporalType.MILESTONE: 0.8,
            TemporalType.LIFE_EVENT: 0.75,
            TemporalType.DECISION: 0.7,
            TemporalType.PROMISE: 0.6,
            TemporalType.GOAL: 0.65,
            TemporalType.BELIEF: 0.6,
            TemporalType.FUTURE_EXPECTATION: 0.55,
            TemporalType.PREDICTION: 0.5,
            TemporalType.FEAR: 0.55,
            TemporalType.QUESTION: 0.5,
        }
        return coarse.get(primary, 0.5)

    @staticmethod
    def _all_signals(matched: Dict[TemporalType, List[str]]) -> List[str]:
        ordered: List[str] = []
        for t in TYPE_PRIORITY:
            for desc in matched.get(t, []):
                if desc not in ordered:
                    ordered.append(desc)
        return ordered[:6]
