"""Deterministic, offline user-state detection for the ChronOS engine.

Scope
-----
This is a *cautious inference about what the input's language suggests about
the current interaction state*. It is:

* NOT psychological or medical diagnosis,
* NOT consciousness,
* NOT a claim of fact about the user.

It is simply a weighted-signal reading of the text: "this input reads like a
frustrated / excited / uncertain interaction". Every dimension is ``None`` /
``0.0`` when there is not enough evidence for it, so the detector never
fabricates a state.

Design
------
* **Weighted signal tables** — every label (emotion, energy, cognitive state,
  urgency, engagement) scores the lowercased input by substring signal
  weights. No single keyword decides a label on its own.
* **Multi-dimensional** — emotional, valence, energy, cognitive, urgency and
  engagement are inferred independently. A primary emotion plus a few
  ``secondary_states`` capture mixed inputs (e.g. "frustrated but excited").
* **Confidence from evidence** — confidence is derived from how many signals
  matched and how strong the winning signal was. No signals at all means
  ``confidence == 0.0`` and the emotional state resolves to ``NEUTRAL``.
* **Intent is context only** — the already-detected ``IntentResult`` may nudge
  engagement (an interaction the user wants handled looks engaged), but it
  never sets an emotion directly.
* **No diagnosis vocabulary** — labels never include clinical terms. The
  detector describes interaction-language signals (e.g. "anxiety-like
  language" never "the user has anxiety").

The detector is local, deterministic, dependency-free and fast: identical
inputs always produce identical results.
"""

from typing import Dict, List, Optional, Tuple

from chronos_engine.core.interfaces import BaseUserStateDetector
from chronos_engine.core.models import UserInput
from chronos_engine.state.models import (
    IntentResult,
    UserCognitiveState,
    UserEmotionState,
    UserEnergy,
    UserStateResult,
)

# (substring pattern, weight, human-readable description)
Signal = Tuple[str, float, str]
# (substring pattern, weight)
WeightedSignal = Tuple[str, float]

# ---------------------------------------------------------------------------
# Emotional-state signal table
# ---------------------------------------------------------------------------

EMOTION_SIGNALS: Dict[UserEmotionState, List[Signal]] = {
    UserEmotionState.FRUSTRATED: [
        ("frustrated", 0.50, "frustration language"),
        ("frustrating", 0.40, "frustration language"),
        ("so frustrated", 0.50, "strong frustration language"),
        ("stuck", 0.35, "extended difficulty language"),
        ("driving me crazy", 0.40, "intense frustration language"),
        ("annoying", 0.35, "annoyance language"),
        ("annoyed", 0.35, "annoyance language"),
        ("infuriating", 0.50, "strong frustration language"),
        ("hours", 0.15, "extended difficulty language"),
        ("trying", 0.10, "extended difficulty language"),
        ("bug", 0.15, "difficulty language"),
        ("fucking", 0.15, "intense negative language"),
        ("won't work", 0.25, "difficulty language"),
        ("doesn't work", 0.25, "difficulty language"),
        ("does not work", 0.25, "difficulty language"),
    ],
    UserEmotionState.EXCITED: [
        ("excited", 0.50, "excitement language"),
        ("so excited", 0.50, "strong excitement language"),
        ("can't wait", 0.40, "anticipation language"),
        ("hyped", 0.40, "excitement language"),
        ("thrilled", 0.45, "excitement language"),
        ("amazing", 0.30, "positive excitement language"),
        ("pumped", 0.35, "excitement language"),
        ("this is awesome", 0.40, "excitement language"),
    ],
    UserEmotionState.POSITIVE: [
        ("perfectly", 0.40, "success language"),
        ("worked perfectly", 0.40, "success language"),
        ("happy", 0.40, "positive language"),
        ("awesome", 0.35, "positive language"),
        ("great", 0.30, "positive language"),
        ("perfect", 0.35, "positive language"),
        ("love it", 0.35, "positive language"),
        ("success", 0.30, "success language"),
        ("good", 0.20, "mild positive language"),
        ("glad", 0.30, "positive language"),
        ("enjoying", 0.30, "positive language"),
    ],
    UserEmotionState.CONFIDENT: [
        ("confident", 0.50, "confidence language"),
        ("i know exactly", 0.45, "clear confidence language"),
        ("i'm sure", 0.40, "confidence language"),
        ("i am sure", 0.40, "confidence language"),
        ("i can do this", 0.40, "self-belief language"),
        ("definitely", 0.30, "confidence language"),
        ("certainly", 0.35, "confidence language"),
    ],
    UserEmotionState.CURIOUS: [
        ("curious", 0.45, "curiosity language"),
        ("wonder", 0.35, "curiosity language"),
        ("interesting", 0.25, "curiosity language"),
        ("i want to learn", 0.40, "learning interest"),
        ("let's figure", 0.40, "exploratory curiosity"),
        ("how does", 0.25, "exploratory curiosity"),
    ],
    UserEmotionState.UNCERTAIN: [
        ("not sure", 0.40, "uncertainty language"),
        ("unsure", 0.40, "uncertainty language"),
        ("don't know", 0.35, "uncertainty language"),
        ("do not know", 0.35, "uncertainty language"),
        ("which approach", 0.30, "indecision language"),
        ("which one", 0.25, "indecision language"),
        ("can't decide", 0.40, "indecision language"),
        ("i guess", 0.25, "hesitation language"),
        ("maybe", 0.20, "hesitation language"),
    ],
    UserEmotionState.OVERWHELMED: [
        ("overwhelmed", 0.50, "overwhelmed language"),
        ("too much", 0.40, "overwhelmed language"),
        ("can't handle", 0.40, "overwhelmed language"),
        ("so many things", 0.35, "overwhelmed language"),
        ("drowning", 0.45, "overwhelmed language"),
    ],
    UserEmotionState.ANXIOUS: [
        ("anxious", 0.50, "anxiety-like language"),
        ("anxiety", 0.45, "anxiety-like language"),
        ("worried", 0.40, "worry language"),
        ("nervous", 0.40, "nervousness language"),
        ("stressed", 0.35, "stress language"),
        ("stressed out", 0.45, "stress language"),
        ("panicking", 0.45, "elevated concern language"),
    ],
    UserEmotionState.SAD: [
        ("sad", 0.50, "sadness language"),
        ("unhappy", 0.40, "sadness language"),
        ("feeling down", 0.40, "low mood language"),
        ("disappointed", 0.35, "disappointment language"),
        ("heartbroken", 0.40, "sadness language"),
    ],
    UserEmotionState.TIRED: [
        ("exhausted", 0.50, "exhaustion language"),
        ("tired", 0.40, "tiredness language"),
        ("drained", 0.45, "exhaustion language"),
        ("burned out", 0.45, "burnout language"),
        ("burnout", 0.40, "burnout language"),
        ("can't focus", 0.35, "low focus language"),
        ("sleepy", 0.35, "sleepiness language"),
    ],
    UserEmotionState.ANGRY: [
        ("angry", 0.50, "anger language"),
        ("pissed", 0.45, "anger language"),
        ("pissed off", 0.50, "anger language"),
        ("furious", 0.50, "anger language"),
        ("hate", 0.30, "anger language"),
        ("fucking", 0.15, "intense negative language"),
    ],
    UserEmotionState.MOTIVATED: [
        ("motivated", 0.50, "motivation language"),
        ("let's go", 0.40, "motivation language"),
        ("let's do", 0.30, "motivation language"),
        ("let's fucking", 0.45, "high motivation language"),
        ("ready to", 0.25, "motivation language"),
        ("build this", 0.25, "action motivation"),
        ("ship this", 0.25, "action motivation"),
        ("ship it", 0.25, "action motivation"),
        ("going to crush", 0.40, "high motivation language"),
        ("energized", 0.30, "motivation language"),
        ("pumped", 0.25, "motivation language"),
    ],
    UserEmotionState.FOCUSED: [
        ("focused", 0.45, "focus language"),
        ("locked in", 0.40, "focus language"),
        ("in the zone", 0.40, "focus language"),
        ("concentrating", 0.40, "focus language"),
        ("deep work", 0.35, "focus language"),
        ("single minded", 0.35, "focus language"),
    ],
    UserEmotionState.RELIEVED: [
        ("finally", 0.30, "relief language"),
        ("finally got it", 0.40, "relief language"),
        ("got it working", 0.30, "relief language"),
        ("relieved", 0.50, "relief language"),
        ("whew", 0.40, "relief language"),
        ("at last", 0.30, "relief language"),
    ],
    UserEmotionState.CALM: [
        ("calm", 0.45, "calm language"),
        ("relaxed", 0.40, "calm language"),
        ("peaceful", 0.40, "calm language"),
        ("at ease", 0.35, "calm language"),
    ],
    UserEmotionState.NEUTRAL: [],
}

# Emotion tie-break order: on a score tie the earlier label wins. Mixed signals
# prefer the more salient reading first while still surfacing the rest as
# secondary states.
EMOTION_PRIORITY: List[UserEmotionState] = [
    UserEmotionState.FRUSTRATED,
    UserEmotionState.ANGRY,
    UserEmotionState.ANXIOUS,
    UserEmotionState.OVERWHELMED,
    UserEmotionState.UNCERTAIN,
    UserEmotionState.TIRED,
    UserEmotionState.SAD,
    UserEmotionState.EXCITED,
    UserEmotionState.MOTIVATED,
    UserEmotionState.POSITIVE,
    UserEmotionState.CONFIDENT,
    UserEmotionState.CURIOUS,
    UserEmotionState.FOCUSED,
    UserEmotionState.RELIEVED,
    UserEmotionState.CALM,
    UserEmotionState.NEUTRAL,
]

# Winning emotion scores below this resolve to NEUTRAL (insufficient evidence).
EMOTION_MIN_SCORE: float = 0.2
# Other emotions at/above this become secondary states.
SECONDARY_MIN_SCORE: float = 0.2
# Max secondary states surfaced alongside the primary emotion.
MAX_SECONDARY_STATES: int = 3

# ---------------------------------------------------------------------------
# Valence signal tables
# ---------------------------------------------------------------------------

NEGATIVE_VALENCE_SIGNALS: List[WeightedSignal] = [
    ("frustrated", 0.25), ("frustrating", 0.20), ("stuck", 0.15),
    ("annoying", 0.15), ("annoyed", 0.15), ("driving me crazy", 0.20),
    ("infuriating", 0.25), ("won't work", 0.15), ("doesn't work", 0.15),
    ("bug", 0.10), ("broken", 0.15), ("error", 0.05), ("issue", 0.05),
    ("confused", 0.10), ("not sure", 0.10), ("don't know", 0.10),
    ("do not know", 0.10), ("unsure", 0.10), ("can't decide", 0.10),
    ("overwhelmed", 0.20), ("too much", 0.15), ("can't handle", 0.15),
    ("anxious", 0.20), ("worried", 0.15), ("nervous", 0.15), ("stressed", 0.15),
    ("sad", 0.20), ("unhappy", 0.20), ("disappointed", 0.15),
    ("exhausted", 0.15), ("tired", 0.10), ("drained", 0.15), ("can't focus", 0.15),
    ("angry", 0.20), ("pissed", 0.20), ("furious", 0.25), ("hate", 0.20),
    ("fucking", 0.10), ("hours", 0.05), ("trying", 0.05),
    ("wrong", 0.10), ("fail", 0.10), ("abandon", 0.15), ("give up", 0.20),
]

POSITIVE_VALENCE_SIGNALS: List[WeightedSignal] = [
    ("excited", 0.20), ("can't wait", 0.15), ("amazing", 0.20), ("awesome", 0.20),
    ("great", 0.15), ("perfect", 0.20), ("perfectly", 0.20), ("happy", 0.20),
    ("love it", 0.15), ("success", 0.15), ("good", 0.10), ("glad", 0.15),
    ("confident", 0.15), ("finally", 0.10), ("relieved", 0.15),
    ("worked perfectly", 0.20), ("motivated", 0.15), ("let's go", 0.15),
    ("build", 0.05), ("ship", 0.05), ("enjoying", 0.15), ("proud", 0.20),
]

# ---------------------------------------------------------------------------
# Energy signal tables
# ---------------------------------------------------------------------------

HIGH_ENERGY_SIGNALS: List[WeightedSignal] = [
    ("excited", 0.25), ("can't wait", 0.25), ("amazing", 0.20),
    ("hyped", 0.30), ("thrilled", 0.25), ("pumped", 0.30),
    ("energized", 0.30), ("build", 0.10), ("ship", 0.10), ("finally", 0.15),
    ("let's go", 0.30), ("let's do", 0.25), ("ready to", 0.15),
    ("!!!", 0.20), ("raring", 0.30), ("crush", 0.20),
]

LOW_ENERGY_SIGNALS: List[WeightedSignal] = [
    ("tired", 0.25), ("exhausted", 0.30), ("drained", 0.30),
    ("can't focus", 0.30), ("sleepy", 0.25), ("burned out", 0.30),
    ("worn out", 0.30), ("no energy", 0.30), ("sluggish", 0.25),
    ("wiped out", 0.25), ("spent", 0.20), ("burnout", 0.25),
]

# An energy dimension requires at least this much signal weight.
ENERGY_MIN_SCORE: float = 0.15
# Dominant energy only when the lead exceeds this margin; otherwise MEDIUM.
ENERGY_LEAD_MARGIN: float = 0.05

# ---------------------------------------------------------------------------
# Cognitive-state signal table
# ---------------------------------------------------------------------------

COGNITIVE_SIGNALS: Dict[UserCognitiveState, List[Signal]] = {
    UserCognitiveState.CLEAR: [
        ("i know exactly", 0.45, "clear understanding language"),
        ("i understand", 0.35, "clear understanding language"),
        ("makes sense", 0.30, "clear understanding language"),
        ("got it", 0.30, "clear understanding language"),
        ("clear", 0.30, "clear thinking language"),
    ],
    UserCognitiveState.UNCERTAIN: [
        ("not sure", 0.40, "uncertainty language"),
        ("unsure", 0.40, "uncertainty language"),
        ("don't know", 0.35, "uncertainty language"),
        ("do not know", 0.35, "uncertainty language"),
        ("can't decide", 0.40, "indecision language"),
        ("which approach", 0.30, "indecision language"),
        ("which one", 0.25, "indecision language"),
        ("i guess", 0.25, "hesitation language"),
        ("maybe", 0.20, "hesitation language"),
    ],
    UserCognitiveState.CONFUSED: [
        ("confused", 0.50, "confusion language"),
        ("don't understand", 0.45, "confusion language"),
        ("do not understand", 0.45, "confusion language"),
        ("doesn't make sense", 0.45, "confusion language"),
        ("can't figure", 0.40, "confusion language"),
        ("puzzled", 0.45, "confusion language"),
        ("why is", 0.25, "confusion language"),
        ("why isn't", 0.30, "confusion language"),
        ("what's going on", 0.40, "confusion language"),
    ],
    UserCognitiveState.FOCUSED: [
        ("focused", 0.45, "focus language"),
        ("locked in", 0.40, "focus language"),
        ("in the zone", 0.40, "focus language"),
        ("concentrating", 0.40, "focus language"),
        ("deep work", 0.35, "focus language"),
    ],
    UserCognitiveState.OVERWHELMED: [
        ("overwhelmed", 0.50, "overwhelmed language"),
        ("too much", 0.40, "overwhelmed language"),
        ("can't handle", 0.40, "overwhelmed language"),
        ("so many things", 0.35, "overwhelmed language"),
        ("drowning", 0.45, "overwhelmed language"),
    ],
    UserCognitiveState.EXPLORATORY: [
        ("let's figure", 0.40, "exploratory reasoning language"),
        ("figure out", 0.40, "exploratory reasoning language"),
        ("explore", 0.40, "exploratory reasoning language"),
        ("investigate", 0.40, "exploratory reasoning language"),
        ("research", 0.30, "exploratory reasoning language"),
        ("understand how", 0.35, "exploratory reasoning language"),
        ("learn about", 0.35, "exploratory reasoning language"),
        ("try to understand", 0.35, "exploratory reasoning language"),
    ],
    UserCognitiveState.DECISIVE: [
        ("i've decided", 0.50, "decision language"),
        ("i have decided", 0.50, "decision language"),
        ("i decided", 0.45, "decision language"),
        ("decided to", 0.45, "decision language"),
        ("going with", 0.40, "decision language"),
        ("i'll use", 0.40, "decision language"),
        ("settled on", 0.40, "decision language"),
        ("decision", 0.35, "decision language"),
        ("choose", 0.30, "decision language"),
    ],
}

COGNITIVE_PRIORITY: List[UserCognitiveState] = [
    UserCognitiveState.CONFUSED,
    UserCognitiveState.OVERWHELMED,
    UserCognitiveState.UNCERTAIN,
    UserCognitiveState.EXPLORATORY,
    UserCognitiveState.DECISIVE,
    UserCognitiveState.FOCUSED,
    UserCognitiveState.CLEAR,
]

COGNITIVE_MIN_SCORE: float = 0.25

# ---------------------------------------------------------------------------
# Urgency signal table
# ---------------------------------------------------------------------------

URGENCY_SIGNALS: List[WeightedSignal] = [
    ("as soon as possible", 0.45), ("asap", 0.40), ("urgent", 0.45),
    ("immediately", 0.35), ("right now", 0.30), ("deadline", 0.30),
    ("today", 0.15), ("can't wait", 0.25), ("quickly", 0.20),
    ("hurry", 0.35), ("emergency", 0.45), ("overdue", 0.40),
    ("tonight", 0.15), ("pressing", 0.30), ("critical", 0.30),
]

# ---------------------------------------------------------------------------
# Engagement signal table
# ---------------------------------------------------------------------------

ENGAGEMENT_SIGNALS: List[WeightedSignal] = [
    ("build", 0.05), ("implement", 0.05), ("fix", 0.05), ("deploy", 0.05),
    ("design", 0.05), ("create", 0.05), ("test", 0.04), ("refactor", 0.05),
    ("because", 0.05), ("however", 0.04), ("therefore", 0.05), ("since", 0.04),
    ("also", 0.03), ("then", 0.03), ("first", 0.03), ("next", 0.03),
    ("step", 0.04), ("what", 0.05), ("how", 0.05), ("why", 0.05),
    ("which", 0.04), ("should", 0.04), ("need", 0.04),
    ("i've been", 0.05), ("i have been", 0.05), ("working on", 0.05),
    ("trying", 0.04), ("project", 0.05), ("backend", 0.04), ("api", 0.04),
    ("database", 0.04), ("finish", 0.04), ("understand", 0.04),
]

MAX_SIGNALS: int = 6


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class UserStateDetector(BaseUserStateDetector):
    """Infers cautious interaction-state signals from an input's language.

    Deterministic and fully offline: every dimension is computed from static
    weighted-signal tables via lowercase substring matching. Identical inputs
    always produce identical results.
    """

    async def detect_state(
        self,
        user_input: UserInput,
        intent: Optional[IntentResult] = None,
    ) -> UserStateResult:
        content = user_input.content or ""
        text = content.lower()

        # Emotional state + secondary states + matched-signal descriptions.
        emotion_scores, emotion_descriptions = self._match_emotions(text)
        primary, secondaries = self._resolve_emotions(emotion_scores)
        n_emotion_signals = sum(len(descs) for descs in emotion_descriptions.values())

        # Independent dimensions.
        valence = self._score_valence(text)
        energy = self._score_energy(text)
        cognitive_state, cognitive_descriptions = self._score_cognitive(text)
        urgency = self._score_urgency(text)
        engagement = self._score_engagement(text, content, intent)

        # Confidence derived from actual evidence (never hard-coded).
        n_other_signals = (
            sum(len(descs) for descs in cognitive_descriptions.values())
            + self._count_matches(text, HIGH_ENERGY_SIGNALS)
            + self._count_matches(text, LOW_ENERGY_SIGNALS)
            + self._count_matches(text, URGENCY_SIGNALS)
        )
        best_emotion_score = max(emotion_scores.values())
        confidence = self._score_confidence(
            best_emotion_score, n_emotion_signals, n_other_signals
        )

        # Human-readable explanation of which signals fired.
        signals = self._collect_signals(
            emotion_descriptions.get(primary, []) if primary else [],
            emotion_descriptions,
            cognitive_descriptions.get(cognitive_state, []) if cognitive_state else [],
        )

        return UserStateResult(
            emotional_state=primary,
            secondary_states=secondaries,
            confidence=confidence,
            signals=signals,
            valence=valence,
            energy=energy,
            cognitive_state=cognitive_state,
            urgency=urgency,
            engagement=engagement,
        )

    # ------------------------------------------------------------------
    # Emotional state
    # ------------------------------------------------------------------

    def _match_emotions(
        self, text: str
    ) -> Tuple[Dict[UserEmotionState, float], Dict[UserEmotionState, List[str]]]:
        scores: Dict[UserEmotionState, float] = {
            state: 0.0 for state in UserEmotionState
        }
        descriptions: Dict[UserEmotionState, List[str]] = {
            state: [] for state in UserEmotionState
        }
        for state, signals in EMOTION_SIGNALS.items():
            for pattern, weight, desc in signals:
                if pattern in text:
                    scores[state] += weight
                    descriptions[state].append(desc)
        return scores, descriptions

    def _resolve_emotions(
        self, scores: Dict[UserEmotionState, float]
    ) -> Tuple[Optional[UserEmotionState], List[UserEmotionState]]:
        best_score = max(scores.values())
        if best_score < EMOTION_MIN_SCORE:
            return UserEmotionState.NEUTRAL, []

        candidates = sorted(
            (state for state, score in scores.items() if score >= SECONDARY_MIN_SCORE),
            key=lambda state: (-scores[state], EMOTION_PRIORITY.index(state)),
        )
        primary = candidates[0]
        secondaries = candidates[1 : 1 + MAX_SECONDARY_STATES]
        return primary, secondaries

    # ------------------------------------------------------------------
    # Valence
    # ------------------------------------------------------------------

    def _score_valence(self, text: str) -> Optional[float]:
        negative = self._sum_weights(text, NEGATIVE_VALENCE_SIGNALS)
        positive = self._sum_weights(text, POSITIVE_VALENCE_SIGNALS)
        if negative == 0.0 and positive == 0.0:
            return 0.0
        return round(_clamp(positive - negative, -1.0, 1.0), 2)

    # ------------------------------------------------------------------
    # Energy
    # ------------------------------------------------------------------

    def _score_energy(self, text: str) -> Optional[UserEnergy]:
        high = self._sum_weights(text, HIGH_ENERGY_SIGNALS)
        low = self._sum_weights(text, LOW_ENERGY_SIGNALS)
        max_energy = max(high, low)
        if max_energy < ENERGY_MIN_SCORE:
            return None
        if high > low and high - low >= ENERGY_LEAD_MARGIN:
            return UserEnergy.HIGH
        if low > high and low - high >= ENERGY_LEAD_MARGIN:
            return UserEnergy.LOW
        return UserEnergy.MEDIUM

    # ------------------------------------------------------------------
    # Cognitive state
    # ------------------------------------------------------------------

    def _score_cognitive(
        self, text: str
    ) -> Tuple[Optional[UserCognitiveState], Dict[UserCognitiveState, List[str]]]:
        scores: Dict[UserCognitiveState, float] = {
            state: 0.0 for state in UserCognitiveState
        }
        descriptions: Dict[UserCognitiveState, List[str]] = {
            state: [] for state in UserCognitiveState
        }
        for state, signals in COGNITIVE_SIGNALS.items():
            for pattern, weight, desc in signals:
                if pattern in text:
                    scores[state] += weight
                    descriptions[state].append(desc)

        best_score = max(scores.values())
        if best_score < COGNITIVE_MIN_SCORE:
            return None, descriptions

        candidates = sorted(
            (state for state, score in scores.items() if score >= COGNITIVE_MIN_SCORE),
            key=lambda state: (-scores[state], COGNITIVE_PRIORITY.index(state)),
        )
        return candidates[0], descriptions

    # ------------------------------------------------------------------
    # Urgency
    # ------------------------------------------------------------------

    def _score_urgency(self, text: str) -> Optional[float]:
        score = self._sum_weights(text, URGENCY_SIGNALS)
        if score == 0.0:
            return 0.0
        return round(_clamp(score, 0.0, 1.0), 2)

    # ------------------------------------------------------------------
    # Engagement
    # ------------------------------------------------------------------

    def _score_engagement(
        self, text: str, content: str, intent: Optional[IntentResult]
    ) -> Optional[float]:
        length_factor = min(1.0, len(content) / 400.0)
        signal_sum = self._sum_weights(text, ENGAGEMENT_SIGNALS)
        question_boost = 0.05 * text.count("?")
        intent_boost = 0.0
        if intent is not None and intent.intent is not None:
            engaged_intents = {
                "EMOTIONAL_SUPPORT",
                "PROBLEM_SOLVING",
                "DECISION",
                "PLANNING",
                "CREATION",
            }
            if intent.intent.value in engaged_intents:
                intent_boost = 0.05
        return round(
            _clamp(
                0.20 + 0.35 * length_factor + signal_sum + question_boost + intent_boost,
                0.0,
                1.0,
            ),
            2,
        )

    # ------------------------------------------------------------------
    # Confidence & signal descriptions
    # ------------------------------------------------------------------

    def _score_confidence(
        self, best_emotion_score: float, n_emotion_signals: int, n_other_signals: int
    ) -> float:
        if best_emotion_score == 0.0 and n_emotion_signals == 0 and n_other_signals == 0:
            return 0.0
        return round(
            min(
                0.98,
                0.20
                + 0.50 * best_emotion_score
                + 0.04 * n_emotion_signals
                + 0.02 * n_other_signals,
            ),
            2,
        )

    def _collect_signals(
        self,
        primary_descriptions: List[str],
        emotion_descriptions: Dict[UserEmotionState, List[str]],
        cognitive_descriptions: List[str],
    ) -> List[str]:
        ordered: List[str] = list(primary_descriptions)
        for state in EMOTION_PRIORITY:
            for desc in emotion_descriptions.get(state, []):
                if desc not in ordered:
                    ordered.append(desc)
        for desc in cognitive_descriptions:
            if desc not in ordered:
                ordered.append(desc)
        return ordered[:MAX_SIGNALS]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sum_weights(text: str, signals: List[WeightedSignal]) -> float:
        total = 0.0
        for pattern, weight in signals:
            if pattern in text:
                total += weight
        return total

    @staticmethod
    def _count_matches(text: str, signals: List[WeightedSignal]) -> int:
        return sum(1 for pattern, _ in signals if pattern in text)
