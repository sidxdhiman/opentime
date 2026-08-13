"""Deterministic, offline user-intent detection for the ChronOS engine.

Implements the 13-category intent taxonomy from the ChronOS plan using a
weighted-signal approach. No LLM calls and no external dependencies: each
intent category carries a list of ``(pattern, weight, description)`` signals
and the detector scores raw input text by lowercase substring matching.

Selection rules
---------------
* Score-primary: the intent with the highest accumulated signal weight wins.
* Threshold: if the winning score is below ``MIN_SCORE`` the intent is
  ``UNKNOWN`` (the input does not clearly signal a communicative need).
* Tie-break: on a score tie the first intent in ``INTENT_PRIORITY`` wins,
  because a stronger communicative need is preferred when signals are
  ambiguous.
* Confidence: derived purely from matched signals —
  ``round(min(0.98, 0.35 + winning_score), 2)``. ``UNKNOWN`` always yields
  ``0.0``.

Intent vs emotion: the detector answers *what the user wants from ChronOS*,
never *how the user feels*. Emotional vocabulary alone (e.g. ``frustrated``)
carries no weight; emotion only matters when it signals a need for support.
"""

from typing import Dict, List, Tuple

from chronos_engine.core.interfaces import BaseIntentDetector
from chronos_engine.core.models import IntentType
from chronos_engine.state.models import IntentResult

# (substring pattern, weight, human-readable description)
Signal = Tuple[str, float, str]

# Signals are matched as lowercase substrings of the lowercased input.
SIGNAL_TABLE: Dict[IntentType, List[Signal]] = {
    IntentType.QUESTION: [
        ("what", 0.15, "starts a wh- question"),
        ("where", 0.15, "starts a wh- question"),
        ("when", 0.15, "starts a wh- question"),
        ("who", 0.15, "starts a wh- question"),
        ("why", 0.15, "starts a wh- question"),
        ("how", 0.15, "starts a wh- question"),
        ("?", 0.15, "ends with a question mark"),
    ],
    IntentType.INFORMATION: [
        ("what is", 0.5, "asks for a definition"),
        ("what are", 0.5, "asks for a definition"),
        ("define", 0.5, "asks for a definition"),
        ("what does", 0.45, "asks for an explanation"),
        ("explain", 0.45, "asks for an explanation"),
        ("tell me about", 0.45, "asks for an explanation"),
        ("difference between", 0.5, "asks for a comparison"),
        ("how does", 0.4, "asks how something works"),
        ("how do i", 0.35, "asks how to do something"),
        ("meaning of", 0.5, "asks for a definition"),
    ],
    IntentType.DECISION: [
        ("should i", 0.5, "asks for a recommendation"),
        ("should we", 0.5, "asks for a recommendation"),
        ("do you think i should", 0.5, "asks for a recommendation"),
        ("choose between", 0.5, "weighs options"),
        ("which should", 0.45, "asks which option to pick"),
        ("is it better to", 0.45, "weighs options"),
        ("can't decide", 0.45, "weighs options"),
        ("worth it", 0.4, "asks whether something is worth it"),
        ("which one", 0.4, "asks which option to pick"),
        ("decide", 0.3, "discusses a decision"),
        ("decision", 0.3, "discusses a decision"),
    ],
    IntentType.PLANNING: [
        ("planning", 0.4, "plans how to proceed"),
        ("plan", 0.35, "plans how to proceed"),
        ("roadmap", 0.5, "plans a roadmap"),
        ("schedule", 0.45, "plans a schedule"),
        ("how should i approach", 0.6, "asks how to approach something"),
        ("steps", 0.35, "plans steps"),
        ("strategy", 0.4, "plans a strategy"),
        ("outline", 0.35, "plans an outline"),
        ("itinerary", 0.5, "plans an itinerary"),
        ("plan out", 0.4, "plans how to proceed"),
        ("organize", 0.35, "plans an organization"),
    ],
    IntentType.REFLECTION: [
        ("how have i changed", 0.7, "asks how they changed"),
        ("looking back", 0.6, "looks back over the past"),
        ("what changed", 0.6, "asks what changed"),
        ("compared to before", 0.6, "compares to the past"),
        ("in retrospect", 0.5, "looks back over the past"),
        ("look back", 0.5, "looks back over the past"),
        ("changed since", 0.5, "asks what changed"),
        ("reflect", 0.45, "reflects on the past"),
        ("reflection", 0.45, "reflects on the past"),
        ("how did i", 0.4, "looks back over the past"),
        ("over the past", 0.35, "looks back over the past"),
        ("over the last", 0.35, "looks back over the past"),
    ],
    IntentType.EMOTIONAL_SUPPORT: [
        ("i don't know what to do", 0.5, "feels lost and needs support"),
        ("feel like giving up", 0.5, "needs support to keep going"),
        ("overwhelmed", 0.45, "feels overwhelmed"),
        ("stressed out", 0.45, "feels stressed"),
        ("it's too much", 0.4, "feels overwhelmed"),
        ("can't handle", 0.4, "feels overwhelmed"),
        ("need support", 0.4, "asks for support"),
        ("need someone to talk to", 0.4, "asks for support"),
        ("i'm feeling", 0.35, "shares how they feel"),
        ("i feel", 0.3, "shares how they feel"),
    ],
    IntentType.CREATION: [
        ("create a", 0.55, "asks to create something"),
        ("create", 0.5, "asks to create something"),
        ("write a", 0.5, "asks to write something"),
        ("build a", 0.5, "asks to build something"),
        ("generate", 0.5, "asks to generate something"),
        ("design a", 0.5, "asks to design something"),
        ("draft a", 0.45, "asks to draft something"),
        ("develop a", 0.45, "asks to develop something"),
        ("implement a", 0.45, "asks to implement something"),
        ("compose", 0.45, "asks to compose something"),
        ("make a", 0.4, "asks to make something"),
        ("produce", 0.4, "asks to produce something"),
    ],
    IntentType.PROBLEM_SOLVING: [
        ("stuck", 0.45, "is stuck on a problem"),
        ("problem", 0.4, "reports a problem"),
        ("issue", 0.35, "reports a problem"),
        ("error", 0.3, "reports an error"),
        ("bug", 0.3, "reports a bug"),
        ("not working", 0.5, "reports something broken"),
        ("doesn't work", 0.5, "reports something broken"),
        ("does not work", 0.5, "reports something broken"),
        ("broken", 0.5, "reports something broken"),
        ("crashing", 0.5, "reports something crashing"),
        ("crash", 0.4, "reports a crash"),
        ("troubleshoot", 0.5, "asks to troubleshoot"),
        ("fix", 0.35, "asks to fix something"),
        ("why isn't", 0.45, "asks why something fails"),
        ("keeps failing", 0.45, "reports a recurring failure"),
    ],
    IntentType.STATUS_UPDATE: [
        ("just finished", 0.5, "reports what was finished"),
        ("wrapped up", 0.5, "reports what was finished"),
        ("finished", 0.4, "reports what was finished"),
        ("completed", 0.4, "reports what was completed"),
        ("done with", 0.4, "reports what was completed"),
        ("now working on", 0.45, "reports current work"),
        ("currently working on", 0.45, "reports current work"),
        ("started working on", 0.4, "reports work just started"),
        ("just started", 0.4, "reports work just started"),
        ("in progress", 0.4, "reports ongoing work"),
        ("update on", 0.4, "gives an update"),
        ("progress", 0.3, "reports progress"),
        ("status", 0.3, "reports status"),
    ],
    IntentType.JOURNAL_ENTRY: [
        ("today i", 0.4, "writes a journal entry"),
        ("today was", 0.4, "writes a journal entry"),
        ("my day", 0.4, "writes a journal entry"),
        ("i woke up", 0.4, "writes a journal entry"),
        ("i noticed", 0.35, "writes a journal entry"),
        ("lately", 0.35, "writes a journal entry"),
        ("this week", 0.3, "writes a journal entry"),
        ("i've been", 0.3, "writes a journal entry"),
        ("i have been", 0.3, "writes a journal entry"),
        ("i felt", 0.3, "writes a journal entry"),
    ],
    IntentType.COMMAND: [
        ("summarize", 0.5, "asks to summarize"),
        ("remind me", 0.5, "asks to set a reminder"),
        ("translate", 0.5, "asks to translate"),
        ("write down", 0.45, "asks to write something down"),
        ("convert", 0.4, "asks to convert"),
        ("take note", 0.4, "asks to take a note"),
        ("remember that", 0.4, "asks to remember something"),
        ("list all", 0.4, "asks to list items"),
        ("show me", 0.3, "asks to show something"),
    ],
    IntentType.REQUEST: [
        ("i need you to", 0.45, "directly requests an action"),
        ("i'd like you to", 0.45, "directly requests an action"),
        ("can you", 0.35, "politely requests an action"),
        ("could you", 0.35, "politely requests an action"),
        ("help me", 0.35, "requests help"),
        ("do me a favor", 0.4, "requests a favor"),
        ("would you", 0.3, "politely requests an action"),
        ("please", 0.3, "politely requests an action"),
    ],
    IntentType.UNKNOWN: [],
}

# Score tie-breaker: stronger communicative needs are preferred first.
INTENT_PRIORITY: List[IntentType] = [
    IntentType.DECISION,
    IntentType.PROBLEM_SOLVING,
    IntentType.PLANNING,
    IntentType.CREATION,
    IntentType.REFLECTION,
    IntentType.EMOTIONAL_SUPPORT,
    IntentType.STATUS_UPDATE,
    IntentType.JOURNAL_ENTRY,
    IntentType.COMMAND,
    IntentType.INFORMATION,
    IntentType.QUESTION,
    IntentType.REQUEST,
    IntentType.UNKNOWN,
]

# Winning scores at or above this threshold produce a real intent; anything
# below resolves to UNKNOWN.
MIN_SCORE: float = 0.2


class IntentDetector(BaseIntentDetector):
    """Classifies raw input text into one of the 13 intent categories.

    Deterministic and fully offline: scores are computed from a static
    weighted-signal table via lowercase substring matching, so identical
    inputs always produce identical results.
    """

    async def detect_intent(self, user_input: str) -> IntentResult:
        """Detect the user's communication intent from raw input text."""
        if not user_input:
            return IntentResult(intent=IntentType.UNKNOWN, confidence=0.0, signals=[])

        text = user_input.lower()
        scores: Dict[IntentType, float] = {category: 0.0 for category in IntentType}
        matched_signals: Dict[IntentType, List[str]] = {
            category: [] for category in IntentType
        }

        for category, signals in SIGNAL_TABLE.items():
            for pattern, weight, description in signals:
                if pattern in text:
                    scores[category] += weight
                    matched_signals[category].append(description)

        best_score = max(scores.values())
        if best_score < MIN_SCORE:
            return IntentResult(intent=IntentType.UNKNOWN, confidence=0.0, signals=[])

        best_candidates = [
            category
            for category, score in scores.items()
            if score == best_score
        ]
        best_candidates.sort(key=lambda category: INTENT_PRIORITY.index(category))

        winning_intent = best_candidates[0]
        confidence = round(min(0.98, 0.35 + best_score), 2)
        return IntentResult(
            intent=winning_intent,
            confidence=confidence,
            signals=matched_signals[winning_intent],
        )
