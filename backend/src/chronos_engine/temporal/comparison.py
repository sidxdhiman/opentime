"""Deterministic Past-vs-Present comparison for the ChronOS Engine (Phase 3E).

Given the authoritative ``TemporalThread`` touched by this interaction and
its persisted ``TemporalEvent`` history, answers exactly one question: how
does the present moment relate to where that story began?

Strictly read-only: the comparison never mutates threads or events, never
persists anything, never crosses thread boundaries and introduces no new
matching algorithm. Threads and their events are handed in by the caller
(loaded through a ``BaseTemporalStore``); the comparison is pure analysis
over that evidence.

Anchors (documented, deterministic):

- Present  the NEWEST persisted event in the thread (the moment just
           attached by the lifecycle manager is included — comparison runs
           after lifecycle handling).
- Past     the stored event anchored to the thread's origin memory when it
           exists among the earlier events; otherwise the EARLIEST stored
           event. A thread needs two distinct moments to be comparable;
           anything less is honestly reported as
           ``INSUFFICIENT_EVIDENCE`` — unless the lifecycle manager itself
           provides a grounded resolution for this very interaction, which
           is reported without pretending a two-moment history exists.

Relation policy (evaluated top-down; first match wins):

1. Lifecycle-grounded transition this turn (authoritative — the single
   transition policy already validated hedging-resistant outcome evidence):
   RESOLVED stays RESOLVED; CHANGED and ABANDONED map to CHANGED
   (withdrawing from a pursuit is a directional change away from the past
   stance — documented mapping).
2. Fear stories: explicit realization evidence ("my fear came true") maps
   to CONTRADICTED; explicit overcoming evidence ("no longer afraid") maps
   to RESOLVED.
3. Deliberation / anticipation stories (QUESTION, DECISION,
   FUTURE_EXPECTATION): any outcome evidence from the SAME signal tables
   the lifecycle policy uses maps to RESOLVED. Unlike the lifecycle (which
   mutates and therefore demands threshold-strength evidence), comparison
   is observational: weaker outcome evidence grounds a lower-confidence
   RESOLVED observation instead of none.
4. Consistency evidence relating to THIS thread (shared meaningful tokens
   or explicit memory links — the same relation notion the matcher and
   lifecycle use): conflicts map to CONTRADICTED, goal/decision changes
   map to CHANGED.
5. Topic continuity between past and present: development/progress
   markers map to EVOLVED; shared meaningful tokens map to CONFIRMED;
   otherwise the story simply remains UNRESOLVED.

Evidence IDs are exposed and deduplicated; confidence is an explainable
evidence-weighted score capped at ``MAX_COMPARISON_CONFIDENCE`` (0.95).
Summaries are conservative templates quoting the stored descriptions —
they add framing words by ``TemporalType``, never invented content.

No AI, no embeddings, no Ollama: works fully with AI disabled.
"""

from typing import Dict, List, Optional

from chronos_engine.core.interfaces import BaseTemporalComparisonEngine
from chronos_engine.state.models import ConsistencyResult, GoalAnalysisResult
from chronos_engine.temporal.lifecycle import (
    _HEDGE_PATTERNS,
    RESOLUTION_SIGNALS,
    _score_signals,
)
from chronos_engine.temporal.matcher import (
    _CHANGE_TYPES,
    _normalize,
    _split_meaningful,
)
from chronos_engine.temporal.models import (
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalLifecycleResult,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)

# Explainability cap: comparison confidence never reaches 1.0. Documented,
# tested implementation value — not a calibrated probability.
MAX_COMPARISON_CONFIDENCE = 0.95

# Development language that indicates ongoing movement without closure.
_PROGRESS_MARKERS: List[str] = [
    "making progress",
    "made progress",
    "getting closer",
    "step closer",
    "one step",
    "still working on",
    "still practicing",
    "still training",
    "improving",
    "since then",
    "update on",
]

# Explicit fear-outcome language. Kept phrase-specific so neutral sentences
# ("it actually happened") cannot fabricate a contradiction.
_FEAR_REALIZED_SIGNALS: List[str] = [
    "fear came true",
    "feared most happened",
    "what i feared happened",
    "what i was afraid of happened",
    "worst case happened",
    "worst fears realized",
    "worst fears were realized",
]

_FEAR_OVERCOME_SIGNALS: List[str] = [
    "no longer afraid",
    "no longer scared",
    "not afraid anymore",
    "not scared anymore",
    "faced my fear",
    "fear is gone",
    "overcame my fear",
    "got over my fear",
]

# Consistency categories describing active conflict rather than evolution.
_CONFLICT_TYPES = {"STATEMENT_CONFLICT", "GOAL_CONFLICT"}

# Conservative framing templates. They quote the stored description and add
# only type-appropriate framing words — content is never invented.
_PAST_SUMMARY_TEMPLATES: Dict[TemporalType, str] = {
    TemporalType.FUTURE_EXPECTATION: 'Back then you were anticipating: "{description}"',
    TemporalType.DECISION: 'Back then you were weighing: "{description}"',
    TemporalType.GOAL: 'Back then you were aiming toward: "{description}"',
    TemporalType.FEAR: 'Back then you were afraid: "{description}"',
    TemporalType.PREDICTION: 'Back then you predicted: "{description}"',
    TemporalType.QUESTION: 'Back then you were wondering: "{description}"',
    TemporalType.PROMISE: 'Back then you had committed yourself: "{description}"',
    TemporalType.LIFE_EVENT: 'An earlier moment: "{description}"',
    TemporalType.BELIEF: 'Back then you believed: "{description}"',
    TemporalType.MILESTONE: 'You were working toward a milestone: "{description}"',
}
_DEFAULT_PAST_TEMPLATE = 'Earlier in this story: "{description}"'
_PAST_TEMPLATE_MAX_DESCRIPTION = 140

_PRESENT_SUMMARY_TEMPLATES: Dict[TemporalComparisonRelation, str] = {
    TemporalComparisonRelation.RESOLVED: 'Now it has played out: "{description}"',
    TemporalComparisonRelation.CONFIRMED: 'Now you stand by it: "{description}"',
    TemporalComparisonRelation.CHANGED: 'Since then your direction changed: "{description}"',
    TemporalComparisonRelation.EVOLVED: 'Where things stand now: "{description}"',
    TemporalComparisonRelation.CONTRADICTED: 'Now the situation contradicts it: "{description}"',
    TemporalComparisonRelation.UNRESOLVED: 'As of now it remains open: "{description}"',
}


def _clip(text: str, limit: int = _PAST_TEMPLATE_MAX_DESCRIPTION) -> str:
    """Trim whitespace and cap length at a word boundary. Never invents."""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit].rsplit(" ", 1)[0].rstrip(",;:- ")
    return cut + "..."


def _dedupe(items: List[Optional[str]]) -> List[str]:
    seen: set = set()
    ordered: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _contains_any(text: str, patterns: List[str]) -> List[str]:
    return [p for p in patterns if p in text]


def _sort_events(events: List[TemporalEvent]) -> List[TemporalEvent]:
    """Deterministic chronological order (store order is not contractual)."""
    return sorted(events, key=lambda event: (event.occurred_at, event.id))


class _PastPresent:
    """Resolved comparison anchors plus the evidence behind them."""

    __slots__ = ("past", "present", "earlier_events")

    def __init__(
        self,
        past: Optional[TemporalEvent],
        present: Optional[TemporalEvent],
        earlier_events: List[TemporalEvent],
    ) -> None:
        self.past = past
        self.present = present
        self.earlier_events = earlier_events


def _resolve_anchors(
    thread: TemporalThread, events: List[TemporalEvent]
) -> _PastPresent:
    """Pick the past/present anchor pair.

    Past prefers the event anchored to the thread's origin memory; the
    newest event is always the present. Only events strictly earlier than
    the present qualify as the past, so a single-moment thread can never
    compare a moment with itself.
    """
    ordered = _sort_events(events)
    if not ordered:
        return _PastPresent(None, None, [])
    present = ordered[-1]
    earlier = ordered[:-1]
    past: Optional[TemporalEvent] = None
    if thread.origin_memory_id:
        for event in earlier:
            if event.memory_id == thread.origin_memory_id:
                past = event
                break
    if past is None and earlier:
        past = earlier[0]
    return _PastPresent(past, present, earlier)


class TemporalComparisonEngine(BaseTemporalComparisonEngine):
    """Default deterministic implementation of BaseTemporalComparisonEngine."""

    async def compare(
        self,
        user_id: str,
        thread: Optional[TemporalThread],
        events: List[TemporalEvent],
        lifecycle_result: Optional[TemporalLifecycleResult] = None,
        consistency_result: Optional[ConsistencyResult] = None,
        goal_analysis: Optional[GoalAnalysisResult] = None,
    ) -> TemporalComparisonResult:
        if thread is None:
            return TemporalComparisonResult(
                attempted=False,
                comparable=False,
                reason="No temporal thread available; comparison skipped.",
            )

        anchors = _resolve_anchors(thread, events)
        lifecycle_applies = bool(
            lifecycle_result is not None
            and lifecycle_result.thread_id == thread.id
        )

        if anchors.past is None or anchors.present is None:
            return self._insufficient_history_result(
                thread, anchors, lifecycle_result if lifecycle_applies else None
            )

        return self._compare_moments(
            thread=thread,
            anchors=anchors,
            lifecycle_result=lifecycle_result if lifecycle_applies else None,
            consistency_result=consistency_result,
        )

    # ------------------------------------------------------------------
    # Insufficient-history handling
    # ------------------------------------------------------------------

    def _insufficient_history_result(
        self,
        thread: TemporalThread,
        anchors: _PastPresent,
        lifecycle_result: Optional[TemporalLifecycleResult],
    ) -> TemporalComparisonResult:
        single = anchors.present
        grounded_resolution = bool(
            lifecycle_result is not None
            and lifecycle_result.transitioned
            and lifecycle_result.current_status is TemporalThreadStatus.RESOLVED
        )
        result = TemporalComparisonResult(
            attempted=True,
            comparable=False,
            thread_id=thread.id,
            present_event_id=single.id if single else None,
            confidence=lifecycle_result.confidence if grounded_resolution else 0.0,
            signals=[
                "Fewer than two distinct temporal moments are recorded "
                "for this thread."
            ],
        )
        if grounded_resolution:
            result.relation = TemporalComparisonRelation.RESOLVED
            result.reason = (
                "The thread holds a single recorded moment, but the lifecycle "
                "manager grounded a resolution for this interaction; reported "
                "without claiming a two-moment comparison."
            )
            result.signals.append(
                "Grounded by lifecycle resolution evidence, not by event history."
            )
        else:
            result.relation = TemporalComparisonRelation.INSUFFICIENT_EVIDENCE
            result.reason = (
                "The thread holds fewer than two distinct temporal moments; "
                "a past-vs-present comparison is not yet possible."
            )
        if single is not None:
            result.evidence_event_ids = [single.id]
            result.evidence_memory_ids = _dedupe([single.memory_id])
        return result

    # ------------------------------------------------------------------
    # Full two-moment comparison
    # ------------------------------------------------------------------

    def _compare_moments(
        self,
        thread: TemporalThread,
        anchors: _PastPresent,
        lifecycle_result: Optional[TemporalLifecycleResult],
        consistency_result: Optional[ConsistencyResult],
    ) -> TemporalComparisonResult:
        past, present = anchors.past, anchors.present
        assert past is not None and present is not None  # narrowed by caller

        evidence_text = (present.description or "").lower()
        shared_meaningful, _shared_generic = _split_meaningful(
            _normalize(past.description) & _normalize(present.description)
        )
        signals: List[str] = [self._overlap_signal(shared_meaningful)]

        relation, confidence, rule_signals = self._decide_relation(
            thread=thread,
            evidence_text=evidence_text,
            shared_meaningful=sorted(shared_meaningful),
            lifecycle_result=lifecycle_result,
            consistency_result=consistency_result,
        )
        signals.extend(rule_signals)

        past_type = past.temporal_type or thread.temporal_type
        past_template = (
            _PAST_SUMMARY_TEMPLATES.get(past_type, _DEFAULT_PAST_TEMPLATE)
            if past_type is not None
            else _DEFAULT_PAST_TEMPLATE
        )
        present_template = _PRESENT_SUMMARY_TEMPLATES[relation]

        return TemporalComparisonResult(
            attempted=True,
            comparable=True,
            relation=relation,
            confidence=confidence,
            thread_id=thread.id,
            past_event_id=past.id,
            present_event_id=present.id,
            past_summary=past_template.format(description=_clip(past.description)),
            present_summary=present_template.format(
                description=_clip(present.description)
            ),
            evidence_event_ids=_dedupe([past.id, present.id]),
            evidence_memory_ids=_dedupe(
                [past.memory_id, present.memory_id, thread.origin_memory_id]
            ),
            signals=signals,
            reason=(
                f"Compared {len(anchors.earlier_events) + 1} recorded moment(s) "
                f"in thread '{thread.subject or thread.id}': relation "
                f"{relation.value}."
            ),
        )

    # ------------------------------------------------------------------
    # Relation policy — first match wins, every rule documented
    # ------------------------------------------------------------------

    def _decide_relation(
        self,
        thread: TemporalThread,
        evidence_text: str,
        shared_meaningful: List[str],
        lifecycle_result: Optional[TemporalLifecycleResult],
        consistency_result: Optional[ConsistencyResult],
    ) -> tuple:
        # 1. Lifecycle-grounded transition this turn (authoritative).
        if lifecycle_result is not None and lifecycle_result.transitioned:
            status = lifecycle_result.current_status
            if status is TemporalThreadStatus.RESOLVED:
                confidence = round(
                    min(MAX_COMPARISON_CONFIDENCE, max(0.65, lifecycle_result.confidence)), 2
                )
                return (
                    TemporalComparisonRelation.RESOLVED,
                    confidence,
                    ["Lifecycle grounded a RESOLVED transition this turn."],
                )
            if status in (TemporalThreadStatus.CHANGED, TemporalThreadStatus.ABANDONED):
                confidence = round(
                    min(MAX_COMPARISON_CONFIDENCE, max(0.60, lifecycle_result.confidence)), 2
                )
                note = (
                    "Lifecycle grounded a CHANGED transition this turn."
                    if status is TemporalThreadStatus.CHANGED
                    else (
                        "Lifecycle grounded an ABANDONED transition this turn; "
                        "withdrawal is reported as a directional change."
                    )
                )
                return TemporalComparisonRelation.CHANGED, confidence, [note]

        # 2. Fear stories: explicit realization or overcoming language.
        if thread.temporal_type is TemporalType.FEAR:
            realized = _contains_any(evidence_text, _FEAR_REALIZED_SIGNALS)
            overcome = _contains_any(evidence_text, _FEAR_OVERCOME_SIGNALS)
            if realized:
                return (
                    TemporalComparisonRelation.CONTRADICTED,
                    0.70,
                    [f"Fear realization evidence: {', '.join(realized)}."],
                )
            if overcome:
                return (
                    TemporalComparisonRelation.RESOLVED,
                    0.70,
                    [f"Fear overcome evidence: {', '.join(overcome)}."],
                )

        # 3. Deliberation / anticipation: outcome evidence from the SAME
        # signal tables the lifecycle policy uses. Observation-only: weaker
        # evidence yields a lower-confidence reading instead of silence.
        if thread.temporal_type in (
            TemporalType.QUESTION,
            TemporalType.DECISION,
            TemporalType.FUTURE_EXPECTATION,
        ):
            outcome_score, outcome_desc = _score_signals(evidence_text, RESOLUTION_SIGNALS)
            if any(hedge in evidence_text for hedge in _HEDGE_PATTERNS):
                outcome_score = round(outcome_score * 0.5, 4)
            if outcome_desc and outcome_score > 0:
                confidence = round(
                    min(0.85, 0.50 + 0.5 * min(1.0, outcome_score)), 2
                )
                return (
                    TemporalComparisonRelation.RESOLVED,
                    confidence,
                    [
                        f"Outcome evidence: {', '.join(outcome_desc)} "
                        f"(score {outcome_score})."
                    ],
                )

        # 4. Consistency evidence relating to THIS thread (relation notion
        # shared with matcher/lifecycle: meaningful token overlap with the
        # subject/description, or explicit shared memory ids).
        conflict_entry, change_entry = self._related_consistency_entries(
            thread, consistency_result
        )
        if conflict_entry is not None:
            label = (conflict_entry.type or "conflict").lower().replace("_", " ")
            return (
                TemporalComparisonRelation.CONTRADICTED,
                0.65,
                [f"Consistency conflict relates to this thread ({label})."],
            )
        if change_entry is not None:
            label = (change_entry.type or "change").lower().replace("_", " ")
            return (
                TemporalComparisonRelation.CHANGED,
                0.60,
                [f"Consistency change relates to this thread ({label})."],
            )

        # 5. Topic continuity between past and present.
        progress = _contains_any(evidence_text, _PROGRESS_MARKERS)
        if progress:
            confidence = round(min(0.80, 0.55 + 0.05 * len(progress)), 2)
            return (
                TemporalComparisonRelation.EVOLVED,
                confidence,
                [f"Development evidence: {', '.join(progress)}."],
            )
        if shared_meaningful:
            confidence = round(
                min(0.75, 0.50 + 0.08 * len(shared_meaningful)), 2
            )
            return (
                TemporalComparisonRelation.CONFIRMED,
                confidence,
                ["Present restates the earlier position on the same topic."],
            )

        return (
            TemporalComparisonRelation.UNRESOLVED,
            0.30,
            ["No conclusive relation evidence beyond an open, ongoing story."],
        )

    @staticmethod
    def _related_consistency_entries(
        thread: TemporalThread,
        consistency_result: Optional[ConsistencyResult],
    ) -> tuple:
        """First related conflict entry and first related change entry."""
        if consistency_result is None:
            return None, None
        subject_tokens = _normalize(thread.subject) | _normalize(thread.description)
        thread_memories = set(thread.related_memory_ids)
        if thread.origin_memory_id:
            thread_memories.add(thread.origin_memory_id)

        conflict: object = None
        change: object = None
        entries = list(consistency_result.changes) + list(
            consistency_result.contradictions
        )
        for entry in entries:
            if (entry.type or "") not in _CHANGE_TYPES:
                continue
            entry_text = " ".join(
                part
                for part in (entry.description, entry.previous_value, entry.current_value)
                if part
            )
            related_by_text = bool(
                _split_meaningful(_normalize(entry_text) & subject_tokens)[0]
            )
            related_by_memory = bool(set(entry.supporting_memory_ids) & thread_memories)
            if not (related_by_text or related_by_memory):
                continue
            if conflict is None and entry.type in _CONFLICT_TYPES:
                conflict = entry
            elif change is None and entry.type not in _CONFLICT_TYPES:
                change = entry
        return conflict, change

    @staticmethod
    def _overlap_signal(shared_meaningful: List[str]) -> str:
        if shared_meaningful:
            return f"Shared topic tokens across moments: {', '.join(shared_meaningful)}."
        return "No meaningful shared topic tokens between the two moments."


__all__ = [
    "TemporalComparisonEngine",
    "MAX_COMPARISON_CONFIDENCE",
]
