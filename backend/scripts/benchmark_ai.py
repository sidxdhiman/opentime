"""Phase 2E manual AI latency benchmark — NOT part of the automated test suite.

Run only when a local Ollama instance is installed and running:

    OLLAMA_ENABLED=true .venv/bin/python scripts/benchmark_ai.py

Runs three DEEP-path inputs (one INTERPRET, one REASON, one REFLECT) through the
full ChronOS engine, records each AI latency segment from ``latency_report()``
plus the actual prompt size, and prints a before/after-friendly table.

This is a manual diagnostic tool: it makes real provider calls and therefore
depends on Ollama availability. It is intentionally NOT wired into CI.
"""

import asyncio
import sys

from chronos_engine import ChronosEngine
from chronos_engine.ai import AIExecutor
from chronos_engine.config import OllamaConfig
from chronos_engine.core.models import UserInput
from chronos_engine.llm import LLMRegistry, OllamaProvider

BENCHMARK_CASES = [
    (
        "INTERPRET",
        (
            "I'm frustrated because I'm stuck trying to finish ChronOS. "
            "Should I keep pushing or step back?"
        ),
    ),
    (
        "REASON",
        "Should I continue building ChronOS or focus on interview preparation?",
    ),
    (
        "REFLECT",
        (
            "Considering everything I've told you about ChronOS, "
            "do you think I should continue investing my time in it?"
        ),
    ),
]

# Seeded history so the model has real, citable evidence (otherwise a fresh
# user has no memories and any cited id is a hallucination).
SEED_INTERACTIONS = [
    "I am building ChronOS as a personal evolution engine on top of OpenTime.",
    "I keep starting new projects before finishing the current one.",
    "I planned to focus on ChronOS for the next three months.",
]


def _make_registry(config: OllamaConfig) -> LLMRegistry:
    registry = LLMRegistry()
    registry.register_provider("ollama", OllamaProvider(config=config))
    return registry


async def main() -> int:
    config = OllamaConfig()
    if not config.enabled:
        print("OLLAMA_ENABLED is false — refusing to run benchmark.")
        print("Set OLLAMA_ENABLED=true (and OLLAMA_MODEL) and retry.")
        return 1

    registry = _make_registry(config)
    engine = ChronosEngine(
        ai_executor=AIExecutor(llm_registry=registry, config=config),
        llm_registry=registry,
    )

    provider = registry.get_provider("ollama")
    health = await provider.health_check()
    print(f"health: reachable={health['reachable']} "
          f"model_available={health['model_available']} model={health['model']}")
    if not health["reachable"]:
        print("Ollama is not reachable. Is it installed and running?")
        return 1
    if not health["model_available"]:
        print(f"Configured model '{config.model}' is not installed on Ollama.")
        return 1

    for i, content in enumerate(SEED_INTERACTIONS, start=1):
        await engine.memory_system.add_interaction(
            UserInput(id=f"seed_{i}", user_id="benchmark_2e", content=content)
        )

    header = (
        f"{'case':<10} {'route':<7} {'model':<10} {'prompt_chars':>12} "
        f"{'tokens_est':>10} {'plan_ms':>8} {'provider_ms':>11} "
        f"{'total_ai_ms':>11} {'used':>5} {'fallback':>8}"
    )
    print("\n" + header)
    print("-" * len(header))

    try:
        for label, content in BENCHMARK_CASES:
            response = await engine.process_user_input(
                user_id="benchmark_2e",
                content=content,
                provider_key="chronos",
            )
            ai = response.ai_execution
            report = ai.latency_report()
            print(
                f"{label:<10} {response.ai_routing.path.value:<7} "
                f"{ai.model:<10} {report['prompt_chars']:>12} "
                f"{report['prompt_tokens_estimate']:>10} "
                f"{report['reasoning_plan_ms']:>8.2f} "
                f"{report['provider_latency_ms']:>11.2f} "
                f"{report['total_ai_ms']:>11.2f} "
                f"{str(ai.used):>5} {str(ai.fallback_used):>8}"
            )
        return 0
    finally:
        await provider.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
