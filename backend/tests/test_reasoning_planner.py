"""Phase 2D tests: ChronOS Reasoning Modes (CLASSIFY / INTERPRET / REASON /
REFLECT / GENERATE).

Covers the deterministic ``ReasoningPlanner`` (mode selection + minimum
sufficiency), the structured AI output contract (``AIReasoningResult``), the
robust parser with fallback, mode-gated prompt minimization, and the
guarantee that a DEEP request performs exactly one LLM call.
"""

import json

from chronos_engine import ChronosEngine
from chronos_engine.ai import (
    AIExecutionResult,
    AIExecutor,
    ChronosAIPromptBuilder,
    ReasoningMode,
    ReasoningPlan,
    ReasoningPlanner,
)
from chronos_engine.config import OllamaConfig
from chronos_engine.core.models import (
    IntentType,
    MemoryItem,
    PatternCategory,
    PatternItem,
    PromptContext,
    RetrievedContext,
    TimelineEvent,
    UserInput,
)
from chronos_engine.llm import LLMRegistry
from chronos_engine.llm.result import LLMResult
from chronos_engine.response.models import ChronosInterpretation, DeterministicResponse
from chronos_engine.routing import RoutingPath
from chronos_engine.routing.models import AIRoutingResult
from chronos_engine.state.models import (
    ChronosState,
    EngineStateResult,
    EngineStatus,
    GoalAnalysisItem,
    GoalAnalysisResult,
    GoalStatus,
    IntentResult,
    UserCognitiveState,
    UserEmotionState,
    UserStateResult,
)

DEEP_INPUT = (
    "Considering everything I've told you about ChronOS, "
    "do you think I should continue investing my time in it?"
)
FAST_INPUT = "What is Python?"


def ok_json(answer: str = "AI_2D_RESPONSE", **overrides) -> LLMResult:
    payload = {
        "interpretation": None,
        "reasoning": "ChronOS weighed the deterministic state.",
        "reflection": None,
        "answer": answer,
        "uncertainties": [],
        "evidence_used": [],
    }
    payload.update(overrides)
    return LLMResult(
        text=json.dumps(payload),
        provider="ollama",
        model="qwen3:4b",
        latency_ms=12.5,
        success=True,
    )


class FakeOllama:
    """Fake provider with the same surface the executor touches."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.generate_calls = []

    def provider_name(self) -> str:
        return "Ollama Local"

    async def generate(self, prompt_context, model_name: str = ""):
        self.generate_calls.append((prompt_context, model_name))
        if self.error is not None:
            raise self.error
        return self.result

    async def generate_response(self, prompt_context, model_name: str = ""):
        if self.error is not None:
            raise self.error
        return self.result.text if self.result else ""


class NoopExecutor:
    """Executor that returns a fallback without touching any provider."""

    async def execute(self, routing_result, chronos_state, deterministic_response):
        return AIExecutionResult(
            attempted=True,
            used=False,
            success=False,
            model="qwen3:4b",
            prompt_context=PromptContext(
                current_input=chronos_state.current_input,
                retrieved_context=chronos_state.context or RetrievedContext(),
                system_prompt="",
                user_prompt="",
            ),
            fallback_used=True,
            error_type="OLLAMA_UNAVAILABLE",
        )


def make_engine(provider, *, enabled=True):
    config = OllamaConfig(
        base_url="http://ollama:11434", model="qwen3:4b", timeout=2.0, enabled=enabled
    )
    registry = LLMRegistry()
    registry.register_provider("ollama", provider)
    executor = AIExecutor(llm_registry=registry, config=config)
    return ChronosEngine(ai_executor=executor, llm_registry=registry)


def core_state(state):
    """The deterministic-state slice that AI must never rewrite."""
    return {
        "intent": state.intent.model_dump() if state.intent else None,
        "user_state": state.user_state.model_dump() if state.user_state else None,
        "goal_analysis": state.goal_analysis.model_dump()
        if state.goal_analysis
        else None,
        "contradictions": [c.model_dump() for c in (state.contradictions or [])],
        "goals": state.goals,
        "patterns": [p.model_dump() for p in state.patterns],
        "engine_state": state.engine_state.model_dump() if state.engine_state else None,
        "confidence": state.confidence,
    }


# ---------------------------------------------------------------------------
# Planner unit helpers
# ---------------------------------------------------------------------------


def _state(
    content,
    *,
    intent=None,
    user_state=None,
    goal=None,
    context=None,
    contradictions=None,
    goals=None,
    patterns=None,
):
    return ChronosState(
        id="state_2d",
        user_id="user_2d",
        current_input=UserInput(
            id="inp_2d", user_id="user_2d", content=content
        ),
        intent=intent,
        user_state=user_state,
        goal_analysis=goal,
        context=context,
        contradictions=contradictions or [],
        goals=goals or [],
        patterns=patterns or [],
    )


def _routing(*signals) -> AIRoutingResult:
    return AIRoutingResult(
        use_ai=True,
        path=RoutingPath.DEEP,
        confidence=0.7,
        reason="test routing",
        signals=list(signals),
    )


def _deterministic(rendered: str = "Deterministic interpretation.") -> DeterministicResponse:
    return DeterministicResponse(
        user_signal="neutral",
        chronos_interpretation=ChronosInterpretation(
            user_state_summary="No strong signals.",
            intent_summary="Decision.",
            context_summary="No stored context.",
        ),
        chronos_state=EngineStateResult(
            status=EngineStatus.NEUTRAL, confidence=0.3, reason="test"
        ),
        rendered=rendered,
    )


# ---------------------------------------------------------------------------
# Test 1 — Simple interpretation: INTERPRET + GENERATE
# ---------------------------------------------------------------------------


def test_simple_interpretation_selects_interpret_and_generate():
    state = _state(
        "I'm frustrated because I'm stuck.",
        intent=IntentResult(intent=IntentType.EMOTIONAL_SUPPORT, confidence=0.8),
        user_state=UserStateResult(
            emotional_state=UserEmotionState.FRUSTRATED, confidence=0.7
        ),
    )
    plan = ReasoningPlanner().plan(state, _routing())

    assert plan.modes == [ReasoningMode.INTERPRET, ReasoningMode.GENERATE]
    assert plan.primary_mode == ReasoningMode.INTERPRET
    assert plan.modes[-1] == ReasoningMode.GENERATE


# ---------------------------------------------------------------------------
# Test 2 — Complex decision: REASON + GENERATE
# ---------------------------------------------------------------------------


def test_complex_decision_selects_reason_and_generate():
    state = _state(
        "Should I continue building ChronOS or focus on interviews?",
        intent=IntentResult(intent=IntentType.DECISION, confidence=0.8),
        goal=GoalAnalysisResult(
            status=GoalStatus.NEW,
            goal="Prepare for interviews",
            items=[
                GoalAnalysisItem(
                    status=GoalStatus.ACTIVE, goal="Build ChronOS", confidence=0.8
                ),
                GoalAnalysisItem(
                    status=GoalStatus.NEW, goal="Prepare for interviews", confidence=0.6
                ),
            ],
        ),
    )
    plan = ReasoningPlanner().plan(
        state, _routing("complex decision", "multiple relevant goals")
    )

    assert plan.modes == [ReasoningMode.REASON, ReasoningMode.GENERATE]
    assert plan.primary_mode == ReasoningMode.REASON
    assert ReasoningMode.INTERPRET not in plan.modes
    assert ReasoningMode.REFLECT not in plan.modes


# ---------------------------------------------------------------------------
# Test 3 — Historical reflection: REFLECT + GENERATE
# ---------------------------------------------------------------------------


def test_historical_reflection_selects_reflect_and_generate():
    state = _state(
        "How have my priorities changed over the last few months?",
        intent=IntentResult(intent=IntentType.REFLECTION, confidence=0.8),
    )
    plan = ReasoningPlanner().plan(
        state, _routing("reflection request", "historical reasoning")
    )

    assert plan.modes == [ReasoningMode.REFLECT, ReasoningMode.GENERATE]
    assert plan.primary_mode == ReasoningMode.REFLECT
    assert plan.requires_history is True


# ---------------------------------------------------------------------------
# Test 4 — Ambiguous classification: CLASSIFY + INTERPRET + GENERATE
# ---------------------------------------------------------------------------


def test_ambiguous_input_selects_classify_and_interpret():
    state = _state(
        "I don't even know what I'm trying to do anymore.",
        intent=IntentResult(intent=IntentType.UNKNOWN, confidence=0.2),
        user_state=UserStateResult(
            cognitive_state=UserCognitiveState.UNCERTAIN, confidence=0.6
        ),
    )
    plan = ReasoningPlanner().plan(state, _routing())

    assert plan.modes == [
        ReasoningMode.CLASSIFY,
        ReasoningMode.INTERPRET,
        ReasoningMode.GENERATE,
    ]
    assert plan.primary_mode == ReasoningMode.INTERPRET
    assert ReasoningMode.REASON not in plan.modes


# ---------------------------------------------------------------------------
# Test 5 — Minimal modes: GENERATE only
# ---------------------------------------------------------------------------


def test_minimal_plan_is_generate_only():
    state = _state(
        "What is Python?",
        intent=IntentResult(intent=IntentType.INFORMATION, confidence=0.9),
    )
    plan = ReasoningPlanner().plan(state, _routing())

    assert plan.modes == [ReasoningMode.GENERATE]
    assert plan.primary_mode == ReasoningMode.GENERATE
    assert plan.requires_context is False
    assert plan.requires_history is False
    assert plan.confidence == 0.45


# ---------------------------------------------------------------------------
# Test 6 — Missing history: reflection still flagged as history-dependent
# ---------------------------------------------------------------------------


def test_reflection_flags_requires_history_even_without_evidence():
    state = _state(
        "How have I changed over the past few months?",
        intent=IntentResult(intent=IntentType.REFLECTION, confidence=0.7),
    )
    plan = ReasoningPlanner().plan(state, _routing("reflection request"))

    assert ReasoningMode.REFLECT in plan.modes
    assert plan.requires_history is True


# ---------------------------------------------------------------------------
# Test 7 — Exactly one LLM call per DEEP request
# ---------------------------------------------------------------------------


async def test_deep_executes_exactly_one_llm_call():
    provider = FakeOllama(result=ok_json("AI_ONE_CALL"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2d_one_call", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.DEEP
    assert len(provider.generate_calls) == 1
    assert response.ai_execution.used is True
    plan = response.ai_execution.reasoning_plan
    assert plan is not None
    assert ReasoningMode.REASON in plan.modes
    assert ReasoningMode.REFLECT in plan.modes
    assert plan.modes[-1] == ReasoningMode.GENERATE


# ---------------------------------------------------------------------------
# Test 8 — No AI on FAST path
# ---------------------------------------------------------------------------


async def test_fast_path_never_plans_or_calls():
    provider = FakeOllama(result=ok_json())
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2d_fast", content=FAST_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.FAST
    assert provider.generate_calls == []
    assert response.ai_execution.attempted is False
    assert response.ai_execution.reasoning_plan is None
    assert response.ai_execution.ai_reasoning is None


# ---------------------------------------------------------------------------
# Test 9 — Structured output contract
# ---------------------------------------------------------------------------


async def test_structured_ai_reasoning_result():
    provider = FakeOllama(
        result=ok_json(
            answer="AI_STRUCTURED_ANSWER",
            interpretation="The user is weighing two priorities.",
            reasoning="ChronOS vs interviews; interviews are time-boxed.",
            uncertainties=["Interview timeline is unclear"],
        )
    )
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2d_structured", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_execution.used is True
    assert response.final_response == "AI_STRUCTURED_ANSWER"
    reasoning = response.ai_execution.ai_reasoning
    assert reasoning is not None
    assert reasoning.answer == "AI_STRUCTURED_ANSWER"
    assert reasoning.interpretation is not None
    assert reasoning.reasoning is not None
    assert isinstance(reasoning.uncertainties, list)
    assert reasoning.evidence_used == []

    dumped = response.model_dump(mode="json")
    assert dumped["ai_execution"]["ai_reasoning"]["answer"] == "AI_STRUCTURED_ANSWER"
    assert dumped["ai_execution"]["reasoning_plan"]["primary_mode"] in {
        m.value for m in ReasoningMode
    }
    assert any(
        "Reasoning plan ->" in s for s in response.reasoning_trace.reasoning_steps
    )


# ---------------------------------------------------------------------------
# Test 10 — Malformed JSON falls back
# ---------------------------------------------------------------------------


async def test_malformed_json_falls_back():
    provider = FakeOllama(
        result=LLMResult(
            text="this is not json", provider="ollama", model="qwen3:4b", success=True
        )
    )
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2d_malformed", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_execution.used is False
    assert response.ai_execution.fallback_used is True
    assert response.ai_execution.error_type == "MALFORMED_JSON"
    assert response.final_response == response.deterministic_response.rendered


# ---------------------------------------------------------------------------
# Test 11 — Hallucinated evidence falls back
# ---------------------------------------------------------------------------


async def test_hallucinated_evidence_falls_back():
    provider = FakeOllama(
        result=ok_json(evidence_used=["[memory:does_not_exist_123]"])
    )
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2d_halluc", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_execution.used is False
    assert response.ai_execution.fallback_used is True
    assert response.ai_execution.error_type == "HALLUCINATED_EVIDENCE"
    assert response.final_response == response.deterministic_response.rendered


# ---------------------------------------------------------------------------
# Test 12 — ChronosState is not mutated by AI reasoning
# ---------------------------------------------------------------------------


async def test_ai_reasoning_does_not_mutate_state():
    provider = FakeOllama(
        result=ok_json(answer="You should pivot to interviews and drop ChronOS.")
    )
    engine_a = make_engine(provider)

    response_a = await engine_a.process_user_input(
        user_id="user_2d_immut", content=DEEP_INPUT, provider_key="chronos"
    )

    engine_b = ChronosEngine(ai_executor=NoopExecutor())
    response_b = await engine_b.process_user_input(
        user_id="user_2d_immut", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response_a.ai_execution.used is True
    assert core_state(response_a.chronos_state) == core_state(response_b.chronos_state)


# ---------------------------------------------------------------------------
# Test 13 — Prompt minimization: mode-gated sections
# ---------------------------------------------------------------------------


def test_prompt_minimization_mode_gating():
    builder = ChronosAIPromptBuilder()
    state = _state(
        "Should I continue building ChronOS?",
        intent=IntentResult(intent=IntentType.DECISION, confidence=0.8),
        context=RetrievedContext(
            relevant_memories=[
                MemoryItem(
                    id="m1",
                    user_id="user_2d",
                    content="Working on ChronOS daily.",
                    importance_score=0.8,
                )
            ],
            timeline_events=[
                TimelineEvent(
                    id="t1",
                    user_id="user_2d",
                    title="Started ChronOS",
                    description="Began the engine build.",
                )
            ],
        ),
        patterns=[
            PatternItem(
                id="p1",
                user_id="user_2d",
                category=PatternCategory.RECURRING_PROBLEM,
                title="Scope creep",
                description="Starting new projects before finishing old ones.",
            )
        ],
    )

    reason_plan = ReasoningPlan(
        modes=[ReasoningMode.REASON, ReasoningMode.GENERATE],
        primary_mode=ReasoningMode.REASON,
        reason="decision",
        confidence=0.6,
        requires_context=True,
    )
    prompt = builder.build(state, _deterministic(), reason_plan)
    user_prompt = prompt.user_prompt
    assert "REASONING PLAN:" in user_prompt
    assert "USER STATE:" in user_prompt
    assert "GOAL ANALYSIS:" in user_prompt
    assert "CONSISTENCY:" in user_prompt
    assert "RELEVANT CONTEXT:" in user_prompt
    assert "[memory:m1]" in user_prompt
    assert "[timeline:t1]" in user_prompt
    assert "PATTERNS:" not in user_prompt
    assert "GOAL CHANGES:" not in user_prompt

    reflect_plan = ReasoningPlan(
        modes=[ReasoningMode.REFLECT, ReasoningMode.GENERATE],
        primary_mode=ReasoningMode.REFLECT,
        reason="reflection",
        confidence=0.6,
        requires_history=True,
        requires_context=True,
    )
    prompt_r = builder.build(state, _deterministic(), reflect_plan)
    user_prompt_r = prompt_r.user_prompt
    assert "PATTERNS:" in user_prompt_r
    assert "GOAL CHANGES:" in user_prompt_r
    assert "[pattern:p1]" in user_prompt_r
    assert "USER STATE:" not in user_prompt_r
    assert "GOAL ANALYSIS:" not in user_prompt_r

    generate_plan = ReasoningPlan(
        modes=[ReasoningMode.GENERATE],
        primary_mode=ReasoningMode.GENERATE,
        reason="generate",
        confidence=0.45,
    )
    prompt_g = builder.build(state, _deterministic(), generate_plan)
    user_prompt_g = prompt_g.user_prompt
    assert "USER STATE:" not in user_prompt_g
    assert "GOAL ANALYSIS:" not in user_prompt_g
    assert "RELEVANT CONTEXT:" not in user_prompt_g
    assert "PATTERNS:" not in user_prompt_g
    assert "OUTPUT FORMAT:" in user_prompt_g


def test_evidence_ids_returns_only_provided_evidence():
    builder = ChronosAIPromptBuilder()
    state = _state(
        "reflection",
        context=RetrievedContext(
            relevant_memories=[
                MemoryItem(
                    id="mem_a",
                    user_id="user_2d",
                    content="Stored memory.",
                    importance_score=0.7,
                )
            ]
        ),
        patterns=[
            PatternItem(
                id="pat_b",
                user_id="user_2d",
                category=PatternCategory.HABIT,
                title="Habit",
                description="A habit.",
            )
        ],
    )
    assert builder.evidence_ids(state) == {"mem_a", "pat_b"}


# ---------------------------------------------------------------------------
# Test 14 — End-to-end DEEP reasoning-plan trace
# ---------------------------------------------------------------------------


async def test_end_to_end_deep_reasoning_plan_trace():
    provider = FakeOllama(result=ok_json("AI_TRACE_ANSWER"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2d_trace", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.DEEP
    assert response.ai_execution.used is True
    assert any(
        "Reasoning plan ->" in s for s in response.reasoning_trace.reasoning_steps
    )
    plan_entry = next(
        (
            e
            for e in response.reasoning_trace.ai_execution_steps
            if e["step"] == "REASONING_PLAN"
        ),
        None,
    )
    assert plan_entry is not None
    assert "GENERATE" in plan_entry["modes"]
    assert plan_entry["primary_mode"] in {m.value for m in ReasoningMode}
    assert response.ai_execution.reasoning_plan is not None
    assert response.ai_execution.reasoning_plan.primary_mode.value == (
        plan_entry["primary_mode"]
    )