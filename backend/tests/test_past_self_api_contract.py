"""Phase 4C tests: Past-Self moment API contract and data flow.

Verifies that the structured PastSelfConversationMoment reaches the
frontend through the EngineResponse serialization, that non-qualifying
moments do not surface, that AI reflection is optional, and that no raw
internal IDs leak into user-facing display fields.
"""

from chronos_engine.core.models import (
    EngineResponse,
    PromptContext,
    ReasoningTrace,
    UserInput,
    ValidationResult,
)
from chronos_engine.state.models import ChronosState, RetrievedContext
from chronos_engine.temporal.models import (
    PastSelfConversationMoment,
    PastSelfPerspective,
    PastSelfQuestionType,
    TemporalComparisonRelation,
    TemporalReflectionResult,
)

USER = "user_4c"


# ── Helpers ─────────────────────────────────────────────────────────────


def _make_moment(*, should_surface: bool = True, **kwargs) -> PastSelfConversationMoment:
    defaults = dict(
        attempted=True,
        should_surface=should_surface,
        thread_id="thread_abc123",
        perspective=PastSelfPerspective.PAST_TO_PRESENT,
        question_type=PastSelfQuestionType.OUTCOME_REVEAL,
        relation=TemporalComparisonRelation.CHANGED,
        opening="Earlier, you were weighing this.",
        context='Earlier in this story: "I don\'t know if I should leave my job."',
        bridge="Since then, things have shifted.",
        question='How do you feel about "Leave my job" now?',
        confidence=0.75,
        reason="Genuine transition detected",
    )
    defaults.update(kwargs)
    return PastSelfConversationMoment(**defaults)


def _make_reflection(
    *, used: bool = True, success: bool = True, reflection: str = ""
) -> TemporalReflectionResult:
    return TemporalReflectionResult(
        attempted=True,
        used=used,
        success=success,
        reflection=reflection,
        tier="LIGHT",
        provider="ollama",
        model="qwen2.5:1.5b",
    )


def _make_response(past_self: PastSelfConversationMoment | None = None,
                   reflection: TemporalReflectionResult | None = None) -> EngineResponse:
    user_input = UserInput(id="in_4c", user_id=USER, content="test")
    state = ChronosState(
        id="state_4c",
        user_id=USER,
        current_input=user_input,
        past_self_conversation=past_self,
        temporal_reflection=reflection,
    )
    final = "Your response text."
    if past_self and past_self.should_surface:
        final += "\n\nSOMETHING FROM YOUR PAST\n\n" + past_self.opening
    return EngineResponse(
        id="resp_4c",
        user_id=USER,
        original_input=user_input,
        raw_llm_response="raw",
        final_response=final,
        provider_name="chronos",
        model_name="test",
        prompt_context=PromptContext(
            current_input=user_input,
            retrieved_context=RetrievedContext(),
            system_prompt="sys",
            user_prompt="usr",
        ),
        reasoning_trace=ReasoningTrace(),
        validation_result=ValidationResult(is_valid=True, validated_response="ok"),
        chronos_state=state,
        processing_time_ms=10.0,
    )


# ── Tests ───────────────────────────────────────────────────────────────


class TestPastSelfApiContract:
    """Verify the structured moment is present in the serialized response."""

    def test_qualifying_moment_in_serialized_response(self):
        moment = _make_moment(should_surface=True)
        resp = _make_response(past_self=moment)
        data = resp.model_dump()

        assert "chronos_state" in data
        cs = data["chronos_state"]
        assert cs is not None
        psc = cs["past_self_conversation"]
        assert psc is not None
        assert psc["should_surface"] is True
        assert psc["opening"] == "Earlier, you were weighing this."
        assert "I don't know if I should leave my job" in psc["context"]
        assert psc["question"] == 'How do you feel about "Leave my job" now?'

    def test_non_qualifying_moment_not_surfaceable(self):
        moment = _make_moment(should_surface=False, opening="", context="", bridge="", question="")
        resp = _make_response(past_self=moment)
        data = resp.model_dump()

        psc = data["chronos_state"]["past_self_conversation"]
        assert psc["should_surface"] is False
        assert psc["opening"] == ""
        assert psc["question"] == ""

    def test_no_moment_at_all(self):
        resp = _make_response(past_self=None)
        data = resp.model_dump()

        assert data["chronos_state"]["past_self_conversation"] is None

    def test_reflection_present_when_successful(self):
        moment = _make_moment()
        refl = _make_reflection(used=True, success=True, reflection="A quiet observation.")
        resp = _make_response(past_self=moment, reflection=refl)
        data = resp.model_dump()

        tr = data["chronos_state"]["temporal_reflection"]
        assert tr is not None
        assert tr["used"] is True
        assert tr["reflection"] == "A quiet observation."

    def test_reflection_absent_when_not_attempted(self):
        moment = _make_moment()
        resp = _make_response(past_self=moment, reflection=None)
        data = resp.model_dump()

        tr = data["chronos_state"]["temporal_reflection"]
        assert tr is None

    def test_reflection_failure_preserves_deterministic_moment(self):
        moment = _make_moment()
        refl = _make_reflection(used=False, success=False, reflection="")
        resp = _make_response(past_self=moment, reflection=refl)
        data = resp.model_dump()

        psc = data["chronos_state"]["past_self_conversation"]
        assert psc["should_surface"] is True
        assert psc["opening"] == "Earlier, you were weighing this."
        tr = data["chronos_state"]["temporal_reflection"]
        assert tr["used"] is False
        assert tr["reflection"] == ""

    def test_no_thread_id_in_user_facing_moment(self):
        moment = _make_moment(thread_id="thread_secret123")
        resp = _make_response(past_self=moment)
        data = resp.model_dump()

        psc = data["chronos_state"]["past_self_conversation"]
        # thread_id is in the structured data but should NOT appear in
        # user-facing text fields
        for field in ("opening", "context", "bridge", "question"):
            assert "thread_secret123" not in psc[field], f"{field} leaked thread_id"

    def test_final_response_contains_flat_section_when_surfacing(self):
        moment = _make_moment(should_surface=True)
        resp = _make_response(past_self=moment)
        assert "SOMETHING FROM YOUR PAST" in resp.final_response

    def test_final_response_omits_flat_section_when_not_surfacing(self):
        moment = _make_moment(should_surface=False)
        resp = _make_response(past_self=moment)
        assert "SOMETHING FROM YOUR PAST" not in resp.final_response

    def test_structured_fields_match_engine_output(self):
        moment = _make_moment(
            opening="Open text",
            context="Context text",
            bridge="Bridge text",
            question="Question text",
        )
        resp = _make_response(past_self=moment)
        data = resp.model_dump()
        psc = data["chronos_state"]["past_self_conversation"]

        assert psc["opening"] == "Open text"
        assert psc["context"] == "Context text"
        assert psc["bridge"] == "Bridge text"
        assert psc["question"] == "Question text"
