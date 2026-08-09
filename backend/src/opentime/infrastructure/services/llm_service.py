"""
LLM Service abstraction layer for Chronos.

The interface defines what Chronos needs from an LLM provider.
Concrete implementations (OpenAI, Anthropic, Mock) plug in via
dependency injection.

IMPORTANT: Never import OpenAI/Anthropic at the module level.
Import lazily only when the provider is actively used.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


class LLMService(ABC):
    """Chronos depends on this interface only – never on concrete providers."""

    @abstractmethod
    async def extract_structured(
        self, text: str, extraction_prompt: str, schema_hint: str = ""
    ) -> dict[str, Any]:
        """Extract structured JSON from free-form text."""
        ...

    @abstractmethod
    async def summarise(self, text: str, max_words: int = 80) -> str:
        """Return a short summary of the given text."""
        ...

    @abstractmethod
    async def extract_topics(self, text: str) -> list[str]:
        """Return a list of topics / keywords."""
        ...

    @abstractmethod
    async def extract_emotions(self, text: str) -> list[dict[str, Any]]:
        """Return detected emotions with confidence, if any."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...


# ---------------------------------------------------------------------------
# Mock implementation (development / testing)
# ---------------------------------------------------------------------------


class MockLLMService(LLMService):
    """
    Deterministic mock implementation for development and testing.
    Returns structurally valid but minimal responses.
    Never makes network calls.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    async def extract_structured(
        self, text: str, extraction_prompt: str, schema_hint: str = ""
    ) -> dict[str, Any]:
        # Return a minimal valid structure so the pipeline doesn't break
        return {
            "phase": None,
            "priorities": [],
            "interests": [],
            "concerns": [],
            "responsibilities": [],
            "projects": [],
            "changes": [],
        }

    async def summarise(self, text: str, max_words: int = 80) -> str:
        words = text.split()
        return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")

    async def extract_topics(self, text: str) -> list[str]:
        # Very naive keyword extraction from the first 200 chars
        stop = {"i", "the", "a", "an", "and", "or", "but", "in", "on", "at",
                "to", "for", "of", "my", "me", "is", "it", "s", "am", "are"}
        words = [w.strip(".,!?;:'\"").lower() for w in text[:200].split()]
        seen: list[str] = []
        for w in words:
            if w and w not in stop and len(w) > 3 and w not in seen:
                seen.append(w)
            if len(seen) >= 5:
                break
        return seen

    async def extract_emotions(self, text: str) -> list[dict[str, Any]]:
        return []   # Conservative – mock never infers emotions


# ---------------------------------------------------------------------------
# OpenAI implementation
# ---------------------------------------------------------------------------


class OpenAILLMService(LLMService):
    """
    Uses the openai Python library (>=1.0).
    Requires OPENAI_API_KEY in environment.
    Requires `pip install openai`.
    """

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self._model = model

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
            raise RuntimeError(
                "openai package not installed – run: pip install openai"
            ) from None

    async def _chat(self, system: str, user: str) -> str:
        client = self._client()
        resp = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        return resp.choices[0].message.content or ""

    async def extract_structured(
        self, text: str, extraction_prompt: str, schema_hint: str = ""
    ) -> dict[str, Any]:
        system = (
            "You are a structured data extraction assistant. "
            "Always respond with a single valid JSON object. "
            "Do not include markdown code blocks. "
            f"{schema_hint}"
        )
        raw = await self._chat(system, f"{extraction_prompt}\n\nText:\n{text}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("llm_json_parse_failed", raw=raw[:200])
            return {}

    async def summarise(self, text: str, max_words: int = 80) -> str:
        system = f"Summarise the following text in at most {max_words} words. Return only the summary."
        return await self._chat(system, text)

    async def extract_topics(self, text: str) -> list[str]:
        system = (
            "Extract up to 8 key topics/themes from the text. "
            "Return a JSON array of strings, e.g. [\"career\", \"health\"]."
        )
        raw = await self._chat(system, text)
        try:
            result = json.loads(raw)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            return []

    async def extract_emotions(self, text: str) -> list[dict[str, Any]]:
        system = (
            "Detect explicit or strongly implied emotions in the text. "
            "Return a JSON array: [{\"emotion\": \"...\", \"confidence\": 0.0-1.0}]. "
            "If none, return []. Be conservative – only include clearly evident emotions."
        )
        raw = await self._chat(system, text)
        try:
            result = json.loads(raw)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            return []


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_llm_service() -> LLMService:
    """
    Returns the appropriate LLM service based on environment variables.

    Priority:
      1. OPENAI_API_KEY → OpenAILLMService
      2. (future) ANTHROPIC_API_KEY → AnthropicLLMService
      3. Fallback → MockLLMService
    """
    if os.environ.get("OPENAI_API_KEY"):
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        logger.info("llm_service_openai", model=model)
        return OpenAILLMService(model=model)

    logger.info(
        "llm_service_mock",
        reason="No OPENAI_API_KEY set – using MockLLMService for development",
    )
    return MockLLMService()
