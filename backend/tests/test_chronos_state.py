"""Phase 1A tests: ChronosState construction and engine integration."""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.models import InputType, RetrievedContext, UserInput
from chronos_engine.state import ChronosState, StateBuilder


@pytest.mark.asyncio
async def test_build_state_from_input_and_context():
    """ChronosState can be assembled from a valid UserInput + RetrievedContext."""
    builder = StateBuilder()
    user_input = UserInput(
        id="in_1a_test",
        user_id="user_1a",
        input_type=InputType.TEXT,
        content="I want to build ChronOS into a real reasoning engine.",
    )
    context = RetrievedContext(
        life_phase="Active System Execution",
        goals=["Build ChronOS v2"],
        recent_changes=["Evolving goal: Build ChronOS v2"],
    )

    state = await builder.build(user_input, context)

    assert state.id.startswith("state_")
    assert state.user_id == "user_1a"
    assert state.current_input.content == "I want to build ChronOS into a real reasoning engine."
    assert state.current_input.input_type == InputType.TEXT
    assert state.context is not None
    assert state.context.life_phase == "Active System Execution"
    assert state.context.goals == ["Build ChronOS v2"]
    assert state.goals == ["Build ChronOS v2"]


@pytest.mark.asyncio
async def test_optional_sections_can_be_empty():
    """Sections without detectors yet must default to empty, not fabricated."""
    builder = StateBuilder()
    user_input = UserInput(id="in_1a_empty", user_id="user_empty", content="")
    empty_context = RetrievedContext()

    state = await builder.build(user_input, empty_context)

    assert state.intent is None
    assert state.user_state is None
    assert state.engine_state is None
    assert state.confidence is None
    assert state.contradictions == []
    assert state.patterns == []
    assert state.goals == []
    assert state.context is not None

    # A bare ChronosState with only the required fields is also constructible.
    bare = ChronosState(id="state_manual", user_id="user_empty", current_input=user_input)
    assert bare.context is None
    assert bare.intent is None
    assert bare.user_state is None
    assert bare.contradictions == []


@pytest.mark.asyncio
async def test_existing_engine_processing_still_succeeds():
    """The existing pipeline must keep working with the state inserted."""
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_1a_engine",
        content="Testing that the existing pipeline still runs.",
        provider_key="chronos",
    )

    assert response is not None
    assert response.final_response
    assert response.chronos_state is not None
    assert (
        response.chronos_state.current_input.content
        == "Testing that the existing pipeline still runs."
    )
    assert response.chronos_state.user_id == "user_1a_engine"


@pytest.mark.asyncio
async def test_engine_response_existing_fields_unchanged():
    """All pre-existing EngineResponse fields must still be present."""
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_1a_fields",
        content="Checking the response contract is unchanged.",
        provider_key="chronos",
    )

    assert response.id.startswith("resp_")
    assert response.user_id == "user_1a_fields"
    assert response.original_input is not None
    assert isinstance(response.raw_llm_response, str)
    assert isinstance(response.final_response, str) and response.final_response
    assert response.provider_name
    assert response.model_name
    assert response.prompt_context is not None
    assert response.reasoning_trace is not None
    assert response.validation_result is not None
    assert response.processing_time_ms >= 0
    assert response.timestamp is not None

    # The trace now records that the state was constructed.
    assert any("ChronosState" in s for s in response.reasoning_trace.reasoning_steps)


@pytest.mark.asyncio
async def test_chronos_state_does_not_break_serialization():
    """model_dump (the wire format used by the API) must include the new field."""
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_1a_serialize",
        content="Serialization must keep working with chronos_state present.",
        provider_key="chronos",
    )

    dumped = response.model_dump(mode="json")

    assert "chronos_state" in dumped
    state = dumped["chronos_state"]
    assert state is not None
    assert state["user_id"] == "user_1a_serialize"
    assert state["current_input"]["content"] == (
        "Serialization must keep working with chronos_state present."
    )
    assert "intent" in state and state["intent"] is None
    assert "user_state" in state and state["user_state"] is None
    assert "context" in state and state["context"] is not None
    assert "goals" in state and isinstance(state["goals"], list)
    assert "patterns" in state and isinstance(state["patterns"], list)
    assert "contradictions" in state and state["contradictions"] == []
