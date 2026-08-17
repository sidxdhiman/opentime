"""Robust parsing of the structured AI output contract.

The provider is asked to return a single JSON object. This parser is
deliberately forgiving — it tolerates markdown fences, prose around the JSON,
and string-escape quirks — but strict about the contract: it rejects output
missing the required ``answer`` or citing evidence that was never provided.

On any failure it raises ``AIResponseParseError`` with a stable ``reason`` so
the executor can fall back deterministically.
"""

import json
import re

from pydantic import ValidationError

from chronos_engine.ai.reasoning.models import AIReasoningResult

MALFORMED_JSON = "MALFORMED_JSON"
MISSING_ANSWER = "MISSING_ANSWER"
HALLUCINATED_EVIDENCE = "HALLUCINATED_EVIDENCE"

_EVIDENCE_TAG = re.compile(r"\[(memory|timeline|pattern):([^\]]+)\]")


class AIResponseParseError(ValueError):
    """Raised when the AI output does not satisfy the structured contract."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"AI response could not be parsed: {reason}")


class AIResponseParser:
    """Parses and validates a provider response into ``AIReasoningResult``."""

    def parse(
        self,
        text: str,
        allowed_evidence_ids: set[str] | None = None,
    ) -> AIReasoningResult:
        if not text or not text.strip():
            raise AIResponseParseError(MALFORMED_JSON)

        payload = self._extract_json(text)
        if payload is None:
            raise AIResponseParseError(MALFORMED_JSON)

        try:
            result = AIReasoningResult.model_validate(payload)
        except ValidationError:
            raise AIResponseParseError(MALFORMED_JSON) from None

        if not result.answer or not result.answer.strip():
            raise AIResponseParseError(MISSING_ANSWER)

        if allowed_evidence_ids:
            cited: set[str] = set()
            for entry in result.evidence_used:
                match = _EVIDENCE_TAG.fullmatch(entry.strip())
                if match is not None:
                    cited.add(match.group(2))
                else:
                    cited.add(entry.strip())
            if cited and not cited.issubset(allowed_evidence_ids):
                raise AIResponseParseError(HALLUCINATED_EVIDENCE)

        return result

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str):
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except ValueError:
            pass
        return _first_json_object(text)


def _first_json_object(text: str):
    """Extract the first balanced JSON object (string/escape aware)."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    payload = json.loads(candidate)
                except ValueError:
                    return None
                return payload if isinstance(payload, dict) else None
    return None
