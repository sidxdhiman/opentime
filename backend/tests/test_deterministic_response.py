"""Phase 1F tests: deterministic ResponseGenerator and engine integration.

The ResponseGenerator turns a structured ``ChronosState`` into a concise,
human-readable interpretation using only templates and rules — no LLM, no
network. These tests verify the interpretation content, the operational-state
rules, and the absence of fabrication.
"""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.models import (
    IntentType,
    MemoryItem,
    MemoryType,
    RetrievedContext,
    UserInput,
)
from chronos_engine.goals import GoalDetector
from chronos_engine.intent import IntentDetector
from chronos_engine.response import ResponseGenerator
from chronos_engine.state import StateBuilder
from chronos_engine.state.models import (
    ChronosState,
    ContradictionResult,
    EngineStatus,
    GoalAnalysisResult,
    GoalStatus,
    IntentResult,
    UserCognitiveState,
    UserEmotionState,
    UserEnergy,
    UserStateResult,
)
from chronos_engine.user_state import UserStateDetector


def mem(memory_id: str, content: str) -> MemoryItem:
    return MemoryItem(
        id=memory_id, user_id="user_1f", content=content, memory_type=MemoryType.LONG_TERM
    )


def make_state(
    content: str,
    *,
    intent: IntentResult,
    user_state,
    goal_analysis=None,
    context=None,
    contradictions=None,
    patterns=None,
) -> ChronosState:
    return ChronosState(
        id="state_1f",
        user_id="user_1f",
        current_input=UserInput(id="in_1f", user_id="user_1f", content=content),
        intent=intent,
        user_state=user_state,
        goal_analysis=goal_analysis,
        context=context or RetrievedContext(),
        contradictions=contradictions or [],
        patterns=patterns or [],
    )


# ---------------------------------------------------------------------------
# Test 1 — Frustrated blocked goal
# ---------------------------------------------------------------------------


def test_frustrated_blocked_goal():
    state = make_state(
        "I'm frustrated because I'm stuck trying to finish ChronOS.",
        intent=IntentResult(
            intent=IntentType.PROBLEM_SOLVING,
            confidence=0.8,
            signals=["is stuck on a problem"],
        ),
        user_state=UserStateResult(
            emotional_state=UserEmotionState.FRUSTRATED,
            confidence=0.75,
            valence=-0.6,
            cognitive_state=UserCognitiveState.UNCERTAIN,
            signals=["frustration language", "blocked language"],
        ),
        goal_analysis=GoalAnalysisResult(
            status=GoalStatus.BLOCKED,
            goal="Build ChronOS",
            confidence=0.7,
            signals=["blocked language"],
        ),
        context=RetrievedContext(
            goals=["Build ChronOS"],
            relevant_memories=[mem("m_1", "I am building ChronOS.")],
        ),
    )

    response = ResponseGenerator().generate(state)

    assert response.chronos_state.status == EngineStatus.CONCERNED
    assert "frustrat" in response.user_signal.lower()
    assert "solve a problem" in response.chronos_interpretation.intent_summary.lower()
    assert response.chronos_interpretation.goal_summary is not None
    assert "chronos" in response.chronos_interpretation.goal_summary.lower()
    assert "blocked" in response.chronos_interpretation.goal_summary.lower()
    assert response.suggested_next_step is not None
    assert "blocker" in response.suggested_next_step.lower()
    assert "concerned" in response.rendered.lower()


# ---------------------------------------------------------------------------
# Test 2 — Positive progress
# ---------------------------------------------------------------------------


def test_positive_progress():
    state = make_state(
        "I finally finished the first version of ChronOS!",
        intent=IntentResult(
            intent=IntentType.STATUS_UPDATE,
            confidence=0.85,
            signals=["reports what was finished"],
        ),
        user_state=UserStateResult(
            emotional_state=UserEmotionState.RELIEVED,
            confidence=0.5,
            valence=0.3,
            energy=UserEnergy.HIGH,
            signals=["relief language"],
        ),
        goal_analysis=GoalAnalysisResult(
            status=GoalStatus.COMPLETED,
            goal="Build ChronOS v1",
            confidence=0.8,
            signals=["completion language"],
        ),
        context=RetrievedContext(
            goals=["Build ChronOS v1"],
            relevant_memories=[mem("m_2", "Working toward ChronOS v1.")],
        ),
    )

    response = ResponseGenerator().generate(state)

    assert response.chronos_state.status in (EngineStatus.POSITIVE, EngineStatus.CONFIDENT)
    assert "relief" in response.user_signal.lower() or "positive" in response.user_signal.lower()
    assert response.chronos_interpretation.goal_summary is not None
    assert "completion" in response.chronos_interpretation.goal_summary.lower()
    assert response.suggested_next_step is not None
    assert "progress" in response.suggested_next_step.lower()


# ---------------------------------------------------------------------------
# Test 3 — Uncertain decision
# ---------------------------------------------------------------------------


def test_uncertain_decision_with_context_is_cautious():
    state = make_state(
        "I'm not sure whether I should use PostgreSQL or MongoDB.",
        intent=IntentResult(
            intent=IntentType.DECISION,
            confidence=0.8,
            signals=["asks for a recommendation"],
        ),
        user_state=UserStateResult(
            emotional_state=UserEmotionState.UNCERTAIN,
            cognitive_state=UserCognitiveState.UNCERTAIN,
            confidence=0.6,
            signals=["uncertainty language"],
        ),
        context=RetrievedContext(
            goals=["Build the data layer"],
            relevant_memories=[mem("m_3", "I want to build the data layer.")],
        ),
    )

    response = ResponseGenerator().generate(state)

    assert "decision" in response.chronos_interpretation.intent_summary.lower()
    assert "uncertain" in response.user_signal.lower()
    assert response.chronos_state.status in (
        EngineStatus.CAUTIOUS,
        EngineStatus.WAITING_FOR_CONTEXT,
    )
    assert response.suggested_next_step is not None
    assert "clarify" in response.suggested_next_step.lower()


def test_uncertain_decision_without_context_waits():
    state = make_state(
        "I'm not sure whether I should use PostgreSQL or MongoDB.",
        intent=IntentResult(intent=IntentType.DECISION, confidence=0.8, signals=[]),
        user_state=UserStateResult(
            emotional_state=UserEmotionState.UNCERTAIN,
            confidence=0.6,
            signals=["uncertainty language"],
        ),
        context=RetrievedContext(),
    )

    response = ResponseGenerator().generate(state)

    assert response.chronos_state.status == EngineStatus.WAITING_FOR_CONTEXT
    assert "more context" in response.suggested_next_step.lower()


# ---------------------------------------------------------------------------
# Test 4 — Goal change
# ---------------------------------------------------------------------------


def test_goal_change():
    state = make_state(
        "I've decided to focus on the web version instead.",
        intent=IntentResult(
            intent=IntentType.DECISION,
            confidence=0.65,
            signals=["discusses a decision"],
        ),
        user_state=UserStateResult(
            cognitive_state=UserCognitiveState.DECISIVE,
            confidence=0.3,
            signals=["decision language"],
        ),
        goal_analysis=GoalAnalysisResult(
            status=GoalStatus.CHANGED,
            goal="Build mobile app",
            matched_existing_goal="Build mobile app",
            confidence=0.7,
            signals=["direction change language"],
        ),
        contradictions=[
            ContradictionResult(
                type="GOAL_CHANGE",
                description=(
                    "The current input indicates the previously stored goal "
                    "'Build mobile app' has changed direction."
                ),
                previous_value="Build mobile app",
                current_value="Changed direction from: Build mobile app",
                confidence=0.75,
            )
        ],
        context=RetrievedContext(
            goals=["Build mobile app"],
            relevant_memories=[mem("m_4", "I want to build a mobile app.")],
        ),
    )

    response = ResponseGenerator().generate(state)

    combined = (
        (response.chronos_interpretation.goal_summary or "")
        + " "
        + " ".join(response.observations)
    ).lower()
    assert "change" in combined
    assert "direction" in combined
    assert response.chronos_state.status == EngineStatus.CAUTIOUS
    assert "confirm" in response.suggested_next_step.lower()


# ---------------------------------------------------------------------------
# Test 5 — No context, no fabrication
# ---------------------------------------------------------------------------


def test_no_context_no_fabrication():
    state = make_state(
        "Interesting.",
        intent=IntentResult(intent=IntentType.UNKNOWN, confidence=0.0, signals=[]),
        user_state=None,
        context=RetrievedContext(),
    )

    response = ResponseGenerator().generate(state)

    assert response.chronos_state.status == EngineStatus.WAITING_FOR_CONTEXT
    assert response.chronos_interpretation.goal_summary is None
    assert response.chronos_interpretation.pattern_summary is None
    assert response.chronos_interpretation.consistency_summary is None
    ctx_text = response.chronos_interpretation.context_summary.lower()
    assert "no significant historical context" in ctx_text
    assert "not yet confident" in response.chronos_interpretation.intent_summary.lower()
    assert "more context" in response.suggested_next_step.lower()


# ---------------------------------------------------------------------------
# Test 6 — Neutral technical input
# ---------------------------------------------------------------------------


def test_neutral_technical_input():
    state = make_state(
        "The backend is running on port 9000.",
        intent=IntentResult(intent=IntentType.UNKNOWN, confidence=0.0, signals=[]),
        user_state=UserStateResult(
            emotional_state=UserEmotionState.NEUTRAL, confidence=0.0, valence=0.0
        ),
        context=RetrievedContext(),
    )

    response = ResponseGenerator().generate(state)

    assert response.chronos_state.status == EngineStatus.NEUTRAL
    assert response.chronos_interpretation.goal_summary is None
    assert response.chronos_interpretation.consistency_summary is None
    assert "frustrat" not in response.user_signal.lower()
    assert "happy" not in response.user_signal.lower()
    assert response.observations == []


# ---------------------------------------------------------------------------
# Acceptance — AI completely off (no engine, no LLM, no network)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_off_full_deterministic_pipeline():
    user_input = UserInput(
        id="in_ai_off",
        user_id="user_ai_off",
        content="I'm frustrated because I'm stuck trying to finish ChronOS.",
    )
    intent = await IntentDetector().detect_intent(user_input.content)
    user_state = await UserStateDetector().detect_state(user_input, intent=intent)
    goal_analysis = await GoalDetector().detect_goals(user_input, ["Build ChronOS"])
    context = RetrievedContext(
        goals=["Build ChronOS"],
        relevant_memories=[mem("m_ai", "I want to build ChronOS.")],
    )
    state = await StateBuilder().build(
        user_input,
        context,
        intent=intent,
        user_state=user_state,
        goal_analysis=goal_analysis,
    )

    response = ResponseGenerator().generate(state)

    assert intent.intent == IntentType.PROBLEM_SOLVING
    assert user_state.emotional_state == UserEmotionState.FRUSTRATED
    assert goal_analysis.status == GoalStatus.BLOCKED
    assert response.chronos_state.status == EngineStatus.CONCERNED
    assert "frustrat" in response.user_signal.lower()
    assert "blocked" in (response.chronos_interpretation.goal_summary or "").lower()
    assert "blocker" in response.suggested_next_step.lower()
    assert "Concer" in response.rendered


# ---------------------------------------------------------------------------
# Test 7 — Full engine integration + serialization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_engine_integration():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_1f_engine",
        content="I'm frustrated because I'm stuck trying to finish ChronOS.",
        provider_key="chronos",
    )

    assert response.deterministic_response is not None
    dr = response.deterministic_response
    assert dr.chronos_state.status == EngineStatus.CONCERNED
    assert dr.chronos_state.confidence > 0.5
    assert dr.chronos_state.reason
    assert response.chronos_state is not None

    # Pre-existing EngineResponse fields remain intact.
    assert response.final_response
    assert response.provider_name
    assert response.model_name
    assert response.prompt_context is not None
    assert response.reasoning_trace is not None
    assert response.validation_result is not None

    # Reasoning trace records the deterministic step with ai_used: False.
    assert any("ai_used: False" in s for s in response.reasoning_trace.reasoning_steps)
    assert "Response Generator" in response.reasoning_trace.context_sources

    # Serialization: all three sections present and valid.
    dumped = response.model_dump(mode="json")
    assert "deterministic_response" in dumped
    dr_json = dumped["deterministic_response"]
    assert dr_json["chronos_state"]["status"] == "CONCERNED"
    assert dr_json["user_signal"]
    assert isinstance(dr_json["observations"], list)
    assert dumped["chronos_state"] is not None
    assert dumped["final_response"]


@pytest.mark.asyncio
async def test_empty_engine_input_still_generates_response():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_1f_empty",
        content="Interesting.",
        provider_key="chronos",
    )

    assert response.deterministic_response is not None
    dr = response.deterministic_response
    assert dr.chronos_state.status in (
        EngineStatus.WAITING_FOR_CONTEXT,
        EngineStatus.UNCERTAIN,
        EngineStatus.CAUTIOUS,
    )
    assert dr.chronos_interpretation.goal_summary is None
