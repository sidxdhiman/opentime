"""Phase 1D tests: deterministic GoalDetector and state integration."""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.models import IntentType, UserInput
from chronos_engine.goals import GoalDetector
from chronos_engine.state.models import (
    GoalStatus,
    UserCognitiveState,
    UserEmotionState,
)
from chronos_engine.user_state import UserStateDetector


async def detect(content: str, existing_goals):
    detector = GoalDetector()
    user_input = UserInput(id="in_1d", user_id="user_1d", content=content)
    return await detector.detect_goals(user_input, existing_goals)


@pytest.mark.asyncio
async def test_new_goal():
    result = await detect("I want to learn Python.", [])
    assert result.status == GoalStatus.NEW
    assert result.goal and "Python" in result.goal


@pytest.mark.asyncio
async def test_existing_goal_active():
    result = await detect("I'm continuing my Python practice.", ["Learn Python"])
    assert result.status == GoalStatus.ACTIVE
    assert result.matched_existing_goal == "Learn Python"


@pytest.mark.asyncio
async def test_existing_goal_progress():
    result = await detect(
        "I finished implementing the UserStateDetector.", ["Build ChronOS"]
    )
    assert result.status == GoalStatus.PROGRESS
    assert result.matched_existing_goal == "Build ChronOS"


@pytest.mark.asyncio
async def test_existing_goal_completed():
    result = await detect(
        "I finally finished my portfolio website.", ["Build portfolio website"]
    )
    assert result.status == GoalStatus.COMPLETED
    assert result.matched_existing_goal == "Build portfolio website"


@pytest.mark.asyncio
async def test_existing_goal_abandoned():
    result = await detect("I don't want to learn Rust anymore.", ["Learn Rust"])
    assert result.status == GoalStatus.ABANDONED
    assert result.matched_existing_goal == "Learn Rust"


@pytest.mark.asyncio
async def test_existing_goal_blocked():
    result = await detect(
        "I'm trying to deploy it but the server keeps failing.",
        ["Deploy the application"],
    )
    assert result.status == GoalStatus.BLOCKED
    assert result.matched_existing_goal == "Deploy the application"


@pytest.mark.asyncio
async def test_existing_goal_changed():
    result = await detect(
        "I've decided to focus on the web version instead.", ["Build mobile app"]
    )
    assert result.status == GoalStatus.CHANGED
    assert result.matched_existing_goal == "Build mobile app"


@pytest.mark.asyncio
async def test_task_is_not_a_goal():
    # An isolated task must not become a new goal, and does not clearly
    # associate with the provided existing goals.
    result = await detect(
        "I need to fix the login button.", ["Build ChronOS", "Learn Python"]
    )
    assert result.status == GoalStatus.NONE
    assert result.items == []


@pytest.mark.asyncio
async def test_trivial_desire_is_not_a_goal():
    result = await detect("I want a coffee.", ["Build ChronOS"])
    assert result.status == GoalStatus.NONE
    assert result.items == []


@pytest.mark.asyncio
async def test_goal_and_user_state_stay_separate():
    # One input: PROBLEM_SOLVING intent + FRUSTRATED state + BLOCKED goal.
    content = "I'm frustrated because I'm stuck trying to finish ChronOS."

    goal = await detect(content, ["Build ChronOS"])
    assert goal.status == GoalStatus.BLOCKED
    assert goal.matched_existing_goal == "Build ChronOS"

    state_detector = UserStateDetector()
    user_input = UserInput(id="in_1d_sep", user_id="u", content=content)
    state_result = await state_detector.detect_state(user_input)
    assert state_result.emotional_state == UserEmotionState.FRUSTRATED


@pytest.mark.asyncio
async def test_engine_integrates_goal_analysis():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_1d_engine",
        content="I'm stuck on this bug and it's driving me crazy.",
        provider_key="chronos",
    )
    state = response.chronos_state
    assert state is not None
    assert state.goal_analysis is not None
    # The trace records the goal-detection step.
    assert any(
        "Detected goal relationship" in s
        for s in response.reasoning_trace.reasoning_steps
    )