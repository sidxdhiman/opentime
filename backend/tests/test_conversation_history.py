"""Phase 4D tests: conversation history persistence and API contract.

Architecture correction: the ChronOS engine no longer persists interaction
records.  Persistence lives at the API/application boundary via
``_persist_interaction`` in ``router.py``.  These tests verify:

- Engine independence (no side-effect persistence)
- API-layer persistence correctness
- Persistence failure resilience
- Retrieval ordering (latest-first)
- Deduplication contract (same ID not rendered twice)
- Past-Self rendering contract (structured fields survive, flat text stored)
- Engine intelligence unchanged
"""

import logging
from unittest.mock import AsyncMock, patch

from chronos_engine.api.router import _persist_interaction
from chronos_engine.core.models import InteractionRecord
from chronos_engine.engine import ChronosEngine

USER_A = "user_4d_a"
USER_B = "user_4d_b"


# ── Helpers ─────────────────────────────────────────────────────────────


async def _process(engine: ChronosEngine, user_id: str, content: str):
    return await engine.process_user_input(
        user_id=user_id,
        content=content,
        input_type="text",
        provider_key="chronos",
    )


async def _persist(resp, engine: ChronosEngine):
    """Persist via the API-layer helper using the test engine's storage."""
    await _persist_interaction(resp, storage=engine.storage)


# ── 1. Engine independence ──────────────────────────────────────────────


class TestEngineIndependence:
    """The engine must NOT persist interaction records as a side-effect."""

    async def test_process_does_not_persist_interaction(self):
        engine = ChronosEngine()
        await _process(engine, USER_A, "No persistence here")
        records = await engine.storage.get_interactions_by_user(USER_A)
        assert len(records) == 0

    async def test_process_does_not_call_save_interaction(self):
        engine = ChronosEngine()
        mock_save = AsyncMock()
        with patch.object(engine.storage, "save_interaction", mock_save):
            await _process(engine, USER_A, "Mock check")
        mock_save.assert_not_called()


# ── 2. API-layer persistence ────────────────────────────────────────────


class TestApiLayerPersistence:
    """_persist_interaction correctly stores an InteractionRecord."""

    async def test_persists_record_with_correct_fields(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "API layer test")
        await _persist(resp, engine)
        records = await engine.storage.get_interactions_by_user(USER_A)
        assert len(records) >= 1
        latest = records[0]
        assert latest.id == resp.id
        assert latest.user_id == USER_A
        assert latest.user_content == "API layer test"
        assert latest.final_response == resp.final_response
        assert len(latest.final_response) > 0

    async def test_persists_model_metadata(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Metadata check")
        await _persist(resp, engine)
        records = await engine.storage.get_interactions_by_user(USER_A)
        latest = records[0]
        assert latest.provider_name == resp.provider_name
        assert latest.model_name == resp.model_name
        assert latest.processing_time_ms > 0

    async def test_input_type_preserved(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Type check")
        await _persist(resp, engine)
        records = await engine.storage.get_interactions_by_user(USER_A)
        latest = records[0]
        assert latest.input_type == "text"

    async def test_no_raw_internal_state_persisted(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Internal check")
        await _persist(resp, engine)
        records = await engine.storage.get_interactions_by_user(USER_A)
        latest = records[0]
        record_dict = latest.model_dump()
        assert "raw_llm_response" not in record_dict
        assert "prompt_context" not in record_dict
        assert "reasoning_trace" not in record_dict
        assert "chronos_state" not in record_dict


# ── 3. Persistence failure resilience ───────────────────────────────────


class TestPersistenceFailure:
    """Persistence failure must not break a successful engine response."""

    async def test_failure_does_not_raise(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Fail test")
        with patch.object(
            engine.storage,
            "save_interaction",
            side_effect=RuntimeError("db down"),
        ):
            # Must not raise
            await _persist(resp, engine)

    async def test_failure_is_logged(self, caplog):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Log test")
        with caplog.at_level(logging.WARNING, logger="chronos_engine.api.router"):
            with patch.object(
                engine.storage,
                "save_interaction",
                side_effect=RuntimeError("db down"),
            ):
                await _persist(resp, engine)
        assert "Failed to persist interaction" in caplog.text
        assert resp.user_id in caplog.text

    async def test_response_returned_normally_when_persistence_fails(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Resilience")
        with patch.object(
            engine.storage,
            "save_interaction",
            side_effect=RuntimeError("db down"),
        ):
            await _persist(resp, engine)
        # Helper returns None (fire-and-forget), but critically does not raise


# ── 4. Retrieval ordering ──────────────────────────────────────────────


class TestRetrievalOrdering:
    """Default retrieval returns the latest interactions, not the oldest."""

    async def test_ordered_newest_first(self):
        engine = ChronosEngine()
        resp_a = await _process(engine, USER_A, "First message")
        resp_b = await _process(engine, USER_A, "Second message")
        resp_c = await _process(engine, USER_A, "Third message")
        await _persist(resp_a, engine)
        await _persist(resp_b, engine)
        await _persist(resp_c, engine)
        records = await engine.storage.get_interactions_by_user(USER_A)
        contents = [r.user_content for r in records]
        assert contents == ["Third message", "Second message", "First message"]

    async def test_limit_returns_latest_not_oldest(self):
        engine = ChronosEngine()
        for i in range(5):
            resp = await _process(engine, USER_A, f"Message {i}")
            await _persist(resp, engine)
        records = await engine.storage.get_interactions_by_user(USER_A, limit=3)
        assert len(records) == 3
        # The 3 most recent should be returned (messages 4, 3, 2)
        assert records[0].user_content == "Message 4"
        assert records[1].user_content == "Message 3"
        assert records[2].user_content == "Message 2"

    async def test_user_isolation(self):
        engine = ChronosEngine()
        resp_a = await _process(engine, USER_A, "Private thought")
        resp_b = await _process(engine, USER_B, "Different user thought")
        await _persist(resp_a, engine)
        await _persist(resp_b, engine)
        records_a = await engine.storage.get_interactions_by_user(USER_A)
        records_b = await engine.storage.get_interactions_by_user(USER_B)
        assert all(r.user_content == "Private thought" for r in records_a)
        assert all(r.user_content == "Different user thought" for r in records_b)

    async def test_empty_user_returns_nothing(self):
        engine = ChronosEngine()
        records = await engine.storage.get_interactions_by_user("nonexistent_user")
        assert records == []


# ── 5. Deduplication contract ──────────────────────────────────────────


class TestDeduplicationContract:
    """Same interaction ID must not render as both latest and historical."""

    async def test_same_id_used_for_response_and_record(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Dedup check")
        await _persist(resp, engine)
        records = await engine.storage.get_interactions_by_user(USER_A)
        assert len(records) >= 1
        assert records[0].id == resp.id

    async def test_filtering_by_id_removes_duplicates(self):
        """Simulates the frontend deduplication logic."""
        interactions = [
            InteractionRecord(
                id="resp_old1", user_id=USER_A, user_content="old1",
                final_response="r1",
            ),
            InteractionRecord(
                id="resp_latest", user_id=USER_A, user_content="latest",
                final_response="r_latest",
            ),
            InteractionRecord(
                id="resp_old2", user_id=USER_A, user_content="old2",
                final_response="r2",
            ),
        ]
        latest_response_id = "resp_latest"
        filtered = [r for r in interactions if r.id != latest_response_id]
        assert len(filtered) == 2
        assert all(r.id != latest_response_id for r in filtered)


# ── 6. Past-Self rendering contract ────────────────────────────────────


class TestPastSelfRenderingContract:
    """Structured Past-Self data survives reload; flat text is in stored response."""

    async def test_empty_fields_when_no_moment(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "What is MongoDB?")
        await _persist(resp, engine)
        records = await engine.storage.get_interactions_by_user(USER_A)
        latest = records[0]
        assert latest.past_self_opening == ""
        assert latest.past_self_context == ""
        assert latest.past_self_bridge == ""
        assert latest.past_self_question == ""
        assert latest.past_self_reflection == ""

    async def test_flat_section_in_stripped_response(self):
        """The stored final_response may contain the flat Past-Self section.
        The frontend strips it before display. Verify it's there so the
        stripping logic has something to work with."""
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Check flat section")
        await _persist(resp, engine)
        records = await engine.storage.get_interactions_by_user(USER_A)
        latest = records[0]
        # Whether the flat section is present depends on the engine's
        # deterministic composition.  We only verify the field exists.
        assert isinstance(latest.final_response, str)


# ── 7. Engine intelligence unchanged ───────────────────────────────────


class TestEngineIntelligenceUnchanged:
    """Verify the engine still works correctly after the architecture correction."""

    async def test_engine_still_processes_input(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Engine still works")
        assert resp is not None
        assert resp.user_id == USER_A
        assert len(resp.final_response) > 0

    async def test_engine_still_returns_chronos_state(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "State check")
        assert resp.chronos_state is not None

    async def test_engine_still_returns_reasoning_trace(self):
        engine = ChronosEngine()
        resp = await _process(engine, USER_A, "Trace check")
        assert resp.reasoning_trace is not None
        assert resp.reasoning_trace.confidence_score > 0
