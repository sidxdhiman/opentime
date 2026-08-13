"""Phase 1B tests: deterministic IntentDetector and engine integration."""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.models import IntentType
from chronos_engine.intent import IntentDetector


@pytest.mark.asyncio
async def test_what_is_mongodb_is_information_not_question():
    """A definition ask must beat the generic question signal."""
    detector = IntentDetector()
    result = await detector.detect_intent("What is MongoDB?")

    assert result.intent == IntentType.INFORMATION
    assert result.confidence == 0.85
    assert any("definition" in s for s in result.signals)


@pytest.mark.asyncio
async def test_should_i_is_decision():
    detector = IntentDetector()
    result = await detector.detect_intent("Should I buy this laptop?")

    assert result.intent == IntentType.DECISION
    assert result.confidence == 0.85


@pytest.mark.asyncio
async def test_plan_is_planning():
    detector = IntentDetector()
    result = await detector.detect_intent("Help me plan my study schedule.")

    assert result.intent == IntentType.PLANNING
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_crashing_and_fix_is_problem_solving():
    detector = IntentDetector()
    result = await detector.detect_intent("My application keeps crashing. How do I fix it?")

    assert result.intent == IntentType.PROBLEM_SOLVING
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_create_a_is_creation():
    detector = IntentDetector()
    result = await detector.detect_intent("Create a Python function that calculates tax.")

    assert result.intent == IntentType.CREATION
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_how_have_i_changed_is_reflection():
    detector = IntentDetector()
    result = await detector.detect_intent("How have I changed over the last few months?")

    assert result.intent == IntentType.REFLECTION
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_finished_and_now_working_is_status_update():
    detector = IntentDetector()
    result = await detector.detect_intent(
        "I finished the backend and I'm now working on the frontend."
    )

    assert result.intent == IntentType.STATUS_UPDATE
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_overwhelmed_is_emotional_support():
    detector = IntentDetector()
    result = await detector.detect_intent("I feel overwhelmed and I don't know what to do.")

    assert result.intent == IntentType.EMOTIONAL_SUPPORT
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_short_acknowledgement_is_unknown():
    """No signals matched -> below MIN_SCORE -> UNKNOWN with zero confidence."""
    detector = IntentDetector()
    result = await detector.detect_intent("Interesting.")

    assert result.intent == IntentType.UNKNOWN
    assert result.confidence == 0.0
    assert result.signals == []


@pytest.mark.asyncio
async def test_frustration_with_should_is_decision_not_emotion():
    """Intent must not be confused with emotion: frustrated + 'should I' is DECISION."""
    detector = IntentDetector()
    result = await detector.detect_intent("I'm frustrated. Should I abandon this project?")

    assert result.intent == IntentType.DECISION
    assert result.confidence == 0.85
    assert not any("emotion" in s or "frustrat" in s.lower() for s in result.signals)


@pytest.mark.asyncio
async def test_empty_and_bare_inputs_are_unknown():
    detector = IntentDetector()

    empty = await detector.detect_intent("")
    bare = await detector.detect_intent("...")

    assert empty.intent == IntentType.UNKNOWN
    assert empty.confidence == 0.0
    assert bare.intent == IntentType.UNKNOWN
    assert bare.confidence == 0.0
    assert bare.signals == []


@pytest.mark.asyncio
async def test_case_and_whitespace_insensitive():
    detector = IntentDetector()
    result = await detector.detect_intent("  SHOULD WE hire more people?  ")

    assert result.intent == IntentType.DECISION
    assert result.confidence == 0.85


@pytest.mark.asyncio
async def test_engine_integrates_intent_into_state():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_1b_intent",
        content="Should I buy this laptop?",
        provider_key="chronos",
    )

    assert response.chronos_state is not None
    assert response.chronos_state.intent is not None
    assert response.chronos_state.intent.intent == IntentType.DECISION
    assert response.chronos_state.intent.confidence == 0.85

    # The reasoning trace records the detected intent.
    assert any(
        "Detected user intent 'DECISION'" in s
        for s in response.reasoning_trace.reasoning_steps
    )


@pytest.mark.asyncio
async def test_unknown_input_also_integrates_into_state():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_1b_unknown",
        content="Interesting.",
        provider_key="chronos",
    )

    assert response.chronos_state is not None
    assert response.chronos_state.intent is not None
    assert response.chronos_state.intent.intent == IntentType.UNKNOWN
    assert response.chronos_state.intent.confidence == 0.0
