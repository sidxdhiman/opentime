"""Phase 1E tests: deterministic ConsistencyEngine and state integration."""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.consistency import ConsistencyEngine
from chronos_engine.core.models import (
    IdentityProfile,
    MemoryItem,
    MemoryType,
    RetrievedContext,
    UserInput,
)
from chronos_engine.goals import GoalDetector


def mem(memory_id: str, content: str) -> MemoryItem:
    return MemoryItem(
        id=memory_id, user_id="user_1e", content=content, memory_type=MemoryType.LONG_TERM
    )


def user_input(content: str) -> UserInput:
    return UserInput(id="in_1e", user_id="user_1e", content=content)


async def detect_goals(content: str, existing_goals):
    return await GoalDetector().detect_goals(user_input(content), existing_goals)


@pytest.mark.asyncio
async def test_no_contradiction():
    identity = IdentityProfile(user_id="user_1e", goals=["Build ChronOS"])
    ctx = RetrievedContext(
        relevant_memories=[mem("m_goal", "I want to build ChronOS as my main project.")],
        goals=["Build ChronOS"],
    )
    result = await ConsistencyEngine().check_consistency(
        user_input("I'm continuing work on ChronOS."), ctx, identity=identity
    )
    assert result.is_consistent is True
    assert result.contradictions == []
    assert result.changes == []


@pytest.mark.asyncio
async def test_goal_change_on_abandonment():
    goal_analysis = await detect_goals(
        "I've decided I don't want to work on ChronOS anymore.", ["Build ChronOS"]
    )
    ctx = RetrievedContext(
        relevant_memories=[mem("m_prev", "I want to make ChronOS my main project.")],
        goals=["Build ChronOS"],
    )
    identity = IdentityProfile(user_id="user_1e", goals=["Build ChronOS"])

    result = await ConsistencyEngine().check_consistency(
        user_input("I've decided I don't want to work on ChronOS anymore."),
        ctx,
        goal_analysis=goal_analysis,
        identity=identity,
    )
    changes = [c for c in result.changes if c.type == "GOAL_CHANGE"]
    assert changes
    gc = changes[0]
    assert gc.previous_value == "Build ChronOS"
    assert "Build ChronOS" in gc.current_value
    assert "m_prev" in gc.supporting_memory_ids


@pytest.mark.asyncio
async def test_goal_conflict():
    identity = IdentityProfile(user_id="user_1e", goals=["Save money for a car"])
    ctx = RetrievedContext(goals=["Save money for a car"])
    result = await ConsistencyEngine().check_consistency(
        user_input("I'm thinking about spending my entire car savings."),
        ctx,
        identity=identity,
    )
    assert any(c.type == "GOAL_CONFLICT" for c in result.contradictions)


@pytest.mark.asyncio
async def test_decision_change():
    ctx = RetrievedContext(relevant_memories=[mem("m_db", "I've decided to use PostgreSQL.")])
    result = await ConsistencyEngine().check_consistency(
        user_input("I've decided to use MongoDB instead."), ctx
    )
    decisions = [c for c in result.contradictions if c.type == "DECISION_CHANGE"]
    assert decisions
    assert decisions[0].previous_value == "postgresql"
    assert decisions[0].current_value == "mongodb"
    assert "m_db" in decisions[0].supporting_memory_ids


@pytest.mark.asyncio
async def test_persistent_preference_change():
    identity = IdentityProfile(
        user_id="user_1e",
        goals=["Build ChronOS"],
        preferences={"communication": "Concise, direct responses"},
    )
    ctx = RetrievedContext(goals=["Build ChronOS"])
    result = await ConsistencyEngine().check_consistency(
        user_input("From now on, give me detailed explanations."),
        ctx,
        identity=identity,
    )
    assert any(c.type == "PREFERENCE_CONFLICT" for c in result.contradictions)


@pytest.mark.asyncio
async def test_single_detailed_request_is_not_permanent():
    identity = IdentityProfile(
        user_id="user_1e",
        goals=["Build ChronOS"],
        preferences={"communication": "Concise, direct responses"},
    )
    ctx = RetrievedContext(goals=["Build ChronOS"])
    result = await ConsistencyEngine().check_consistency(
        user_input("Give me a very detailed explanation of this one thing."),
        ctx,
        identity=identity,
    )
    assert not any(c.type == "PREFERENCE_CONFLICT" for c in result.contradictions)


@pytest.mark.asyncio
async def test_weak_uncertainty_has_no_high_confidence_change():
    goal_analysis = await detect_goals("Maybe I should learn something else.", ["Learn Rust"])
    ctx = RetrievedContext(goals=["Learn Rust"])
    identity = IdentityProfile(user_id="user_1e", goals=["Learn Rust"])
    result = await ConsistencyEngine().check_consistency(
        user_input("Maybe I should learn something else."),
        ctx,
        goal_analysis=goal_analysis,
        identity=identity,
    )
    assert not any(c.type == "GOAL_CHANGE" and c.confidence >= 0.6 for c in result.changes)


@pytest.mark.asyncio
async def test_no_invented_contradiction_without_evidence():
    # No stored goal, no memories: nothing to contradict against.
    identity = IdentityProfile(user_id="user_1e", goals=[], values=[], preferences={})
    ctx = RetrievedContext(relevant_memories=[], goals=[])
    result = await ConsistencyEngine().check_consistency(
        user_input("I've decided to stop working on ChronOS."), ctx, identity=identity
    )
    assert result.contradictions == []
    assert result.changes == []


@pytest.mark.asyncio
async def test_user_evolution_goal_change():
    goal_analysis = await detect_goals(
        "I've changed my mind. I want to focus on Python.", ["Learn Rust"]
    )
    ctx = RetrievedContext(relevant_memories=[mem("m_rust", "I want to learn Rust.")])
    identity = IdentityProfile(user_id="user_1e", goals=["Learn Rust"])

    result = await ConsistencyEngine().check_consistency(
        user_input("I've changed my mind. I want to focus on Python."),
        ctx,
        goal_analysis=goal_analysis,
        identity=identity,
    )
    changes = [c for c in result.changes if c.type == "GOAL_CHANGE"]
    assert changes
    gc = changes[0]
    assert gc.previous_value == "Learn Rust"
    assert "Python" in gc.current_value
    assert "m_rust" in gc.supporting_memory_ids


@pytest.mark.asyncio
async def test_full_engine_integration():
    engine = ChronosEngine()
    # First establish a real stored goal from shared data, so the subsequent
    # contradiction is grounded in what the user actually said (never an
    # assumed/fabricated founder goal).
    await engine.process_user_input(
        user_id="user_1e_engine",
        content="I want to keep building OpenTime as my top priority.",
        provider_key="chronos",
    )
    response = await engine.process_user_input(
        user_id="user_1e_engine",
        content="I'm abandoning the OpenTime platform for good.",
        provider_key="chronos",
    )
    state = response.chronos_state
    assert state is not None
    assert state.intent is not None
    assert state.user_state is not None
    assert state.goal_analysis is not None
    assert state.contradictions != []

    assert any(
        "Consistency check" in s for s in response.reasoning_trace.reasoning_steps
    )