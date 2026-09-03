"""Phase 5G-F tests: per-memory deletion purges the memory's own media.

Closing a data-lifecycle gap: deleting a single memory previously left its
associated on-disk media (referenced by ``metadata["media_url"]``) behind, so
an orphaned private file remained servable to its owner.

These tests verify, for the user-scoped DELETE /memories/{id} endpoint:
- the memory's own user-owned media file is unlinked when the memory is deleted
- a failed media purge surfaces as 500 (no false 204) and the memory record is
  retained so a retry is safe and idempotent
- deleting again once the media is already gone still returns 204
- media owned by other users is never touched
- media URLs that are foreign or malformed (path traversal, out-of-dir) are
  never unlinked, and the memory itself is still deleted
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi import status
from httpx import ASGITransport, AsyncClient

from chronos_engine.core.models import MemoryItem
from chronos_engine.engine import ChronosEngine
from chronos_engine.storage import InMemoryStorageAdapter, InMemoryTemporalStore
from opentime.main import app
from tests.conftest import AUTH_USER_ID, OTHER_AUTH_USER_ID

PREFIX = "/api/v1/chronos/engine"
BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _patch_engine(storage, store):
    engine = ChronosEngine(storage=storage, temporal_store=store)
    return patch("chronos_engine.api.router.engine_instance", engine)


def _media_memory(storage, user_id, memory_id, media_url):
    return storage.save_memory(
        MemoryItem(
            id=memory_id,
            user_id=user_id,
            content="a memory with media",
            timestamp=BASE,
            metadata={"media_url": media_url},
        )
    )


def _make_upload_dir(upload_root, user_id, file_name, data=b"x"):
    user_dir = upload_root / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / file_name
    path.write_bytes(data)
    return path


class TestMemoryMediaPurge:
    async def test_delete_purges_owned_media_and_record(self, override_auth, tmp_path):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        upload_dir = tmp_path / "uploads"
        media_path = _make_upload_dir(upload_dir, AUTH_USER_ID, "note.webm")
        await _media_memory(
            storage, AUTH_USER_ID, "mem_own",
            f"/uploads/{AUTH_USER_ID}/note.webm",
        )

        with _patch_engine(storage, store), patch(
            "chronos_engine.api.router._upload_dir", return_value=upload_dir
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"{PREFIX}/memories/mem_own")

        assert r.status_code == status.HTTP_204_NO_CONTENT
        assert not media_path.exists()
        remaining = await storage.get_memories_by_user(AUTH_USER_ID, limit=100)
        assert all(m.id != "mem_own" for m in remaining)

    async def test_media_already_gone_still_deletes(self, override_auth, tmp_path):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        upload_dir = tmp_path / "uploads"
        media_path = _make_upload_dir(upload_dir, AUTH_USER_ID, "note.webm")
        await _media_memory(
            storage, AUTH_USER_ID, "mem_own",
            f"/uploads/{AUTH_USER_ID}/note.webm",
        )
        # The file is already gone (e.g. cleaned by a prior partial run).
        media_path.unlink()

        with _patch_engine(storage, store), patch(
            "chronos_engine.api.router._upload_dir", return_value=upload_dir
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"{PREFIX}/memories/mem_own")

        assert r.status_code == status.HTTP_204_NO_CONTENT
        remaining = await storage.get_memories_by_user(AUTH_USER_ID, limit=100)
        assert all(m.id != "mem_own" for m in remaining)

    async def test_media_purge_failure_returns_500_and_keeps_record(
        self, override_auth, tmp_path
    ):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        upload_dir = tmp_path / "uploads"
        media_path = _make_upload_dir(upload_dir, AUTH_USER_ID, "note.webm")
        await _media_memory(
            storage, AUTH_USER_ID, "mem_own",
            f"/uploads/{AUTH_USER_ID}/note.webm",
        )

        engine = ChronosEngine(storage=storage, temporal_store=store)
        with patch("chronos_engine.api.router.engine_instance", engine), patch(
            "chronos_engine.api.router._upload_dir", return_value=upload_dir
        ):
            # Land a real path but force the unlink to fail.
            with patch(
                "chronos_engine.api.router._memory_media_path", return_value=media_path
            ), patch.object(
                Path, "unlink", side_effect=OSError("disk full")
            ):
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    r = await client.delete(f"{PREFIX}/memories/mem_own")

        assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        # The memory record must remain intact so a retry is safe.
        remaining = await storage.get_memories_by_user(AUTH_USER_ID, limit=100)
        assert any(m.id == "mem_own" for m in remaining)

    async def test_cross_user_media_untouched(self, override_auth, tmp_path):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        upload_dir = tmp_path / "uploads"
        own_media = _make_upload_dir(upload_dir, AUTH_USER_ID, "note.webm")
        other_media = _make_upload_dir(
            upload_dir, OTHER_AUTH_USER_ID, "other.webm", data=b"y"
        )
        await _media_memory(
            storage, AUTH_USER_ID, "mem_own",
            f"/uploads/{AUTH_USER_ID}/note.webm",
        )

        with _patch_engine(storage, store), patch(
            "chronos_engine.api.router._upload_dir", return_value=upload_dir
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"{PREFIX}/memories/mem_own")

        assert r.status_code == status.HTTP_204_NO_CONTENT
        assert not own_media.exists()
        assert other_media.read_bytes() == b"y"

    async def test_foreign_or_traversal_media_url_never_unlinked(
        self, override_auth, tmp_path
    ):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        upload_dir = tmp_path / "uploads"
        foreign_media = _make_upload_dir(
            upload_dir, OTHER_AUTH_USER_ID, "victim.webm", data=b"z"
        )
        # Own memory references a foreign user's file -> must not be unlinked.
        await _media_memory(
            storage, AUTH_USER_ID, "mem_foreign",
            f"/uploads/{OTHER_AUTH_USER_ID}/victim.webm",
        )
        # Own memory with a traversal media_url -> must not be unlinked.
        await _media_memory(
            storage, AUTH_USER_ID, "mem_traversal",
            f"/uploads/{AUTH_USER_ID}/../{OTHER_AUTH_USER_ID}/victim.webm",
        )

        with _patch_engine(storage, store), patch(
            "chronos_engine.api.router._upload_dir", return_value=upload_dir
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r1 = await client.delete(f"{PREFIX}/memories/mem_foreign")
                r2 = await client.delete(f"{PREFIX}/memories/mem_traversal")

        assert r1.status_code == status.HTTP_204_NO_CONTENT
        assert r2.status_code == status.HTTP_204_NO_CONTENT
        # The victim file is never deleted, and both memories are gone.
        assert foreign_media.read_bytes() == b"z"
        remaining = await storage.get_memories_by_user(AUTH_USER_ID, limit=100)
        assert all(m.id not in ("mem_foreign", "mem_traversal") for m in remaining)

    async def test_cross_user_cannot_delete_and_no_media_touched(
        self, override_auth, tmp_path
    ):
        storage = InMemoryStorageAdapter()
        store = InMemoryTemporalStore()
        upload_dir = tmp_path / "uploads"
        other_media = _make_upload_dir(
            upload_dir, OTHER_AUTH_USER_ID, "other.webm", data=b"y"
        )
        await _media_memory(
            storage, OTHER_AUTH_USER_ID, "mem_other",
            f"/uploads/{OTHER_AUTH_USER_ID}/other.webm",
        )

        # Authenticated as AUTH_USER_ID, tries to delete OTHER's memory.
        with _patch_engine(storage, store), patch(
            "chronos_engine.api.router._upload_dir", return_value=upload_dir
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"{PREFIX}/memories/mem_other")

        assert r.status_code == status.HTTP_404_NOT_FOUND
        assert other_media.read_bytes() == b"y"
        remaining = await storage.get_memories_by_user(OTHER_AUTH_USER_ID, limit=100)
        assert any(m.id == "mem_other" for m in remaining)
