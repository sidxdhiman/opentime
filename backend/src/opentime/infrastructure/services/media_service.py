"""
Media processing service interface.

Audio/video support for the Genesis Memory step.
The interface is defined here; provider-specific implementations are
explicitly marked as TODO so real processing can be added without
changing calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class MediaTranscript:
    text: str
    language: str | None = None
    duration_seconds: float | None = None
    confidence: float = 1.0


class MediaService(ABC):
    @abstractmethod
    async def transcribe_audio(
        self, audio_bytes: bytes, filename: str
    ) -> MediaTranscript:
        """Transcribe audio bytes to text."""
        ...

    @abstractmethod
    async def extract_audio_from_video(self, video_bytes: bytes) -> bytes:
        """Extract audio track from video bytes."""
        ...

    @abstractmethod
    async def transcribe_video(
        self, video_bytes: bytes, filename: str
    ) -> MediaTranscript:
        """Transcribe video (extract audio first, then transcribe)."""
        ...


class StubMediaService(MediaService):
    """
    Stub implementation.

    TODO: Replace with real implementation using:
      - Whisper (openai.audio.transcriptions.create) for audio/video
      - FFmpeg (via subprocess) for audio extraction from video

    This stub returns a placeholder transcript so the pipeline
    can proceed without a real transcription provider.
    """

    async def transcribe_audio(
        self, audio_bytes: bytes, filename: str
    ) -> MediaTranscript:
        logger.warning(
            "media_service_stub_transcribe",
            filename=filename,
            note="StubMediaService – integrate real Whisper transcription here",
        )
        # TODO: Replace with: openai.audio.transcriptions.create(...)
        return MediaTranscript(
            text=f"[Audio transcription placeholder for: {filename}]",
            language=None,
            duration_seconds=None,
            confidence=0.0,
        )

    async def extract_audio_from_video(self, video_bytes: bytes) -> bytes:
        logger.warning(
            "media_service_stub_extract_audio",
            note="StubMediaService – integrate FFmpeg extraction here",
        )
        # TODO: Replace with: ffmpeg subprocess extraction
        return video_bytes  # pass-through stub

    async def transcribe_video(
        self, video_bytes: bytes, filename: str
    ) -> MediaTranscript:
        audio = await self.extract_audio_from_video(video_bytes)
        return await self.transcribe_audio(audio, filename)


def create_media_service() -> MediaService:
    # TODO: When OPENAI_API_KEY is available, return WhisperMediaService()
    return StubMediaService()
