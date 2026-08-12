import base64
import uuid
from typing import Any, Dict, Optional

from chronos_engine.core.models import InputType, UserInput


class MediaProcessor:
    """
    Input Processing Layer for Chronos Engine.
    Handles Text, Audio recordings/uploads, and Video recordings/uploads.
    Media files are persisted elsewhere; this layer only builds the metadata.
    """

    @staticmethod
    async def process_raw_input(
        user_id: str,
        content: Optional[str] = None,
        input_type: str = "text",
        media_bytes: Optional[bytes] = None,
        file_name: Optional[str] = None,
        base64_data: Optional[str] = None,
        media_url: Optional[str] = None,
    ) -> UserInput:
        parsed_type = InputType.TEXT
        if input_type in [t.value for t in InputType]:
            parsed_type = InputType(input_type)

        extracted_text = content or ""
        media_metadata: Dict[str, Any] = {}

        # Handle base64 encoded media if provided
        if base64_data and not media_bytes:
            if "," in base64_data:
                header, base64_str = base64_data.split(",", 1)
                if "audio" in header:
                    parsed_type = InputType.AUDIO
                elif "video" in header:
                    parsed_type = InputType.VIDEO
            else:
                base64_str = base64_data
            try:
                media_bytes = base64.b64decode(base64_str)
            except Exception:
                media_bytes = None

        if parsed_type in [InputType.AUDIO, InputType.VIDEO]:
            file_name = file_name or f"{parsed_type.value}_{uuid.uuid4().hex[:8]}.webm"
            media_metadata = MediaProcessor._extract_media_features(
                parsed_type, media_bytes, file_name
            )

            # Honest placeholder until real transcription (Whisper etc.) is wired in.
            if not extracted_text:
                extracted_text = (
                    "[Voice note - awaiting transcription]"
                    if parsed_type == InputType.AUDIO
                    else "[Video note - awaiting transcription]"
                )

        input_id = f"in_{uuid.uuid4().hex[:12]}"
        return UserInput(
            id=input_id,
            user_id=user_id,
            input_type=parsed_type,
            content=extracted_text,
            media_url=media_url or (f"/uploads/{file_name}" if file_name else None),
            file_name=file_name,
            media_metadata=media_metadata,
        )

    @staticmethod
    def _extract_media_features(
        input_type: InputType, media_bytes: Optional[bytes], file_name: str
    ) -> Dict[str, Any]:
        size_bytes = len(media_bytes) if media_bytes else 1024 * 50
        duration_est = round(max(2.5, size_bytes / 32000.0), 1)

        return {
            "format": file_name.split(".")[-1] if "." in file_name else "webm",
            "size_bytes": size_bytes,
            "estimated_duration_sec": duration_est,
            "media_type": input_type.value,
        }
