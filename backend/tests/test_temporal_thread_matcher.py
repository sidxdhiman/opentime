"""Phase 3C tests: deterministic TemporalThread matching.

Covers the required matching behavior: basic outcomes (no event / no
candidates / confident match), false-positive protection (generic tokens,
compatible types and supporting evidence alone can never match), ambiguity
handling, the type-compatibility map, evidence boosts (goal association,
consistency/change, memory continuity), bounded candidate retrieval from
the temporal store, and the additive engine integration. Deterministic,
offline, read-only — no AI, no embeddings, no new threads, no persistence.
"""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.interfaces import BaseTemporalThreadMatcher
from chronos_engine.state.models import (
    ConsistencyResult,
    ContradictionResult,
    GoalAnalysisResult,
    GoalStatus,
)
from chronos_engine.storage import InMemoryTemporalStore
from chronos_engine.temporal.matcher import (
    MATCH_THRESHOLD,
    MAX_CONFIDENCE,
    TemporalThreadMatcher,
)
from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalThread,
    TemporalThreadMatchResult,
    TemporalThreadStatus,
    TemporalType,
)

USER = "user_3c"


def mk_thread(subject, ttype=None, description=None, **kwargs) -> TemporalThread:
    return TemporalThread(
        user_id=USER, temporal_type=ttype, subject=subject, description=description, **kwargs
    )


def mk_event(description, ttype=None, **kwargs) -> TemporalEvent:
    kwargs.setdefault("user_id", USER)
    return TemporalEvent(temporal_type=ttype, description=description, **kwargs)


async def match(event, threads, **evidence) -> TemporalThreadMatchResult:
    return await TemporalThreadMatcher().match_threads(event, threads, **evidence)


# ── Basic behavior ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_candidate_threads_attempted_but_not_matched():
    result = await match(mk_event("I actually left my job.", TemporalType.LIFE_EVENT), [])
    assert result.attempted
    assert not result.matched
    assert result.thread_id is None
    assert not result.ambiguous
    assert result.candidate_count == 0


@pytest.mark.asyncio
async def test_strong_subject_overlap_and_compatible_type_matches():
    # Flagship story: earlier "I don't know if I should leave my job."
    # (DECISION thread), later "I actually left my job." (LIFE_EVENT).
    thread = mk_thread("Decision about leaving current job", TemporalType.DECISION)
    event = mk_event("I actually left my job.", TemporalType.LIFE_EVENT)

    result = await match(event, [thread])

    assert result.attempted
    assert result.matched
    assert result.thread_id == thread.id
    assert result.matched_thread is not None
    assert result.matched_thread.id == thread.id
    assert result.confidence >= MATCH_THRESHOLD
    assert any("overlap" in s.lower() for s in result.signals)


# ── False-positive protection ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unrelated_topic_does_not_match():
    # "Build ChronOS" vs "I built a shelf." — compatible types, no shared topic.
    thread = mk_thread("Build ChronOS project", TemporalType.GOAL)
    event = mk_event("I built a shelf today.", TemporalType.MILESTONE)

    result = await match(event, [thread])

    assert result.attempted
    assert not result.matched
    assert not result.ambiguous


@pytest.mark.asyncio
async def test_generic_token_overlap_only_never_matches():
    # Shared words are all generic filler; same type adds a nudge but the
    # total stays far below the consideration floor.
    thread = mk_thread("A big thing happened recently", TemporalType.DECISION)
    event = mk_event("Some big thing keeps happening.", TemporalType.DECISION)

    result = await match(event, [thread])

    assert not result.matched
    assert any("generic" in s.lower() for s in result.signals)


@pytest.mark.asyncio
async def test_compatible_type_alone_cannot_match():
    thread = mk_thread("Learn guitar basics", TemporalType.GOAL)
    event = mk_event("Graduated from university.", TemporalType.MILESTONE)

    result = await match(event, [thread])

    assert not result.matched
    assert "floor" in result.reason or "threshold" in result.reason


@pytest.mark.asyncio
async def test_weak_description_only_overlap_below_threshold():
    # The only shared meaningful token lives in the thread *description*,
    # which weighs less than the subject — total stays below threshold.
    thread = mk_thread(
        "A big personal decision",
        TemporalType.DECISION,
        description="mentions adopting a dog someday",
    )
    event = mk_event("My neighbor got a dog.", TemporalType.LIFE_EVENT)

    result = await match(event, [thread])

    assert not result.matched
    assert result.confidence < MATCH_THRESHOLD


# ── Ambiguity handling ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_two_similarly_plausible_threads_is_ambiguous():
    ta = mk_thread("Career decision about leaving the job", TemporalType.DECISION)
    tb = mk_thread("Decision regarding his new job offer", TemporalType.DECISION)
    event = mk_event("Something happened with my job today.", TemporalType.LIFE_EVENT)

    result = await match(event, [ta, tb])

    assert result.attempted
    assert not result.matched
    assert result.ambiguous
    assert result.thread_id is None
    assert result.candidate_count == 2


@pytest.mark.asyncio
async def test_clear_winner_is_selected():
    strong = mk_thread(
        "Career decision about leaving the job and difficult manager situation",
        TemporalType.DECISION,
    )
    unrelated = mk_thread("Weekend trip planning", TemporalType.DECISION)
    event = mk_event(
        "I finally talked to my manager about leaving the job.",
        TemporalType.LIFE_EVENT,
    )

    result = await match(event, [strong, unrelated])

    assert result.matched
    assert result.thread_id == strong.id
    assert not result.ambiguous


# ── Type compatibility ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decision_to_life_event_pair_supported():
    thread = mk_thread("Decision about leaving current job", TemporalType.DECISION)
    event = mk_event("I actually left my job.", TemporalType.LIFE_EVENT)

    matched = await match(event, [thread])

    assert matched.matched
    assert any(
        "compatible temporal types" in s.lower() for s in matched.signals
    )


@pytest.mark.asyncio
async def test_incompatible_type_contributes_nothing():
    # Identical subject text as the flagship, but PROMISE <-> LIFE_EVENT is
    # not a documented compatible pair — topic overlap alone cannot match.
    thread = mk_thread("Decision about leaving current job", TemporalType.PROMISE)
    event = mk_event("I actually left my job.", TemporalType.LIFE_EVENT)

    result = await match(event, [thread])

    assert not result.matched
    assert not any("compatible" in s.lower() for s in result.signals)


@pytest.mark.asyncio
async def test_goal_to_milestone_pair_supported():
    thread = mk_thread("Run a full marathon this year", TemporalType.GOAL)
    event = mk_event("Finally finished my marathon.", TemporalType.MILESTONE)

    result = await match(event, [thread])

    assert result.matched
    assert result.thread_id == thread.id


@pytest.mark.asyncio
async def test_same_type_alone_insufficient_for_match():
    thread = mk_thread("Beliefs about money and happiness", TemporalType.BELIEF)
    event = mk_event("Money worries me lately.", TemporalType.BELIEF)

    result = await match(event, [thread])

    assert not result.matched
    assert not result.ambiguous


# ── Evidence signals ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_goal_association_boosts_across_threshold():
    thread = mk_thread(
        "Personal growth journey",
        TemporalType.GOAL,
        description="wants to learn guitar someday",
    )
    event = mk_event("I finally picked up the guitar.", TemporalType.LIFE_EVENT)

    without_goal = await match(event, [thread])
    assert not without_goal.matched

    goal_evidence = GoalAnalysisResult(
        status=GoalStatus.NEW,
        goal="Learn to play the guitar",
        confidence=0.8,
    )
    with_goal = await match(event, [thread], goal_analysis=goal_evidence)

    assert with_goal.matched
    assert with_goal.thread_id == thread.id
    assert any("goal association" in s.lower() for s in with_goal.signals)


@pytest.mark.asyncio
async def test_consistency_change_evidence_boosts_across_threshold():
    thread = mk_thread("Considering building ChronOS", TemporalType.DECISION)
    event = mk_event("Thinking of abandoning ChronOS.", TemporalType.DECISION)

    plain = await match(event, [thread])
    assert not plain.matched

    consistency = ConsistencyResult(
        is_consistent=True,
        confidence=0.7,
        changes=[
            ContradictionResult(
                type="DECISION_CHANGE",
                previous_value="build ChronOS",
                current_value="abandon ChronOS project",
                confidence=0.75,
            )
        ],
    )
    boosted = await match(event, [thread], consistency_result=consistency)

    assert boosted.matched
    assert boosted.thread_id == thread.id
    assert any("consistency" in s.lower() for s in boosted.signals)


@pytest.mark.asyncio
async def test_memory_continuity_enables_match_without_lexical_overlap():
    # Explicit memory linkage already stored on the thread is the one
    # evidence path that does not require topical overlap.
    thread = mk_thread(
        "Worries about public speaking",
        TemporalType.FEAR,
        related_memory_ids=["mem_42"],
    )
    event = mk_event(
        "Completely different words entirely here.",
        TemporalType.DECISION,
        memory_id="mem_42",
    )

    result = await match(event, [thread])

    assert result.matched
    assert result.thread_id == thread.id
    assert any("continuity" in s.lower() for s in result.signals)


@pytest.mark.asyncio
async def test_supporting_evidence_alone_cannot_fabricate_match():
    # Compatible types + goal association + consistency evidence all fire,
    # but there is zero direct topic overlap and zero memory continuity —
    # the hard gate must reject the match anyway.
    thread = mk_thread("Learn guitar deeply", TemporalType.GOAL)
    event = mk_event("Completely unrelated sentence here.", TemporalType.MILESTONE)
    goal_evidence = GoalAnalysisResult(status=GoalStatus.NEW, goal="Learn guitar basics")
    consistency = ConsistencyResult(
        changes=[ContradictionResult(type="GOAL_CHANGE", previous_value="learn guitar basics")]
    )

    result = await match(
        event,
        [thread],
        goal_analysis=goal_evidence,
        consistency_result=consistency,
    )

    assert not result.matched
    assert result.confidence < MAX_CONFIDENCE
    assert "topical" in result.reason or "continuity" in result.reason


# ── Safety ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confidence_stays_bounded():
    cases = [
        (mk_thread("Decision about leaving current job", TemporalType.DECISION),
         mk_event("I actually left my job.", TemporalType.LIFE_EVENT)),
        (mk_thread("Learn guitar deeply", TemporalType.GOAL),
         mk_event("Completely unrelated sentence here.", TemporalType.MILESTONE)),
        (mk_thread("Beliefs about money and happiness", TemporalType.BELIEF),
         mk_event("Money worries me lately.", TemporalType.BELIEF)),
    ]
    for thread, event in cases:
        result = await match(event, [thread])
        assert 0.0 <= result.confidence <= MAX_CONFIDENCE
        if result.matched:
            assert result.confidence >= MATCH_THRESHOLD


@pytest.mark.asyncio
async def test_matching_does_not_mutate_candidate_threads():
    thread = mk_thread("Decision about leaving current job", TemporalType.DECISION)
    before = thread.model_dump()
    event = mk_event("I actually left my job.", TemporalType.LIFE_EVENT)

    result = await match(event, [thread])

    assert result.matched  # a real match happened...
    assert thread.model_dump() == before  # ...and the candidate is untouched.


# ── Candidate retrieval from the store ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_candidate_threads_returns_live_threads_only():
    store = InMemoryTemporalStore()
    statuses = [
        (TemporalThreadStatus.OPEN, True),
        (TemporalThreadStatus.ACTIVE, True),
        (TemporalThreadStatus.CHANGED, True),
        (TemporalThreadStatus.RESOLVED, False),
        (TemporalThreadStatus.ABANDONED, False),
        (TemporalThreadStatus.ARCHIVED, False),
    ]
    for status, _live in statuses:
        await store.save_thread(TemporalThread(user_id=USER, status=status))
    await store.save_thread(TemporalThread(user_id="someone_else"))

    candidates = await store.get_candidate_threads(USER)

    returned_statuses = {t.status for t in candidates}
    assert returned_statuses == {
        TemporalThreadStatus.OPEN,
        TemporalThreadStatus.ACTIVE,
        TemporalThreadStatus.CHANGED,
    }
    assert all(t.user_id == USER for t in candidates)


@pytest.mark.asyncio
async def test_get_candidate_threads_bounded_and_most_recent_first():
    from datetime import datetime, timedelta, timezone

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store = InMemoryTemporalStore()
    for i in range(5):
        await store.save_thread(
            TemporalThread(user_id=USER, created_at=base + timedelta(days=i))
        )

    candidates = await store.get_candidate_threads(USER, limit=2)

    assert len(candidates) == 2
    assert candidates[0].created_at > candidates[1].created_at


@pytest.mark.asyncio
async def test_default_limit_applies_without_argument():
    from datetime import datetime, timedelta, timezone

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store = InMemoryTemporalStore()
    for i in range(30):
        await store.save_thread(
            TemporalThread(user_id=USER, created_at=base + timedelta(minutes=i))
        )

    candidates = await store.get_candidate_threads(USER)

    assert len(candidates) <= 25


# ── Engine integration ────────────────────────────────────────────────────


def _engine() -> ChronosEngine:
    return ChronosEngine()


@pytest.mark.asyncio
async def test_engine_skips_matching_when_no_temporal_event():
    engine = _engine()
    response = await engine.process_user_input(
        user_id=USER,
        content="Hi there!",
        input_type="text",
        provider_key="chronos",
    )

    state = response.chronos_state
    assert not state.temporal_event_detection.detected
    assert state.temporal_thread_match is not None
    assert not state.temporal_thread_match.attempted
    assert not state.temporal_thread_match.matched

    trace_text = "\n".join(response.reasoning_trace.reasoning_steps)
    assert "thread matching skipped" in trace_text.lower()


@pytest.mark.asyncio
async def test_engine_reports_no_match_with_empty_store():
    engine = _engine()
    response = await engine.process_user_input(
        user_id=USER,
        content="Actually left my job today.",
        input_type="text",
        provider_key="chronos",
    )

    state = response.chronos_state
    assert state.temporal_event_detection.detected
    match_result = state.temporal_thread_match
    assert match_result.attempted
    assert not match_result.matched
    assert match_result.candidate_count == 0

    trace_text = "\n".join(response.reasoning_trace.reasoning_steps)
    assert "no sufficiently reliable temporal thread match" in trace_text.lower()


@pytest.mark.asyncio
async def test_engine_matches_event_to_seeded_thread_and_links_in_memory():
    engine = _engine()
    thread = mk_thread("Decision about leaving current job", TemporalType.DECISION)
    await engine.temporal_store.save_thread(thread)

    response = await engine.process_user_input(
        user_id=USER,
        content="Actually left my job today.",
        input_type="text",
        provider_key="chronos",
    )

    state = response.chronos_state
    match_result = state.temporal_thread_match
    assert match_result is not None
    assert match_result.matched
    assert match_result.thread_id == thread.id
    assert state.temporal_event_detection.event.thread_id == thread.id

    trace_text = "\n".join(response.reasoning_trace.reasoning_steps)
    assert f"matched existing thread '{thread.id}'" in trace_text.lower()


@pytest.mark.asyncio
async def test_engine_matching_persists_event_and_updates_thread():
    """Phase 3D supersedes the temporary 3C 'no persistence' contract: a
    confident match now attaches and persists the event, links the memory,
    refreshes ``updated_at``, and applies evidence-based transitions ("left
    my job" resolves a DECISION thread) — never creating duplicate threads."""
    engine = _engine()
    thread = mk_thread("Decision about leaving current job", TemporalType.DECISION)
    await engine.temporal_store.save_thread(thread)
    stored_before = (await engine.temporal_store.get_thread(thread.id, USER)).model_dump()

    response = await engine.process_user_input(
        user_id=USER,
        content="Actually left my job today.",
        input_type="text",
        provider_key="chronos",
    )

    state = response.chronos_state
    assert state.temporal_thread_match.matched

    # Exactly one thread exists (no duplicate creation), updated in place.
    stored_after = await engine.temporal_store.get_thread(thread.id, USER)
    assert stored_after.id == stored_before["id"]
    assert stored_after.origin_memory_id == stored_before["origin_memory_id"]
    assert stored_after.created_at == stored_before["created_at"]
    assert stored_after.updated_at > stored_before["updated_at"]

    # Strong explicit outcome evidence moved OPEN -> RESOLVED, so the thread
    # no longer appears among live matching candidates.
    assert stored_before["status"] == TemporalThreadStatus.OPEN.value
    assert stored_after.status is TemporalThreadStatus.RESOLVED

    events = await engine.temporal_store.get_events_by_thread(thread.id, USER)
    assert len(events) == 1
    assert events[0].memory_id == state.temporal_event_detection.event.memory_id
    assert events[0].thread_id == thread.id


@pytest.mark.asyncio
async def test_engine_defaults_wire_temporal_store_and_matcher():
    engine = _engine()
    assert isinstance(engine.temporal_store, InMemoryTemporalStore)
    assert isinstance(engine.temporal_thread_matcher, BaseTemporalThreadMatcher)


@pytest.mark.asyncio
async def test_existing_engine_lifecycle_remains_functional():
    engine = _engine()
    response = await engine.process_user_input(
        user_id=USER,
        content="Hi there!",
        input_type="text",
        provider_key="chronos",
    )

    assert response.final_response
    assert response.deterministic_response is not None
    assert response.ai_routing is not None
    assert response.validation_result.is_valid
    steps = list(response.reasoning_trace.reasoning_steps)
    assert any("temporal event detection" in s.lower() for s in steps)
    assert any("thread matching skipped" in s.lower() for s in steps)
