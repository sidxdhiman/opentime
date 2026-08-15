"""Manual Ollama smoke test — NOT part of the automated test suite.

Run this only when a local Ollama instance is installed and running:

    OLLAMA_ENABLED=true .venv/bin/python scripts/smoke_ollama.py

Performs:
    1. Health check against the configured Ollama instance.
    2. A simple generation round-trip.

Expected successful output:

    health: reachable=True model_available=True model=qwen3:4b
    CHRONOS_OLLAMA_OK
"""

import asyncio
import sys

from chronos_engine.config import OllamaConfig
from chronos_engine.core.models import PromptContext, RetrievedContext, UserInput
from chronos_engine.llm import OllamaProvider


async def main() -> int:
    config = OllamaConfig()
    if not config.enabled:
        print("OLLAMA_ENABLED is false — refusing to run smoke test.")
        print("Set OLLAMA_ENABLED=true (and OLLAMA_MODEL) and retry.")
        return 1

    provider = OllamaProvider(config=config)
    try:
        health = await provider.health_check()
        print(f"health: reachable={health['reachable']} "
              f"model_available={health['model_available']} model={health['model']}")
        if not health["reachable"]:
            print("Ollama is not reachable. Is it installed and running?")
            return 1
        if not health["model_available"]:
            print(f"Configured model '{config.model}' is not installed on Ollama.")
            return 1

        prompt = PromptContext(
            current_input=UserInput(
                id="smoke", user_id="smoke", content="Reply with exactly: CHRONOS_OLLAMA_OK"
            ),
            retrieved_context=RetrievedContext(),
            system_prompt="You are a helpful assistant.",
            user_prompt="Reply with exactly: CHRONOS_OLLAMA_OK",
        )
        result = await provider.generate(prompt)
        print(result.text)
        return 0
    finally:
        await provider.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
