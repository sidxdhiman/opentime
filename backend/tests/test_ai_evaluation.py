"""Phase 2E tests: AI evaluation + latency optimization.

Covers:

* Deterministic evaluation fixtures (``fixtures/ai_evaluation/cases.json``)
  asserting mode selection and prompt content as PROPERTIES, never exact
  wording (LLM output is naturally variable).
* AI latency instrumentation: every DEEP stage is measured with monotonic
  timing; prompt size and a labeled token estimate are recorded.
* Mode-specific context (section 6) and bounded evidence (section 8).
* Hallucination guardrails (section 18): invented evidence ids are rejected,
  the goal in the prompt is grounded, and inferred emotions stay cautious.
"""

import json
from pathlib import Path

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.ai import (
    AIExecutor,
    AIResponseParseError,
    AIResponseParser,
    ChronosAIPromptBuilder,
    ContextBudget,
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

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ai_evaluation"


# ---------------------------------------------------------------------------
# Fixture loading + state construction
# ---------------------------------------------------------------------------


def load_cases():
    with open(FIXTURE_DIR / "cases.json", encoding="utf-8") as f:
        return json.load(f)["cases"]


def _user_state(case):
    us = case.get("user_state")
    if not us:
        return None
    return UserStateResult(
        emotional_state=(
            UserEmotionState(us["emotional_state"])
            if us.get("emotional_state")
            else None
        ),
        cognitive_state=(
            UserCognitiveState(us["cognitive_state"])
            if us.get("cognitive_state")
            else None
        ),
        confidence=us.get("confidence", 0.6),
    )


def _goal(case):
    if case.get("goal"):
        g = case["goal"]
        return GoalAnalysisResult(
            status=GoalStatus(g["status"]), goal=g["goal"], confidence=0.8
        )
    if case.get("goal_items"):
        items = [
            GoalAnalysisItem(
                status=GoalStatus(i["status"]), goal=i["goal"], confidence=0.8
            )
            for i in case["goal_items"]
        ]
        return GoalAnalysisResult(
            status=items[0].status,
            goal=items[0].goal,
            confidence=items[0].confidence,
            items=items,
        )
    return None


def _patterns(case):
    return [
        PatternItem(
            id=f"p{i + 1}",
            user_id="user_ev",
            category=PatternCategory[p["name"]],
            title=p["title"],
            description=p["description"],
        )
        for i, p in enumerate(case.get("patterns", []))
    ]


def build_state(case) -> ChronosState:
    memories = [
        MemoryItem(
            id=f"m{i + 1}",
            user_id="user_ev",
            content=text,
            importance_score=0.8,
        )
        for i, text in enumerate(case.get("context_memories", []))
    ]
    context = (
        RetrievedContext(relevant_memories=memories)
        if memories
        else RetrievedContext()
    )
    goals = (
        [i["goal"] for i in case["goal_items"]]
        if case.get("goal_items")
        else ([case["goal"]["goal"]] if case.get("goal") else [])
    )
    intent = (
        IntentResult(intent=IntentType(case["intent"]), confidence=0.8)
        if case.get("intent")
        else None
    )
    return ChronosState(
        id="state_ev",
        user_id="user_ev",
        current_input=UserInput(
            id="inp_ev", user_id="user_ev", content=case["input"]
        ),
        intent=intent,
        user_state=_user_state(case),
        goal_analysis=_goal(case),
        context=context,
        patterns=_patterns(case),
        goals=goals,
    )


def _routing(*signals) -> AIRoutingResult:
    return AIRoutingResult(
        use_ai=True,
        path=RoutingPath.DEEP,
        confidence=0.7,
        reason="evaluation fixture",
        signals=list(signals),
    )


def deterministic(rendered: str = "Deterministic interpretation.") -> DeterministicResponse:
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
# Engine harness (fake provider — no real Ollama needed)
# ---------------------------------------------------------------------------


def ok_json(answer: str = "AI_2E_RESPONSE", **overrides) -> LLMResult:
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
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.generate_calls = []

    def provider_name(self):
        return "Ollama Local"

    async def generate(self, prompt_context, model_name: str = "", inference_options=None):
        self.generate_calls.append((prompt_context, model_name, inference_options))
        if self.error is not None:
            raise self.error
        return self.result

    async def generate_response(self, prompt_context, model_name: str = ""):
        if self.error is not None:
            raise self.error
        return self.result.text if self.result else ""


def make_engine(provider, *, enabled=True):
    config = OllamaConfig(
        base_url="http://ollama:11434", model="qwen3:4b", timeout=2.0, enabled=enabled
    )
    registry = LLMRegistry()
    registry.register_provider("ollama", provider)
    executor = AIExecutor(llm_registry=registry, config=config)
    return ChronosEngine(ai_executor=executor, llm_registry=registry)


# ---------------------------------------------------------------------------
# Evaluation fixtures (property-based, section 16/17)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", load_cases(), ids=[c["id"] for c in load_cases()])
def test_evaluation_case_modes_and_prompt(case):
    state = build_state(case)
    plan = ReasoningPlanner().plan(state, _routing(*case.get("routing_signals", [])))

    modes = {m for m in plan.modes}
    for expected in case["expected_modes"]:
        assert ReasoningMode(expected) in modes
    assert ReasoningMode.GENERATE in modes

    prompt = ChronosAIPromptBuilder().build(state, deterministic(), plan).user_prompt
    for concept in case["expected_prompt_concepts"]:
        assert concept in prompt


# ---------------------------------------------------------------------------
# Latency + prompt-size instrumentation (sections 2/3/4/11)
# ---------------------------------------------------------------------------


async def test_deep_execution_records_latency_breakdown_and_prompt_size():
    provider = FakeOllama(result=ok_json("AI_MEASURED"))
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2e_latency", content=DEEP_INPUT, provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.DEEP
    assert len(provider.generate_calls) == 1
    ai = response.ai_execution
    assert ai.used is True

    assert ai.prompt_chars is not None and ai.prompt_chars > 0
    assert ai.prompt_tokens_estimate is not None and ai.prompt_tokens_estimate > 0
    assert ai.prompt_context_hash is not None and len(ai.prompt_context_hash) == 16
    assert ai.reasoning_plan_ms is not None and ai.reasoning_plan_ms >= 0
    assert ai.prompt_build_ms is not None and ai.prompt_build_ms >= 0
    assert ai.provider_latency_ms is not None and ai.provider_latency_ms >= 0
    assert ai.parse_ms is not None and ai.parse_ms >= 0
    assert ai.validation_ms is not None and ai.validation_ms >= 0
    assert ai.total_ai_ms is not None and ai.total_ai_ms >= 0

    report = ai.latency_report()
    assert report["prompt_chars"] == ai.prompt_chars
    assert report["prompt_tokens_estimate"] == ai.prompt_tokens_estimate
    assert report["total_ai_ms"] == ai.total_ai_ms
    assert report["provider_latency_ms"] == ai.provider_latency_ms
    assert response.reasoning_trace.ai_execution_steps[-1]["step"] == "AI_LATENCY"


async def test_disabled_path_records_plan_and_prompt_build():
    provider = FakeOllama(result=ok_json())
    engine = make_engine(provider, enabled=False)

    response = await engine.process_user_input(
        user_id="user_2e_disabled", content=DEEP_INPUT, provider_key="chronos"
    )

    ai = response.ai_execution
    assert ai.fallback_used is True
    assert ai.error_type == "LLMDisabledError"
    assert ai.reasoning_plan_ms is not None and ai.reasoning_plan_ms >= 0
    assert ai.prompt_build_ms is not None and ai.prompt_build_ms >= 0
    assert ai.prompt_chars is not None and ai.prompt_chars > 0
    assert ai.total_ai_ms is not None and ai.total_ai_ms >= 0


async def test_fast_path_has_no_ai_timing():
    provider = FakeOllama(result=ok_json())
    engine = make_engine(provider)

    response = await engine.process_user_input(
        user_id="user_2e_fast", content="What is Python?", provider_key="chronos"
    )

    assert response.ai_routing.path == RoutingPath.FAST
    ai = response.ai_execution
    assert ai.attempted is False
    assert ai.total_ai_ms is None
    assert ai.prompt_chars is None
    assert ai.prompt_context_hash is None


# ---------------------------------------------------------------------------
# Mode-specific context + evidence budget (sections 6/7/8)
# ---------------------------------------------------------------------------


def test_context_budget_bounds_evidence():
    memories = [
        MemoryItem(id=f"m{i}", user_id="u", content=f"Memory {i}", importance_score=0.8)
        for i in range(1, 8)
    ]
    timeline = [
        TimelineEvent(id=f"t{i}", user_id="u", title=f"Event {i}", description=f"Desc {i}")
        for i in range(1, 5)
    ]
    state = ChronosState(
        id="s",
        user_id="u",
        current_input=UserInput(id="i", user_id="u", content="Should I continue ChronOS?"),
        intent=IntentResult(intent=IntentType.DECISION, confidence=0.8),
        goal=GoalAnalysisResult(status=GoalStatus.ACTIVE, goal="Build ChronOS", confidence=0.8),
        context=RetrievedContext(relevant_memories=memories, timeline_events=timeline),
    )
    plan = ReasoningPlanner().plan(state, _routing("complex decision"))
    budget = ContextBudget(max_memories=2, max_timeline_events=1, max_patterns=0)
    builder = ChronosAIPromptBuilder()

    ctx = builder.context_for(state, plan, budget=budget)
    assert len(ctx.memory_excerpts) == 2
    assert len(ctx.timeline_excerpts) == 1
    assert ctx.evidence_ids == {"m1", "m2", "m3", "m4", "m5", "m6", "m7", "t1", "t2", "t3", "t4"}

    prompt = builder.build(state, deterministic(), plan, budget=budget).user_prompt
    assert "[memory:m1" in prompt
    assert "[memory:m2" in prompt
    assert "[memory:m3" not in prompt
    assert "[timeline:t1" in prompt
    assert "[timeline:t2" not in prompt


def test_classify_gets_no_historical_context():
    state = ChronosState(
        id="s",
        user_id="u",
        current_input=UserInput(id="i", user_id="u", content="I don't even know what I want."),
        intent=IntentResult(intent=IntentType.UNKNOWN, confidence=0.2),
        context=RetrievedContext(
            relevant_memories=[
                MemoryItem(id="m1", user_id="u", content="Old memory.", importance_score=0.8)
            ]
        ),
    )
    plan = ReasoningPlanner().plan(state, _routing())
    assert ReasoningMode.CLASSIFY in plan.modes

    prompt = ChronosAIPromptBuilder().build(state, deterministic(), plan).user_prompt
    assert "RELEVANT CONTEXT:" not in prompt
    assert "[memory:m1" not in prompt
    assert "USER STATE:" in prompt  # minimal user state is allowed


def test_reason_does_not_include_patterns_unless_reflect():
    state = ChronosState(
        id="s",
        user_id="u",
        current_input=UserInput(id="i", user_id="u", content="Should I continue ChronOS?"),
        intent=IntentResult(intent=IntentType.DECISION, confidence=0.8),
        context=RetrievedContext(
            relevant_memories=[
                MemoryItem(id="m1", user_id="u", content="Building ChronOS.", importance_score=0.8)
            ]
        ),
        patterns=[
            PatternItem(
                id="p1",
                user_id="u",
                category=PatternCategory.RECURRING_PROBLEM,
                title="Scope creep",
                description="Starting new projects before finishing old ones.",
            )
        ],
    )
    builder = ChronosAIPromptBuilder()

    reason_plan = ReasoningPlanner().plan(state, _routing("complex decision"))
    prompt_reason = builder.build(state, deterministic(), reason_plan).user_prompt
    assert "RELEVANT CONTEXT:" in prompt_reason
    assert "[memory:m1" in prompt_reason
    assert "PATTERNS:" not in prompt_reason
    assert "[pattern:p1" not in prompt_reason

    reflect_plan = ReasoningPlan(
        modes=[ReasoningMode.REFLECT, ReasoningMode.GENERATE],
        primary_mode=ReasoningMode.REFLECT,
        reason="r",
        confidence=0.6,
        requires_history=True,
    )
    prompt_reflect = builder.build(state, deterministic(), reflect_plan).user_prompt
    assert "PATTERNS:" in prompt_reflect
    assert "[pattern:p1" in prompt_reflect


# ---------------------------------------------------------------------------
# Hallucination guardrails (section 18)
# ---------------------------------------------------------------------------


def test_invented_historical_evidence_rejected():
    state = build_state(
        {
            "input": "reflect",
            "context_memories": ["Memory one.", "Memory two."],
        }
    )
    allowed = ChronosAIPromptBuilder().evidence_ids(state)
    assert allowed == {"m1", "m2"}

    parser = AIResponseParser()
    response = json.dumps(
        {
            "interpretation": None,
            "reasoning": None,
            "reflection": "A fabricated memory.",
            "answer": "Based on memory 999...",
            "uncertainties": [],
            "evidence_used": ["[memory:memory_999]"],
        }
    )
    with pytest.raises(AIResponseParseError) as exc_info:
        parser.parse(response, allowed_evidence_ids=allowed)
    assert exc_info.value.reason == "HALLUCINATED_EVIDENCE"


def test_invented_goal_is_grounded_in_prompt():
    state = build_state(
        {
            "input": "Should I continue ChronOS?",
            "intent": "DECISION",
            "goal": {"status": "ACTIVE", "goal": "Build ChronOS"},
            "routing_signals": ["complex decision"],
        }
    )
    plan = ReasoningPlanner().plan(state, _routing("complex decision"))
    built = ChronosAIPromptBuilder().build(state, deterministic(), plan)

    assert "Build ChronOS" in built.user_prompt
    assert "do not invent" in built.system_prompt.lower()
    assert "a suggestion is never certainty" in built.system_prompt
    # The deterministic gate against fabricated claims is evidence validation:
    # the model may only cite ids that actually exist in the state. This state
    # has no memories/patterns, so there is nothing it is allowed to cite.
    assert ChronosAIPromptBuilder().evidence_ids(state) == set()