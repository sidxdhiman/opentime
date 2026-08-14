"""Phase 1C tests: deterministic UserStateDetector and engine integration."""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.models import IntentType, UserInput
from chronos_engine.state.models import (
    UserCognitiveState,
    UserEmotionState,
    UserEnergy,
)
from chronos_engine.user_state import UserStateDetector


def make_detector():
    return UserStateDetector()


async def detect(content: str):
    detector = make_detector()
    user_input = UserInput(id="in_1c", user_id="user_1c", content=content)
    return await detector.detect_state(user_input)


@pytest.mark.asyncio
async def test_frustration_detected():
    result = await detect("I'm stuck on this bug and it's driving me crazy.")
    assert result.emotional_state == UserEmotionState.FRUSTRATED
    assert result.confidence >= 0.4


@pytest.mark.asyncio
async def test_excitement_with_motivated_secondary():
    result = await detect("I'm really excited to finally ship this!")
    assert result.emotional_state == UserEmotionState.EXCITED
    assert UserEmotionState.MOTIVATED in result.secondary_states


@pytest.mark.asyncio
async def test_uncertainty_detected():
    result = await detect("I don't know which approach I should use.")
    assert result.emotional_state == UserEmotionState.UNCERTAIN


@pytest.mark.asyncio
async def test_tired_with_low_energy():
    result = await detect("I'm exhausted and can't focus anymore.")
    assert result.emotional_state == UserEmotionState.TIRED
    assert result.energy == UserEnergy.LOW


@pytest.mark.asyncio
async def test_positive_with_positive_valence():
    result = await detect("This worked perfectly. I'm really happy with the result.")
    assert result.emotional_state == UserEmotionState.POSITIVE
    assert result.valence is not None and result.valence > 0.0


@pytest.mark.asyncio
async def test_mixed_state_keeps_secondary_positive():
    result = await detect(
        "I'm frustrated with the bugs but I'm still excited to finish this."
    )
    assert result.emotional_state == UserEmotionState.FRUSTRATED
    assert UserEmotionState.EXCITED in result.secondary_states


@pytest.mark.asyncio
async def test_neutral_statement_is_neutral():
    result = await detect("The backend is running on port 9000.")
    assert result.emotional_state == UserEmotionState.NEUTRAL


@pytest.mark.asyncio
async def test_technical_statement_does_not_invent_emotion():
    # No emotional keywords: the detector must not fabricate an emotion or
    # assign confidence from nothing.
    result = await detect("The server binds to port 9000 and handles HTTP requests.")
    assert result.emotional_state == UserEmotionState.NEUTRAL
    assert result.confidence == 0.0
    assert result.signals == []


@pytest.mark.asyncio
async def test_urgency_is_elevated():
    result = await detect("I need this fixed ASAP. The deadline is today.")
    assert result.urgency is not None and result.urgency >= 0.5


@pytest.mark.asyncio
async def test_cognitive_confusion_detected():
    result = await detect("I'm confused about why this API is returning this error.")
    assert result.cognitive_state == UserCognitiveState.CONFUSED


@pytest.mark.asyncio
async def test_intent_and_state_stay_separate():
    # "Should I ..." -> DECISION intent; "frustrated" -> FRUSTRATED state. Both
    # are independent readings of the same input.
    reactor = ChronosEngine()
    response = await reactor.process_user_input(
        user_id="user_1c_sep",
        content="I'm frustrated. Should I abandon this project?",
        provider_key="chronos",
    )
    state = response.chronos_state
    assert state is not None
    assert state.intent is not None
    assert state.intent.intent == IntentType.DECISION
    assert state.user_state is not None
    assert state.user_state.emotional_state == UserEmotionState.FRUSTRATED


@pytest.mark.asyncio
async def test_engine_integrates_user_state():
    reactor = ChronosEngine()
    response = await reactor.process_user_input(
        user_id="user_1c_engine",
        content="I'm stuck on this bug and it's driving me crazy. I don't get it.",
        provider_key="chronos",
    )
    state = response.chronos_state
    assert state is not None
    assert state.intent is not None
    assert state.user_state is not None

    # The reasoning trace records the user-state detection step.
    assert any(
        "Detected user interaction state" in s
        for s in response.reasoning_trace.reasoning_steps
    )