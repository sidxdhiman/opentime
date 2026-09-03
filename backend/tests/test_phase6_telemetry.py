"""Phase 6 tests: metadata-only product telemetry and its data lifecycle.

Verifies the metadata-only ``product_events`` instrumentation:
- ``record_event`` writes a user-scoped, metadata-only document (never content)
- telemetry is failure-safe (a DB failure never breaks or raises into the product)
- the wiring points emit on the right user actions:
  * ``memory_deleted`` on single-memory delete
  * ``data_exported`` on export
  * ``conversation_processed`` carries only coarse booleans/counts
- ``delete_user_data`` purges the user's ``product_events`` (privacy-first) and
  does not purge other users' events (cross-user isolation)
- the dev-only metrics endpoint is gated behind ``debug`` (no production exposure)
"""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import mongomock_motor
from httpx import ASGITransport, AsyncClient

from chronos_engine.engine import ChronosEngine
from chronos_engine.storage import InMemoryStorageAdapter, InMemoryTemporalStore
from chronos_engine.telemetry import record_event
from opentime.main import app
from tests.conftest import AUTH_USER_ID, OTHER_AUTH_USER_ID

PREFIX = "/api/v1/chronos/engine"


def _mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["opentime_test"]


async def _find_all(db, query):
    docs = []
    async for doc in db["product_events"].find(query):
        docs.append(doc)
    return docs


def _patch_engine(storage, store):
    engine = ChronosEngine(storage=storage, temporal_store=store)
    return patch("chronos_engine.api.router.engine_instance", engine)


def _noop_upload_dir():
    return Path("/tmp/opencode-nonexistent-upload")


class TestRecordEvent:
    async def test_writes_metadata_only_document(self):
        db = _mock_db()
        with patch("chronos_engine.telemetry.get_mongo_db", return_value=db):
            await record_event(
                AUTH_USER_ID,
                "memory_deleted",
                {"count": 1},
            )
        docs = await _find_all(db, {"user_id": AUTH_USER_ID})
        assert len(docs) == 1
        doc = docs[0]
        assert doc["event_type"] == "memory_deleted"
        assert doc["data"] == {"count": 1}
        assert isinstance(doc["occurred_at"], datetime)
        # No keys for content, prompts, responses, or user data beyond id/type.
        assert not any(
            k in doc
            for k in ("content", "response", "prompt", "memory_id", "thread_id")
        )

    async def test_db_failure_is_swallowed_not_raised(self):
        class _Boom:
            def __getitem__(self, _):
                raise RuntimeError("boom")

        with patch("chronos_engine.telemetry.get_mongo_db", return_value=_Boom()):
            # Must not raise even though the underlying write fails.
            await record_event(AUTH_USER_ID, "account_created")

    async def test_insert_failure_is_swallowed_not_raised(self):
        class _BoomColl:
            async def insert_one(self, _doc):
                raise RuntimeError("no db")

        class _BoomDb:
            def __getitem__(self, _):
                return _BoomColl()

        with patch("chronos_engine.telemetry.get_mongo_db", return_value=_BoomDb()):
            await record_event(AUTH_USER_ID, "conversation_failed")


class TestConversationMetadata:
    def _state(self, **overrides):
        base = dict(
            temporal_event_detection=SimpleNamespace(detected=True),
            temporal_thread_match=SimpleNamespace(attempted=True, matched=True),
            temporal_lifecycle=SimpleNamespace(
                created=True, updated=False, transitioned=True
            ),
            temporal_comparison=SimpleNamespace(attempted=True, relation="NOTABLE"),
            temporal_relevance=SimpleNamespace(decision="SURFACE"),
            past_self_question=SimpleNamespace(should_ask=True),
            temporal_reflection=SimpleNamespace(used=True),
            active_temporal_context=object(),
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_maps_coarse_booleans_only(self):
        from chronos_engine.api.router import _conversation_metadata

        response = SimpleNamespace(
            original_input=SimpleNamespace(input_type=SimpleNamespace(value="text")),
            processing_time_ms=42.6,
            ai_execution=SimpleNamespace(used=True),
            chronos_state=self._state(),
        )
        m = _conversation_metadata(response)
        assert m["input_type"] == "text"
        assert m["processing_time_ms"] == 42.6
        assert m["ai_used"] is True
        assert m["temporal_detected"] is True
        assert m["thread_matched"] is True
        assert m["thread_created"] is True
        assert m["thread_transitioned"] is True
        assert m["comparison_relation"] == "NOTABLE"
        assert m["relevance_decision"] == "SURFACE"
        assert m["past_self_question"] is True
        assert m["reflection_used"] is True
        assert m["active_story_context"] is True
        # Never sensitive: only booleans/strings/enums + a count, no content.
        assert not any(
            k in m for k in ("content", "response", "reasoning", "memory_id")
        )

    def test_state_none_returns_empty_base_metadata(self):
        from chronos_engine.api.router import _conversation_metadata

        response = SimpleNamespace(
            original_input=SimpleNamespace(input_type=SimpleNamespace(value="audio")),
            processing_time_ms=1.5,
            ai_execution=None,
            chronos_state=None,
        )
        m = _conversation_metadata(response)
        assert m["input_type"] == "audio"
        assert m["ai_used"] is False
        assert "temporal_detected" not in m


class TestWiring:
    async def test_memory_delete_emits_event(self, override_auth, tmp_path):
        from datetime import UTC, datetime

        from chronos_engine.core.models import MemoryItem

        storage = InMemoryStorageAdapter()
        await storage.save_memory(
            MemoryItem(
                id="mem_t",
                user_id=AUTH_USER_ID,
                content="a memory",
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        db = _mock_db()
        with _patch_engine(storage, InMemoryTemporalStore()), patch(
            "chronos_engine.telemetry.get_mongo_db", return_value=db
        ), patch("chronos_engine.api.router.get_mongo_db", return_value=db), patch(
            "chronos_engine.api.router._upload_dir", return_value=_noop_upload_dir()
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"{PREFIX}/memories/mem_t")
        assert r.status_code == 204
        docs = await _find_all(db, {"user_id": AUTH_USER_ID})
        assert [d["event_type"] for d in docs] == ["memory_deleted"]

    async def test_export_emits_event(self, override_auth):
        db = _mock_db()
        with _patch_engine(InMemoryStorageAdapter(), InMemoryTemporalStore()), patch(
            "chronos_engine.telemetry.get_mongo_db", return_value=db
        ), patch("chronos_engine.api.router.get_mongo_db", return_value=db), patch(
            "chronos_engine.api.router._upload_dir", return_value=_noop_upload_dir()
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get(f"{PREFIX}/export")
        assert r.status_code == 200
        docs = await _find_all(db, {"user_id": AUTH_USER_ID})
        assert [d["event_type"] for d in docs] == ["data_exported"]


class TestDeletePurge:
    async def test_delete_purges_own_telemetry_only(self, override_auth):
        db = _mock_db()
        await db["product_events"].insert_many(
            [
                {
                    "user_id": AUTH_USER_ID,
                    "event_type": "conversation_processed",
                    "data": {},
                    "occurred_at": datetime.now(UTC),
                },
                {
                    "user_id": OTHER_AUTH_USER_ID,
                    "event_type": "conversation_processed",
                    "data": {},
                    "occurred_at": datetime.now(UTC),
                },
            ]
        )

        with _patch_engine(InMemoryStorageAdapter(), InMemoryTemporalStore()), patch(
            "chronos_engine.api.router.get_mongo_db", return_value=db
        ), patch(
            "chronos_engine.api.router._upload_dir", return_value=_noop_upload_dir()
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(PREFIX)
        assert r.status_code == 204

        assert await db["product_events"].count_documents({"user_id": AUTH_USER_ID}) == 0
        # Other users' telemetry is never touched.
        assert await db["product_events"].count_documents(
            {"user_id": OTHER_AUTH_USER_ID}
        ) == 1


class TestMetricsEndpoint:
    async def test_gated_behind_debug(self, override_auth):
        with patch(
            "chronos_engine.api.router.get_settings"
        ) as mock_settings:
            mock_settings.return_value.debug = False
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get(f"{PREFIX}/metrics/events")
        assert r.status_code == 404
