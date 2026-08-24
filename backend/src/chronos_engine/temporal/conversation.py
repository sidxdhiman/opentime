"""Deterministic Past-Self Conversation composition for the ChronOS Engine
(Phase 3H).

Phases 3A–3G detect temporal events, connect them into threads, compare the
past with the present, plan what a past-self question should be (Phase 3F)
and decide whether NOW is the right moment to surface it (Phase 3G). This
module turns a valid ``SURFACE_NOW`` permission into an actual user-facing
conversational moment — subtle and grounded, never theatrical:

    SOMETHING FROM YOUR PAST

    Earlier, you were weighing this.
    Back then you were weighing: "I don't know if I should quit my job."
    Now it has played out: "I finally left my job."
    How do you feel about "Quit my job" now?

Strict rules enforced here:

- SURFACE_NOW is PERMISSION to surface, never permission to invent. A hard
  gate requires Phase 3F ``should_ask=True``, a valid planned question, a
  matching grounded thread, a meaningful comparison and no ambiguity.
  Phase 3F/3G refusals are echoed honestly, never overridden.
- Every rendered line quotes or paraphrases ONLY handed-in evidence:
  thread subject/description, anchored event descriptions and comparison
  summaries. No emotions, motivations, outcomes or elapsed durations are
  ever generated. Internal IDs stay out of user-facing text.
- Wording comes from fixed deterministic templates keyed by the existing
  ``PastSelfQuestionType``; ``PastSelfPerspective.PAST_TO_PRESENT`` is the
  only perspective produced by Phase 3F and the only one framed here.
- Strictly read-only pure computation over handed-in objects: no AI, no
  embeddings, no storage access, no mutation, no persistence, no
  scheduling, no notifications. Synchronous by convention (no I/O).
"""


from chronos_engine.core.interfaces import BasePastSelfConversationComposer
from chronos_engine.temporal.models import (
    PastSelfConversationMoment,
    PastSelfQuestionResult,
    PastSelfQuestionType,
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalLifecycleResult,
    TemporalRelevanceDecision,
    TemporalRelevanceResult,
    TemporalThread,
)

# Confidence can never exceed the weakest permission in the chain, and
# never reaches 1.0.
_MAX_MOMENT_CONFIDENCE = 0.95

# Quoted descriptions are clipped at a word boundary (mirrors the
# comparison engine's conservative summary clipping).
_CLIP_LIMIT = 140

# User-facing section heading. Matches the deterministic response's
# ALL-CAPS section conventions ("USER SIGNAL", "CHRONOS STATE", ...).
SECTION_HEADING = "SOMETHING FROM YOUR PAST"

# Short connective opening per question type. Framing only — every claim
# is entailed by the relation/question-type semantics already decided by
# Phases 3E–3G, never by new assumptions about the user.
_OPENINGS: dict[PastSelfQuestionType | None, str] = {
    PastSelfQuestionType.OUTCOME_REVEAL: "Earlier, you were weighing this.",
    PastSelfQuestionType.REFLECTION: "Earlier, this was on your mind.",
    PastSelfQuestionType.CHECK_IN: (
        "Some time ago, this was something you were working toward."
    ),
    PastSelfQuestionType.REASSURANCE: (
        "You were already moving in this direction."
    ),
    PastSelfQuestionType.REVISIT: "This remains open for you.",
    # SURPRISE is reserved in Phase 3F (no deterministic producer exists);
    # if one ever arrives it still renders conservatively.
    PastSelfQuestionType.SURPRISE: "An earlier moment of yours connects to now.",
    None: "An earlier moment of yours connects to now.",
}

# The past-self question itself, keyed by question type. The subject is
# always quoted so the user can see exactly which stored story is meant.
_QUESTIONS: dict[PastSelfQuestionType | None, str] = {
    PastSelfQuestionType.OUTCOME_REVEAL: 'How do you feel about "{subject}" now?',
    PastSelfQuestionType.REFLECTION: 'What do you think about "{subject}" now?',
    PastSelfQuestionType.CHECK_IN: 'How is "{subject}" going for you now?',
    PastSelfQuestionType.REASSURANCE: (
        'Does "{subject}" still feel right to you now?'
    ),
    PastSelfQuestionType.REVISIT: (
        'Where do things stand with "{subject}" for you now?'
    ),
    PastSelfQuestionType.SURPRISE: (
        'Looking back, how does "{subject}" look to you now?'
    ),
    None: 'Looking back, how does "{subject}" look to you now?',
}


def _clip(text: str, limit: int = _CLIP_LIMIT) -> str:
    """Trim whitespace and cap length at a word boundary. Never invents."""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"


def _dedupe(items: list[str | None]) -> list[str]:
    seen: set = set()
    ordered: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


class PastSelfConversationComposer(BasePastSelfConversationComposer):
    """Default deterministic implementation of
    BasePastSelfConversationComposer."""

    def compose(
        self,
        user_id: str,
        past_self_question: PastSelfQuestionResult,
        relevance_result: TemporalRelevanceResult | None,
        thread: TemporalThread | None = None,
        comparison: TemporalComparisonResult | None = None,
        lifecycle_result: TemporalLifecycleResult | None = None,
        events: list[TemporalEvent] | None = None,
    ) -> PastSelfConversationMoment:
        gate = self._hard_gate(
            past_self_question, relevance_result, thread, comparison, lifecycle_result
        )
        if gate is not None:
            return gate

        assert past_self_question is not None and relevance_result is not None
        assert thread is not None and comparison is not None
        question_type = past_self_question.question_type
        assert question_type is not None and past_self_question.intent is not None

        events = events or []
        past_event, present_event = self._anchor_events(past_self_question, events)

        subject = self._grounded_subject(thread, past_event)
        if subject is None:
            return self._not_surfaced_from(
                past_self_question,
                "No grounded subject was available for this story; a "
                "conversation moment cannot be composed without inventing "
                "content.",
            )

        context_line = self._context_line(comparison, past_event, thread, subject)
        bridge_line = (comparison.present_summary or "").strip()

        confidence = round(
            min(
                _MAX_MOMENT_CONFIDENCE,
                min(past_self_question.confidence, relevance_result.confidence),
            ),
            2,
        )

        return PastSelfConversationMoment(
            attempted=True,
            should_surface=True,
            thread_id=thread.id,
            perspective=past_self_question.intent.perspective,
            question_type=question_type,
            relation=comparison.relation,
            opening=_OPENINGS.get(question_type, _OPENINGS[None]),
            context=context_line,
            bridge=bridge_line,
            question=(
                _QUESTIONS.get(question_type, _QUESTIONS[None]).format(
                    subject=subject
                )
            ),
            confidence=confidence,
            evidence_memory_ids=_dedupe(
                list(past_self_question.supporting_memory_ids)
                + list(comparison.evidence_memory_ids)
            ),
            evidence_event_ids=_dedupe(
                list(past_self_question.supporting_event_ids)
                + list(comparison.evidence_event_ids)
            ),
            reason=(
                f"Phase 3F planned a {question_type.value.lower()} question, "
                f"Phase 3G decided {relevance_result.decision.value}, and all "
                "grounding gates passed."
            ),
        )

    # ------------------------------------------------------------------
    # Hard surface gate — Phases 3F/3G are never overridden
    # ------------------------------------------------------------------

    @staticmethod
    def _hard_gate(
        past_self_question: PastSelfQuestionResult | None,
        relevance_result: TemporalRelevanceResult | None,
        thread: TemporalThread | None,
        comparison: TemporalComparisonResult | None,
        lifecycle_result: TemporalLifecycleResult | None,
    ) -> PastSelfConversationMoment | None:
        """Return an honest no-surface result when ANY condition fails."""
        decision_label = (
            relevance_result.decision.value
            if relevance_result is not None
            else "unavailable"
        )
        if relevance_result is None or not relevance_result.attempted:
            return PastSelfConversationComposer._not_surfaced_from(
                past_self_question,
                "No relevance decision was available; surfacing skipped.",
            )
        if relevance_result.decision is not TemporalRelevanceDecision.SURFACE_NOW:
            return PastSelfConversationComposer._not_surfaced_from(
                past_self_question,
                f"Relevance decision was {decision_label}, not SURFACE_NOW.",
            )
        if (
            past_self_question is None
            or not past_self_question.attempted
            or not past_self_question.should_ask
        ):
            return PastSelfConversationComposer._not_surfaced_from(
                past_self_question,
                "Past-self planning did not produce an askable question.",
            )
        if (
            past_self_question.question_type is None
            or past_self_question.intent is None
        ):
            return PastSelfConversationComposer._not_surfaced_from(
                past_self_question,
                "The planned past-self question lacks a usable type or "
                "intent payload.",
            )
        if thread is None or past_self_question.thread_id != thread.id:
            return PastSelfConversationComposer._not_surfaced_from(
                past_self_question,
                "The planned question does not belong to a present, "
                "grounded thread.",
            )
        if (
            comparison is None
            or not comparison.comparable
            or comparison.relation is TemporalComparisonRelation.INSUFFICIENT_EVIDENCE
        ):
            return PastSelfConversationComposer._not_surfaced_from(
                past_self_question,
                "The underlying comparison is not meaningful enough to "
                "ground a conversation moment.",
            )
        if lifecycle_result is not None and lifecycle_result.ambiguous:
            return PastSelfConversationComposer._not_surfaced_from(
                past_self_question,
                "The thread relationship was ambiguous; nothing is surfaced.",
            )
        return None

    @staticmethod
    def _not_surfaced_from(
        question: PastSelfQuestionResult | None,
        reason: str,
    ) -> PastSelfConversationMoment:
        return PastSelfConversationMoment(
            attempted=True,
            should_surface=False,
            thread_id=question.thread_id if question is not None else None,
            question_type=(
                question.question_type if question is not None else None
            ),
            reason=reason,
        )

    # ------------------------------------------------------------------
    # Grounded content assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _anchor_events(
        question: PastSelfQuestionResult, events: list[TemporalEvent]
    ) -> tuple:
        by_id = {event.id: event for event in events}
        past = by_id.get(question.past_event_id) if question.past_event_id else None
        present = (
            by_id.get(question.present_event_id)
            if question.present_event_id
            else None
        )
        return past, present

    @staticmethod
    def _grounded_subject(
        thread: TemporalThread, past_event: TemporalEvent | None
    ) -> str | None:
        """A quotable subject from evidence, or ``None`` when none exists."""
        subject = (thread.subject or "").strip()
        if subject:
            return _clip(subject)
        description = (thread.description or "").strip()
        if description:
            return _clip(description)
        if past_event is not None and (past_event.description or "").strip():
            return _clip(past_event.description)
        return None

    @staticmethod
    def _context_line(
        comparison: TemporalComparisonResult,
        past_event: TemporalEvent | None,
        thread: TemporalThread,
        subject: str,
    ) -> str:
        """Grounded reminder of the earlier moment (never invented)."""
        summary = (comparison.past_summary or "").strip()
        if summary:
            return summary
        description = ""
        if past_event is not None:
            description = (past_event.description or "").strip()
        if not description:
            description = (thread.description or "").strip()
        if not description:
            description = subject
        return f'Earlier in this story: "{_clip(description)}"'


def render_past_self_section(moment: PastSelfConversationMoment) -> str:
    """Render the surfaced moment as an additive response section.

    Deterministic plain-text rendering consistent with the deterministic
    response's section style. Empty lines are omitted; internal IDs never
    appear here by construction.
    """
    lines: list[str] = [SECTION_HEADING, ""]
    for text in (moment.opening, moment.context, moment.bridge, moment.question):
        cleaned = (text or "").strip()
        if cleaned:
            lines.append(cleaned)
            lines.append("")
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


__all__ = [
    "PastSelfConversationComposer",
    "render_past_self_section",
    "SECTION_HEADING",
]
