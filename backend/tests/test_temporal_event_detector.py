"""Phase 3B tests: deterministic temporal event detection.

Covers the required detection cases, the significance filter, mixed-input
primary-type selection, grounded descriptions, evidence-based confidence,
reuse of existing ChronOS detector output, memory linking, and the additive
engine integration. Detection only — no threads, no matching, no
persistence, no AI.
"""

import pytest

from chronos_engine import ChronosEngine
from chronos_engine.core.interfaces import BaseTemporalEventDetector
from chronos_engine.core.models import InputType, RetrievedContext, UserInput
from chronos_engine.goals.service import GoalDetector
from chronos_engine.state.builder import StateBuilder
from chronos_engine.state.models import (
    GoalStatus,
    UserEmotionState,
    UserStateResult,
)
from chronos_engine.storage import InMemoryTemporalStore
from chronos_engine.temporal.detector import TemporalEventDetector
from chronos_engine.temporal.models import (
    TemporalEventDetectionResult,
    TemporalType,
)


async def detect(content: str, **kwargs):
    detector = TemporalEventDetector()
    user_input = UserInput(id="in_3b", user_id="user_3b", content=content)
    return await detector.detect_temporal_event(user_input, **kwargs)


# ── Required detection cases ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decision_deliberation_detected():
    result = await detect("I'm thinking about leaving my job.")
    assert result.detected
    assert result.event.temporal_type is TemporalType.DECISION


@pytest.mark.asyncio
async def test_college_start_detected_as_life_event():
    # Documented rule: a concrete life-transition noun ("college") elevates
    # the input to LIFE_EVENT even when anchored to a future time marker.
    result = await detect("I start college next month.")
    assert result.detected
    assert result.event.temporal_type is TemporalType.LIFE_EVENT


@pytest.mark.asyncio
async def test_fear_of_failure_detected():
    result = await detect("I'm scared I'll fail my exams.")
    assert result.detected
    assert result.event.temporal_type is TemporalType.FEAR


@pytest.mark.asyncio
async def test_settled_decision_detected():
    result = await detect("I've decided to pursue an MBA.")
    assert result.detected
    assert result.event.temporal_type is TemporalType.DECISION


@pytest.mark.asyncio
async def test_milestone_detected():
    result = await detect("I graduated today.")
    assert result.detected
    assert result.event.temporal_type is TemporalType.MILESTONE


@pytest.mark.asyncio
async def test_belief_detected():
    result = await detect("I believe freedom matters more than money.")
    assert result.detected
    assert result.event.temporal_type is TemporalType.BELIEF


# ── Significance filter rejections ───────────────────────────────────────


@pytest.mark.asyncio
async def test_trivial_bodily_state_rejected():
    result = await detect("I'm hungry.")
    assert not result.detected
    assert result.event is None


@pytest.mark.asyncio
async def test_informational_question_rejected():
    result = await detect("What is Python?")
    assert not result.detected
    assert result.event is None


@pytest.mark.asyncio
async def test_task_command_rejected():
    result = await detect("Fix the login button.")
    assert not result.detected
    assert result.event is None


@pytest.mark.asyncio
async def test_empty_and_whitespace_input_safe():
    for content in ["", "   "]:
        result = await detect(content)
        assert not result.detected
        assert result.event is None
        assert result.reason == "Empty input"


@pytest.mark.asyncio
async def test_weak_ambiguous_input_conservatively_rejected():
    result = await detect("I watched a movie yesterday.")
    assert not result.detected
    assert result.event is None
    assert result.reason  # rejection is explained honestly


# ── Mixed inputs: one input -> zero or one event ─────────────────────────


@pytest.mark.asyncio
async def test_mixed_input_single_event_with_deterministic_primary():
    content = "I'm scared to leave my job, but I think I'm going to do it."
    first = await detect(content)
    second = await detect(content)

    assert first.detected
    assert first.event is not None  # exactly one event, never multiple

    # Deterministic primary selection across runs.
    assert first.event.temporal_type is second.event.temporal_type
    assert first.confidence == second.confidence
    assert first.signals == second.signals

    # Primary reflects the resolved commitment; fear remains recorded.
    assert first.event.temporal_type is TemporalType.DECISION
    assert any("FEAR" in signal for signal in first.signals)


@pytest.mark.asyncio
async def test_flagship_past_self_example_detected_as_decision():
    """The canonical ChronOS past moment must be recognized."""
    result = await detect("I don't know if I should leave my job.")
    assert result.detected
    assert result.event.temporal_type is TemporalType.DECISION


@pytest.mark.asyncio
async def test_direct_interrogative_resolves_to_question():
    """A direct crossroads question is QUESTION primary; decision language
    may still appear as secondary evidence."""
    result = await detect("Should I leave my job?")
    assert result.detected
    assert result.event.temporal_type is TemporalType.QUESTION


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("I'll be working abroad soon.", TemporalType.FUTURE_EXPECTATION),
        ("I promise myself I won't give up.", TemporalType.PROMISE),
        ("I think this job will make me miserable.", TemporalType.PREDICTION),
        ("I actually left my job.", TemporalType.LIFE_EVENT),
        ("I got accepted into college.", TemporalType.LIFE_EVENT),
    ],
)
@pytest.mark.asyncio
async def test_remaining_vocabulary(content, expected):
    result = await detect(content)
    assert result.detected
    assert result.event.temporal_type is expected


# ── Description grounding ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_description_grounded_in_strongest_sentence():
    """Multi-sentence input: the pizza sentence is ignored; the description
    comes from the sentence carrying the decision evidence."""
    result = await detect("I had pizza today. I've decided to pursue an MBA.")
    assert result.detected
    assert result.event.description == "I've decided to pursue an MBA."
    assert result.event.description not in ("I had pizza today.",)


@pytest.mark.asyncio
async def test_description_is_normalized_not_invented():
    result = await detect("I graduated today")
    assert result.event.description == "I graduated today."


# ── Confidence & metadata ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confidence_bounded_and_evidence_based():
    strong = await detect("I've decided to pursue an MBA.")
    weak = await detect("I decided to move out.")

    for result in (strong, weak):
        assert 0 < result.confidence <= 0.95
        assert 0 < result.event.importance <= 1.0

    # More matched evidence yields higher (or equal) deterministic confidence.
    assert strong.confidence >= weak.confidence


@pytest.mark.asyncio
async def test_memory_id_linked_when_available():
    result = await detect("I graduated today.", memory_id="mem_abc123")
    assert result.event.memory_id == "mem_abc123"


@pytest.mark.asyncio
async def test_detected_event_has_no_thread_until_matching_exists():
    """Phase 3B never creates or links threads — thread_id stays empty."""
    result = await detect("I graduated today.")
    assert result.event.thread_id is None


@pytest.mark.asyncio
async def test_detection_persists_nothing():
    """Detection writes nowhere: no storage attribute, dormant store untouched."""
    detector = TemporalEventDetector()
    assert not hasattr(detector, "storage")

    store = InMemoryTemporalStore()
    user_input = UserInput(id="in_3b", user_id="user_3b", content="I graduated today.")
    await detector.detect_temporal_event(user_input, memory_id="mem_x")

    assert await store.get_threads_by_user("user_3b") == []
    assert await store.get_snapshots_by_user("user_3b") == []


# ── Reuse of existing ChronOS evidence ───────────────────────────────────


@pytest.mark.asyncio
async def test_goal_evidence_reused_from_goal_detector():
    """A NEW-goal analysis from the existing GoalDetector provides GOAL
    evidence without duplicating goal classification."""
    content = "I'm working toward becoming a doctor."
    user_input = UserInput(id="in_3b", user_id="user_3b", content=content)

    goal_analysis = await GoalDetector().detect_goals(user_input, [])
    assert goal_analysis.status is GoalStatus.NEW

    without_evidence = await TemporalEventDetector().detect_temporal_event(user_input)
    with_evidence = await TemporalEventDetector().detect_temporal_event(
        user_input, goal_analysis=goal_analysis
    )

    # Existing detector evidence makes the difference — support strengthens,
    # it cannot fabricate from nothing.
    assert not without_evidence.detected
    assert with_evidence.detected
    assert with_evidence.event.temporal_type is TemporalType.GOAL


@pytest.mark.asyncio
async def test_anxious_user_state_alone_cannot_create_fear():
    user_state = UserStateResult(emotional_state=UserEmotionState.ANXIOUS, confidence=0.9)
    result = await detect(
        "This whole situation with my job keeps me up at night.",
        user_state=user_state,
    )
    assert not result.detected


# ── Additive state integration ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_chronos_state_defaults_to_no_temporal_detection():
    user_input = UserInput(id="in_3b", user_id="user_3b", content="hello")
    state = await StateBuilder().build(user_input, RetrievedContext())
    assert state.temporal_event_detection is None


@pytest.mark.asyncio
async def test_state_builder_passes_detection_through():
    user_input = UserInput(id="in_3b", user_id="user_3b", content="x")
    detection = TemporalEventDetectionResult(reason="passthrough")
    state = await StateBuilder().build(
        user_input, RetrievedContext(), temporal_event_detection=detection
    )
    assert state.temporal_event_detection is detection


# ── Engine integration (no user-facing behavior change) ─────────────────


@pytest.mark.asyncio
async def test_engine_attaches_detection_and_links_memory():
    engine = ChronosEngine()
    user_id = "user_3b_engine"

    response = await engine.process_user_input(
        user_id=user_id,
        content="I'm thinking about leaving my job.",
        input_type=InputType.TEXT.value,
        provider_key="chronos",
    )

    detection = response.chronos_state.temporal_event_detection
    assert detection is not None
    assert detection.detected
    assert detection.event.temporal_type is TemporalType.DECISION

    # Memory linking: the current interaction's memory ID is attached safely.
    memories = await engine.get_memories(user_id)
    memory_ids = {m.id for m in memories}
    assert detection.event.memory_id in memory_ids

    # Honest reasoning trace step.
    assert any(
        "Temporal event detection -> DECISION" in step
        for step in response.reasoning_trace.reasoning_steps
    )

    # Existing response behavior intact.
    assert response.final_response
    assert response.user_id == user_id


@pytest.mark.asyncio
async def test_engine_reports_honest_none_for_low_significance_input():
    engine = ChronosEngine()
    response = await engine.process_user_input(
        user_id="user_3b_engine_quiet",
        content="What is Python?",
        input_type=InputType.TEXT.value,
        provider_key="chronos",
    )
    detection = response.chronos_state.temporal_event_detection
    assert detection is not None
    assert not detection.detected
    assert detection.event is None
    assert any(
        "Temporal event detection -> NONE" in step
        for step in response.reasoning_trace.reasoning_steps
    )


@pytest.mark.asyncio
async def test_detector_injection_via_dependency_injection():
    class StubTemporalDetector(BaseTemporalEventDetector):
        async def detect_temporal_event(self, user_input, **kwargs):
            return TemporalEventDetectionResult(reason="stub detector")

    engine = ChronosEngine(temporal_event_detector=StubTemporalDetector())
    response = await engine.process_user_input(
        user_id="user_3b_stub",
        content="I graduated today.",
        input_type=InputType.TEXT.value,
        provider_key="chronos",
    )
    assert response.chronos_state.temporal_event_detection.reason == "stub detector"
