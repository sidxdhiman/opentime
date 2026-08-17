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

    # Request structured JSON output via ``"format": "json"``. Default OFF:
    # reasoning models like ``qwen3:4b`` route their final answer into the
    # ``thinking`` channel when this is set, leaving ``response`` empty and
    # failing generation. The DEEP path prompts for JSON regardless and its
    # parser tolerates surrounding text, so JSON mode is opt-in only.
    format_json: bool = False
