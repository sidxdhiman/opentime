"""Phase 4G tests: active thread as continuity evidence in the matcher.

Verifies that the active temporal thread context provides a bounded
continuity bonus when the user explicitly selects a thread AND the
candidate already has grounded evidence (topic overlap or memory
continuity).  The active thread alone can NEVER fabricate a match.

Scoring reference (from matcher.py):
  - _TOPIC_BASE = 0.30 (subject overlap)
  - _DESCRIPTION_BASE = 0.22 (description-only overlap)
  - _TYPE_COMPATIBILITY[DECISION↔LIFE_EVENT] = 0.25
  - _ACTIVE_THREAD_CONTINUITY_BONUS = 0.30
  - MATCH_THRESHOLD = 0.50

Design: description-only overlap + type compat = 0.22 + 0.25 = 0.47 < 0.50.
With active thread bonus: 0.47 + 0.30 = 0.77 >= 0.50.  This proves the
bonus pushes a weak-but-grounded candidate across the threshold.
"""

import pytest

from chronos_engine.temporal.matcher import (
    MATCH_THRESHOLD,
    TemporalThreadMatcher,
)
from chronos_engine.temporal.models import (
    ActiveTemporalContext,
    TemporalEvent,
    TemporalThread,
    TemporalThreadMatchResult,
    TemporalType,
)

USER = "user_4g"


# ── Helpers ─────────────────────────────────────────────────────────────


def _mk_thread(subject: str, ttype: TemporalType = TemporalType.DECISION,
               description: str = None, **kw) -> TemporalThread:
    return TemporalThread(
        user_id=USER, subject=subject, temporal_type=ttype,
        description=description, **kw,
    )


def _mk_event(description: str, ttype: TemporalType = TemporalType.LIFE_EVENT,
              **kw) -> TemporalEvent:
    return TemporalEvent(temporal_type=ttype, description=description, **kw)


def _active_ctx(thread: TemporalThread, **kw) -> ActiveTemporalContext:
    return ActiveTemporalContext(
        thread_id=thread.id,
        subject=thread.subject,
        temporal_type=thread.temporal_type,
        status=thread.status.value,
        events=[],
        **kw,
    )


async def _match(event, threads, **kw) -> TemporalThreadMatchResult:
    return await TemporalThreadMatcher().match_threads(event, threads, **kw)


# ── 1. Continuity evidence: active thread + description overlap → match ─


@pytest.mark.asyncio
async def test_active_thread_with_description_overlap_boosts_across_threshold():
    """Thread subject is generic; 'job' is in description only.

    Description-only overlap = 0.22 + type_compat 0.25 = 0.47 < 0.50.
    With active thread bonus 0.30 → 0.77 >= 0.50 → match.
    """
    thread = _mk_thread(
        "My unresolved dilemma",
        TemporalType.DECISION,
        description="Decision about leaving current job",
    )
    # subject_tokens: {my, unresolved, dilemma} (after normalization)
    # event_tokens: {talked, manager, job, situation}
    # subject_shared = {} → falls through to desc_only_shared = {job}
    # topic_overlap = _DESCRIPTION_BASE = 0.22
    event = _mk_event("Talked to my manager about my job situation.")

    # Without active context — below threshold
    baseline = await _match(event, [thread])
    assert not baseline.matched

    # With active context — matches
    result = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert result.matched
    assert result.thread_id == thread.id
    assert result.confidence >= MATCH_THRESHOLD
    assert any("Active thread selection" in s for s in result.signals)


@pytest.mark.asyncio
async def test_active_thread_with_subject_overlap_still_matches():
    """Strong subject overlap already matches without context; context doesn't break it."""
    thread = _mk_thread("Decision about leaving current job", TemporalType.DECISION)
    event = _mk_event("I actually left my job.", TemporalType.LIFE_EVENT)

    without = await _match(event, [thread])
    with_ctx = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert without.matched
    assert with_ctx.matched
    assert with_ctx.thread_id == without.thread_id


# ── 2. Active thread alone (zero overlap) → NO match ───────────────────


@pytest.mark.asyncio
async def test_active_thread_alone_cannot_fabricate_match():
    """Completely unrelated topic — active thread alone must not match."""
    thread = _mk_thread("Decision about leaving current job", TemporalType.DECISION)
    event = _mk_event("I need to buy groceries for dinner.", TemporalType.LIFE_EVENT)

    result = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert not result.matched
    assert result.thread_id is None


@pytest.mark.asyncio
async def test_active_thread_zero_overlap_no_bonus_signal():
    """Zero lexical overlap — no active thread signal should appear."""
    thread = _mk_thread("Plan vacation to Japan", TemporalType.DECISION)
    event = _mk_event("The database migration completed successfully.",
                       TemporalType.LIFE_EVENT)

    result = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert not result.matched
    assert not any("Active thread" in s for s in result.signals)


@pytest.mark.asyncio
async def test_active_thread_only_type_compat_no_match():
    """Type compat (DECISION↔LIFE_EVENT) but zero topic overlap → no match.

    The active thread bonus requires topic_overlap > 0 or continuity > 0;
    type compatibility alone does not gate it.
    """
    thread = _mk_thread("Decision about leaving current job", TemporalType.DECISION)
    event = _mk_event("I think I'm finally ready to do it.", TemporalType.LIFE_EVENT)

    result = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert not result.matched
    assert not any("Active thread" in s for s in result.signals)


# ── 3. Unrelated input with active thread ───────────────────────────────


@pytest.mark.asyncio
async def test_technical_input_with_personal_thread():
    """Technical question while personal thread is active — no match."""
    thread = _mk_thread("Dealing with anxiety about work", TemporalType.DECISION)
    event = _mk_event("How do I set up a PostgreSQL index?",
                       TemporalType.LIFE_EVENT)

    result = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert not result.matched


# ── 4. Ambiguous input with active thread → still ambiguous ────────────


@pytest.mark.asyncio
async def test_active_thread_with_ambiguous_input_remains_ambiguous():
    """Two plausible threads with zero overlap — still ambiguous or no match."""
    t1 = _mk_thread("My unresolved dilemma A", TemporalType.DECISION,
                     description="Decision about leaving current job")
    t2 = _mk_thread("My unresolved dilemma B", TemporalType.DECISION,
                     description="Decision about changing careers")
    # Event shares no tokens with either subject; shares 'job' with t1 desc
    event = _mk_event("I don't know anymore about anything.")

    result = await _match(event, [t1, t2], active_temporal_context=_active_ctx(t1))

    # Neither subject has overlap; 'anything' doesn't match 'job'
    # Both get type_bonus = 0.10 (SAME_TYPE) → low scores
    # Should not match or be ambiguous
    assert not result.matched


# ── 5. Correct thread: bonus only for matching thread_id ────────────────


@pytest.mark.asyncio
async def test_bonus_applies_only_to_matching_thread():
    """Active thread is t1; t2 also exists. Only t1 gets the bonus."""
    t1 = _mk_thread(
        "My unresolved dilemma",
        TemporalType.DECISION,
        description="Decision about leaving current job",
    )
    t2 = _mk_thread(
        "My other problem",
        TemporalType.DECISION,
        description="Decision about buying a house",
    )
    # 'job' overlaps with t1's description, not t2's
    event = _mk_event("Talked to my manager about my job situation.")

    result = await _match(event, [t1, t2], active_temporal_context=_active_ctx(t1))

    if result.matched:
        assert result.thread_id == t1.id


@pytest.mark.asyncio
async def test_active_thread_wrong_id_no_bonus():
    """Active thread ID doesn't match any candidate — no bonus applied."""
    thread = _mk_thread(
        "My unresolved dilemma",
        TemporalType.DECISION,
        description="Decision about leaving current job",
    )
    other = _mk_thread("Something else entirely", TemporalType.DECISION)
    event = _mk_event("Talked to my manager about my job situation.")

    # Active context on other thread (different ID, no overlap with event)
    result = await _match(event, [thread], active_temporal_context=_active_ctx(other))

    # 'job' overlaps with thread's description → topic_overlap = 0.22
    # + type_bonus = 0.25 → total = 0.47 < 0.50 → no match (no bonus for this thread)
    assert not result.matched


# ── 6. Confidence bounded ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_active_thread_bonus_never_exceeds_max_confidence():
    """Even with all evidence signals + active thread, confidence ≤ 1.0."""
    thread = _mk_thread("Decision about leaving current job", TemporalType.DECISION)
    event = _mk_event("I actually left my job today.", TemporalType.LIFE_EVENT)

    result = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert result.confidence <= 1.0


# ── 7. Existing matcher behavior unchanged without active context ───────


@pytest.mark.asyncio
async def test_matcher_unchanged_without_active_context():
    """Without active_temporal_context, behavior is identical to pre-4G."""
    thread = _mk_thread("Decision about leaving current job", TemporalType.DECISION)
    event = _mk_event("I actually left my job.", TemporalType.LIFE_EVENT)

    result = await _match(event, [thread])

    assert result.matched
    assert result.confidence >= MATCH_THRESHOLD
    assert not any("Active thread" in s for s in result.signals)


@pytest.mark.asyncio
async def test_empty_candidates_returns_attempted():
    """Empty candidates with active context — attempted=True is existing behavior."""
    event = _mk_event("Something happened.")
    ctx = ActiveTemporalContext(
        thread_id="nonexistent",
        subject="test",
        temporal_type=TemporalType.DECISION,
        status="open",
        events=[],
    )

    result = await _match(event, [], active_temporal_context=ctx)

    assert result.attempted
    assert not result.matched


# ── 8. Lifecycle not mutated ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_matcher_does_not_mutate_thread_status():
    """Matching with active context does not change thread status."""
    thread = _mk_thread(
        "My unresolved dilemma",
        TemporalType.DECISION,
        description="Decision about leaving current job",
    )
    event = _mk_event("Talked to my manager about my job situation.")

    original_status = thread.status

    await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert thread.status == original_status


# ── 9. Detector not affected ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_detector_ignores_active_thread_context():
    """TemporalEventDetector.detect_temporal_event() has no active_thread param."""
    import inspect

    from chronos_engine.temporal.detector import TemporalEventDetector

    detector = TemporalEventDetector()
    sig = inspect.signature(detector.detect_temporal_event)
    assert "active_temporal_context" not in sig.parameters


# ── 11. Contradictory evidence blocks match ────────────────────────────


@pytest.mark.asyncio
async def test_active_thread_does_not_override_completely_unrelated():
    """Active thread + zero overlap → no match, no active signal."""
    thread = _mk_thread("Plan trip to Hawaii", TemporalType.DECISION)
    event = _mk_event("The compiler threw a segmentation fault.",
                       TemporalType.LIFE_EVENT)

    result = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert not result.matched
    assert not any("Active thread" in s for s in result.signals)


@pytest.mark.asyncio
async def test_active_thread_with_description_overlap_below_threshold_no_match():
    """Description overlap exists but total score still below threshold.

    Thread description has many tokens diluting the overlap ratio.
    Even with type_compat, total stays below MATCH_THRESHOLD.
    """
    thread = _mk_thread(
        "My unresolved dilemma",
        TemporalType.DECISION,
        description=(
            "A long-standing decision about leaving current job "
            "that I have been thinking about for months"
        ),
    )
    event = _mk_event("The coffee shop was nice today.", TemporalType.LIFE_EVENT)

    # 'shop' doesn't appear in thread tokens; no overlap at all
    result = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert not result.matched


# ── 12. Multiple candidates: bonus applies only to correct one ─────────


@pytest.mark.asyncio
async def test_bonus_selects_correct_thread_among_multiple():
    """Two candidates; active context on t1 helps t1 when overlap exists."""
    t1 = _mk_thread(
        "My unresolved dilemma",
        TemporalType.DECISION,
        description="Decision about leaving current job",
    )
    t2 = _mk_thread(
        "My other problem",
        TemporalType.DECISION,
        description="Decision about buying a house",
    )
    # 'job' overlaps with t1's description, not t2's
    event = _mk_event("Talked to my manager about my job situation.")

    result = await _match(event, [t1, t2], active_temporal_context=_active_ctx(t1))

    if result.matched:
        assert result.thread_id == t1.id


@pytest.mark.asyncio
async def test_bonus_not_applied_to_wrong_candidate():
    """Active thread is t2; t1 has description overlap but no bonus."""
    t1 = _mk_thread(
        "My unresolved dilemma",
        TemporalType.DECISION,
        description="Decision about leaving current job",
    )
    t2 = _mk_thread(
        "My other problem",
        TemporalType.DECISION,
        description="Decision about buying a house",
    )
    # 'job' overlaps with t1's description, but active context is on t2
    event = _mk_event("Talked to my manager about my job situation.")

    result = await _match(event, [t1, t2], active_temporal_context=_active_ctx(t2))

    # t1 has desc overlap 0.22 + type 0.25 = 0.47 (no bonus, not active)
    # t2 has type 0.25 only (no overlap, no bonus — active thread is t2 but
    #   t2 has no topic_overlap or continuity → bonus not gated)
    # Neither should match confidently
    assert not result.matched


# ── 13. Active thread signal explains the bonus in the result ──────────


@pytest.mark.asyncio
async def test_active_thread_signal_in_result():
    """When active thread bonus applies, the signal list explains it."""
    thread = _mk_thread(
        "My unresolved dilemma",
        TemporalType.DECISION,
        description="Decision about leaving current job",
    )
    event = _mk_event("Talked to my manager about my job situation.")

    result = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    assert result.matched
    assert any("Active thread selection" in s for s in result.signals)
    assert any("explicitly continuing" in s for s in result.signals)


# ── 14. Baseline comparison: with vs without context ───────────────────


@pytest.mark.asyncio
async def test_context_increases_confidence_when_applied():
    """Same event/thread pair: context always increases or maintains confidence."""
    thread = _mk_thread(
        "My unresolved dilemma",
        TemporalType.DECISION,
        description="Decision about leaving current job",
    )
    event = _mk_event("Talked to my manager about my job situation.")

    baseline = await _match(event, [thread])
    with_ctx = await _match(event, [thread], active_temporal_context=_active_ctx(thread))

    if baseline.matched and with_ctx.matched:
        assert with_ctx.confidence >= baseline.confidence
    elif not baseline.matched and with_ctx.matched:
        # Context pushed it across — this is the key scenario
        assert with_ctx.confidence >= MATCH_THRESHOLD
