"""Phase 4F tests: Active temporal thread context.

Verifies the active-thread-context feature end-to-end:
  - API boundary resolution, ownership, and bounding
  - Engine invariants (no AI force, no event creation, no lifecycle mutation)
  - Serialization contract (context survives model_dump round-trip)
  - User input remains authoritative
  - Context reaches ChronosState and DEEP prompt during processing
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from chronos_engine.core.models import (
    EngineResponse,
    PromptContext,
    ReasoningTrace,
    RetrievedContext,
    UserInput,
    ValidationResult,
)
from chronos_engine.engine import ChronosEngine
from chronos_engine.storage import InMemoryStorageAdapter, InMemoryTemporalStore
from chronos_engine.temporal.models import (
    ActiveTemporalContext,
    ActiveTemporalEvent,
    TemporalEvent,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)
from opentime.main import app
from tests.conftest import AUTH_USER_ID, OTHER_AUTH_USER_ID

# Authenticated engine API endpoints resolve the user from the bearer token,
# so the API tests in this module run with get_current_user overridden to
# AUTH_USER_ID. Stored data keyed by USER_F is therefore the authenticated
# user's own data.
pytestmark = pytest.mark.usefixtures("override_auth")

USER_F = AUTH_USER_ID
OTHER_F = OTHER_AUTH_USER_ID
BASE = datetime(2026, 1, 1, tzinfo=UTC)
PREFIX = "/api/v1/chronos/engine"


# ── Helpers ─────────────────────────────────────────────────────────────


async def _make_thread(
    store, subject, status=TemporalThreadStatus.OPEN,
    ttype=TemporalType.DECISION, user_id=USER_F,
):
    t = TemporalThread(
        user_id=user_id, subject=subject,
        status=status, temporal_type=ttype,
    )
    return await store.save_thread(t)


async def _make_event(
    store, thread_id, description, occurred_at,
    ttype=TemporalType.DECISION, user_id=USER_F,
):
    e = TemporalEvent(
        thread_id=thread_id, user_id=user_id,
        description=description, temporal_type=ttype,
        occurred_at=occurred_at,
    )
    return await store.save_event(e)


def _patch_engine(store: InMemoryTemporalStore):
    """Return a context manager that patches the global engine_instance."""
    engine = ChronosEngine(
        storage=InMemoryStorageAdapter(),
        temporal_store=store,
    )
    return patch(
        "chronos_engine.api.router.engine_instance", engine
    )


# ── 1. Request without active thread behaves exactly as before ──────────


class TestNoActiveThread:
    """Requests without active_thread_id are unaffected."""

    async def test_process_json_without_thread(self):
        store = InMemoryTemporalStore()
        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "Hello ChronOS",
                        "input_type": "text",
                    },
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["active_thread_context"] is None

    async def test_process_multipart_without_thread(self):
        store = InMemoryTemporalStore()
        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process",
                    data={
                        "content": "Hello via form",
                        "input_type": "text",
                        "provider_key": "chronos",
                    },
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["active_thread_context"] is None


# ── 2. Valid active thread is loaded and passed as grounded context ─────


class TestActiveThreadLoaded:
    """A valid thread ID produces a grounded context in the response."""

    async def test_valid_thread_produces_context(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Should I leave my job?")
        await _make_event(
            store, t.id, "I am thinking about quitting.",
            BASE + timedelta(days=30),
        )
        await _make_event(
            store, t.id, "I finally left my job.",
            BASE + timedelta(days=90),
        )

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "Thinking about my career",
                        "active_thread_id": t.id,
                    },
                )
            assert resp.status_code == 200
            ctx = resp.json()["active_thread_context"]
            assert ctx is not None
            assert ctx["thread_id"] == t.id
            assert ctx["subject"] == "Should I leave my job?"
            assert ctx["temporal_type"] == "DECISION"
            assert len(ctx["recent_events"]) == 2
            # Events are chronological (earliest first)
            assert ctx["recent_events"][0]["description"] == (
                "I am thinking about quitting."
            )
            assert ctx["recent_events"][1]["description"] == (
                "I finally left my job."
            )


# ── 3. Unknown thread ID fails safely ──────────────────────────────────


class TestUnknownThread:
    """A non-existent thread ID returns 404."""

    async def test_unknown_thread_id_returns_404(self):
        store = InMemoryTemporalStore()
        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "test",
                        "active_thread_id": "thread_nonexistent",
                    },
                )
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"].lower()


# ── 4. Another user's thread cannot be selected ────────────────────────


class TestCrossUserIsolation:
    """A thread belonging to another user returns 404."""

    async def test_other_users_thread_returns_404(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(
            store, "Other user story", user_id=OTHER_F,
        )

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "test",
                        "active_thread_id": t.id,
                    },
                )
            assert resp.status_code == 404


# ── 5. Active thread does not force AI usage ────────────────────────────


class TestNoAIForce:
    """Selecting a thread does not upgrade the engine tier."""

    async def test_thread_context_does_not_change_provider(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Test thread")

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Without thread
                resp1 = await client.post(
                    f"{PREFIX}/process-json",
                    json={"content": "Hello"},
                )
                # With thread
                resp2 = await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "Hello",
                        "active_thread_id": t.id,
                    },
                )
            assert resp1.status_code == 200
            assert resp2.status_code == 200
            # Provider and model must not change
            assert resp1.json()["provider_name"] == resp2.json()["provider_name"]
            assert resp1.json()["model_name"] == resp2.json()["model_name"]


# ── 6. Active thread does not automatically create a temporal event ─────


class TestNoAutoEventCreation:
    """Selecting a thread does not create events in the store."""

    async def test_no_events_created_by_selection(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Eventless thread")
        events_before = await store.get_events_by_thread(t.id, USER_F)
        assert len(events_before) == 0

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "test",
                        "active_thread_id": t.id,
                    },
                )
            assert resp.status_code == 200
            events_after = await store.get_events_by_thread(t.id, USER_F)
            assert len(events_after) == 0


# ── 7. Active thread does not mutate thread lifecycle ───────────────────


class TestNoLifecycleMutation:
    """Selecting a thread does not change its status."""

    async def test_thread_status_unchanged(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(
            store, "Status test",
            status=TemporalThreadStatus.OPEN,
        )

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "test",
                        "active_thread_id": t.id,
                    },
                )
            fetched = await store.get_thread(t.id, USER_F)
            assert fetched.status == TemporalThreadStatus.OPEN


# ── 8. Current input remains authoritative ──────────────────────────────


class TestInputAuthoritative:
    """The user's current message is what the engine processes, not the thread."""

    async def test_engine_processes_current_input(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Old topic")

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "I love cooking pasta",
                        "active_thread_id": t.id,
                    },
                )
            assert resp.status_code == 200
            data = resp.json()
            # The engine received and processed the current input
            assert data["original_input"]["content"] == "I love cooking pasta"
            # The thread context is separate metadata
            assert data["active_thread_context"]["subject"] == "Old topic"


# ── 9. Context is bounded ──────────────────────────────────────────────


class TestContextBounded:
    """The context includes at most _ACTIVE_THREAD_MAX_EVENTS events."""

    async def test_many_events_are_bounded(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Long thread")

        # Create 15 events (more than the 10-event bound)
        for i in range(15):
            await _make_event(
                store, t.id,
                f"Event {i:02d}",
                BASE + timedelta(days=i),
            )

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "test",
                        "active_thread_id": t.id,
                    },
                )
            ctx = resp.json()["active_thread_context"]
            assert len(ctx["recent_events"]) == 10
            # First event is the earliest
            assert ctx["recent_events"][0]["description"] == "Event 00"
            # Last event is event 9 (bounded at 10)
            assert ctx["recent_events"][9]["description"] == "Event 09"


# ── 10. Thread context ordering is deterministic ───────────────────────


class TestDeterministicOrdering:
    """Events in the context are always in chronological order."""

    async def test_events_are_chronological(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Ordering test")

        # Insert out of order
        await _make_event(store, t.id, "Third", BASE + timedelta(days=20))
        await _make_event(store, t.id, "First", BASE)
        await _make_event(store, t.id, "Second", BASE + timedelta(days=10))

        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={
                        "content": "test",
                        "active_thread_id": t.id,
                    },
                )
            ctx = resp.json()["active_thread_context"]
            descriptions = [e["description"] for e in ctx["recent_events"]]
            assert descriptions == ["First", "Second", "Third"]


# ── 11. Existing conversation flow works without an active thread ───────


class TestExistingFlowUnchanged:
    """The normal process endpoint still works without active_thread_id."""

    async def test_process_endpoint_works_normally(self):
        store = InMemoryTemporalStore()
        with _patch_engine(store):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process",
                    data={
                        "content": "Normal message",
                        "input_type": "text",
                        "provider_key": "chronos",
                    },
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["active_thread_context"] is None
            assert data["original_input"]["content"] == "Normal message"


# ── 12. Serialization contract ─────────────────────────────────────────


class TestSerializationContract:
    """ActiveTemporalContext survives model_dump round-trip."""

    def test_context_serializes_cleanly(self):
        ctx = ActiveTemporalContext(
            thread_id="thread_test",
            subject="Test subject",
            description="Test description",
            temporal_type="GOAL",
            status="ACTIVE",
            origin_description="Origin moment",
            origin_occurred_at=BASE,
            recent_events=[
                ActiveTemporalEvent(
                    description="Event one",
                    temporal_type="DECISION",
                    occurred_at=BASE + timedelta(days=5),
                ),
            ],
        )
        dumped = ctx.model_dump()
        restored = ActiveTemporalContext(**dumped)
        assert restored.thread_id == "thread_test"
        assert restored.subject == "Test subject"
        assert len(restored.recent_events) == 1
        assert restored.recent_events[0].description == "Event one"

    def test_engine_response_includes_context(self):
        ctx = ActiveTemporalContext(
            thread_id="thread_x",
            subject="X subject",
        )
        user_input = UserInput(id="in_4f", user_id=USER_F, content="test")
        resp = EngineResponse(
            id="resp_4f",
            user_id=USER_F,
            original_input=user_input,
            raw_llm_response="raw",
            final_response="final",
            provider_name="chronos",
            model_name="test",
            prompt_context=PromptContext(
                current_input=user_input,
                retrieved_context=RetrievedContext(),
                system_prompt="sys",
                user_prompt="usr",
            ),
            reasoning_trace=ReasoningTrace(),
            validation_result=ValidationResult(
                is_valid=True, validated_response="ok",
            ),
            active_thread_context=ctx,
        )
        dumped = resp.model_dump()
        assert dumped["active_thread_context"]["thread_id"] == "thread_x"
        assert dumped["active_thread_context"]["subject"] == "X subject"

    def test_engine_response_without_context(self):
        user_input = UserInput(id="in_4f_2", user_id=USER_F, content="test")
        resp = EngineResponse(
            id="resp_4f_2",
            user_id=USER_F,
            original_input=user_input,
            raw_llm_response="raw",
            final_response="final",
            provider_name="chronos",
            model_name="test",
            prompt_context=PromptContext(
                current_input=user_input,
                retrieved_context=RetrievedContext(),
                system_prompt="sys",
                user_prompt="usr",
            ),
            reasoning_trace=ReasoningTrace(),
            validation_result=ValidationResult(
                is_valid=True, validated_response="ok",
            ),
        )
        dumped = resp.model_dump()
        assert dumped["active_thread_context"] is None


# ── 13. Context reaches ChronosState during processing ───────────────────


class TestContextReachesState:
    """active_temporal_context is present on ChronosState after engine runs."""

    async def test_chronos_state_contains_context(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "State wiring test")
        await _make_event(
            store, t.id, "First moment", BASE,
        )

        engine = ChronosEngine(
            storage=InMemoryStorageAdapter(),
            temporal_store=store,
        )
        ctx = ActiveTemporalContext(
            thread_id=t.id,
            subject="State wiring test",
            status="OPEN",
            temporal_type="DECISION",
            recent_events=[
                ActiveTemporalEvent(description="First moment", temporal_type="DECISION"),
            ],
        )
        response = await engine.process_user_input(
            user_id=USER_F,
            content="Thinking about career",
            active_temporal_context=ctx,
        )
        assert response.chronos_state is not None
        assert response.chronos_state.active_temporal_context is not None
        assert response.chronos_state.active_temporal_context.thread_id == t.id
        assert response.chronos_state.active_temporal_context.subject == "State wiring test"
        assert len(response.chronos_state.active_temporal_context.recent_events) == 1

    async def test_chronos_state_without_context(self):
        engine = ChronosEngine(
            storage=InMemoryStorageAdapter(),
            temporal_store=InMemoryTemporalStore(),
        )
        response = await engine.process_user_input(
            user_id=USER_F,
            content="No thread context",
        )
        assert response.chronos_state is not None
        assert response.chronos_state.active_temporal_context is None

    async def test_engine_response_has_context_from_state(self):
        store = InMemoryTemporalStore()
        t = await _make_thread(store, "Response wiring")
        engine = ChronosEngine(
            storage=InMemoryStorageAdapter(),
            temporal_store=store,
        )
        ctx = ActiveTemporalContext(
            thread_id=t.id, subject="Response wiring",
        )
        response = await engine.process_user_input(
            user_id=USER_F, content="hello",
            active_temporal_context=ctx,
        )
        # EngineResponse.active_thread_context populated from ChronosState
        assert response.active_thread_context is not None
        assert response.active_thread_context.thread_id == t.id

    async def test_engine_response_without_context_none(self):
        engine = ChronosEngine(
            storage=InMemoryStorageAdapter(),
            temporal_store=InMemoryTemporalStore(),
        )
        response = await engine.process_user_input(
            user_id=USER_F, content="hello",
        )
        assert response.active_thread_context is None


# ── 14. ReasoningContextBuilder includes active thread lines ─────────────


class TestReasoningContextBuilderThreadLines:
    """ReasoningContextBuilder populates active_thread_lines when present."""

    def test_builder_includes_thread_lines(self):
        from chronos_engine.ai.context import ReasoningContextBuilder
        from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
        from chronos_engine.state.models import ChronosState

        ctx = ActiveTemporalContext(
            thread_id="thread_abc",
            subject="Career decision",
            status="OPEN",
            temporal_type="DECISION",
            description="Should I change careers?",
            origin_description="Thinking about leaving",
            recent_events=[
                ActiveTemporalEvent(description="Considering options", temporal_type="DECISION"),
                ActiveTemporalEvent(description="Made a choice", temporal_type="DECISION"),
            ],
        )
        state = ChronosState(
            id="state_test", user_id=USER_F,
            current_input=UserInput(id="in1", user_id=USER_F, content="test"),
            active_temporal_context=ctx,
        )
        plan = ReasoningPlan(
            modes=[ReasoningMode.INTERPRET, ReasoningMode.GENERATE],
            primary_mode=ReasoningMode.INTERPRET,
            reason="Test",
            confidence=0.8,
        )
        builder = ReasoningContextBuilder()
        rc = builder.build(state, plan)
        assert rc.show_active_thread is True
        assert len(rc.active_thread_lines) > 0
        assert any("Career decision" in line for line in rc.active_thread_lines)
        assert any("DECISION" in line for line in rc.active_thread_lines)

    def test_builder_omits_thread_lines_when_absent(self):
        from chronos_engine.ai.context import ReasoningContextBuilder
        from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
        from chronos_engine.state.models import ChronosState

        state = ChronosState(
            id="state_no_thread", user_id=USER_F,
            current_input=UserInput(id="in2", user_id=USER_F, content="test"),
        )
        plan = ReasoningPlan(
            modes=[ReasoningMode.INTERPRET, ReasoningMode.GENERATE],
            primary_mode=ReasoningMode.INTERPRET,
            reason="Test",
            confidence=0.8,
        )
        builder = ReasoningContextBuilder()
        rc = builder.build(state, plan)
        assert rc.show_active_thread is False
        assert rc.active_thread_lines == []


# ── 15. DEEP prompt includes ACTIVE THREAD CONTEXT section ───────────────


class TestPromptIncludesThreadSection:
    """ChronosAIPromptBuilder renders active thread section in DEEP prompt."""

    def test_prompt_contains_thread_section(self):
        from chronos_engine.ai.prompts import ChronosAIPromptBuilder
        from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
        from chronos_engine.response.models import ChronosInterpretation, DeterministicResponse
        from chronos_engine.state.models import ChronosState, EngineStateResult

        ctx = ActiveTemporalContext(
            thread_id="thread_prompt",
            subject="Health journey",
            status="ACTIVE",
            temporal_type="GOAL",
            recent_events=[
                ActiveTemporalEvent(description="Started running", temporal_type="GOAL"),
            ],
        )
        state = ChronosState(
            id="state_prompt", user_id=USER_F,
            current_input=UserInput(id="in3", user_id=USER_F, content="test"),
            active_temporal_context=ctx,
        )
        plan = ReasoningPlan(
            modes=[ReasoningMode.INTERPRET, ReasoningMode.GENERATE],
            primary_mode=ReasoningMode.INTERPRET,
            reason="Test",
            confidence=0.8,
        )
        det_response = DeterministicResponse(
            user_signal="neutral",
            chronos_interpretation=ChronosInterpretation(
                user_state_summary="neutral",
                intent_summary="general",
                context_summary="none",
            ),
            chronos_state=EngineStateResult(),
            rendered="Deterministic answer.",
        )
        builder = ChronosAIPromptBuilder()
        prompt_ctx = builder.build(state, det_response, plan)
        user_prompt = prompt_ctx.user_prompt
        assert "ACTIVE THREAD CONTEXT:" in user_prompt
        assert "Health journey" in user_prompt
        assert "Started running" in user_prompt

    def test_prompt_omits_thread_section_when_absent(self):
        from chronos_engine.ai.prompts import ChronosAIPromptBuilder
        from chronos_engine.ai.reasoning.models import ReasoningMode, ReasoningPlan
        from chronos_engine.response.models import ChronosInterpretation, DeterministicResponse
        from chronos_engine.state.models import ChronosState, EngineStateResult

        state = ChronosState(
            id="state_no_prompt", user_id=USER_F,
            current_input=UserInput(id="in4", user_id=USER_F, content="test"),
        )
        plan = ReasoningPlan(
            modes=[ReasoningMode.INTERPRET, ReasoningMode.GENERATE],
            primary_mode=ReasoningMode.INTERPRET,
            reason="Test",
            confidence=0.8,
        )
        det_response = DeterministicResponse(
            user_signal="neutral",
            chronos_interpretation=ChronosInterpretation(
                user_state_summary="neutral",
                intent_summary="general",
                context_summary="none",
            ),
            chronos_state=EngineStateResult(),
            rendered="Deterministic answer.",
        )
        builder = ChronosAIPromptBuilder()
        prompt_ctx = builder.build(state, det_response, plan)
        assert "ACTIVE THREAD CONTEXT:" not in prompt_ctx.user_prompt
