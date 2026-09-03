"""Phase 5G-E: adversarial truthfulness + deletion-integrity regression tests.

Confirms:
  - A brand-new (empty) account is NEVER shown fabricated identity, reflection
    insights, or behavioral patterns. GETs return truthful empty data and
    persist nothing (no fabricated founder persona / insights / patterns).
  - A permanent deletion that partially fails surfaces an HTTP error (no false
    204 success) for both the application-layer Mongo deletes and on-disk media.
"""

from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from chronos_engine.core.models import MemoryItem
from chronos_engine.engine import ChronosEngine
from chronos_engine.storage import InMemoryStorageAdapter, InMemoryTemporalStore
from opentime.main import app
from tests.conftest import AUTH_USER_ID

PREFIX = "/api/v1/chronos/engine"


class _FakeDb:
    """Minimal async fake DB that records delete_many calls per collection."""

    def __init__(self) -> None:
        self.deleted: dict[str, list] = {}

    def __getitem__(self, name: str) -> "_FakeCollection":
        return _FakeCollection(self.deleted, name)


class _FakeCollection:
    def __init__(self, store: dict, name: str) -> None:
        self._store = store
        self._name = name

    async def delete_many(self, query: dict) -> None:
        self._store.setdefault(self._name, []).append(query)


class _BoomDb:
    """Fake DB whose delete_many always raises (partial failure)."""

    def __getitem__(self, name: str) -> "_BoomCollection":
        return _BoomCollection()


class _BoomCollection:
    async def delete_many(self, query: dict) -> None:
        raise RuntimeError("mongo down")


def _noop_upload_dir():
    return Path("/tmp/opencode-nonexistent-upload")


def _make_engine():
    storage = InMemoryStorageAdapter()
    store = InMemoryTemporalStore()
    return storage, store, ChronosEngine(storage=storage, temporal_store=store)


class TestEmptyUserTruthfulness:
    """A brand-new account must present no fabricated identity/insights/patterns."""

    async def test_empty_identity_has_no_fabricated_content(self, override_auth):
        storage, store, engine = _make_engine()

        with patch("chronos_engine.api.router.engine_instance", engine):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"{PREFIX}/identity")

        assert resp.status_code == 200
        data = resp.json()
        assert not data["interests"]
        assert not data["goals"]
        assert not data["values"]
        assert not data["skills"]
        assert not data["relationships"]
        assert not data["decision_patterns"]

        # Nothing was persisted by the read.
        assert await storage.get_identity(AUTH_USER_ID) is None

    async def test_empty_reflections_are_empty(self, override_auth):
        storage, store, engine = _make_engine()

        with patch("chronos_engine.api.router.engine_instance", engine):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"{PREFIX}/reflections")

        assert resp.status_code == 200
        assert resp.json() == []
        assert await storage.get_reflections_by_user(AUTH_USER_ID) == []

    async def test_empty_patterns_are_empty(self, override_auth):
        storage, store, engine = _make_engine()

        with patch("chronos_engine.api.router.engine_instance", engine):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"{PREFIX}/patterns")

        assert resp.status_code == 200
        assert resp.json() == []
        assert await storage.get_patterns_by_user(AUTH_USER_ID) == []


class TestNoRefabricationAfterDelete:
    """After a permanent deletion, reads must NOT re-seed fabricated data."""

    async def test_delete_then_read_does_not_resurrect_data(self, override_auth):
        storage, store, engine = _make_engine()
        await storage.save_memory(
            MemoryItem(
                id="mem_real",
                user_id=AUTH_USER_ID,
                content="I am learning Spanish this year.",
                importance_score=0.8,
            )
        )

        with patch("chronos_engine.api.router.engine_instance", engine), patch(
            "chronos_engine.api.router.get_mongo_db", return_value=_FakeDb()
        ), patch("chronos_engine.api.router._upload_dir", return_value=_noop_upload_dir()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                del_resp = await client.delete(PREFIX)
                id_resp = await client.get(f"{PREFIX}/identity")
                ref_resp = await client.get(f"{PREFIX}/reflections")
                pat_resp = await client.get(f"{PREFIX}/patterns")

        assert del_resp.status_code == 204
        assert id_resp.status_code == 200
        assert ref_resp.status_code == 200
        assert pat_resp.status_code == 200

        identity = id_resp.json()
        assert not identity["interests"]
        assert not identity["goals"]
        assert not identity["relationships"]
        assert ref_resp.json() == []
        assert pat_resp.json() == []

        # Nothing re-seeded into storage.
        assert await storage.get_memories_by_user(AUTH_USER_ID) == []
        assert await storage.get_identity(AUTH_USER_ID) is None
        assert await storage.get_reflections_by_user(AUTH_USER_ID) == []
        assert await storage.get_patterns_by_user(AUTH_USER_ID) == []


class TestDeletePartialFailureSurfacesError:
    """A partially successful permanent deletion must not report 204."""

    async def test_app_layer_mongo_failure_returns_500(self, override_auth):
        storage, store, engine = _make_engine()
        await storage.save_memory(
            MemoryItem(
                id="mem_real",
                user_id=AUTH_USER_ID,
                content="I am learning Spanish this year.",
                importance_score=0.8,
            )
        )

        with patch("chronos_engine.api.router.engine_instance", engine), patch(
            "chronos_engine.api.router.get_mongo_db", return_value=_BoomDb()
        ), patch("chronos_engine.api.router._upload_dir", return_value=_noop_upload_dir()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(PREFIX)

        # No false 204: the client must know deletion did not fully complete.
        assert resp.status_code == 500
        # No internal details leaked to the client.
        assert "mongo" not in resp.json().get("detail", "")

    async def test_media_deletion_failure_returns_500(self, override_auth, tmp_path):
        storage, store, engine = _make_engine()
        await storage.save_memory(
            MemoryItem(
                id="mem_real",
                user_id=AUTH_USER_ID,
                content="I am learning Spanish this year.",
                importance_score=0.8,
            )
        )

        upload_dir = tmp_path / "uploads"
        own_dir = upload_dir / AUTH_USER_ID
        own_dir.mkdir(parents=True)
        (own_dir / "note.webm").write_bytes(b"x")

        def boom_unlink(self, *a, **k):
            raise OSError("disk full")

        with patch("chronos_engine.api.router.engine_instance", engine), patch(
            "chronos_engine.api.router.get_mongo_db", return_value=_FakeDb()
        ), patch("chronos_engine.api.router._upload_dir", return_value=upload_dir), patch.object(
            Path, "unlink", boom_unlink
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(PREFIX)

        assert resp.status_code == 500
