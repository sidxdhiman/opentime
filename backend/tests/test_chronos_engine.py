import pytest
from chronos_engine import ChronosEngine
from chronos_engine.core.models import InputType


@pytest.mark.asyncio
async def test_chronos_engine_full_lifecycle():
    engine = ChronosEngine()
    user_id = "test_user_42"

    # Seed state
    await engine.seed_initial_state(user_id)

    # 1. Process Text Input
    response = await engine.process_user_input(
        user_id=user_id,
        content="I want to transition from early research into shipping ChronOS v1.0 engine.",
        input_type="text",
        provider_key="chronos",
    )

    assert response is not None
    assert response.user_id == user_id
    assert "ChronOS" in response.final_response
    assert response.reasoning_trace.confidence_score > 0.5
    assert len(response.reasoning_trace.reasoning_steps) >= 4

    # 2. Test Audio Input Processing
    audio_response = await engine.process_user_input(
        user_id=user_id,
        content="Recording audio note about goal alignment and emotional sentiment.",
        input_type="audio",
        file_name="thought_log.webm",
        provider_key="chronos",
    )

    assert audio_response.original_input.input_type == InputType.AUDIO
    assert audio_response.original_input.file_name == "thought_log.webm"

    # 3. Memory System Inspection
    memories = await engine.get_memories(user_id)
    assert len(memories) >= 5

    # 4. Timeline Engine Inspection
    timeline = await engine.get_timeline(user_id)
    assert len(timeline) >= 4

    # 5. Identity Profile Evolution Inspection
    identity = await engine.get_identity(user_id)
    assert identity.user_id == user_id
    assert len(identity.interests) > 0
    assert len(identity.goals) > 0

    # 6. Reflection Engine Inspection
    reflections = await engine.get_reflections(user_id)
    assert len(reflections) >= 2
    assert reflections[0].confidence_score > 0.7

    # 7. Pattern Detection Inspection
    patterns = await engine.get_patterns(user_id)
    assert len(patterns) >= 2

    # 8. Model-Agnostic LLM Provider Swap Test
    openai_resp = await engine.process_user_input(
        user_id=user_id,
        content="Evaluating model-agnostic LLM swapping capability.",
        input_type="text",
        provider_key="openai",
        model_name="gpt-4o",
    )
    assert "OpenAI" in openai_resp.provider_name or "OpenAI" in openai_resp.final_response
