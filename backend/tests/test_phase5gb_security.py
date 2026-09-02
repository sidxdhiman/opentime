"""Phase 5G-B: Security & privacy hardening integration tests.

Covers:
  - JWT secret hardening (fail closed in production)
  - Private media authorization (authenticated ownership)
  - /seed endpoint restriction to dev/test only
  - Error response sanitization (no internal details leaked)
  - Complete right-to-be-forgotten (deletion coverage)
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from chronos_engine.core.models import (
    InteractionRecord,
    MemoryItem,
    TimelineEvent,
)
from chronos_engine.engine import ChronosEngine
from chronos_engine.storage import InMemoryStorageAdapter, InMemoryTemporalStore
from chronos_engine.temporal.models import (
    ReturnLedger,
    TemporalEvent,
    TemporalSnapshot,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)
from opentime.infrastructure.config import (
    _INSECURE_JWT_SECRETS,
    Settings,
)
from opentime.main import app
from tests.conftest import AUTH_USER_ID, OTHER_AUTH_USER_ID

PREFIX = "/api/v1/chronos/engine"


# ── JWT secret hardening ────────────────────────────────────────────────────


class TestJWTSecret:
    def test_insecure_default_secrets_are_registered(self):
        # The placeholders we ship / documented must be blocked.
        assert "change-me-in-production-use-a-long-random-string" in _INSECURE_JWT_SECRETS
        assert "dev-secret-change-in-production" in _INSECURE_JWT_SECRETS

    def test_production_missing_secret_fails_closed(self):
        # debug=False (production) with the default/placeholder secret must raise.
        with pytest.raises(ValueError):
            Settings(debug=False, jwt_secret_key="change-me-in-production-use-a-long-random-string")

    def test_production_known_default_fails_closed(self):
        with pytest.raises(ValueError):
            Settings(debug=False, jwt_secret_key="dev-secret-change-in-production")

    def test_production_empty_secret_fails_closed(self):
        with pytest.raises(ValueError):
            Settings(debug=False, jwt_secret_key="")

    def test_production_strong_secret_works(self):
        s = Settings(debug=False, jwt_secret_key="a" * 64)
        assert s.jwt_secret_key == "a" * 64

    def test_development_placeholder_allowed_when_debug(self):
        s = Settings(debug=True, jwt_secret_key="change-me-in-production-use-a-long-random-string")
        assert s.jwt_secret_key  # allowed in dev


# ── Private media authorization ─────────────────────────────────────────────


@pytest.fixture
def _media_on_disk(tmp_path):
    """Create an upload dir with a media file and point settings at it."""
    # We target the module-level `_upload_dir()` which reads settings.
    upload_dir = tmp_path / "uploads"
    (upload_dir / AUTH_USER_ID).mkdir(parents=True)
    (upload_dir / OTHER_AUTH_USER_ID).mkdir(parents=True)
    (upload_dir / AUTH_USER_ID / "note.webm").write_bytes(b"auth-user-media")
    (upload_dir / OTHER_AUTH_USER_ID / "secret.webm").write_bytes(b"other-user-media")

    with patch("chronos_engine.api.router._upload_dir", return_value=upload_dir):
        yield upload_dir


class TestMediaAuthorization:
    async def test_owner_can_retrieve_own_media(self, override_auth, _media_on_disk):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"{PREFIX}/media/{AUTH_USER_ID}/note.webm")
        assert resp.status_code == 200
        assert resp.content == b"auth-user-media"

    async def test_other_user_cannot_retrieve_own_media(self, override_auth, _media_on_disk):
        # Authenticated as AUTH_USER_ID; tries to read OTHER_USER's media.
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"{PREFIX}/media/{OTHER_AUTH_USER_ID}/secret.webm")
        assert resp.status_code == 404

    async def test_guessing_media_path_does_not_bypass_auth(self, override_auth, _media_on_disk):
        # Try arbitrary/guessed path under own user dir.
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"{PREFIX}/media/{AUTH_USER_ID}/guessed.webm")
        assert resp.status_code == 404

    async def test_unauthenticated_media_rejected(self, _media_on_disk):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"{PREFIX}/media/{AUTH_USER_ID}/note.webm")
        assert resp.status_code == 401

    async def test_directory_traversal_blocked(self, override_auth, _media_on_disk):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"{PREFIX}/media/{AUTH_USER_ID}/..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code == 404


# ── /seed endpoint restriction ──────────────────────────────────────────────


class TestSeedRestriction:
    async def test_seed_rejected_in_production_mode(self, override_auth):
        with patch("chronos_engine.api.router.get_settings") as mock_settings:
            mock_settings.return_value.debug = False
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"{PREFIX}/seed")
        assert resp.status_code == 404

    async def test_seed_available_in_debug_mode(self, override_auth):
        with patch("chronos_engine.api.router.get_settings") as mock_settings:
            mock_settings.return_value.debug = True
            storage = InMemoryStorageAdapter()
            store = InMemoryTemporalStore()
            engine = ChronosEngine(storage=storage, temporal_store=store)
            with patch("chronos_engine.api.router.engine_instance", engine):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(f"{PREFIX}/seed")
        assert resp.status_code == 200
        assert len(await storage.get_memories_by_user(AUTH_USER_ID)) > 0


# ── Error leakage ───────────────────────────────────────────────────────────

_INTERNAL_PATTERNS = [
    "Traceback (most recent call last)",
    "File \"",
    "chronos_engine.",
    "opentime.",
    "MongoServerError",
    "pymongo.",
    "AttributeError",
    "KeyError",
    "ValueError:",
]


class TestErrorLeakage:
    async def test_engine_processing_error_is_sanitized(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        engine = ChronosEngine(storage=storage, temporal_store=store)

        async def boom(*args, **kwargs):
            raise RuntimeError("internal secret detail: db=mongo://host:27017")

        engine.process_user_input = boom  # type: ignore
        with patch("chronos_engine.api.router.engine_instance", engine):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={"content": "hello"},
                )
        assert resp.status_code == 500
        body = resp.json().get("detail", "")
        assert "internal secret detail" not in body
        assert "db=mongo" not in body
        assert "RuntimeError" not in body
        for pat in _INTERNAL_PATTERNS:
            assert pat not in body

    async def test_process_json_error_is_sanitized(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        engine = ChronosEngine(storage=storage, temporal_store=store)

        async def boom(*args, **kwargs):
            raise ValueError("Traceback (most recent call last): File \"/app/src/x.py\"")

        engine.process_user_input = boom  # type: ignore
        with patch("chronos_engine.api.router.engine_instance", engine):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={"content": "hello"},
                )
        assert resp.status_code == 500
        body = resp.json().get("detail", "")
        for pat in _INTERNAL_PATTERNS:
            assert pat not in body

    async def test_generic_unhandled_error_is_sanitized(self, override_auth):
        # Force an uncaught exception through a known route and ensure the
        # global handler returns a generic message with no internal details.
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        engine = ChronosEngine(storage=storage, temporal_store=store)

        async def boom(*args, **kwargs):
            raise RuntimeError(
                "Traceback (most recent call last): File \"/app/src/opentime/main.py\" line 42"
            )

        engine.process_user_input = boom  # type: ignore
        with patch("chronos_engine.api.router.engine_instance", engine):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"{PREFIX}/process-json",
                    json={"content": "hello"},
                )
        assert resp.status_code == 500
        body = resp.json().get("detail", "")
        for pat in _INTERNAL_PATTERNS:
            assert pat not in body


# ── Complete right-to-be-forgotten ──────────────────────────────────────────


async def _seed_full_user(storage, store, user_id):
    await storage.save_memory(
        MemoryItem(
            id=f"mem_{user_id}",
            user_id=user_id,
            content=f"memory {user_id}",
            importance_score=0.8,
        )
    )
    await storage.save_interaction(
        InteractionRecord(
            id=f"int_{user_id}",
            user_id=user_id,
            user_content="hi",
            final_response="hello",
            provider_name="chron",
            model_name="m",
        )
    )
    t = TemporalThread(
        id=f"thread_{user_id}",
        user_id=user_id,
        subject="story",
        status=TemporalThreadStatus.OPEN,
        temporal_type=TemporalType.DECISION,
    )
    t = await store.save_thread(t)
    await store.save_event(
        TemporalEvent(
            id=f"ev_{user_id}",
            thread_id=t.id,
            user_id=user_id,
            description="event",
            temporal_type=TemporalType.DECISION,
        )
    )
    await store.save_snapshot(
        TemporalSnapshot(id=f"snap_{user_id}", user_id=user_id, context_description="snap")
    )
    await store.save_return_ledger(ReturnLedger(user_id=user_id))
    await storage.save_timeline_event(
        TimelineEvent(
            id=f"tl_{user_id}",
            user_id=user_id,
            title="title",
            description="desc",
        )
    )


class TestCompleteDeletionInMemory:
    async def test_delete_clears_all_inmemory_stores(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        await _seed_full_user(storage, store, AUTH_USER_ID)
        # Seed another user to ensure isolation.
        await _seed_full_user(storage, store, OTHER_AUTH_USER_ID)

        engine = ChronosEngine(storage=storage, temporal_store=store)
        with patch("chronos_engine.api.router.engine_instance", engine), patch(
            "chronos_engine.api.router.get_mongo_db"
        ) as mock_db, patch("chronos_engine.api.router._upload_dir") as mock_upload:
            mock_db.return_value = _FakeDb()
            mock_upload.return_value = _noop_upload_dir()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(PREFIX)
        assert resp.status_code == 204

        # Own data gone.
        assert await storage.get_memories_by_user(AUTH_USER_ID) == []
        assert await storage.get_interactions_by_user(AUTH_USER_ID) == []
        assert await storage.get_timeline_by_user(AUTH_USER_ID) == []
        assert await store.get_thread(f"thread_{AUTH_USER_ID}", AUTH_USER_ID) is None
        assert await store.get_snapshots_by_user(AUTH_USER_ID) == []
        assert await store.get_return_ledger(AUTH_USER_ID) is None

        # Other user's data intact.
        assert len(await storage.get_memories_by_user(OTHER_AUTH_USER_ID)) == 1
        other_thread = await store.get_thread(
            f"thread_{OTHER_AUTH_USER_ID}", OTHER_AUTH_USER_ID
        )
        assert other_thread is not None


class _FakeDb:
    """Minimal async fake DB that records delete_many calls per collection."""

    def __init__(self) -> None:
        self.deleted: dict[str, list] = {}

    def __getitem__(self, name: str) -> "_FakeCollection":
        return _FakeCollection(self.deleted, name)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FakeCollection:
    def __init__(self, store: dict, name: str) -> None:
        self._store = store
        self._name = name

    async def delete_many(self, query: dict) -> None:
        self._store.setdefault(self._name, []).append(query)


def _noop_upload_dir():
    return Path("/tmp/opencode-nonexistent-upload")


class TestDeletionAuxiliaryStores:
    async def test_delete_targets_all_auxiliary_collections(self, override_auth):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        await _seed_full_user(storage, store, AUTH_USER_ID)
        engine = ChronosEngine(storage=storage, temporal_store=store)
        fake_db = _FakeDb()
        with patch("chronos_engine.api.router.engine_instance", engine), patch(
            "chronos_engine.api.router.get_mongo_db"
        ) as mock_db, patch("chronos_engine.api.router._upload_dir") as mock_upload:
            mock_db.return_value = fake_db
            mock_upload.return_value = _noop_upload_dir()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(PREFIX)
        assert resp.status_code == 204

        expected = {
            "memories",
            "identity_states",
            "goals",
            "timeline_events",
            "patterns",
            "analysis_preferences",
            "chronos_states",
            "onboarding_sessions",
            "onboarding_responses",
        }
        assert expected.issubset(set(fake_db.deleted.keys()))
        # All deletes must be user-scoped, never a bare {} wipe.
        for queries in fake_db.deleted.values():
            for q in queries:
                assert "user_id" in q
                assert q["user_id"] == AUTH_USER_ID


class TestDeletionMediaRemoved:
    async def test_delete_removes_media_directory(self, override_auth, tmp_path):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        await _seed_full_user(storage, store, AUTH_USER_ID)
        await _seed_full_user(storage, store, OTHER_AUTH_USER_ID)

        upload_dir = tmp_path / "uploads"
        own_dir = upload_dir / AUTH_USER_ID
        other_dir = upload_dir / OTHER_AUTH_USER_ID
        own_dir.mkdir(parents=True)
        other_dir.mkdir(parents=True)
        (own_dir / "note.webm").write_bytes(b"x")
        (other_dir / "other.webm").write_bytes(b"y")

        engine = ChronosEngine(storage=storage, temporal_store=store)
        with patch("chronos_engine.api.router.engine_instance", engine), patch(
            "chronos_engine.api.router.get_mongo_db"
        ) as mock_db, patch("chronos_engine.api.router._upload_dir", return_value=upload_dir):
            mock_db.return_value = _FakeDb()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(PREFIX)
        assert resp.status_code == 204

        # Own media removed; other user's media untouched.
        assert not own_dir.exists()
        assert (other_dir / "other.webm").read_bytes() == b"y"


class TestMongoBackedDeletion:
    """Deletion through the real Mongo adapters (mongomock-motor)."""

    async def test_mongo_engine_and_auxiliary_deletion(self, override_auth, mock_db):
        from chronos_engine.storage.mongo_repository import (
            MongoStorageAdapter,
            MongoTemporalStore,
        )

        # The adapter resolves its DB through the module-level get_mongo_db.
        # Patch it for the whole test so seeding and deletion both hit mock_db.
        with patch(
            "chronos_engine.storage.mongo_repository.get_mongo_db", return_value=mock_db
        ):
            storage = MongoStorageAdapter()
            store = MongoTemporalStore(mock_db)

            # Seed engine runtime + temporal data for both users.
            await storage.save_memory(
                MemoryItem(
                    id=f"mem_{AUTH_USER_ID}", user_id=AUTH_USER_ID,
                    content="own", importance_score=0.7,
                )
            )
            await storage.save_memory(
                MemoryItem(
                    id=f"mem_{OTHER_AUTH_USER_ID}", user_id=OTHER_AUTH_USER_ID,
                    content="other", importance_score=0.7,
                )
            )
            own_thread = await store.save_thread(
                TemporalThread(
                    id=f"thread_{AUTH_USER_ID}", user_id=AUTH_USER_ID,
                    subject="own", status=TemporalThreadStatus.OPEN,
                    temporal_type=TemporalType.DECISION,
                )
            )
            await store.save_event(
                TemporalEvent(
                    id=f"ev_{AUTH_USER_ID}", thread_id=own_thread.id,
                    user_id=AUTH_USER_ID, description="event",
                    temporal_type=TemporalType.DECISION,
                )
            )
            await store.save_return_ledger(ReturnLedger(user_id=AUTH_USER_ID))
            other_thread = await store.save_thread(
                TemporalThread(
                    id=f"thread_{OTHER_AUTH_USER_ID}", user_id=OTHER_AUTH_USER_ID,
                    subject="other", status=TemporalThreadStatus.OPEN,
                    temporal_type=TemporalType.DECISION,
                )
            )

            # Seed auxiliary (app-layer + onboarding) collections directly.
            for col, user_field in [
                ("memories", "user_id"),
                ("identity_states", "user_id"),
                ("goals", "user_id"),
                ("timeline_events", "user_id"),
                ("patterns", "user_id"),
                ("analysis_preferences", "user_id"),
                ("chronos_states", "user_id"),
                ("onboarding_sessions", "user_id"),
                ("onboarding_responses", "user_id"),
            ]:
                await mock_db[col].insert_one({user_field: AUTH_USER_ID, "x": 1})
                await mock_db[col].insert_one({user_field: OTHER_AUTH_USER_ID, "x": 1})

            engine = ChronosEngine(storage=storage, temporal_store=store)
            with patch("chronos_engine.api.router.engine_instance", engine), patch(
                "chronos_engine.api.router.get_mongo_db", return_value=mock_db
            ), patch("chronos_engine.api.router._upload_dir") as mock_upload:
                mock_upload.return_value = _noop_upload_dir()
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    resp = await client.delete(PREFIX)
            assert resp.status_code == 204

            # Own engine data gone.
            assert await storage.get_memories_by_user(AUTH_USER_ID) == []
            assert await store.get_thread(
                f"thread_{AUTH_USER_ID}", AUTH_USER_ID
            ) is None
            assert await store.get_return_ledger(AUTH_USER_ID) is None

            # Other user's engine data intact.
            assert len(await storage.get_memories_by_user(OTHER_AUTH_USER_ID)) == 1
            assert other_thread is not None
            assert await store.get_thread(
                f"thread_{OTHER_AUTH_USER_ID}", OTHER_AUTH_USER_ID
            ) is not None

            # All auxiliary collections purged for this user only.
            for col in (
                "memories",
                "identity_states",
                "goals",
                "timeline_events",
                "patterns",
                "analysis_preferences",
                "chronos_states",
                "onboarding_sessions",
                "onboarding_responses",
            ):
                assert await mock_db[col].count_documents(
                    {"user_id": AUTH_USER_ID}
                ) == 0
                assert await mock_db[col].count_documents(
                    {"user_id": OTHER_AUTH_USER_ID}
                ) == 1
