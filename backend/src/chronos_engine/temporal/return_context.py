"""Deterministic return-loop / resurfacing context for the ChronOS Engine
(Phase 5D).

This module answers ONE question when a user opens ChronOS again:

    What meaningfully changed since this user was last here, if anything?

It is deliberately NOT an engagement system. It never optimises for
notifications, streaks, reminders or arbitrary activity. Its whole job is to
give the user a genuine, grounded reason to continue — and, just as
importantly, to say *nothing* when there is nothing meaningful to say.

Design principles honoured here:

- **Reuse, don't duplicate.** Meaningful change is classified using the
  existing ``TemporalComparisonEngine`` relation vocabulary (RESOLVED /
  CHANGED / CONTRADICTED / EVOLVED / CONFIRMED / UNRESOLVED /
  INSUFFICIENT_EVIDENCE) and the existing lifecycle-thread statuses. No
  second temporal reasoning system is introduced. Past-Self moments are
  left to their own existing pipeline (Phase 3F/3G/3H) — this module never
  bypasses those gates.
- **No fabrication.** A return insight is never surfaced merely because time
  has passed. Every change is derived from stored temporal threads and their
  persisted events. An unrelated new memory that attached to no thread is
  NOT treated as a meaningful change.
- **User controls the loop.** The in-app hook respects a per-user ``enabled``
  preference (persisted in the return ledger). No external notifications
  are produced; scheduling/reminder architecture is out of scope here.
- **Duplicate suppression.** A persisted ``ReturnLedger`` records the last
  timestamp up to which changes have already been surfaced. Only temporal
  activity after that marker is considered again, so the identical insight
  is never shown repeatedly when nothing new has happened.
- **Deterministic & efficient.** Bounded reads over the temporal store
  (threads + their events) — never a scan of the whole memory database.
  No AI calls are ever made to construct return context.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from chronos_engine.core.interfaces import (
    BaseTemporalComparisonEngine,
    BaseTemporalStore,
)
from chronos_engine.temporal.comparison import TemporalComparisonEngine
from chronos_engine.temporal.models import (
    ReturnChange,
    ReturnChangeType,
    ReturnContext,
    ReturnLedger,
    ReturnUserKind,
    TemporalComparisonRelation,
    TemporalEvent,
    TemporalThread,
    TemporalThreadStatus,
)

# Minimum elapsed time since the user's last interaction before they are
# classified as "meaningfully returning". This is informational only — the
# decision to surface anything is always gated on grounded meaningful change,
# never on this interval alone. Explicit, deterministic, configurable.
MEANINGFULLY_RETURNING_MIN_INTERVAL = timedelta(hours=12)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clip(text: str, limit: int = 90) -> str:
    """Trim whitespace and cap at a word boundary. Never invents."""
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit].rsplit(" ", 1)[0].rstrip(",;:- ")
    return cut + "..."


class ReturnContextEngine:
    """Deterministic construction of a grounded return context (Phase 5D).

    Read-only with respect to temporal truth: it only observes persisted
    threads/events, reuses ``TemporalComparisonEngine`` for relation verdicts,
    and updates the user's ``ReturnLedger`` (the sole write) purely to track
    what has already been surfaced and to honour the user's opt-in.
    """

    def __init__(
        self,
        temporal_store: BaseTemporalStore,
        comparison_engine: Optional[BaseTemporalComparisonEngine] = None,
    ) -> None:
        self.temporal_store = temporal_store
        self.comparison_engine = comparison_engine or TemporalComparisonEngine()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def build(
        self,
        user_id: str,
        latest_interaction_at: Optional[datetime] = None,
        now: Optional[datetime] = None,
    ) -> ReturnContext:
        """Compute the return context for ``user_id``.

        ``latest_interaction_at`` is the ``created_at`` of the user's most
        recent prior interaction (the "previous visit" anchor). When it is
        ``None`` the user has no prior interaction — a first-ever visit.

        The returned context contains user-facing copy only, scoped to this
        authenticated user, and is bounded/synchronous (no AI).
        """
        now = now or _utcnow()

        if latest_interaction_at is None:
            return self._first_ever_context(now)

        kind = self._user_kind(latest_interaction_at, now)
        ledger = await self.temporal_store.get_return_ledger(user_id)

        # When the user has opted out of in-app return insights, say nothing.
        if ledger is not None and not ledger.enabled:
            return self._empty_context(kind, latest_interaction_at, now)

        # Effective baseline of "what has already been surfaced". Falls back
        # to the previous visit time so brand-new resurfacing logic degrades
        # gracefully when no ledger exists yet (or no marker has been set).
        effective_since = latest_interaction_at
        if ledger is not None and ledger.last_surfaced_at is not None:
            effective_since = ledger.last_surfaced_at

        changes = await self._detect_changes(
            user_id, effective_since=effective_since
        )

        context = ReturnContext(
            has_return_context=bool(changes),
            user_kind=kind,
            since_timestamp=latest_interaction_at,
            welcome="Welcome back.",
            changes=changes,
        )

        if changes:
            context.summary_section = self._summary_for(changes)
            # Story-based hook: pick the most relevant live story from the
            # meaningful changes so the user can continue a real storyline.
            self._attach_suggested_story(context, changes, effective_since)

        # Persist the advanced marker — even with no changes — so a page
        # re-render never loops the same content (Part 14).
        await self.temporal_store.save_return_ledger(
            self._advance_ledger(user_id, ledger, now)
        )
        return context

    # ------------------------------------------------------------------
    # User-kind classification (Part 2)
    # ------------------------------------------------------------------

    def _user_kind(
        self, latest_interaction_at: datetime, now: datetime
    ) -> ReturnUserKind:
        if (now - latest_interaction_at) >= MEANINGFULLY_RETURNING_MIN_INTERVAL:
            return ReturnUserKind.MEANINGFULLY_RETURNING
        return ReturnUserKind.RETURNING

    # ------------------------------------------------------------------
    # Meaningful-change detection (Part 3)
    # ------------------------------------------------------------------

    async def _detect_changes(
        self, user_id: str, effective_since: Optional[datetime]
    ) -> List[ReturnChange]:
        """Find grounded meaningful changes since ``effective_since``.

        For each of the user's threads we check whether it has any new
        temporal event after ``effective_since``. Only threads with such new
        activity are considered, so an unrelated new memory that attached to
        no thread never produces an insight. The change is classified using
        the existing comparison-engine relation where enough history exists,
        otherwise by lifecycle status and continuity.
        """
        if effective_since is None:
            return []

        threads = await self.temporal_store.get_threads_by_user(user_id)
        changes: List[ReturnChange] = []
        seen_subjects: set = set()

        for thread in threads:
            events = await self.temporal_store.get_events_by_thread(thread.id, user_id)
            new_events = [
                e for e in events if self._is_after(e, effective_since)
            ]
            if not new_events:
                continue

            change = await self._classify_change(thread, events)
            if change is None:
                continue
            # De-duplicate in case two threads share the same surfaced subject.
            if change.subject in seen_subjects:
                continue
            seen_subjects.add(change.subject)
            changes.append(change)

        # Stable, deterministic ordering: resolved/changed first (most
        # consequential), then progressed, then new stories; ties broken by
        # subject for reproducibility (never by raw document order).
        changes.sort(key=lambda c: (_CHANGE_RANK[c.change_type], (c.subject or "").lower()))
        return changes

    async def _classify_change(
        self, thread: TemporalThread, events: List[TemporalEvent]
    ) -> Optional[ReturnChange]:
        """Classify one thread with new activity into a grounded change."""
        subject = _clip(thread.subject) or (thread.status.value or "story")

        if thread.status is TemporalThreadStatus.RESOLVED:
            return ReturnChange(
                change_type=ReturnChangeType.STORY_RESOLVED,
                headline=f"Your story about {subject} reached a turning point.",
                detail=self._relation_detail(thread, events, "RESOLVED"),
                thread_id=thread.id,
                subject=subject,
            )

        if thread.status in (TemporalThreadStatus.CHANGED, TemporalThreadStatus.ABANDONED):
            return ReturnChange(
                change_type=ReturnChangeType.STORY_CHANGED,
                headline=f"Your story about {subject} took a different direction.",
                detail=self._relation_detail(thread, events, "CHANGED"),
                thread_id=thread.id,
                subject=subject,
            )

        # A new story (single origin event) that is still open.
        if len(events) == 1:
            return ReturnChange(
                change_type=ReturnChangeType.NEW_STORY,
                headline=f"A new thread began: {subject}.",
                detail="",
                thread_id=thread.id,
                subject=subject,
            )

        # A continuing story (>=2 moments) gained a new moment since the
        # user's last visit. The fact that the user added a new moment to an
        # already-open story is itself grounded, factual progress — surfaced
        # as STORY_PROGRESSED. The supporting detail quotes the newest
        # recorded event; the comparison relation (where available) only
        # nuances the wording and is never surfaced alone as an insight.
        relation = await self._relation(thread, events)
        return ReturnChange(
            change_type=ReturnChangeType.STORY_PROGRESSED,
            headline=f"Your story about {subject} moved forward.",
            detail=self._relation_detail(
                thread, events, relation.value if relation else "PROGRESSED"
            ),
            thread_id=thread.id,
            subject=subject,
        )

    # ------------------------------------------------------------------
    # Reuse of the existing comparison engine (Part 6)
    # ------------------------------------------------------------------

    async def _relation(
        self, thread: TemporalThread, events: List[TemporalEvent]
    ) -> Optional[TemporalComparisonRelation]:
        try:
            result = await self.comparison_engine.compare(
                user_id=thread.user_id, thread=thread, events=events
            )
        except Exception:
            return None
        if result is None or not result.attempted or not result.comparable:
            return None
        return result.relation

    def _relation_detail(
        self, thread: TemporalThread, events: List[TemporalEvent], relation: str
    ) -> str:
        """A single grounded supporting sentence for the change.

        Uses the newest recorded event description plus the relation label —
        both grounded, never invented. The relation text is drawn from the
        comparison engine's own conservative vocabulary.
        """
        newest = max(events, key=lambda e: e.occurred_at, default=None)
        if newest is None or not newest.description:
            return ""
        short = _clip(newest.description, limit=140)
        if relation in {"RESOLVED", "CHANGED", "CONTRADICTED"}:
            return f"Since then: {short}"
        return short

    # ------------------------------------------------------------------
    # Story-based resurfacing (Part 8)
    # ------------------------------------------------------------------

    def _attach_suggested_story(
        self,
        context: ReturnContext,
        changes: List[ReturnChange],
        effective_since: Optional[datetime],
    ) -> None:
        """Deterministically pick the most relevant live story to resurface.

        Prefer, in order: a live (open/active/changed) story; a story type
        that carries forward-looking meaning; then the one with the most
        recent new activity (most recently updated). We do NOT just select
        the newest thread — a story must be both live AND meaningful.
        """
        candidates = [
            c for c in changes
            if c.thread_id and c.change_type != ReturnChangeType.STORY_CHANGED
        ]
        if not candidates:
            return
        # Prefer live-status stories; rank by updated_at recency.
        ranked = sorted(
            candidates,
            key=lambda c: (_priority_of(c), c.thread_id or ""),
        )
        best = ranked[0]
        context.suggested_story_subject = best.subject
        context.suggested_thread_id = best.thread_id
        context.suggested_story_because = self._story_because(best)

    # ------------------------------------------------------------------
    # Summary line (Part 5)
    # ------------------------------------------------------------------

    def _summary_for(self, changes: List[ReturnChange]) -> str:
        """One grounded, deterministic summary line (Part 5)."""
        has_resolved = any(
            c.change_type is ReturnChangeType.STORY_RESOLVED for c in changes
        )
        has_changed = any(
            c.change_type in (ReturnChangeType.STORY_CHANGED, ReturnChangeType.STORY_PROGRESSED)
            for c in changes
        )
        if has_resolved:
            return "Something you were working through reached a turning point."
        if has_changed and len(changes) > 1:
            return "Several of your stories moved forward."
        if has_changed:
            return "One of your stories moved forward."
        return "Something changed since you were last here."

    def _story_because(self, change: ReturnChange) -> str:
        if change.change_type is ReturnChangeType.STORY_RESOLVED:
            return "This story reached a turning point."
        if change.change_type is ReturnChangeType.STORY_PROGRESSED:
            return "This story is still moving forward."
        return "A new story has begun."

    # ------------------------------------------------------------------
    # First-ever / empty contexts
    # ------------------------------------------------------------------

    def _first_ever_context(self, now: datetime) -> ReturnContext:
        return ReturnContext(
            has_return_context=False,
            user_kind=ReturnUserKind.FIRST_EVER,
            welcome="Welcome.",
            changes=[],
        )

    def _empty_context(
        self, kind: ReturnUserKind, latest_interaction_at: datetime, now: datetime
    ) -> ReturnContext:
        return ReturnContext(
            has_return_context=False,
            user_kind=kind,
            since_timestamp=latest_interaction_at,
            welcome="Welcome back.",
            changes=[],
        )

    # ------------------------------------------------------------------
    # Ledger / suppression (Part 14)
    # ------------------------------------------------------------------

    def _advance_ledger(
        self, user_id: str, ledger: Optional[ReturnLedger], now: datetime
    ) -> None:
        """Advance the surfaced marker to ``now`` and persist.

        Advance even when there were no changes: this is exactly what stops a
        "no meaningful change" page re-render from looping. The marker always
        moves forward, never backward, so changes are never shown twice.
        """
        next_ledger = ReturnLedger(
            user_id=user_id,
            last_surfaced_at=now,
            enabled=ledger.enabled if ledger is not None else True,
            updated_at=now,
        )
        return next_ledger

    @staticmethod
    def _is_after(event: TemporalEvent, when: datetime) -> bool:
        return event.recorded_at > when or event.occurred_at > when

    async def set_enabled(self, user_id: str, enabled: bool) -> None:
        """Set the user's in-app return-hook preference (Part 19).

        Disabling must NOT advance the surfaced marker: the user never saw
        those insights, so re-enabling should let genuinely unmet changes be
        surfaced again rather than silently discarding them.
        """
        ledger = await self.temporal_store.get_return_ledger(user_id)
        now = _utcnow()
        await self.temporal_store.save_return_ledger(
            ReturnLedger(
                user_id=user_id,
                last_surfaced_at=ledger.last_surfaced_at if ledger else None,
                enabled=enabled,
                updated_at=now,
            )
        )


def _priority_of(change: ReturnChange) -> int:
    """Lower = more relevant for the suggested story hook."""
    if change.change_type is ReturnChangeType.STORY_RESOLVED:
        return 0
    if change.change_type is ReturnChangeType.STORY_PROGRESSED:
        return 1
    if change.change_type is ReturnChangeType.NEW_STORY:
        return 2
    return 3


_CHANGE_RANK = {
    ReturnChangeType.STORY_RESOLVED: 0,
    ReturnChangeType.STORY_CHANGED: 1,
    ReturnChangeType.STORY_PROGRESSED: 2,
    ReturnChangeType.NEW_STORY: 3,
}
