"""Deterministic Past-Self Question planning for the ChronOS Engine
(Phase 3F).

ChronOS is not just tracking goals: a user records fears, decisions,
expectations and beliefs — and months later ChronOS should reconnect the
present self with the past self. This module decides, deterministically and
conservatively, whether such a reconnection is APPROPRIATE for the temporal
thread touched by this interaction:

1. whether a past-self interaction is appropriate,
2. what KIND of interaction is appropriate (``PastSelfQuestionType``),
3. WHAT it should be about (grounded focus + canonical template),
4. WHICH already-stored evidence supports it.

Strictly read-only pure computation over handed-in objects (thread,
comparison result, lifecycle result, events). It never mutates threads or
events, never persists anything, never schedules, never creates snapshots
or notifications and never touches lifecycle status or comparison results.

Conservative by design — a comparison existing does NOT automatically mean
a question should be asked:

- single-moment histories are never compared into a question,
- comparisons below the documented confidence floor are skipped,
- ``INSUFFICIENT_EVIDENCE`` comparisons never fabricate a question,
- ``UNRESOLVED`` stories require real continuity (several recorded moments
  or shared topic continuity) before a cautious ``REVISIT`` is allowed,
- ambiguous thread relationships produce nothing.

The WHAT/HOW separation is explicit: ``PastSelfQuestionIntent.focus``
describes the grounded topic; ``canonical_template`` is a skeleton with a
literal ``{subject}`` placeholder that a FUTURE rendering/AI layer fills
from the evidence-grounded thread subject. No conversational sentence, no
simulated personality, no invented emotions or memories — wording and
personalization are deferred by design.

No AI, no Ollama, no embeddings, no vector search: works fully with AI
disabled. The planner is synchronous because it performs no I/O (mirroring
the synchronous router/planner conventions).
"""

from typing import Dict, List, Optional

from chronos_engine.core.interfaces import BasePastSelfQuestionPlanner
from chronos_engine.temporal.matcher import _normalize, _split_meaningful
from chronos_engine.temporal.models import (
    PastSelfPerspective,
    PastSelfQuestionIntent,
    PastSelfQuestionResult,
    PastSelfQuestionType,
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalLifecycleResult,
    TemporalThread,
    TemporalType,
)

# A comparison must clear this floor before any question is planned.
# Documented, tested implementation value — not a calibrated probability.
_MIN_COMPARISON_CONFIDENCE = 0.55

# Planner confidence never reaches 1.0.
_MAX_QUESTION_CONFIDENCE = 0.95

_MEMORY_GROUNDING_BONUS = 0.05        # both anchors anchored to stored memories
_CONTINUITY_BONUS_PER_EXTRA_EVENT = 0.05
_MAX_CONTINUITY_EXTRAS = 2

_REVISIT_CAP = 0.70                   # revisits stay deliberately modest

# Relation -> default interaction kind (first mapping of the policy).
_RELATION_TO_QUESTION_TYPE: Dict[TemporalComparisonRelation, PastSelfQuestionType] = {
    TemporalComparisonRelation.RESOLVED: PastSelfQuestionType.OUTCOME_REVEAL,
    TemporalComparisonRelation.CHANGED: PastSelfQuestionType.REFLECTION,
    TemporalComparisonRelation.CONTRADICTED: PastSelfQuestionType.REFLECTION,
    TemporalComparisonRelation.EVOLVED: PastSelfQuestionType.CHECK_IN,
    TemporalComparisonRelation.CONFIRMED: PastSelfQuestionType.REASSURANCE,
    TemporalComparisonRelation.UNRESOLVED: PastSelfQuestionType.REVISIT,
}

# Type-specific refinement of RESOLVED stories: an overcome fear or an
# answered old question invites looking back rather than announcing an
# outcome. Only deviations from the relation default are listed.
_RESOLVED_TYPE_OVERRIDES: Dict[object, PastSelfQuestionType] = {
    TemporalType.FEAR: PastSelfQuestionType.REFLECTION,
    TemporalType.QUESTION: PastSelfQuestionType.REFLECTION,
}

# WHAT to ask, keyed by the thread's temporal type (guidance mappings, not
# fabricated semantics). Fixed framing only; content comes from evidence.
_TYPE_FOCUS: Dict[object, str] = {
    TemporalType.DECISION: (
        "How the user feels now about the decision they were once "
        "uncertain about"
    ),
    TemporalType.FEAR: (
        "What the user would want to tell their past self about the fear "
        "they once carried"
    ),
    TemporalType.GOAL: "How the journey compares to what the user imagined",
    TemporalType.FUTURE_EXPECTATION: (
        "How reality compared with what the user expected"
    ),
    TemporalType.PREDICTION: "How reality compared with what the user predicted",
    TemporalType.BELIEF: "What changed the user's perspective",
    TemporalType.LIFE_EVENT: "How the user sees the change now",
    TemporalType.MILESTONE: "How the user sees the change now",
    TemporalType.QUESTION: (
        "Whether the question the user once had has now been answered"
    ),
    TemporalType.PROMISE: "Whether the user followed through on their commitment",
}
_DEFAULT_FOCUS = "How the story that began earlier looks to the user now"


class PastSelfQuestionPlanner(BasePastSelfQuestionPlanner):
    """Default deterministic implementation of BasePastSelfQuestionPlanner."""

    def plan(
        self,
        user_id: str,
        thread: Optional[TemporalThread],
        comparison: Optional[TemporalComparisonResult],
        lifecycle_result: Optional[TemporalLifecycleResult] = None,
        events: Optional[List[TemporalEvent]] = None,
    ) -> PastSelfQuestionResult:
        if thread is None:
            return PastSelfQuestionResult(
                attempted=False,
                should_ask=False,
                reason="No temporal thread available; planning skipped.",
            )

        if (
            comparison is None
            or not comparison.attempted
            or comparison.thread_id != thread.id
        ):
            return self._skip(
                thread,
                comparison,
                "The temporal thread has no applicable comparison result.",
            )

        if lifecycle_result is not None and lifecycle_result.ambiguous:
            return self._skip(
                thread,
                comparison,
                "Temporal thread relationship was ambiguous; no question planned.",
            )

        if not comparison.comparable:
            return self._skip(
                thread,
                comparison,
                "The thread holds fewer than two distinct grounded moments; "
                "no past-self question can be fabricated.",
            )

        relation = comparison.relation
        if relation is None or relation is TemporalComparisonRelation.INSUFFICIENT_EVIDENCE:
            return self._skip(
                thread,
                comparison,
                "The comparison found insufficient evidence for a question.",
            )

        anchors_ok, anchor_note = self._anchors_match_history(comparison, events)
        if not anchors_ok:
            return self._skip(thread, comparison, anchor_note)

        past_event, present_event = self._anchor_events(comparison, events or [])

        if relation is TemporalComparisonRelation.UNRESOLVED:
            return self._plan_revisit(
                thread=thread,
                comparison=comparison,
                events=events or [],
                past_event=past_event,
                present_event=present_event,
            )

        if comparison.confidence < _MIN_COMPARISON_CONFIDENCE:
            return self._skip(
                thread,
                comparison,
                "Comparison confidence below the conservative planning "
                "threshold; asking would be speculative.",
            )

        question_type = self._question_type_for(relation, thread)
        focus = self._focus_for(thread)
        signals: List[str] = [
            f"Relation {relation.value} supports a "
            f"{question_type.value.lower()} interaction.",
            f"Grounded focus from thread subject: '{thread.subject or thread.id}'.",
        ]

        confidence = self._confidence_for(comparison, len(events or []))
        return PastSelfQuestionResult(
            attempted=True,
            should_ask=True,
            question_type=question_type,
            reason=(
                f"Comparison relation {relation.value} with sufficient "
                f"evidence justifies a {question_type.value.lower()} "
                f"question about this thread."
            ),
            confidence=confidence,
            thread_id=thread.id,
            comparison_relation=relation,
            past_event_id=comparison.past_event_id,
            present_event_id=comparison.present_event_id,
            supporting_memory_ids=list(comparison.evidence_memory_ids),
            supporting_event_ids=list(comparison.evidence_event_ids),
            intent=PastSelfQuestionIntent(
                focus=focus,
                canonical_template=self._template_for(question_type),
                perspective=PastSelfPerspective.PAST_TO_PRESENT,
            ),
            signals=signals,
        )

    # ------------------------------------------------------------------
    # UNRESOLVED stories: cautious REVISIT only with real continuity
    # ------------------------------------------------------------------

    def _plan_revisit(
        self,
        thread: TemporalThread,
        comparison: TemporalComparisonResult,
        events: List[TemporalEvent],
        past_event: Optional[TemporalEvent],
        present_event: Optional[TemporalEvent],
    ) -> PastSelfQuestionResult:
        shared_meaningful: set = set()
        if past_event is not None and present_event is not None:
            shared_meaningful = _split_meaningful(
                _normalize(past_event.description)
                & _normalize(present_event.description)
            )[0]

        rich_history = len(events) >= 3
        topical_continuity = bool(shared_meaningful) and len(events) >= 2
        if not (rich_history or topical_continuity):
            return self._skip(
                thread,
                comparison,
                "The story remains open without enough continuity to justify "
                "a revisit.",
            )

        confidence = round(
            min(_REVISIT_CAP, 0.50 + 0.05 * min(4, max(0, len(events) - 1))), 2
        )
        basis = (
            f"{len(events)} recorded moments keep this story open"
            if rich_history
            else "the two moments share topical continuity while staying open"
        )
        return PastSelfQuestionResult(
            attempted=True,
            should_ask=True,
            question_type=PastSelfQuestionType.REVISIT,
            reason=(
                f"UNRESOLVED story with meaningful continuity ({basis}); "
                f"a cautious revisit is appropriate."
            ),
            confidence=confidence,
            thread_id=thread.id,
            comparison_relation=comparison.relation,
            past_event_id=comparison.past_event_id,
            present_event_id=comparison.present_event_id,
            supporting_memory_ids=list(comparison.evidence_memory_ids),
            supporting_event_ids=list(comparison.evidence_event_ids),
            intent=PastSelfQuestionIntent(
                focus=self._focus_for(thread),
                canonical_template=self._template_for(
                    PastSelfQuestionType.REVISIT
                ),
                perspective=PastSelfPerspective.PAST_TO_PRESENT,
            ),
            signals=[
                "Open story kept alive across several moments.",
                f"Grounded focus from thread subject: '{thread.subject or thread.id}'.",
            ],
        )

    # ------------------------------------------------------------------
    # Mapping helpers (documented, deterministic)
    # ------------------------------------------------------------------

    @staticmethod
    def _question_type_for(
        relation: TemporalComparisonRelation, thread: TemporalThread
    ) -> PastSelfQuestionType:
        question_type = _RELATION_TO_QUESTION_TYPE.get(
            relation, PastSelfQuestionType.REFLECTION
        )
        if (
            question_type is PastSelfQuestionType.OUTCOME_REVEAL
            and thread.temporal_type in _RESOLVED_TYPE_OVERRIDES
        ):
            return _RESOLVED_TYPE_OVERRIDES[thread.temporal_type]
        return question_type

    @staticmethod
    def _focus_for(thread: TemporalThread) -> str:
        if thread.temporal_type is not None and thread.temporal_type in _TYPE_FOCUS:
            return _TYPE_FOCUS[thread.temporal_type]
        return _DEFAULT_FOCUS

    @staticmethod
    def _template_for(question_type: PastSelfQuestionType) -> str:
        templates: Dict[PastSelfQuestionType, str] = {
            PastSelfQuestionType.CHECK_IN: (
                "Looking back at {subject}, how are things going for you now?"
            ),
            PastSelfQuestionType.OUTCOME_REVEAL: (
                "Back then, {subject} was still an open question. "
                "How do you feel about it now?"
            ),
            PastSelfQuestionType.REFLECTION: (
                "Back then, {subject}. Looking back now, what would you "
                "tell your past self?"
            ),
            PastSelfQuestionType.REVISIT: (
                "{subject} was left open back then. Where do things stand "
                "for you now?"
            ),
            PastSelfQuestionType.REASSURANCE: (
                "Your stance on {subject} held over time. Does it still "
                "feel right?"
            ),
        }
        return templates.get(question_type, "")

    @staticmethod
    def _confidence_for(
        comparison: TemporalComparisonResult, event_count: int
    ) -> float:
        """Evidence-weighted blend, capped below 1.0 (documented constants)."""
        confidence = comparison.confidence
        signals: List[str] = []
        if (
            comparison.past_summary
            and comparison.present_summary
            and comparison.evidence_memory_ids
        ):
            confidence += _MEMORY_GROUNDING_BONUS
            signals.append("Memory-grounded comparison evidence.")
        extras = min(_MAX_CONTINUITY_EXTRAS, max(0, event_count - 2))
        if extras:
            confidence += _CONTINUITY_BONUS_PER_EXTRA_EVENT * extras
            signals.append(f"Continuity across {event_count} recorded moments.")
        return round(min(_MAX_QUESTION_CONFIDENCE, confidence), 2)

    @staticmethod
    def _anchor_events(
        comparison: TemporalComparisonResult, events: List[TemporalEvent]
    ) -> tuple:
        by_id = {event.id: event for event in events}
        past = by_id.get(comparison.past_event_id) if comparison.past_event_id else None
        present = (
            by_id.get(comparison.present_event_id)
            if comparison.present_event_id
            else None
        )
        return past, present

    def _anchors_match_history(
        self, comparison: TemporalComparisonResult, events: Optional[List[TemporalEvent]]
    ) -> tuple:
        """Defensive integrity check: comparison anchors exist in history."""
        if events is None:
            return True, ""
        known_ids = {event.id for event in events}
        for anchor in (comparison.past_event_id, comparison.present_event_id):
            if anchor and anchor not in known_ids:
                return (
                    False,
                    "Comparison anchors do not match the loaded history; "
                    "planning conservatively skipped.",
                )
        return True, ""

    @staticmethod
    def _skip(
        thread: TemporalThread,
        comparison: Optional[TemporalComparisonResult],
        reason: str,
    ) -> PastSelfQuestionResult:
        return PastSelfQuestionResult(
            attempted=True,
            should_ask=False,
            thread_id=thread.id,
            comparison_relation=(
                comparison.relation if comparison is not None else None
            ),
            reason=reason,
        )


__all__ = ["PastSelfQuestionPlanner"]
