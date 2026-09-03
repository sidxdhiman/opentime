import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from chronos_engine.core.models import EngineResponse, InteractionRecord
from chronos_engine.engine import ChronosEngine
from chronos_engine.storage.mongo_repository import MongoStorageAdapter, MongoTemporalStore
from chronos_engine.temporal.models import (
    ActiveTemporalContext,
    ActiveTemporalEvent,
    ReturnContext,
)
from chronos_engine.temporal.return_context import ReturnContextEngine
from opentime.api.dependencies import get_current_user
from opentime.application.auth.dto import UserResponse
from opentime.infrastructure.config import get_settings
from opentime.infrastructure.mongodb.client import get_mongo_db

logger = logging.getLogger(__name__)

# Maximum number of recent events included in the grounded thread context
# passed to the engine.  Keeps the context bounded and predictable.
_ACTIVE_THREAD_MAX_EVENTS = 10

# Temporal thread/event response models (subset of the full domain models,
# safe for API exposure — internal IDs like user_id are omitted).


class TemporalEventResponse(BaseModel):
    """The subset of a moment the Stories UI needs.

    Internal provenance (memory ids, confidence, importance) is intentionally
    excluded so it never becomes user-facing content.
    """

    id: str
    temporal_type: Optional[str] = None
    description: str = ""
    occurred_at: str
    recorded_at: str


class TemporalThreadResponse(BaseModel):
    """The subset of a Story the Stories UI needs.

    Contains identity, subject, presentation status, temporal type (kept
    secondary for human wording), timestamps, an accurate moment count and
    the chronological moments themselves. Internal confidence/importance and
    memory linkage are excluded from API exposure.
    """

    id: str
    temporal_type: Optional[str] = None
    subject: str = ""
    description: Optional[str] = None
    status: str = "OPEN"
    created_at: str
    updated_at: str
    event_count: int = 0
    user_archived: bool = False
    events: List[TemporalEventResponse] = []

router = APIRouter(prefix="/chronos/engine", tags=["ChronOS Engine"])

# Global engine instance backed by persistent MongoDB storage (memories via
# the storage adapter, temporal threads/events via the Phase 3D temporal
# store).
engine_instance = ChronosEngine(
    storage=MongoStorageAdapter(),
    temporal_store=MongoTemporalStore(),
)

# Phase 5D: deterministic return-loop context, backed by the same temporal
# store so meaningful-change detection is user-scoped and reuse the existing
# TemporalComparisonEngine relation vocabulary.  It is constructed per request
# from the current ``engine_instance`` so tests that patch ``engine_instance``
# (with an in-memory store) work unchanged.
def _return_context_engine() -> ReturnContextEngine:
    return ReturnContextEngine(temporal_store=engine_instance.temporal_store)

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]")


def _upload_dir() -> Path:
    settings = get_settings()
    directory = Path(settings.upload_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def _persist_media(user_id: str, file_name: str, media_bytes: bytes) -> Optional[str]:
    """Save the uploaded recording to disk and return its public URL."""
    if not media_bytes:
        return None

    safe_name = _SAFE_NAME.sub("_", file_name or f"recording_{uuid.uuid4().hex[:8]}.webm")
    user_dir = _upload_dir() / user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    target = user_dir / safe_name
    # Never overwrite an existing file.
    if target.exists():
        safe_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        target = user_dir / safe_name

    target.write_bytes(media_bytes)
    return f"/uploads/{user_id}/{safe_name}"


async def serve_user_media(
    user_id: str,
    file_name: str,
    current_user: UserResponse = Depends(get_current_user),
) -> FileResponse:
    """Serve an uploaded media file only to its owner.

    The authenticated user must match the ``user_id`` path parameter.
    Directory traversal is blocked by rejecting ``..`` and ``/`` in the
    file name.
    """
    auth_user_id = str(current_user.id)
    if auth_user_id != user_id:
        raise HTTPException(status_code=404, detail="Media not found")

    if ".." in file_name or "/" in file_name:
        raise HTTPException(status_code=404, detail="Media not found")

    media_path = _upload_dir() / user_id / file_name
    if not media_path.is_file():
        raise HTTPException(status_code=404, detail="Media not found")

    return FileResponse(path=str(media_path))


router.add_api_route(
    "/media/{user_id}/{file_name}",
    serve_user_media,
    methods=["GET"],
    tags=["ChronOS Engine"],
)


async def _persist_interaction(
    response: EngineResponse,
    storage=None,
) -> None:
    """Persist a lightweight InteractionRecord for conversation history.

    This lives at the API/application boundary — the ChronOS engine itself
    has no knowledge of conversation-history persistence.  A failure here
    must never break a successful engine response.
    """
    try:
        chronos = response.chronos_state
        psc = chronos.past_self_conversation if chronos else None
        refl_text = ""
        if chronos and chronos.temporal_reflection:
            tr = chronos.temporal_reflection
            if tr.used and tr.success and tr.reflection.strip():
                refl_text = tr.reflection.strip()
        record = InteractionRecord(
            id=response.id,
            user_id=response.user_id,
            user_content=response.original_input.content or "",
            input_type=(
                response.original_input.input_type.value
                if hasattr(response.original_input.input_type, "value")
                else str(response.original_input.input_type)
            ),
            final_response=response.final_response,
            provider_name=response.provider_name,
            model_name=response.model_name,
            processing_time_ms=response.processing_time_ms,
            past_self_opening=psc.opening if psc and psc.should_surface else "",
            past_self_context=psc.context if psc and psc.should_surface else "",
            past_self_bridge=psc.bridge if psc and psc.should_surface else "",
            past_self_question=psc.question if psc and psc.should_surface else "",
            past_self_reflection=refl_text,
        )
        target_storage = storage or engine_instance.storage
        await target_storage.save_interaction(record)
    except Exception:
        logger.warning(
            "Failed to persist interaction for user=%s response=%s",
            response.user_id,
            response.id,
            exc_info=True,
        )


# ── Phase 4F: Active thread context resolution ───────────────────────────


async def _resolve_active_thread(
    active_thread_id: Optional[str],
    user_id: str,
) -> Optional[ActiveTemporalContext]:
    """Resolve an active thread ID into a grounded, bounded context.

    Called at the API boundary *before* the engine runs.  Loads the thread
    through the temporal store (which enforces user ownership), fetches
    recent events in chronological order, and returns a minimal snapshot.
    Returns ``None`` when no thread ID is provided.
    """
    if not active_thread_id:
        return None

    thread = await engine_instance.temporal_store.get_thread(
        active_thread_id, user_id
    )
    if thread is None:
        raise HTTPException(
            status_code=404,
            detail="Temporal thread not found or does not belong to this user",
        )

    events = await engine_instance.temporal_store.get_events_by_thread(
        active_thread_id, user_id
    )
    # Chronological order (earliest first), bounded
    events.sort(key=lambda e: e.occurred_at)
    bounded_events = events[:_ACTIVE_THREAD_MAX_EVENTS]

    origin_event = bounded_events[0] if bounded_events else None

    return ActiveTemporalContext(
        thread_id=thread.id,
        subject=thread.subject,
        description=thread.description,
        temporal_type=(
            thread.temporal_type.value if thread.temporal_type else None
        ),
        status=thread.status.value,
        origin_description=origin_event.description if origin_event else None,
        origin_occurred_at=origin_event.occurred_at if origin_event else None,
        recent_events=[
            ActiveTemporalEvent(
                description=e.description,
                temporal_type=(
                    e.temporal_type.value if e.temporal_type else None
                ),
                occurred_at=e.occurred_at,
            )
            for e in bounded_events
        ],
    )


class ProcessInputRequest(BaseModel):
    content: Optional[str] = None
    input_type: str = "text"
    base64_data: Optional[str] = None
    file_name: Optional[str] = None
    provider_key: str = "chronos"
    model_name: Optional[str] = None
    active_thread_id: Optional[str] = None


@router.post("/process", status_code=status.HTTP_200_OK)
async def process_input(
    current_user: UserResponse = Depends(get_current_user),
    content: Optional[str] = Form(None),
    input_type: str = Form("text"),
    provider_key: str = Form("chronos"),
    model_name: Optional[str] = Form(None),
    base64_data: Optional[str] = Form(None),
    active_thread_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
) -> Dict[str, Any]:
    """
    Core Input Processing Endpoint for ChronOS Engine.
    Handles Text, Voice Audio Files/Recordings, and Video Files/Recordings.
    Memories are persisted in MongoDB and media files are saved to disk.

    The user identity is derived from the authenticated bearer token.  A
    client-supplied ``user_id`` is never trusted for data access.
    """
    user_id = str(current_user.id)
    media_bytes = None
    file_name = None
    media_url = None
    if file:
        media_bytes = await file.read()
        file_name = file.filename
        media_url = await _persist_media(user_id, file_name, media_bytes)
        if not input_type or input_type == "text":
            if file.content_type and "audio" in file.content_type:
                input_type = "audio"
            elif file.content_type and "video" in file.content_type:
                input_type = "video"

    active_context = await _resolve_active_thread(active_thread_id, user_id)

    try:
        response = await engine_instance.process_user_input(
            user_id=user_id,
            content=content,
            input_type=input_type,
            media_bytes=media_bytes,
            file_name=file_name,
            media_url=media_url,
            base64_data=base64_data,
            provider_key=provider_key,
            model_name=model_name,
            active_temporal_context=active_context,
        )
        await _persist_interaction(response)
        return response.model_dump()
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "ChronOS engine processing failed for user=%s", user_id
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your input.",
        )


@router.post("/process-json", status_code=status.HTTP_200_OK)
async def process_input_json(
    payload: ProcessInputRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """JSON variant of input processing endpoint.

    The user identity always comes from the authenticated bearer token, never
    from the request body.
    """
    user_id = str(current_user.id)
    active_context = await _resolve_active_thread(
        payload.active_thread_id, user_id
    )
    try:
        response = await engine_instance.process_user_input(
            user_id=user_id,
            content=payload.content,
            input_type=payload.input_type,
            base64_data=payload.base64_data,
            file_name=payload.file_name,
            provider_key=payload.provider_key,
            model_name=payload.model_name,
            active_temporal_context=active_context,
        )
        await _persist_interaction(response)
        return response.model_dump()
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "ChronOS engine processing failed for user=%s", user_id
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your input.",
        )


@router.get("/memories")
async def get_memories(
    current_user: UserResponse = Depends(get_current_user),
    limit: int = 100,
) -> List[Dict[str, Any]]:
    user_id = str(current_user.id)
    memories = await engine_instance.get_memories(user_id, limit=limit)
    result = []
    for m in memories:
        d = m.model_dump(mode="json")
        d.pop("embedding", None)  # embeddings are never exposed through the API
        result.append(d)
    return result


@router.get("/timeline")
async def get_timeline(
    current_user: UserResponse = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    user_id = str(current_user.id)
    events = await engine_instance.get_timeline(user_id)
    return [e.model_dump() for e in events]


@router.get("/identity")
async def get_identity(
    current_user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    user_id = str(current_user.id)
    identity = await engine_instance.get_identity(user_id)
    return identity.model_dump()


@router.get("/reflections")
async def get_reflections(
    current_user: UserResponse = Depends(get_current_user),
    days_back: int = 30,
) -> List[Dict[str, Any]]:
    user_id = str(current_user.id)
    reflections = await engine_instance.get_reflections(user_id, days_back=days_back)
    return [r.model_dump() for r in reflections]


@router.get("/patterns")
async def get_patterns(
    current_user: UserResponse = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    user_id = str(current_user.id)
    patterns = await engine_instance.get_patterns(user_id)
    return [p.model_dump() for p in patterns]


@router.get("/providers")
async def get_providers() -> Dict[str, Any]:
    return {
        "active": engine_instance.llm_registry._active_provider_key,
        "available": engine_instance.llm_registry.list_providers(),
    }


@router.get("/interactions")
async def get_interactions(
    current_user: UserResponse = Depends(get_current_user),
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Recent ChronOS interactions for conversation history."""
    user_id = str(current_user.id)
    records = await engine_instance.storage.get_interactions_by_user(
        user_id, limit=limit
    )
    return [
        {
            "id": r.id,
            "user_content": r.user_content,
            "input_type": r.input_type,
            "final_response": r.final_response,
            "provider_name": r.provider_name,
            "model_name": r.model_name,
            "processing_time_ms": r.processing_time_ms,
            "created_at": r.created_at.isoformat(),
            "past_self_opening": r.past_self_opening,
            "past_self_context": r.past_self_context,
            "past_self_bridge": r.past_self_bridge,
            "past_self_question": r.past_self_question,
            "past_self_reflection": r.past_self_reflection,
        }
        for r in records
    ]


def _thread_response(thread, events) -> TemporalThreadResponse:
    """Build the user-safe Story response from a thread and its moments."""
    return TemporalThreadResponse(
        id=thread.id,
        temporal_type=thread.temporal_type.value if thread.temporal_type else None,
        subject=thread.subject,
        description=thread.description,
        status=thread.status.value,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
        event_count=len(events),
        user_archived=thread.user_archived,
        events=[
            TemporalEventResponse(
                id=e.id,
                temporal_type=e.temporal_type.value if e.temporal_type else None,
                description=e.description,
                occurred_at=e.occurred_at.isoformat(),
                recorded_at=e.recorded_at.isoformat(),
            )
            for e in events
        ],
    )


@router.get("/threads")
async def get_threads(
    current_user: UserResponse = Depends(get_current_user),
) -> List[TemporalThreadResponse]:
    """List all Stories for the authenticated user, newest first.

    Each response already contains its chronological moments, so the Stories
    view renders with a single request — no per-story detail fetch (N+1 fix).
    Internal IDs and metadata (confidence, importance, memory linkage) are
    never exposed.
    """
    user_id = str(current_user.id)
    threads = await engine_instance.temporal_store.get_threads_by_user(user_id)
    result: List[TemporalThreadResponse] = []
    for t in threads:
        events = await engine_instance.temporal_store.get_events_by_thread(t.id, user_id)
        result.append(_thread_response(t, events))
    return result


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> TemporalThreadResponse:
    """Get one Story with all its moments for the authenticated user."""
    user_id = str(current_user.id)
    thread = await engine_instance.temporal_store.get_thread(thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    events = await engine_instance.temporal_store.get_events_by_thread(thread_id, user_id)
    return _thread_response(thread, events)


def _memory_media_path(user_id: str, memory: Any) -> Path | None:
    """Resolve the on-disk path of a memory's own media, if it is user-owned.

    The memory's ``metadata["media_url"]`` is a server-authoritative
    ``/uploads/{user_id}/{file_name}`` reference. We only ever delete media
    that (a) is owned by this user and (b) lives directly under this user's
    upload directory. Anything else (missing, malformed, foreign, or pointing
    outside the user's own dir) is treated as not deletable here and returns
    ``None`` so unrelated media is never touched.
    """
    media_url = (memory.metadata or {}).get("media_url")
    if not media_url:
        return None
    prefix = f"/uploads/{user_id}/"
    if not isinstance(media_url, str) or not media_url.startswith(prefix):
        return None
    file_name = media_url[len(prefix):]
    if (
        not file_name
        or ".." in file_name
        or "/" in file_name
        or "\\" in file_name
    ):
        return None
    return _upload_dir() / user_id / file_name


@router.delete(
    "/memories/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_memory(
    memory_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    """Permanently delete one memory and its associated media, owned by the user.

    The memory record is removed and the store purges every reference to it
    (other memories' links, timeline, reflections, patterns, and temporal
    threads/events/snapshots). Any media the memory itself owns (per its
    ``metadata["media_url"]``) is purged on disk too, so deleting a memory does
    not leave its private media behind.

    The user's own media file is unlinked BEFORE the record is removed: a
    failed media purge therefore surfaces as an HTTP error (no false 204) and
    the memory record remains intact so a retry is safe and idempotent.

    - 401 when unauthenticated
    - 404 when the memory does not exist for this user
    - the identity is always the authenticated user; a client-supplied
      ``user_id`` is never read or trusted.
    """
    user_id = str(current_user.id)
    memory = await engine_instance.get_memory(user_id, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    media_path = _memory_media_path(user_id, memory)
    if media_path is not None:
        try:
            if media_path.is_file():
                media_path.unlink()
        except Exception:
            logger.exception(
                "Failed to delete media for memory=%s user=%s", memory_id, user_id
            )
            raise HTTPException(
                status_code=500,
                detail="Memory deletion could not fully complete.",
            )

    deleted = await engine_instance.delete_memory(user_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")


@router.post("/threads/{thread_id}/archive")
async def archive_thread(
    thread_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> TemporalThreadResponse:
    """User-controlled archive of a Story (presentation-level, Phase 5E-C).

    Sets a presentation flag so the Story no longer appears as an active/
    ongoing Story and is excluded from future continuation matches. It does
    NOT mutate the deterministic lifecycle ``status`` and does NOT delete or
    rewrite any historical events — the user can restore it later.

    Ownership is enforced via the authenticated user.
    """
    user_id = str(current_user.id)
    thread = await engine_instance.set_thread_user_archived(
        user_id, thread_id, archived=True
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    events = await engine_instance.temporal_store.get_events_by_thread(thread_id, user_id)
    return _thread_response(thread, events)


@router.post("/threads/{thread_id}/restore")
async def restore_thread(
    thread_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> TemporalThreadResponse:
    """Restore a previously archived Story (presentation-level).

    Clears the user-controlled archive flag so the Story is active again.
    Historical evidence is untouched. Ownership enforced via auth.
    """
    user_id = str(current_user.id)
    thread = await engine_instance.set_thread_user_archived(
        user_id, thread_id, archived=False
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    events = await engine_instance.temporal_store.get_events_by_thread(thread_id, user_id)
    return _thread_response(thread, events)


class ReturnContextEnabledRequest(BaseModel):
    enabled: bool


async def _latest_interaction_at(user_id: str) -> Optional[datetime]:
    """Newest interaction's ``created_at`` — the "previous visit" anchor.

    Uses the existing user-scoped interaction read (bounded to the latest
    record). No new timestamp field is added: this reuses what the storage
    adapter already persists.
    """
    records = await engine_instance.storage.get_interactions_by_user(
        user_id, limit=1
    )
    if not records:
        return None
    return records[0].created_at


@router.get("/return-context")
async def get_return_context(
    current_user: UserResponse = Depends(get_current_user),
) -> ReturnContext:
    """Return the user's grounded return context (Phase 5D).

    Computed deterministically from stored temporal activity; user-scoped to
    the authenticated user; never fabricated; no AI. The surfaced marker is
    advanced so the identical insight is not shown repeatedly.
    """
    user_id = str(current_user.id)
    latest_at = await _latest_interaction_at(user_id)
    return await _return_context_engine().build(user_id, latest_interaction_at=latest_at)


@router.patch("/return-context")
async def set_return_context_preference(
    payload: ReturnContextEnabledRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """Set the user's in-app return-hook preference (Phase 5D, Part 19).

    Honors a real behavior: when ``enabled`` is false, the in-app return hook
    stops surfacing for this user.
    """
    user_id = str(current_user.id)
    await _return_context_engine().set_enabled(user_id, payload.enabled)
    return {"enabled": payload.enabled}


@router.post("/seed")
async def seed_state(
    current_user: UserResponse = Depends(get_current_user),
) -> Dict[str, str]:
    """Restricted developer/tooling seeding endpoint.

    Only enabled when ``debug=True`` (local/test environments). In production
    this endpoint is unavailable so arbitrary, unmarked data cannot be
    injected into a user's engine.
    """
    if not get_settings().debug:
        raise HTTPException(status_code=404, detail="Not found")
    user_id = str(current_user.id)
    await engine_instance.seed_initial_state(user_id)
    return {"status": "success", "message": f"Initial state seeded for user '{user_id}'"}


@router.get("/export")
async def export_user_data(
    current_user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """Export the authenticated user's ChronOS engine data.

    Only the current user's own memories, timeline, identity, reflections,
    patterns, interactions and temporal threads/events are returned. No
    embeddings, provider secrets, credentials, or other users' data are
    included.
    """
    user_id = str(current_user.id)

    memories = []
    for m in await engine_instance.get_memories(user_id, limit=10000):
        d = m.model_dump(mode="json")
        d.pop("embedding", None)
        memories.append(d)

    timeline = [e.model_dump() for e in await engine_instance.get_timeline(user_id)]
    identity = await engine_instance.get_identity(user_id)
    reflections = [
        r.model_dump() for r in await engine_instance.get_reflections(user_id, days_back=36500)
    ]
    patterns = [p.model_dump() for p in await engine_instance.get_patterns(user_id)]
    interactions = [
        r.model_dump(mode="json")
        for r in await engine_instance.storage.get_interactions_by_user(user_id, limit=10000)
    ]

    threads = await engine_instance.temporal_store.get_threads_by_user(user_id)
    temporal_threads = []
    temporal_events = []
    for t in threads:
        temporal_threads.append(t.model_dump(mode="json"))
        temporal_events.extend(
            e.model_dump(mode="json")
            for e in await engine_instance.temporal_store.get_events_by_thread(t.id, user_id)
        )

    return {
        "user_id": user_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "memories": memories,
        "timeline": timeline,
        "identity": identity.model_dump(mode="json") if identity else None,
        "reflections": reflections,
        "patterns": patterns,
        "interactions": interactions,
        "temporal_threads": temporal_threads,
        "temporal_events": temporal_events,
    }


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_data(
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    """Permanently delete the authenticated user's ChronOS engine data.

    Removes everything user-scoped across every store:
      - engine runtime stores (memories, timeline, identity, reflections,
        patterns, interactions)
      - temporal domain stores (threads, events, snapshots, return ledgers)
      - application-layer Chronos domain (memories, identity states, goals,
        timeline events, patterns, analysis preferences, chronos states)
      - onboarding sessions and responses
      - uploaded media files on disk

    Other users' data is never touched.
    """
    user_id = str(current_user.id)
    await engine_instance.storage.delete_all_for_user(user_id)
    await engine_instance.temporal_store.delete_all_for_user(user_id)

    # Application-layer Chronos domain repos + onboarding (MongoDB).
    # A failure here must surface as an HTTP error (no false 204): the client
    # must know the permanent deletion did not fully complete.
    try:
        db = await get_mongo_db()
        for collection in (
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
            await db[collection].delete_many({"user_id": user_id})
    except Exception:
        logger.exception("Failed to delete application-layer data for user=%s", user_id)
        raise HTTPException(
            status_code=500,
            detail="Permanent deletion did not fully complete. No data was falsely reported as removed.",
        )

    # Uploaded media on disk. Failures surface as an HTTP error (no false 204).
    media_dir = _upload_dir() / user_id
    if media_dir.exists():
        try:
            for f in media_dir.iterdir():
                if f.is_file():
                    f.unlink()
            media_dir.rmdir()
        except Exception:
            logger.exception("Failed to delete media files for user=%s", user_id)
            raise HTTPException(
                status_code=500,
                detail="Permanent deletion did not fully complete. No data was falsely reported as removed.",
            )
