"""Phase 2J manual LIGHT/DEEP smoke test — NOT part of the automated suite.

Run only when a local Ollama instance is installed and running AND the light
model has been manually installed:

    OLLAMA_ENABLED=true \
    OLLAMA_MODEL=qwen3:4b \
    OLLAMA_LIGHT_MODEL=qwen2.5:1.5b \
    .venv/bin/python scripts/smoke_light.py

Performs:
    1. Health check for BOTH the DEEP and LIGHT models.
    2. INTERPRET + CLASSIFY through the LIGHT tier (real AIExecutor), then one
       DEEP request through the full engine — verifying model separation
       (LIGHT -> qwen2.5:1.5b, DEEP -> qwen3:4b).
    3. Records model, prompt/generated tokens, latency, tokens/sec, success,
       fallback, validation, and VRAM when measurable.

Does NOT require both models for CI: it is a manual diagnostic tool and
refuses to run when a configured model is missing.
"""

import argparse
import asyncio
import shutil
import subprocess
import sys

import httpx

from chronos_engine.ai import (
    AIExecutor,
    InferencePolicy,
    InferenceTier,
    ModelCapability,
    ReasoningMode,
    ReasoningPlan,
)
from chronos_engine.config import OllamaConfig
from chronos_engine.core.models import RetrievedContext, UserInput
from chronos_engine.llm import LLMRegistry, OllamaProvider
from chronos_engine.routing.models import AIRoutingResult
from chronos_engine.state.models import ChronosState

INTERPRET_INPUT = "I'm frustrated because I'm stuck."
CLASSIFY_INPUT = "I don't know what I'm trying to do anymore."
DEEP_INPUT = (
    "Considering everything I've told you about ChronOS, "
    "do you think I should continue investing my time in it?"
)

PROMPT_TEMPLATE = (
    "ChronOS assistant. Respond ONLY with a JSON object matching this schema: "
    '{"interpretation": null, "reasoning": null, "reflection": null, '
    '"answer": string, "uncertainties": [], "evidence_used": []}. '
    "Keep the answer concise and grounded in the provided state."
)


def _gpu_mem_mb() -> int | None:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used",
             "--format=csv,noheader,nounits"],
            text=True,
        )
        return int(out.strip().splitlines()[0].strip())
    except (subprocess.CalledProcessError, ValueError, IndexError):
        return None


def _state(content: str) -> ChronosState:
    return ChronosState(
        id="smoke_2j",
        user_id="user_2j",
        current_input=UserInput(id="in_2j", user_id="user_2j", content=content),
        context=RetrievedContext(),
    )


def _deterministic():
    from chronos_engine.response.models import (
        ChronosInterpretation,
        DeterministicResponse,
    )
    from chronos_engine.state.models import EngineStateResult

    return DeterministicResponse(
        user_signal="input",
        chronos_interpretation=ChronosInterpretation(
            user_state_summary="n", intent_summary="n", context_summary="n"
        ),
        chronos_state=EngineStateResult(),
        rendered="deterministic",
    )


def _plan(mode: ReasoningMode) -> ReasoningPlan:
    return ReasoningPlan(
        modes=[mode, ReasoningMode.GENERATE],
        primary_mode=mode,
        reason="smoke",
        confidence=0.6,
    )


def _routing() -> AIRoutingResult:
    from chronos_engine.routing import RoutingPath

    return AIRoutingResult(
        use_ai=True, path=RoutingPath.DEEP, confidence=0.8, reason="smoke", signals=[]
    )


async def _direct_chat_metrics(client, base_url, model, user_text) -> dict:
    """Token/latency metrics from a raw /api/chat call (no engine involved)."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PROMPT_TEMPLATE},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 4096},
    }
    resp = await client.post(f"{base_url}/api/chat", json=payload)
    data = resp.json()
    eval_count = data.get("eval_count") or 0
    eval_duration = data.get("eval_duration") or 0
    prompt_count = data.get("prompt_eval_count") or 0
    tps = round(eval_count / (eval_duration / 1e9), 1) if eval_duration else 0.0
    return {
        "model": model,
        "prompt_tokens": prompt_count,
        "generated_tokens": eval_count,
        "tokens_per_sec": tps,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="ChronOS LIGHT/DEEP smoke test")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    config = OllamaConfig()
    if not config.enabled:
        print("OLLAMA_ENABLED is false — refusing to run smoke test.")
        return 1
    if not config.light_model:
        print("OLLAMA_LIGHT_MODEL is unset — LIGHT tier is unavailable.")
        return 1

    base_url = (args.base_url or config.base_url).rstrip("/")
    deep_model = config.model
    light_model = config.light_model

    provider = OllamaProvider(config=config)
    gpu_before = _gpu_mem_mb()
    print(f"gpu_mem_before_mib: {gpu_before}")
    print(f"deep_model: {deep_model}  light_model: {light_model}")

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
        tags = await client.get(f"{base_url}/api/tags")
        installed = {m.get("name", "") for m in (tags.json().get("models") or [])}
        print(f"installed_models: {sorted(installed)}")
        for model in (deep_model, light_model):
            if model not in installed:
                print(f"Model '{model}' is NOT installed — run `ollama pull {model}` "
                      f"first, then retry.")
                return 1

        # LIGHT tier: INTERPRET + CLASSIFY through the real AIExecutor.
        policy = InferencePolicy(
            config=config,
            available_models=[
                ModelCapability(provider="ollama", model=light_model, tier="LIGHT"),
                ModelCapability(provider="ollama", model=deep_model, tier="DEEP"),
            ],
        )
        registry = LLMRegistry()
        registry.register_provider("ollama", provider)
        executor = AIExecutor(llm_registry=registry, config=config)

        for label, user_text, mode in (
            ("INTERPRET", INTERPRET_INPUT, ReasoningMode.INTERPRET),
            ("CLASSIFY", CLASSIFY_INPUT, ReasoningMode.CLASSIFY),
        ):
            decision = policy.decide(_routing(), _plan(mode))
            if decision.tier != InferenceTier.LIGHT:
                print(f"[{label}] WARNING: policy did not select LIGHT "
                      f"(tier={decision.tier.value})")
            result = await executor.execute(
                _routing(), _state(user_text), _deterministic(),
                inference_policy_decision=decision,
            )
            metrics = await _direct_chat_metrics(client, base_url, light_model, user_text)
            validation = (
                result.validation_result.is_valid
                if result.validation_result is not None
                else False
            )
            print(
                f"[{label}] tier={result.tier} model={result.model} "
                f"success={result.success} fallback={result.fallback_used} "
                f"validation={'ok' if validation else 'FAIL'} "
                f"latency_ms={result.latency_ms} "
                f"prompt_tokens={metrics['prompt_tokens']} "
                f"generated_tokens={metrics['generated_tokens']} "
                f"tokens_per_sec={metrics['tokens_per_sec']}"
            )
            if result.model != light_model:
                print(f"[{label}] FAIL: expected LIGHT model '{light_model}'.")
                return 1

        # DEEP tier: one real request through the full engine (REASON -> DEEP).
        from chronos_engine import ChronosEngine

        engine = ChronosEngine(ai_executor=executor, llm_registry=registry)
        response = await engine.process_user_input(
            user_id="user_2j_smoke", content=DEEP_INPUT, provider_key="chronos"
        )
        ai = response.ai_execution
        deep_metrics = await _direct_chat_metrics(client, base_url, deep_model, DEEP_INPUT)
        print(
            f"[DEEP] route={response.ai_routing.path.value} tier={ai.tier} "
            f"model={ai.model} success={ai.success} fallback={ai.fallback_used} "
            f"latency_ms={ai.latency_ms} "
            f"prompt_tokens={deep_metrics['prompt_tokens']} "
            f"generated_tokens={deep_metrics['generated_tokens']} "
            f"tokens_per_sec={deep_metrics['tokens_per_sec']}"
        )
        if ai.model != deep_model:
            print(f"[DEEP] FAIL: expected DEEP model '{deep_model}'.")
            return 1

    gpu_after = _gpu_mem_mb()
    print(f"gpu_mem_after_mib: {gpu_after} "
          f"(delta {gpu_after - gpu_before} if both measured)")
    print("SMOKE_2J_OK — LIGHT and DEEP models executed separately.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))