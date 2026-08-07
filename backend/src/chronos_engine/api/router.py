from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from chronos_engine.engine import ChronosEngine

router = APIRouter(prefix="/chronos", tags=["ChronOS Engine"])

# Global singleton engine instance (Dependency injection point)
engine_instance = ChronosEngine()


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
    """
    media_bytes = None
    file_name = None
    if file:
        media_bytes = await file.read()
        file_name = file.filename
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
            base64_data=base64_data,
            provider_key=provider_key,
            model_name=model_name,
        )
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
        return response.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ChronOS Engine Error: {str(e)}")


@router.get("/memories")
async def get_memories(user_id: str = "user_default", limit: int = 100) -> List[Dict[str, Any]]:
    memories = await engine_instance.get_memories(user_id, limit=limit)
    return [m.model_dump() for m in memories]


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


@router.post("/seed")
async def seed_state(user_id: str = "user_default") -> Dict[str, str]:
    await engine_instance.seed_initial_state(user_id)
    return {"status": "success", "message": f"Initial state seeded for user '{user_id}'"}
