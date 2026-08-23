"""Deterministic TemporalThread lifecycle handling for the ChronOS Engine
(Phase 3D).

Turns meaningful temporal moments into persistent life threads. Given the
already-computed outputs of Phase 3B (``TemporalEventDetector``) and Phase 3C
(``TemporalThreadMatcher``), answers exactly one question per interaction:
what lifecycle mutation — if any — should be performed and persisted?

Behavior contract (all deterministic, all offline):

A. Confident NO_MATCH     A new ``TemporalThread`` is created. Its subject is
                          derived conservatively from the event's grounded
                          description (leading deliberation phrases are
                          stripped, nothing is invented). The thread carries
                          ``origin_memory_id`` / ``related_memory_ids``
                          references to the existing memory — never copies of
                          memory content — and both thread and event are
                          persisted through the ``BaseTemporalStore``.
B. Confident MATCH        The event is attached to the authoritative stored
                          thread (``thread_id``, deduplicated memory link,
                          fresh ``updated_at``) and an explicit, single-place
                          transition policy decides whether the status moves
                          (OPEN->ACTIVE on plain continuation; RESOLVED /
                          ABANDONED / CHANGED only with strong, hedging-
                          resistant outcome evidence). Historical fields
                          (origin, subject, created_at) are never rewritten.
C. AMBIGUOUS              No mutation whatsoever: no thread is created, none
                          of the candidate threads is touched, the event
                          stays unthreaded. The result says so honestly.
D. NO EVENT               Nothing happens; ``attempted=False``.

Idempotency: before creating a thread, the manager checks whether a thread
already originates from the same memory (bounded targeted lookup) and, before
attaching an event, whether that memory is already linked to the matched
thread — accidental reprocessing cannot duplicate threads or events.

No AI, no embeddings, no Ollama: works fully with AI disabled.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from chronos_engine.core.interfaces import (
    BaseTemporalStore,
    BaseTemporalThreadLifecycleManager,
)
from chronos_engine.state.models import ConsistencyResult, GoalAnalysisResult
from chronos_engine.temporal.matcher import (
    _CHANGE_TYPES,
    _normalize,
    _split_meaningful,
)
from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalEventDetectionResult,
    TemporalLifecycleResult,
    TemporalThread,
    TemporalThreadMatchResult,
    TemporalThreadStatus,
)

# (substring pattern, weight, human-readable description)
Signal = Tuple[str, float, str]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Thread subject derivation
# ---------------------------------------------------------------------------

# Leading deliberation phrases removed when deriving a thread subject. Matched
# longest-first so compound phrases win over their suffixes. Stripping only
# ever removes the user's own framing words — the remaining words stay
# untouched, so subjects remain evidence-grounded.
_SUBJECT_STRIP_PREFIXES: List[str] = [
    "i don't know if i should",
    "i dont know if i should",
    "i'm not sure if i should",
    "im not sure if i should",
    "not sure whether i should",
    "not sure if i should",
    "seriously considering",
    "i'm thinking about",
    "i am thinking about",
    "im thinking about",
    "i'm thinking of",
    "i am thinking of",
    "im thinking of",
    "i've decided to",
    "i have decided to",
    "ive decided to",
    "i made up my mind to",
    "made up my mind to",
    "i'm considering",
    "i am considering",
    "im considering",
    "whether i should",
    "i decided to",
    "thinking about",
    "thinking of",
    "considering",
    "my goal is to",
    "my dream is to",
    "i want to become",
    "i promised myself",
    "promise myself",
    "i decided",
    "decided to",
    "chose to",
    "i want to",
    "i wanted to",
    "want to",
    "i'm going to",
    "i am going to",
    "im going to",
    "going to",
    "should i",
    "i should",
    "what if i",
    "i'm scared of",
    "i am scared of",
    "im scared of",
    "i'm afraid of",
    "i am afraid of",
    "scared of",
    "afraid of",
    "terrified of",
    "i'm scared",
    "i am scared",
    "i'm afraid",
    "i believe",
    "i've realised",
    "i've realized",
    "i realized",
    "i used to think",
    "my goal is",
    "my dream is",
    "i promise",
    "from now on",
]

# Connective openers sometimes left behind after prefix stripping.
_SUBJECT_CONNECTORS: List[str] = ["to ", "that i ", "that "]

_SUBJECT_MAX_LENGTH = 72


def derive_thread_subject(description: str, temporal_type=None) -> str:
    """Derive a concise, evidence-grounded subject from an event description.

    Deterministic: strips a known deliberation prefix when present, drops
    trailing punctuation, collapses whitespace, caps length at a word
    boundary and capitalizes the first letter. Never invents content; when
    nothing usable remains the (capped) description itself is used.
    """
    text = " ".join((description or "").split())
    if not text:
        label = temporal_type.value.replace("_", " ").lower() if temporal_type else "life"
        return f"Untitled {label} thread"

    lowered = text.lower()
    for prefix in sorted(_SUBJECT_STRIP_PREFIXES, key=len, reverse=True):
        if lowered.startswith(prefix):
            remainder = text[len(prefix):].lstrip(" ,.;:-–—")
            for connector in _SUBJECT_CONNECTORS:
                if remainder.lower().startswith(connector):
                    remainder = remainder[len(connector):]
                    break
            text = remainder.strip() or text
            break

    text = text.rstrip(".!? ").strip()
    if len(text) > _SUBJECT_MAX_LENGTH:
        cut = text[:_SUBJECT_MAX_LENGTH].rsplit(" ", 1)[0].rstrip(",;:- ")
        text = cut + "..."

    for idx, char in enumerate(text):
        if char.isalpha():
            text = text[:idx] + char.upper() + text[idx + 1:]
            break
    return text


# ---------------------------------------------------------------------------
# Status-transition evidence
# ---------------------------------------------------------------------------

# Transitions away from mere continuation require explicit outcome evidence
# in the current input. Weights are documented, tested implementation values,
# not calibrated probabilities.
RESOLUTION_SIGNALS: List[Signal] = [
    ("finally left", 0.70, "completed exit"),
    ("i left my job", 0.60, "job exit stated"),
    ("left my job", 0.55, "job exit stated"),
    ("finally quit", 0.70, "completed quit"),
    ("i quit my", 0.65, "quit stated"),
    ("quit my job", 0.60, "job quit stated"),
    ("resigned from", 0.65, "resignation"),
    ("handed in my notice", 0.70, "resignation"),
    ("things worked out", 0.60, "positive outcome"),
    ("it worked out", 0.60, "positive outcome"),
    ("ended up", 0.45, "outcome stated"),
    ("made my decision", 0.70, "decision reached"),
    ("decision is made", 0.65, "decision reached"),
    ("decision made", 0.60, "decision reached"),
    ("decided to stay", 0.65, "decision reached"),
    ("decided to leave", 0.65, "decision reached"),
    ("decided to go", 0.55, "decision reached"),
    ("i stayed", 0.50, "outcome stated"),
    ("i'm staying", 0.55, "outcome stated"),
    ("i am staying", 0.55, "outcome stated"),
    ("finally graduated", 0.75, "milestone completed"),
    ("i graduated", 0.70, "milestone completed"),
    ("finished my degree", 0.65, "milestone completed"),
    ("completed my degree", 0.65, "milestone completed"),
    ("got my degree", 0.60, "milestone completed"),
    ("landed the job", 0.65, "offer accepted"),
    ("got the job", 0.60, "offer accepted"),
    ("passed my exam", 0.60, "exam passed"),
    ("passed my exams", 0.60, "exam passed"),
    ("passed my final", 0.55, "exam passed"),
    ("got married", 0.70, "milestone completed"),
    ("moved in", 0.50, "transition completed"),
    ("finally launched", 0.60, "launch completed"),
    ("finally shipped", 0.55, "ship completed"),
    ("it's done", 0.60, "completion stated"),
    ("its done", 0.55, "completion stated"),
    ("all done", 0.45, "completion stated"),
]

ABANDONED_SIGNALS: List[Signal] = [
    ("i give up", 0.80, "explicit giving up"),
    ("gave up on", 0.70, "explicit giving up"),
    ("giving up on", 0.70, "explicit giving up"),
    ("i've given up", 0.75, "explicit giving up"),
    ("ive given up", 0.75, "explicit giving up"),
    ("giving up", 0.60, "giving-up language"),
    ("abandoning my", 0.65, "abandonment language"),
    ("abandon the plan", 0.65, "abandonment language"),
    ("abandon this", 0.60, "abandonment language"),
    ("not going to pursue", 0.65, "pursuit ended"),
    ("no longer pursuing", 0.65, "pursuit ended"),
]

CHANGED_SIGNALS: List[Signal] = [
    ("changed my mind", 0.75, "direction change stated"),
    (" instead", 0.60, "alternative direction chosen"),
    ("going a different direction", 0.70, "direction change stated"),
    ("taking a different direction", 0.70, "direction change stated"),
    ("different path now", 0.65, "direction change stated"),
    ("switching to", 0.65, "direction change stated"),
    ("switched to", 0.65, "direction change stated"),
    ("no longer want to", 0.70, "desire withdrawn"),
    ("don't want to be", 0.60, "identity direction dropped"),
]

# Existing consistency-engine change evidence that relates to the matched
# thread corroborates a CHANGED transition.
_CHANGE_CORROBORATION_BONUS = 0.35

# Hedging language dampens outcome evidence: weak outcomes under hedges must
# never move a thread's status. Strong multi-signal evidence survives.
_HEDGE_PATTERNS: List[str] = [
    "maybe",
    "perhaps",
    "possibly",
    "not sure",
    "not certain",
    "i think",
    "kinda",
    "sort of",
]
_HEDGE_PENALTY = 0.5

# Minimum penalized evidence score for RESOLVED / ABANDONED / CHANGED.
_TRANSITION_THRESHOLD = 0.55

# Deterministic precedence when several categories clear the threshold:
# an explicit outcome resolves the question first, explicit giving-up beats a
# redirection, redirection beats the rest.
_TRANSITION_PRECEDENCE: List[Tuple[str, object]] = [
    ("RESOLVED", TemporalThreadStatus.RESOLVED),
    ("ABANDONED", TemporalThreadStatus.ABANDONED),
    ("CHANGED", TemporalThreadStatus.CHANGED),
]

# Allowed transitions away from each current status. Continuation (keeping
# the status, or OPEN -> ACTIVE) is handled separately. Terminal statuses
# allow nothing; they are excluded from candidate retrieval anyway — this is
# defensive symmetry with the store contract.
_ALLOWED_TRANSITIONS: Dict[TemporalThreadStatus, set] = {
    TemporalThreadStatus.OPEN: {
        TemporalThreadStatus.RESOLVED,
        TemporalThreadStatus.ABANDONED,
        TemporalThreadStatus.CHANGED,
    },
    TemporalThreadStatus.ACTIVE: {
        TemporalThreadStatus.RESOLVED,
        TemporalThreadStatus.ABANDONED,
        TemporalThreadStatus.CHANGED,
    },
    TemporalThreadStatus.CHANGED: {
        TemporalThreadStatus.RESOLVED,
        TemporalThreadStatus.ABANDONED,
    },
    TemporalThreadStatus.RESOLVED: set(),
    TemporalThreadStatus.ABANDONED: set(),
    TemporalThreadStatus.ARCHIVED: set(),
}


class _TransitionProposal:
    """Outcome of the single transition-policy evaluation."""

    __slots__ = ("status", "transitioned", "reason", "confidence", "signals")

    def __init__(self, status, transitioned, reason, confidence, signals):
        self.status = status
        self.transitioned = transitioned
        self.reason = reason
        self.confidence = confidence
        self.signals = signals


def _score_signals(text: str, table: List[Signal]) -> Tuple[float, List[str]]:
    total = 0.0
    descriptions: List[str] = []
    for pattern, weight, desc in table:
        if pattern in text:
            total += weight
            if desc not in descriptions:
                descriptions.append(desc)
    return round(total, 4), descriptions


class TemporalThreadLifecycleManager(BaseTemporalThreadLifecycleManager):
    """Default deterministic implementation of the Phase 3D lifecycle."""

    def __init__(self, store: BaseTemporalStore) -> None:
        self.store = store

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def handle(
        self,
        user_id: str,
        detection: TemporalEventDetectionResult,
        match_result: Optional[TemporalThreadMatchResult] = None,
        input_content: Optional[str] = None,
        goal_analysis: Optional[GoalAnalysisResult] = None,
        consistency_result: Optional[ConsistencyResult] = None,
    ) -> TemporalLifecycleResult:
        if detection is None or not detection.detected or detection.event is None:
            return TemporalLifecycleResult(
                attempted=False,
                skipped=True,
                reason="No temporal event detected; lifecycle handling skipped.",
            )

        event = detection.event
        match_result = match_result or TemporalThreadMatchResult(attempted=False)

        # Ambiguity: perform nothing, say so honestly.
        if match_result.ambiguous:
            return TemporalLifecycleResult(
                attempted=True,
                created=False,
                updated=False,
                persisted=False,
                ambiguous=True,
                skipped=False,
                reason=(
                    "Multiple plausible temporal threads were found; "
                    "no lifecycle mutation was made."
                ),
                confidence=round(match_result.confidence, 2),
                signals=list(match_result.signals)[:6],
            )

        try:
            if match_result.matched and match_result.thread_id:
                return await self._continue_thread(
                    user_id=user_id,
                    event=event,
                    detection=detection,
                    match_result=match_result,
                    input_content=input_content,
                    consistency_result=consistency_result,
                )
            return await self._create_thread(
                user_id=user_id,
                event=event,
                detection=detection,
            )
        except Exception as exc:  # storage failures must never claim success
            return TemporalLifecycleResult(
                attempted=True,
                created=False,
                updated=False,
                persisted=False,
                reason=(
                    "Temporal lifecycle handling failed before completing "
                    f"({type(exc).__name__}); no success is claimed."
                ),
            )

    # ------------------------------------------------------------------
    # Creation (confident NO_MATCH)
    # ------------------------------------------------------------------

    async def _create_thread(
        self,
        user_id: str,
        event: TemporalEvent,
        detection: TemporalEventDetectionResult,
    ) -> TemporalLifecycleResult:
        # Idempotency: a thread originating from this exact memory already
        # exists (reprocessing) — continue it instead of duplicating.
        if event.memory_id:
            existing = await self.store.find_thread_by_origin_memory(
                user_id, event.memory_id
            )
            if existing is not None:
                redirect_match = TemporalThreadMatchResult(
                    attempted=True,
                    matched=True,
                    thread_id=existing.id,
                    confidence=round(detection.confidence, 2),
                    reason=(
                        "A thread already originates from this memory; "
                        "continuing it instead of creating a duplicate."
                    ),
                    matched_thread=existing,
                )
                result = await self._continue_thread(
                    user_id=user_id,
                    event=event,
                    detection=detection,
                    match_result=redirect_match,
                    input_content=event.description,
                    consistency_result=None,
                )
                result.signals.insert(
                    0, "Duplicate-thread guard: origin memory already owns a thread."
                )
                return result

        subject = derive_thread_subject(event.description, event.temporal_type)
        now = _utcnow()
        thread = TemporalThread(
            user_id=user_id,
            temporal_type=event.temporal_type,
            subject=subject,
            description=event.description or None,
            status=TemporalThreadStatus.OPEN,
            origin_memory_id=event.memory_id,
            related_memory_ids=[event.memory_id] if event.memory_id else [],
            importance=event.importance,
            confidence=round(detection.confidence, 2),
            created_at=now,
            updated_at=now,
        )
        saved_thread = await self.store.save_thread(thread)

        event.thread_id = saved_thread.id
        if not event.user_id:
            event.user_id = user_id
        saved_event = await self.store.save_event(event)

        return TemporalLifecycleResult(
            attempted=True,
            created=True,
            updated=False,
            persisted=True,
            thread_id=saved_thread.id,
            event_id=saved_event.id,
            thread_subject=saved_thread.subject,
            previous_status=None,
            current_status=saved_thread.status,
            transitioned=False,
            reason=(
                f"Created new temporal thread '{saved_thread.subject}' from "
                f"detected "
                f"{event.temporal_type.value if event.temporal_type else 'TEMPORAL'} event."
            ),
            confidence=round(detection.confidence, 2),
            signals=[
                f"Subject derived conservatively from event evidence: '{saved_thread.subject}'.",
                (
                    f"Origin memory linked: {event.memory_id}"
                    if event.memory_id
                    else "No memory reference available."
                ),
            ],
        )

    # ------------------------------------------------------------------
    # Continuation (confident MATCH, or idempotent redirect)
    # ------------------------------------------------------------------

    async def _continue_thread(
        self,
        user_id: str,
        event: TemporalEvent,
        detection: TemporalEventDetectionResult,
        match_result: TemporalThreadMatchResult,
        input_content: Optional[str],
        consistency_result: Optional[ConsistencyResult],
    ) -> TemporalLifecycleResult:
        thread = await self.store.get_thread(match_result.thread_id, user_id)
        if thread is None:
            return TemporalLifecycleResult(
                attempted=True,
                created=False,
                updated=False,
                persisted=False,
                thread_id=match_result.thread_id,
                reason=(
                    "Matched thread could not be loaded for this user; "
                    "nothing was modified."
                ),
                confidence=round(match_result.confidence, 2),
            )

        # Idempotency: this memory is already attached to the thread —
        # reprocessing must not append duplicates or mutate the thread again.
        if event.memory_id:
            attached = await self.store.get_events_by_thread(thread.id, user_id)
            if any(e.memory_id == event.memory_id for e in attached):
                event.thread_id = thread.id
                return TemporalLifecycleResult(
                    attempted=True,
                    created=False,
                    updated=False,
                    persisted=False,
                    thread_id=thread.id,
                    event_id=event.id,
                    thread_subject=thread.subject,
                    previous_status=thread.status,
                    current_status=thread.status,
                    transitioned=False,
                    reason=(
                        f"This memory is already attached to thread "
                        f"'{thread.subject or thread.id}'; no duplicate write was made."
                    ),
                    confidence=round(match_result.confidence, 2),
                    signals=["Idempotency guard: memory already linked to thread."],
                )

        proposal = self._propose_transition(
            thread,
            input_content if input_content else event.description,
            consistency_result,
            match_confidence=match_result.confidence,
        )

        previous_status = thread.status
        event.thread_id = thread.id
        if not event.user_id:
            event.user_id = user_id
        saved_event = await self.store.save_event(event)

        if event.memory_id and event.memory_id not in thread.related_memory_ids:
            thread.related_memory_ids.append(event.memory_id)
        thread.updated_at = _utcnow()
        thread.status = proposal.status
        await self.store.save_thread(thread)

        label = thread.subject or thread.id
        return TemporalLifecycleResult(
            attempted=True,
            created=False,
            updated=True,
            persisted=True,
            thread_id=thread.id,
            event_id=saved_event.id,
            thread_subject=label,
            previous_status=previous_status,
            current_status=thread.status,
            transitioned=proposal.transitioned,
            reason=proposal.reason,
            confidence=proposal.confidence,
            signals=proposal.signals,
        )

    # ------------------------------------------------------------------
    # Transition policy — the ONLY place status mutations are decided
    # ------------------------------------------------------------------

    def _propose_transition(
        self,
        thread: TemporalThread,
        text: str,
        consistency_result: Optional[ConsistencyResult],
        match_confidence: float,
    ) -> _TransitionProposal:
        label = thread.subject or thread.id
        current = thread.status
        evidence_text = (text or "").lower()

        resolved_score, resolved_desc = _score_signals(evidence_text, RESOLUTION_SIGNALS)
        abandoned_score, abandoned_desc = _score_signals(evidence_text, ABANDONED_SIGNALS)
        changed_score, changed_desc = _score_signals(evidence_text, CHANGED_SIGNALS)

        signals: List[str] = []
        if resolved_desc:
            signals.append(f"Resolution evidence: {', '.join(resolved_desc)}.")
        if abandoned_desc:
            signals.append(f"Abandonment evidence: {', '.join(abandoned_desc)}.")
        if changed_desc:
            signals.append(f"Direction-change evidence: {', '.join(changed_desc)}.")

        if self._change_evidence_relates(thread, consistency_result):
            changed_score = round(changed_score + _CHANGE_CORROBORATION_BONUS, 4)
            signals.append("Consistency/change evidence relates to this thread.")

        if any(hedge in evidence_text for hedge in _HEDGE_PATTERNS):
            resolved_score = round(resolved_score * _HEDGE_PENALTY, 4)
            abandoned_score = round(abandoned_score * _HEDGE_PENALTY, 4)
            changed_score = round(changed_score * _HEDGE_PENALTY, 4)
            signals.append("Hedging language present; outcome evidence dampened.")

        scored = [
            (score, name, status)
            for score, (name, status) in zip(
                [resolved_score, abandoned_score, changed_score],
                _TRANSITION_PRECEDENCE,
            )
        ]
        scored.sort(key=lambda item: (-item[0], _TRANSITION_PRECEDENCE.index((item[1], item[2]))))
        best_score, best_name, best_status = scored[0]

        if best_score < _TRANSITION_THRESHOLD:
            # Plain continuation. Confidence mirrors the matcher's evidence.
            continuation = (
                TemporalThreadStatus.ACTIVE if current is TemporalThreadStatus.OPEN else current
            )
            transitioned = continuation is not current
            reason = (
                f"Attached temporal event to existing thread '{label}'; "
                f"status {'OPEN -> ACTIVE' if transitioned else f'remains {current.value}'}."
            )
            return _TransitionProposal(
                status=continuation,
                transitioned=transitioned,
                reason=reason,
                confidence=round(min(0.95, match_confidence), 2),
                signals=signals
                or ["No outcome evidence beyond confident thread continuation."],
            )

        if best_status not in _ALLOWED_TRANSITIONS.get(current, set()):
            signals.append(
                f"{best_name.title()} evidence found but transition from "
                f"{current.value} is not permitted; status kept."
            )
            return _TransitionProposal(
                status=current,
                transitioned=False,
                reason=(
                    f"Attached temporal event to existing thread '{label}'; "
                    f"{best_name.lower()} evidence insufficient to leave "
                    f"{current.value}; status remains {current.value}."
                ),
                confidence=round(min(0.95, match_confidence), 2),
                signals=signals,
            )

        confidence = round(min(0.95, 0.5 * match_confidence + 0.5 * min(1.0, best_score)), 2)
        return _TransitionProposal(
            status=best_status,
            transitioned=best_status is not current,
            reason=(
                f"Attached temporal event to existing thread '{label}'; "
                f"status {current.value} -> {best_status.value} ({best_name.lower()} evidence)."
            ),
            confidence=confidence,
            signals=signals,
        )

    @staticmethod
    def _change_evidence_relates(
        thread: TemporalThread,
        consistency_result: Optional[ConsistencyResult],
    ) -> bool:
        """Does consistency/change evidence clearly refer to THIS thread?

        Mirrors the matcher's relation notion (shared meaningful tokens with
        the subject, or explicit shared memory ids) without duplicating its
        scoring.
        """
        if consistency_result is None:
            return False
        subject_tokens = _normalize(thread.subject)
        thread_memories = set(thread.related_memory_ids)
        if thread.origin_memory_id:
            thread_memories.add(thread.origin_memory_id)
        for entry in list(consistency_result.changes) + list(consistency_result.contradictions):
            if (entry.type or "") not in _CHANGE_TYPES:
                continue
            entry_text = " ".join(
                part
                for part in (entry.description, entry.previous_value, entry.current_value)
                if part
            )
            if _split_meaningful(_normalize(entry_text) & subject_tokens)[0]:
                return True
            if thread_memories and set(entry.supporting_memory_ids) & thread_memories:
                return True
        return False


__all__ = [
    "TemporalThreadLifecycleManager",
    "derive_thread_subject",
]
