import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from chronos_engine.core.models import EngineResponse, InteractionRecord
from chronos_engine.engine import ChronosEngine
from chronos_engine.storage.mongo_repository import MongoStorageAdapter, MongoTemporalStore
from opentime.infrastructure.config import get_settings

logger = logging.getLogger(__name__)

# Temporal thread/event response models (subset of the full domain models,
# safe for API exposure — internal IDs like user_id are omitted).


class TemporalEventResponse(BaseModel):
    id: str
    thread_id: Optional[str] = None
    temporal_type: Optional[str] = None
    description: str = ""
    memory_id: Optional[str] = None
    occurred_at: str
    recorded_at: str
    importance: float = 0.5
    confidence: float = 0.5


class TemporalThreadResponse(BaseModel):
    id: str
    temporal_type: Optional[str] = None
    subject: str = ""
    description: Optional[str] = None
    status: str = "OPEN"
    origin_memory_id: Optional[str] = None
    related_memory_ids: List[str] = []
    importance: float = 0.5
    confidence: float = 0.5
    created_at: str
    updated_at: str
    event_count: int = 0
    events: List[TemporalEventResponse] = []

router = APIRouter(prefix="/chronos/engine", tags=["ChronOS Engine"])

# Global engine instance backed by persistent MongoDB storage (memories via
# the storage adapter, temporal threads/events via the Phase 3D temporal
# store).
engine_instance = ChronosEngine(
    storage=MongoStorageAdapter(),
    temporal_store=MongoTemporalStore(),
)

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


class ProcessInputRequest(BaseModel):
    user_id: str = "user_default"
    content: Optional[str] = None
    input_type: str = "text"
    base64_data: Optional[str] = None
    file_name: Optional[str] = None
    provider_key: str = "chronos"
    model_name: Optional[str] = None


@router.post("/process", status_code=status.HTTP_200_OK)
async def process_input(
    user_id: str = Form("user_default"),
    content: Optional[str] = Form(None),
    input_type: str = Form("text"),
    provider_key: str = Form("chronos"),
    model_name: Optional[str] = Form(None),
    base64_data: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
) -> Dict[str, Any]:
    """
    Core Input Processing Endpoint for ChronOS Engine.
    Handles Text, Voice Audio Files/Recordings, and Video Files/Recordings.
    Memories are persisted in MongoDB and media files are saved to disk.
    """
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
        )
        await _persist_interaction(response)
        return response.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ChronOS Engine Error: {str(e)}")


@router.post("/process-json", status_code=status.HTTP_200_OK)
async def process_input_json(payload: ProcessInputRequest) -> Dict[str, Any]:
    """JSON variant of input processing endpoint."""
    try:
        response = await engine_instance.process_user_input(
            user_id=payload.user_id,
            content=payload.content,
            input_type=payload.input_type,
            base64_data=payload.base64_data,
            file_name=payload.file_name,
            provider_key=payload.provider_key,
            model_name=payload.model_name,
        )
        await _persist_interaction(response)
        return response.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ChronOS Engine Error: {str(e)}")


@router.get("/memories")
async def get_memories(user_id: str = "user_default", limit: int = 100) -> List[Dict[str, Any]]:
    memories = await engine_instance.get_memories(user_id, limit=limit)
    result = []
    for m in memories:
        d = m.model_dump(mode="json")
        d.pop("embedding", None)  # embeddings are never exposed through the API
        result.append(d)
    return result


@router.get("/timeline")
async def get_timeline(user_id: str = "user_default") -> List[Dict[str, Any]]:
    events = await engine_instance.get_timeline(user_id)
    return [e.model_dump() for e in events]


@router.get("/identity")
async def get_identity(user_id: str = "user_default") -> Dict[str, Any]:
    identity = await engine_instance.get_identity(user_id)
    return identity.model_dump()


@router.get("/reflections")
async def get_reflections(user_id: str = "user_default", days_back: int = 30) -> List[Dict[str, Any]]:
    reflections = await engine_instance.get_reflections(user_id, days_back=days_back)
    return [r.model_dump() for r in reflections]


@router.get("/patterns")
async def get_patterns(user_id: str = "user_default") -> List[Dict[str, Any]]:
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
    user_id: str = "user_default", limit: int = 20
) -> List[Dict[str, Any]]:
    """Recent ChronOS interactions for conversation history."""
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


@router.get("/threads")
async def get_threads(user_id: str = "user_default") -> List[Dict[str, Any]]:
    """List all temporal threads for a user, newest first."""
    threads = await engine_instance.temporal_store.get_threads_by_user(user_id)
    return [
        {
            "id": t.id,
            "temporal_type": t.temporal_type.value if t.temporal_type else None,
            "subject": t.subject,
            "description": t.description,
            "status": t.status.value,
            "origin_memory_id": t.origin_memory_id,
            "related_memory_ids": t.related_memory_ids,
            "importance": t.importance,
            "confidence": t.confidence,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "event_count": len(t.related_memory_ids),
        }
        for t in threads
    ]


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    user_id: str = "user_default",
) -> Dict[str, Any]:
    """Get a specific temporal thread with all its events."""
    thread = await engine_instance.temporal_store.get_thread(thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    events = await engine_instance.temporal_store.get_events_by_thread(thread_id, user_id)
    return {
        "id": thread.id,
        "temporal_type": thread.temporal_type.value if thread.temporal_type else None,
        "subject": thread.subject,
        "description": thread.description,
        "status": thread.status.value,
        "origin_memory_id": thread.origin_memory_id,
        "related_memory_ids": thread.related_memory_ids,
        "importance": thread.importance,
        "confidence": thread.confidence,
        "created_at": thread.created_at.isoformat(),
        "updated_at": thread.updated_at.isoformat(),
        "event_count": len(events),
        "events": [
            {
                "id": e.id,
                "thread_id": e.thread_id,
                "temporal_type": e.temporal_type.value if e.temporal_type else None,
                "description": e.description,
                "memory_id": e.memory_id,
                "occurred_at": e.occurred_at.isoformat(),
                "recorded_at": e.recorded_at.isoformat(),
                "importance": e.importance,
                "confidence": e.confidence,
            }
            for e in events
        ],
    }


@router.post("/seed")
async def seed_state(user_id: str = "user_default") -> Dict[str, str]:
    await engine_instance.seed_initial_state(user_id)
    return {"status": "success", "message": f"Initial state seeded for user '{user_id}'"}
