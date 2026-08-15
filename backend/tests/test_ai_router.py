"""Phase 2A tests: deterministic AI router.

The AIRouter decides whether a ``ChronosState`` is sufficiently handled by the
deterministic engine (``FAST``) or would benefit from an AI model (``DEEP``).

Critical properties verified here:

* The router is deterministic and fully offline — it NEVER calls an LLM.
* Emotion alone never routes to AI: ``"I'm frustrated."`` is FAST.
* The decision surfaces on ``EngineResponse.ai_routing`` and in the reasoning
  trace, and serializes cleanly.
"""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.models import (
    IntentType,
    MemoryItem,
    MemoryType,
    PatternItem,
    RetrievedContext,
    UserInput,
)
from chronos_engine.routing import AIRouter, RoutingPath
from chronos_engine.state.models import (
    ChronosState,
    ContradictionResult,
    GoalAnalysisItem,
    GoalAnalysisResult,
    GoalStatus,
    IntentResult,
    UserCognitiveState,
    UserEmotionState,
    UserEnergy,
    UserStateResult,
)

router = AIRouter()


def mem(memory_id: str, content: str) -> MemoryItem:
    return MemoryItem(
        id=memory_id, user_id="user_2a", content=content, memory_type=MemoryType.LONG_TERM
    )


def make_state(
    content: str,
    *,
    intent: IntentResult = None,
    user_state: UserStateResult = None,
    goal_analysis=None,
    context=None,
    contradictions=None,
    patterns=None,
) -> ChronosState:
    return ChronosState(
        id="state_2a",
        user_id="user_2a",
        current_input=UserInput(id="in_2a", user_id="user_2a", content=content),
        intent=intent,
        user_state=user_state,
        goal_analysis=goal_analysis,
        context=context or RetrievedContext(),
        contradictions=contradictions or [],
        patterns=patterns or [],
    )


def intent_result(intent: IntentType, confidence: float = 0.8) -> IntentResult:
    return IntentResult(intent=intent, confidence=confidence, signals=["test"])


def neutral_state() -> UserStateResult:
    return UserStateResult(
        emotional_state=UserEmotionState.NEUTRAL,
        confidence=0.8,
        valence=0.0,
        energy=UserEnergy.MEDIUM,
        cognitive_state=UserCognitiveState.CLEAR,
    )


# ---------------------------------------------------------------------------
# Test 1 — Trivial factual question → FAST
# ---------------------------------------------------------------------------


def test_what_is_mongodb_routes_fast():
    state = make_state(
        "What is MongoDB?",
        intent=intent_result(IntentType.INFORMATION),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(status=GoalStatus.NONE, confidence=0.2),
    )

    result = router.route(state)

    assert result.path == RoutingPath.FAST
    assert result.use_ai is False
    assert "simple information request" in result.signals
    assert "historical reasoning" not in result.signals
    assert "MongoDB" not in result.reason


# ---------------------------------------------------------------------------
# Test 2 — Frustrated but resolvable → FAST (emotion alone is not DEEP)
# ---------------------------------------------------------------------------


def test_frustrated_stuck_routes_fast():
    state = make_state(
        "I'm so frustrated because I'm stuck on the ChronOS router.",
        intent=intent_result(IntentType.PROBLEM_SOLVING),
        user_state=UserStateResult(
            emotional_state=UserEmotionState.FRUSTRATED,
            confidence=0.75,
            valence=-0.6,
            cognitive_state=UserCognitiveState.UNCERTAIN,
            signals=["frustration language"],
        ),
        goal_analysis=GoalAnalysisResult(
            status=GoalStatus.BLOCKED, goal="Build ChronOS", confidence=0.7
        ),
        context=RetrievedContext(goals=["Build ChronOS"]),
    )

    result = router.route(state)

    assert result.path == RoutingPath.FAST
    assert result.use_ai is False
    # Strong emotional language alone must never escalate to AI.
    assert "historical reasoning" not in result.signals


# ---------------------------------------------------------------------------
# Test 3 — Simple status update → FAST
# ---------------------------------------------------------------------------


def test_simple_status_update_routes_fast():
    state = make_state(
        "I finished implementing the UserStateDetector.",
        intent=intent_result(IntentType.STATUS_UPDATE),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(status=GoalStatus.PROGRESS, confidence=0.8),
    )

    result = router.route(state)

    assert result.path == RoutingPath.FAST
    assert result.use_ai is False
    assert "simple status update" in result.signals
    assert "simple progress update" in result.signals


# ---------------------------------------------------------------------------
# Test 4 — Complex decision, single goal → DEEP
# ---------------------------------------------------------------------------

# Section 12: "Should I continue building ChronOS or focus on interview
# preparation?" is a complex decision, DEEP.


def test_complex_decision_routes_deep():
    state = make_state(
        "Should I continue building ChronOS or focus on interview preparation?",
        intent=intent_result(IntentType.DECISION),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(
            status=GoalStatus.ACTIVE, goal="Build ChronOS", confidence=0.7
        ),
        context=RetrievedContext(goals=["Build ChronOS"]),
    )

    result = router.route(state)

    assert result.path == RoutingPath.DEEP
    assert result.use_ai is True
    assert "complex decision" in result.signals
    assert "complex decision" in result.reason.lower()


# ---------------------------------------------------------------------------
# Test 5 — Ambiguous + historical → DEEP
# ---------------------------------------------------------------------------


def test_ambiguous_with_history_routes_deep():
    state = make_state(
        "Considering everything I've told you, what do you think?",
        intent=intent_result(IntentType.QUESTION),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(status=GoalStatus.NONE, confidence=0.2),
        context=RetrievedContext(
            goals=["Build ChronOS"],
            relevant_memories=[mem("m_1", "I am building ChronOS.")],
        ),
    )

    result = router.route(state)

    assert result.path == RoutingPath.DEEP
    assert result.use_ai is True
    assert "historical reasoning" in result.signals


# ---------------------------------------------------------------------------
# Test 6 — No memory/history, ambiguous → FAST
# ---------------------------------------------------------------------------


def test_ambiguous_no_history_routes_fast():
    state = make_state(
        "Interesting. What do you think?",
        intent=intent_result(IntentType.QUESTION),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(status=GoalStatus.NONE, confidence=0.2),
        context=RetrievedContext(),
    )

    result = router.route(state)

    assert result.path == RoutingPath.FAST
    assert result.use_ai is False


# ---------------------------------------------------------------------------
# Test 7 — Show my goals → FAST
# ---------------------------------------------------------------------------


def test_show_goals_routes_fast():
    state = make_state(
        "Show me my current goals.",
        intent=intent_result(IntentType.COMMAND),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(
            status=GoalStatus.ACTIVE, goal="Build ChronOS", confidence=0.8
        ),
        context=RetrievedContext(goals=["Build ChronOS", "Master orchestration"]),
    )

    result = router.route(state)

    assert result.path == RoutingPath.FAST
    assert result.use_ai is False
    assert "simple command" in result.signals


# ---------------------------------------------------------------------------
# Test 8 — "I'm frustrated." alone → FAST
# ---------------------------------------------------------------------------


def test_frustrated_alone_routes_fast():
    state = make_state(
        "I'm frustrated.",
        intent=intent_result(IntentType.EMOTIONAL_SUPPORT),
        user_state=UserStateResult(
            emotional_state=UserEmotionState.FRUSTRATED,
            confidence=0.8,
            valence=-0.7,
            signals=["frustration language"],
        ),
        goal_analysis=GoalAnalysisResult(status=GoalStatus.NONE, confidence=0.2),
        context=RetrievedContext(goals=["Build ChronOS"]),
    )

    result = router.route(state)

    assert result.path == RoutingPath.FAST
    assert result.use_ai is False


# ---------------------------------------------------------------------------
# Test 9 — Complex decision + multiple goals → DEEP
# ---------------------------------------------------------------------------

# Section 12: multiple goals + decision → DEEP, "nuanced reasoning across
# multiple goals".


def test_complex_decision_multiple_goals_routes_deep():
    state = make_state(
        "Should I continue building ChronOS or prepare for interviews?",
        intent=intent_result(IntentType.DECISION),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(
            status=GoalStatus.ACTIVE,
            goal="Build ChronOS",
            confidence=0.7,
            items=[
                GoalAnalysisItem(status=GoalStatus.ACTIVE, goal="Build ChronOS", confidence=0.7),
                GoalAnalysisItem(
                    status=GoalStatus.ACTIVE, goal="Prepare interviews", confidence=0.6
                ),
            ],
        ),
        context=RetrievedContext(
            goals=["Build ChronOS", "Prepare for interviews"],
        ),
    )

    result = router.route(state)

    assert result.path == RoutingPath.DEEP
    assert result.use_ai is True
    assert "complex decision" in result.signals
    assert "multiple relevant goals" in result.signals
    assert "multiple goals" in result.reason.lower()


# ---------------------------------------------------------------------------
# Test 10 — Goal change → FAST
# ---------------------------------------------------------------------------


def test_simple_goal_change_routes_fast():
    state = make_state(
        "I've decided to stop working on ChronOS.",
        intent=intent_result(IntentType.INFORMATION),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(
            status=GoalStatus.ABANDONED, goal="Build ChronOS", confidence=0.8
        ),
        contradictions=[
            ContradictionResult(
                type="GOAL_CHANGE",
                description="User dropped the ChronOS goal.",
                previous_value="ACTIVE",
                current_value="ABANDONED",
            )
        ],
        context=RetrievedContext(goals=["Build ChronOS"]),
    )

    result = router.route(state)

    assert result.path == RoutingPath.FAST
    assert result.use_ai is False
    assert "deterministic goal change" in result.signals


# ---------------------------------------------------------------------------
# Test 11 — Pattern analysis → DEEP
# ---------------------------------------------------------------------------


def test_pattern_analysis_routes_deep():
    state = make_state(
        "Why do I keep getting stuck on the same type of problem?",
        intent=intent_result(IntentType.REFLECTION),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(status=GoalStatus.NONE, confidence=0.2),
        context=RetrievedContext(
            goals=["Build ChronOS"],
            relevant_memories=[mem("m_1", "I got stuck on a problem before.")],
        ),
        patterns=[
            PatternItem(
                id="p_1",
                user_id="user_2a",
                category="recurring_problem",
                title="Repeated stuck problem",
                description="Keeps hitting the same kind of bug.",
            )
        ],
    )

    result = router.route(state)

    assert result.path == RoutingPath.DEEP
    assert result.use_ai is True
    assert "pattern analysis" in result.signals
    assert "pattern" in result.reason.lower()


# ---------------------------------------------------------------------------
# Test 12 — Router never invokes the LLM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_never_invokes_llm(monkeypatch):
    from chronos_engine.core.interfaces import BaseLLMProvider

    def boom(self, **kwargs):
        raise AssertionError("LLM must never be called during routing.")

    monkeypatch.setattr(BaseLLMProvider, "generate_response", boom)

    engine = ChronosEngine()
    # A DEEP-routed input must still produce an EngineResponse without the
    # LLM being touched. (Phase 2A: AI path is not wired up yet.)
    response = await engine.process_user_input(
        user_id="user_2a_llm",
        content="Should I continue building ChronOS or prepare for interviews?",
        provider_key="chronos",
    )

    assert response.ai_routing is not None
    assert response.ai_routing.use_ai is True
    assert response.ai_routing.path == RoutingPath.DEEP
    assert response.deterministic_response is not None


# ---------------------------------------------------------------------------
# Test 13 — Engine integration: ai_routing on EngineResponse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_engine_integration_ai_routing_field():
    engine = ChronosEngine()

    fast_response = await engine.process_user_input(
        user_id="user_2a_fast",
        content="What is MongoDB?",
        provider_key="chronos",
    )
    assert fast_response.ai_routing is not None
    assert fast_response.ai_routing.path == RoutingPath.FAST
    assert fast_response.ai_routing.use_ai is False
    assert any(
        "AI routing -> FAST" in s for s in fast_response.reasoning_trace.reasoning_steps
    )
    assert "AI Router" in fast_response.reasoning_trace.context_sources

    deep_response = await engine.process_user_input(
        user_id="user_2a_deep",
        content="Why do I keep getting stuck on the same type of problem?",
        provider_key="chronos",
    )
    assert deep_response.ai_routing is not None
    assert deep_response.ai_routing.path == RoutingPath.DEEP
    assert deep_response.ai_routing.use_ai is True
    assert any(
        "AI routing -> DEEP" in s for s in deep_response.reasoning_trace.reasoning_steps
    )

    # Serialization: ai_routing section present and valid.
    dumped = deep_response.model_dump(mode="json")
    assert "ai_routing" in dumped
    ai_json = dumped["ai_routing"]
    assert ai_json["path"] == "DEEP"
    assert ai_json["use_ai"] is True
    assert isinstance(ai_json["signals"], list)


# ---------------------------------------------------------------------------
# Test 14 — Determinism: identical states route identically
# ---------------------------------------------------------------------------


def test_router_is_deterministic():
    a = make_state(
        "Should I keep working on ChronOS?",
        intent=intent_result(IntentType.DECISION),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(status=GoalStatus.ACTIVE, confidence=0.7),
        context=RetrievedContext(goals=["Build ChronOS"]),
    )
    b = make_state(
        "Should I keep working on ChronOS?",
        intent=intent_result(IntentType.DECISION),
        user_state=neutral_state(),
        goal_analysis=GoalAnalysisResult(status=GoalStatus.ACTIVE, confidence=0.7),
        context=RetrievedContext(goals=["Build ChronOS"]),
    )

    assert router.route(a).model_dump() == router.route(b).model_dump()


# ---------------------------------------------------------------------------
# Test 15 — Emotional reflection with history → DEEP
# ---------------------------------------------------------------------------

# Section 12: "I'm frustrated because I've been stuck for a long time and keep
# facing the same problem" — emotional + historical + pattern → DEEP.


def test_frustration_plus_history_routes_deep():
    state = make_state(
        "I've been stuck for a long time and keep facing the same problem. "
        "Why does this keep happening?",
        intent=intent_result(IntentType.REFLECTION),
        user_state=UserStateResult(
            emotional_state=UserEmotionState.FRUSTRATED,
            confidence=0.75,
            valence=-0.6,
            cognitive_state=UserCognitiveState.UNCERTAIN,
            signals=["frustration language"],
        ),
        goal_analysis=GoalAnalysisResult(status=GoalStatus.NONE, confidence=0.2),
        context=RetrievedContext(
            goals=["Build ChronOS"],
            relevant_memories=[
                mem("m_1", "I got stuck on a problem before."),
            ],
        ),
        patterns=[
            PatternItem(
                id="p_1",
                user_id="user_2a",
                category="recurring_problem",
                title="Repeated stuck problem",
                description="Keeps hitting the same kind of bug.",
            )
        ],
    )

    result = router.route(state)

    assert result.path == RoutingPath.DEEP
    assert result.use_ai is True
    assert "historical reasoning" in result.signals or "pattern analysis" in result.signals
