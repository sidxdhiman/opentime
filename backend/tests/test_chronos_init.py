"""
Tests for ChronosInitializationService.

Covers:
  1.  Full pipeline creates Chronos state
  2.  Genesis memory is created
  3.  Identity state is created
  4.  Goals are extracted from structured input
  5.  Timeline events are created
  6.  Analysis preferences are stored
  7.  Pattern baseline is created
  8.  Idempotency — second call raises ChronosAlreadyInitialized
  9.  Handles missing optional responses gracefully
  10. Each resource is scoped to the correct user (user isolation)
  11. Failed LLM extraction doesn't crash the pipeline (mock returns empty)
  12. Failed embedding returns deterministic mock vector
"""

import pytest

from opentime.application.onboarding.init_service import (
    ChronosAlreadyInitialized,
    ChronosInitializationService,
)
from opentime.domain.onboarding.entities import OnboardingResponse, OnboardingStep

USER = "chronos-test-user-001"
OTHER_USER = "chronos-test-user-002"


def _make_response(user_id: str, step: OnboardingStep, response: object) -> OnboardingResponse:
    return OnboardingResponse(
        user_id=user_id,
        session_id="session-test-001",
        step=step,
        question=f"Question for {step.value}",
        response=response,
    )


def _full_responses(user_id: str) -> list[OnboardingResponse]:
    return [
        _make_response(user_id, OnboardingStep.ABOUT_YOU, {
            "preferred_name": "Alice", "timezone": "Asia/Kolkata", "occupation": "Engineer"
        }),
        _make_response(user_id, OnboardingStep.LIFE_RIGHT_NOW,
            "I'm currently working as a software engineer at a startup. "
            "I spend most of my time building backend systems and learning. "
            "I'm excited about AI and trying to figure out what to do next in my career."),
        _make_response(user_id, OnboardingStep.WHATS_ON_MIND,
            "I'm worried about work-life balance and whether I'm growing fast enough."),
        _make_response(user_id, OnboardingStep.WHERE_GOING, {
            "goals": [
                {"title": "Get better at system design", "description": "",
                 "category": "career", "importance": 0.9},
                {"title": "Exercise more regularly", "description": "",
                 "category": "health", "importance": 0.7},
            ]
        }),
        _make_response(user_id, OnboardingStep.HOW_CHANGED,
            "I used to be more anxious. I've become more confident at work over the past year."),
        _make_response(user_id, OnboardingStep.FIRST_MEMORY,
            "Today is August 2026. I'm 27, living in Bangalore, working hard and "
            "trying to understand who I'm becoming. I care deeply about building things that matter."),
        _make_response(user_id, OnboardingStep.ANALYSIS_PREFS,
            ["how_i_changed", "goals_progress", "habits_patterns"]),
    ]


# ── 1. Full pipeline ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_creates_chronos_state(
    chronos_init_service: ChronosInitializationService,
    chronos_repo,
):
    responses = _full_responses(USER)
    state = await chronos_init_service.initialize(user_id=USER, responses=responses)

    assert state.user_id == USER
    assert state.is_initialised is True
    assert state.version == 1

    stored = await chronos_repo.get_for_user(USER)
    assert stored is not None
    assert stored.is_initialised is True


# ── 2. Genesis memory ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_genesis_memory_created(
    chronos_init_service: ChronosInitializationService,
    memory_repo,
):
    await chronos_init_service.initialize(user_id=USER, responses=_full_responses(USER))
    genesis = await memory_repo.get_genesis(USER)
    assert genesis is not None
    assert genesis.is_genesis is True
    assert genesis.source == "genesis"
    assert "August 2026" in genesis.content


# ── 3. Identity state ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_identity_state_created(
    chronos_init_service: ChronosInitializationService,
    identity_repo,
):
    state = await chronos_init_service.initialize(user_id=USER, responses=_full_responses(USER))
    identity = await identity_repo.get_latest(USER)
    assert identity is not None
    assert identity.user_id == USER
    assert identity.version == 1
    assert state.identity_state_id == identity.id


# ── 4. Goals extracted from structured input ──────────────────────────────────

@pytest.mark.asyncio
async def test_goals_extracted(
    chronos_init_service: ChronosInitializationService,
    goal_repo,
):
    state = await chronos_init_service.initialize(user_id=USER, responses=_full_responses(USER))
    goals = await goal_repo.get_active_for_user(USER)
    assert len(goals) == 2
    assert any("system design" in g.title.lower() for g in goals)
    assert any("exercise" in g.title.lower() for g in goals)
    assert len(state.goal_ids) == 2


# ── 5. Timeline events ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_timeline_events_created(
    chronos_init_service: ChronosInitializationService,
    timeline_repo,
):
    await chronos_init_service.initialize(user_id=USER, responses=_full_responses(USER))
    events = await timeline_repo.get_for_user(USER)
    # At minimum the "Joined OpenTime" genesis event should exist
    assert len(events) >= 1
    titles = [e.title for e in events]
    assert "Joined OpenTime" in titles


# ── 6. Analysis preferences stored ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analysis_preferences_stored(
    chronos_init_service: ChronosInitializationService,
    pref_repo,
):
    await chronos_init_service.initialize(user_id=USER, responses=_full_responses(USER))
    prefs = await pref_repo.get_for_user(USER)
    assert len(prefs) == 3
    values = [p.preference for p in prefs]
    assert "how_i_changed" in values
    assert "goals_progress" in values


# ── 7. Pattern baseline ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pattern_baseline_created(
    chronos_init_service: ChronosInitializationService,
    pattern_repo,
):
    await chronos_init_service.initialize(user_id=USER, responses=_full_responses(USER))
    patterns = await pattern_repo.get_for_user(USER)
    assert len(patterns) >= 1
    for p in patterns:
        assert p.confidence <= 0.5  # baseline confidence is low


# ── 8. Idempotency ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_second_init_raises_already_initialized(
    chronos_init_service: ChronosInitializationService,
):
    responses = _full_responses(USER)
    await chronos_init_service.initialize(user_id=USER, responses=responses)
    with pytest.raises(ChronosAlreadyInitialized):
        await chronos_init_service.initialize(user_id=USER, responses=responses)


# ── 9. Missing optional responses don't crash ─────────────────────────────────

@pytest.mark.asyncio
async def test_init_without_optional_steps(
    chronos_init_service: ChronosInitializationService,
):
    # Only include required steps (no whats_on_mind, how_changed)
    minimal_responses = [
        _make_response(USER, OnboardingStep.ABOUT_YOU, {"preferred_name": "Bob"}),
        _make_response(USER, OnboardingStep.LIFE_RIGHT_NOW,
            "I'm a student trying to figure out what to do with my life."),
        _make_response(USER, OnboardingStep.WHERE_GOING,
            {"goals": [{"title": "Graduate", "description": "", "category": "education", "importance": 0.9}]}),
        _make_response(USER, OnboardingStep.FIRST_MEMORY,
            "This is my first memory for Chronos. I am starting something new today."),
        _make_response(USER, OnboardingStep.ANALYSIS_PREFS, ["goals_progress"]),
    ]
    state = await chronos_init_service.initialize(user_id=USER, responses=minimal_responses)
    assert state.is_initialised is True


# ── 10. User isolation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_isolation(
    chronos_init_service: ChronosInitializationService,
    memory_repo,
    goal_repo,
):
    # Init both users
    await chronos_init_service.initialize(user_id=USER, responses=_full_responses(USER))

    other_responses = [
        _make_response(OTHER_USER, OnboardingStep.ABOUT_YOU, {"preferred_name": "Other"}),
        _make_response(OTHER_USER, OnboardingStep.LIFE_RIGHT_NOW, "Other user's life is very different."),
        _make_response(OTHER_USER, OnboardingStep.WHERE_GOING,
            {"goals": [{"title": "Travel the world", "description": "", "category": "lifestyle", "importance": 0.8}]}),
        _make_response(OTHER_USER, OnboardingStep.FIRST_MEMORY, "Other user's genesis memory is private."),
        _make_response(OTHER_USER, OnboardingStep.ANALYSIS_PREFS, ["relationships"]),
    ]
    await chronos_init_service.initialize(user_id=OTHER_USER, responses=other_responses)

    # Memories must be scoped
    user_mems = await memory_repo.get_for_user(USER)
    other_mems = await memory_repo.get_for_user(OTHER_USER)
    assert all(m.user_id == USER for m in user_mems)
    assert all(m.user_id == OTHER_USER for m in other_mems)

    # Goals must be scoped
    user_goals = await goal_repo.get_all_for_user(USER)
    other_goals = await goal_repo.get_all_for_user(OTHER_USER)
    assert all(g.user_id == USER for g in user_goals)
    assert all(g.user_id == OTHER_USER for g in other_goals)


# ── 11. Failed LLM (mock returns empty) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_survives_empty_llm_extraction(
    chronos_init_service: ChronosInitializationService,
):
    """MockLLMService returns empty structures; pipeline must not crash."""
    responses = _full_responses(USER)
    state = await chronos_init_service.initialize(user_id=USER, responses=responses)
    assert state is not None
    assert state.is_initialised is True


# ── 12. Embeddings are generated (mock returns deterministic vector) ──────────

@pytest.mark.asyncio
async def test_genesis_memory_has_embedding(
    chronos_init_service: ChronosInitializationService,
    memory_repo,
):
    await chronos_init_service.initialize(user_id=USER, responses=_full_responses(USER))
    genesis = await memory_repo.get_genesis(USER)
    assert genesis is not None
    assert len(genesis.embedding) == 256  # MockEmbeddingService dimension
    # Embeddings must be normalised
    mag = sum(x * x for x in genesis.embedding) ** 0.5
    assert abs(mag - 1.0) < 1e-4
