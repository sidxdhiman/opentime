"""Model-agnostic inference options for a single provider call.

The DEEP path may tune the provider's inference controls per reasoning mode.
These options are deliberately generic: every field maps directly to a
supported Ollama request field/option, and the provider never interprets
reasoning modes itself — it only receives resolved knobs. This keeps the
provider model-agnostic and the mode policy in the executor/configuration.

``None`` means "use the configuration default", so an empty
``InferenceOptions`` preserves current behavior exactly.
"""

from pydantic import BaseModel


class InferenceOptions(BaseModel):
    """Resolved inference knobs for one provider call.

    * ``thinking_enabled`` — maps to the supported top-level Ollama ``think``
      field. NOTE: the installed runtime (Ollama 0.20.5 + ``qwen3:4b``) always
      generates thinking tokens; this flag only controls whether thinking is
      split into its own channel (``thinking``) or merged inline into
      ``response``. It does NOT reduce the thinking-token count.
    * ``num_predict`` — maps to ``options.num_predict``: a cap on TOTAL output
      tokens (thinking + answer). Must be large enough for the whole
      generation to finish, otherwise the JSON answer is truncated.
    * ``num_ctx`` / ``temperature`` — maps to the matching ``options.*``
      fields, passed through unchanged.
    """

    thinking_enabled: bool | None = None
    num_predict: int | None = None
    num_ctx: int | None = None
    temperature: float | None = None