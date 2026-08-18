"""Ollama provider configuration.

Settings are read from environment variables prefixed with ``OLLAMA_``:

* ``OLLAMA_BASE_URL``  — base URL of the local Ollama HTTP API.
* ``OLLAMA_MODEL``     — model name to use for generation.
* ``OLLAMA_TIMEOUT``   — per-request timeout in seconds.
* ``OLLAMA_ENABLED``   — whether the provider is active.

The provider is DISABLED by default so that existing deployments and tests
never unexpectedly activate Ollama. The base URL defaults to the standard
local Ollama endpoint but is never hard-coded in the provider itself.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OLLAMA_", env_file=None, extra="ignore")

    base_url: str = "http://localhost:11434"
    model: str = "llama3:latest"
    timeout: float = 60.0
    enabled: bool = False

    # Optional generation controls, passed through to Ollama's ``options``.
    # ``None`` (the default) preserves current behavior — nothing is sent, so
    # Ollama uses its own defaults. These are exposed only because they are
    # supported by the existing /api/generate client and tested; they are NOT
    # used to force aggressive limits.
    temperature: float | None = None
    num_ctx: int | None = None
    num_predict: int | None = None

    # Thinking-channel control, mapped to the supported top-level Ollama
    # ``think`` request field. NOTE: the installed runtime (Ollama 0.20.5 +
    # ``qwen3:4b``) ALWAYS generates thinking tokens — its template
    # unconditionally inserts the `` thinking`` prefix — so this flag only
    # controls whether thinking is split into its own channel (``thinking``)
    # or merged inline into ``response``. It does NOT reduce the
    # thinking-token count (no supported thinking-budget parameter exists in
    # the installed runtime), so it defaults to ``True`` to preserve current
    # behavior.
    thinking_enabled: bool = True

    # Per-reasoning-mode inference overrides, keyed by ``ReasoningMode`` value
    # (e.g. ``"REASON"``). Supported keys mirror the global knobs above and
    # take precedence over them for the plan's ``primary_mode``. Empty by
    # default so current behavior is preserved unless explicitly configured.
    mode_thinking_enabled: dict[str, bool] = Field(default_factory=dict)
    mode_num_predict: dict[str, int] = Field(default_factory=dict)

    # Timeout safety: when an output budget (``num_predict``) is in effect the
    # provider derives an effective per-request timeout of
    # ``max(timeout, num_predict / min_tokens_per_sec + timeout_margin)`` so a
    # deliberately configured generation budget can never be silently cut off
    # by the client timeout. ``min_tokens_per_sec`` is a conservative floor
    # (measured qwen3:4b throughput is ~26-34 tok/s) and ``timeout_margin`` is
    # the extra headroom in seconds.
    min_tokens_per_sec: float = 10.0
    timeout_margin: float = 30.0

    # Request structured JSON output via ``"format": "json"``. Default OFF:
    # reasoning models like ``qwen3:4b`` route their final answer into the
    # ``thinking`` channel when this is set, leaving ``response`` empty and
    # failing generation. The DEEP path prompts for JSON regardless and its
    # parser tolerates surrounding text, so JSON mode is opt-in only.
    format_json: bool = False
