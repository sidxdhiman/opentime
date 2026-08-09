"""
EmbeddingService interface + implementations.

The embedding dimension is configurable.
Embeddings are stored in memories.embedding as list[float], ready for
MongoDB Atlas Vector Search.
"""

from __future__ import annotations

import hashlib
import math
import os
from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger()


class EmbeddingService(ABC):
    @abstractmethod
    async def generate_embedding(self, text: str) -> list[float]:
        """Return a normalised embedding vector for the given text."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...


# ---------------------------------------------------------------------------
# Mock / deterministic stub (for development and testing)
# ---------------------------------------------------------------------------


class MockEmbeddingService(EmbeddingService):
    """
    Produces a deterministic 256-dimensional vector from a hash of the text.
    NOT semantically meaningful – only for dev/test so the pipeline runs
    end-to-end without an API key.
    """

    _DIM = 256

    @property
    def dimensions(self) -> int:
        return self._DIM

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate_embedding(self, text: str) -> list[float]:
        # SHA-256 → 32 bytes → 32 floats, then pad/truncate to _DIM
        digest = hashlib.sha256(text.encode()).digest()
        floats = [b / 255.0 for b in digest]  # 32 values in [0,1]
        # Tile to fill _DIM
        tiled = (floats * math.ceil(self._DIM / len(floats)))[: self._DIM]
        # L2 normalise
        norm = math.sqrt(sum(x * x for x in tiled)) or 1.0
        return [x / norm for x in tiled]


# ---------------------------------------------------------------------------
# OpenAI text-embedding-3-small (1536 dims)
# ---------------------------------------------------------------------------


class OpenAIEmbeddingService(EmbeddingService):
    """
    Requires openai>=1.0 and OPENAI_API_KEY.
    """

    _DIM = 1536

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self._model = model

    @property
    def dimensions(self) -> int:
        return self._DIM

    @property
    def provider_name(self) -> str:
        return f"openai:{self._model}"

    def _client(self):  # type: ignore[return]
        try:
            import openai  # noqa: PLC0415
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set")
            return openai.AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise RuntimeError("openai not installed") from None

    async def generate_embedding(self, text: str) -> list[float]:
        client = self._client()
        resp = await client.embeddings.create(model=self._model, input=text)
        return resp.data[0].embedding


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_embedding_service() -> EmbeddingService:
    if os.environ.get("OPENAI_API_KEY"):
        model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
        logger.info("embedding_service_openai", model=model)
        return OpenAIEmbeddingService(model=model)

    logger.info(
        "embedding_service_mock",
        reason="No OPENAI_API_KEY – using MockEmbeddingService",
    )
    return MockEmbeddingService()
