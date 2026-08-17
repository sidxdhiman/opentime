"""Manual Ollama smoke test — NOT part of the automated test suite.

Run this only when a local Ollama instance is installed and running:

    OLLAMA_ENABLED=true .venv/bin/python scripts/smoke_ollama.py

Performs:
    1. Health check against the configured Ollama instance.
    2. A simple generation round-trip.
    3. Phase 2C end-to-end: user input -> Chronos analysis -> AIRouter=DEEP
       -> Ollama -> ResponseValidator -> final AI response.

Expected successful output:

    health: reachable=True model_available=True model=qwen3:4b
    CHRONOS_OLLAMA_OK
    route: DEEP | ai_used: True | fallback: False
    final_response:
    <the model's grounded natural-language response>
"""

import asyncio
import sys

from chronos_engine import ChronosEngine
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

        # Phase 2C end-to-end DEEP path.
        from chronos_engine.ai import AIExecutor

        registry = _make_registry_with(config)
        engine = ChronosEngine(
            ai_executor=AIExecutor(llm_registry=registry, config=config),
            llm_registry=registry,
        )
        response = await engine.process_user_input(
            user_id="smoke_e2e",
            content=(
                "Considering everything I've told you about ChronOS, "
                "do you think I should continue investing my time in it?"
            ),
            provider_key="chronos",
        )
        ai = response.ai_execution
        print(f"route: {response.ai_routing.path.value} | "
              f"ai_used: {ai.used} | fallback: {ai.fallback_used} | "
              f"latency_ms: {ai.latency_ms}")
        if not ai.used:
            print("AI was not used — inspect the deterministic fallback output below.")
        print("final_response:")
        print(response.final_response)
        return 0
    finally:
        await provider.close()


def _make_registry_with(config: OllamaConfig):
    from chronos_engine.llm import LLMRegistry

    registry = LLMRegistry()
    registry.register_provider("ollama", OllamaProvider(config=config))
    return registry


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
