"""Structured provider results.

An additive, structured result that providers may return alongside the plain
string returned by ``BaseLLMProvider.generate_response``. It carries only
metadata — never full prompts or responses, which keeps logging safe.
"""

from typing import Optional

from pydantic import BaseModel, Field


class LLMResult(BaseModel):
    text: str = ""
    provider: str = ""
    model: str = ""
    latency_ms: Optional[float] = None
    success: bool = False
    error_type: Optional[str] = None
