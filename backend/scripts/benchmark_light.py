"""Phase 2I isolated LIGHT-tier benchmark — NOT part of the automated test suite.

Run only when a local Ollama instance is installed and running:

    OLLAMA_ENABLED=true .venv/bin/python scripts/benchmark_light.py
    .venv/bin/python scripts/benchmark_light.py --model qwen3:4b

This is an ISOLATED diagnostic tool for evaluating small local models on the
ChronOS LIGHT workload. It deliberately does NOT touch the engine, the
inference policy, or any production component: it speaks directly to Ollama's
``/api/chat`` endpoint and records timing, token, VRAM, and JSON-quality
metrics for each LIGHT task.

Four LIGHT tasks are exercised (mirroring the planned LIGHT tier):

    A. INTERPRET                 — "I'm frustrated because I'm stuck trying
                                    to finish ChronOS."
    B. INTERPRET + GENERATE      — "I'm exhausted and wondering whether this
                                    project is worth continuing."
    C. SIMPLE CLASSIFY           — "I don't know what I'm trying to do anymore."
    D. CONTEXTUAL INTERPRETATION — intent=PROBLEM_SOLVING, state=FRUSTRATED,
                                    goal=Build ChronOS, goal status=BLOCKED.

Every task requests the same structured contract:

    {"answer": "...", "uncertainties": [], "evidence_used": []}

Metrics recorded per task: total latency, prompt tokens, output tokens,
tokens/sec, thinking tokens (when the model emits a separate ``thinking``
channel), JSON parse success, and contract-field presence. VRAM usage and
GPU/CPU layer split are captured from ``nvidia-smi`` and ``ollama ps``.
"""

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import time

import httpx

from chronos_engine.config.ollama import OllamaConfig

CONTRACT_FIELDS = ("answer", "uncertainties", "evidence_used")

LIGHT_SYSTEM_PROMPT = (
    "ChronOS LIGHT assistant. You produce concise, grounded interpretations "
    "of brief user statements for a personal evolution engine. Respond ONLY "
    "with a JSON object matching this exact schema: "
    '{"answer": string, "uncertainties": string[], "evidence_used": string[]}. '
    "Keep the answer under 80 words. Do not invent facts; if something is "
    "unknown, list it in uncertainties."
)

TASKS = [
    (
        "A.INTERPRET",
        "I'm frustrated because I'm stuck trying to finish ChronOS.",
    ),
    (
        "B.INTERPRET+GENERATE",
        "I'm exhausted and wondering whether this project is worth continuing.",
    ),
    (
        "C.SIMPLE CLASSIFY",
        "I don't know what I'm trying to do anymore.",
    ),
    (
        "D.CONTEXTUAL",
        "Intent: PROBLEM_SOLVING. User state: FRUSTRATED. Goal: Build ChronOS. "
        "Goal status: BLOCKED. Interpret what the user needs right now.",
    ),
]


def _nvidia_used_mb() -> int | None:
    """Current GPU memory used (MiB), or None if nvidia-smi is unavailable."""
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        )
        return int(out.strip().splitlines()[0].strip())
    except (subprocess.CalledProcessError, ValueError, IndexError):
        return None


def _ollama_ps_split() -> str | None:
    """GPU/CPU layer split for loaded models from ``ollama ps``.

    Ollama 0.20.5 does not support ``--format json``; fall back to the plain
    table and return its header lines as the split summary.
    """
    if shutil.which("ollama") is None:
        return None
    try:
        out = subprocess.check_output(
            ["ollama", "ps", "--format", "json"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(out)
        entries = data.get("models", []) or []
        parts = []
        for m in entries:
            parts.append(
                f"{m.get('name')} size={m.get('size') or '?'} "
                f"vram={m.get('size_vram') or '?'} split={m.get('split') or '?'}"
            )
        if parts:
            return "; ".join(parts)
    except (subprocess.CalledProcessError, ValueError):
        pass
    try:
        out = subprocess.check_output(
            ["ollama", "ps"], text=True, stderr=subprocess.DEVNULL
        )
        lines = [ln for ln in out.splitlines() if ln.strip()]
        return " | ".join(lines[:2]) if lines else None
    except subprocess.CalledProcessError:
        return None


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (chars/4) for thinking-channel verbosity."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _validate_contract(content: str) -> tuple[bool, str]:
    """Parse the model's JSON output against the LIGHT contract."""
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        return False, "invalid JSON"
    if not isinstance(data, dict):
        return False, "not an object"
    missing = [f for f in CONTRACT_FIELDS if f not in data]
    if missing:
        return False, f"missing fields: {','.join(missing)}"
    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return False, "empty answer"
    return True, "ok"


async def _chat_call(
    client: httpx.AsyncClient,
    base_url: str,
    model: str,
    system: str,
    user: str,
) -> dict:
    """One non-streaming /api/chat call returning raw metrics + content."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": "json",
        "think": True,
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096,
        },
    }
    start = time.perf_counter()
    resp = await client.post(f"{base_url}/api/chat", json=payload)
    total_ms = round((time.perf_counter() - start) * 1000.0, 1)
    data = resp.json()
    message = data.get("message", {}) or {}
    content = message.get("content", "") or ""
    thinking = message.get("thinking", "") or ""
    eval_count = data.get("eval_count") or 0
    eval_duration = data.get("eval_duration") or 0
    prompt_eval_count = data.get("prompt_eval_count") or 0
    tps = (
        round(eval_count / (eval_duration / 1e9), 1) if eval_duration else 0.0
    )
    valid, note = _validate_contract(content)
    return {
        "total_ms": total_ms,
        "prompt_tokens": prompt_eval_count,
        "output_tokens": eval_count,
        "tps": tps,
        "thinking_chars": len(thinking),
        "thinking_tokens_est": _estimate_tokens(thinking),
        "content": content,
        "json_valid": valid,
        "note": note,
    }


async def _first_token_ms(
    client: httpx.AsyncClient,
    base_url: str,
    model: str,
    system: str,
    user: str,
) -> float | None:
    """Time to first generated token using a streaming request."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "options": {"temperature": 0.2, "num_ctx": 4096},
    }
    start = time.perf_counter()
    try:
        async with client.stream("POST", f"{base_url}/api/chat", json=payload) as resp:
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                chunk = json.loads(line)
                msg = chunk.get("message", {}) or {}
                if msg.get("content") or msg.get("thinking"):
                    return round((time.perf_counter() - start) * 1000.0, 1)
    except Exception:
        return None
    return None


async def run(model: str) -> int:
    config = OllamaConfig()
    base_url = config.base_url.rstrip("/")

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
        try:
            resp = await client.get(f"{base_url}/api/tags")
        except httpx.HTTPError:
            print(f"Ollama not reachable at {base_url}. Is it running?")
            return 1
        if resp.status_code != 200:
            print(f"Ollama returned HTTP {resp.status_code}.")
            return 1
        installed = {
            m.get("name", "")
            for m in (resp.json().get("models") or [])
        }
        if model not in installed:
            print(
                f"Model '{model}' is not installed on Ollama. Installed: "
                f"{sorted(installed)}"
            )
            return 1

        print(f"model: {model}")
        print(f"base_url: {base_url}")
        vram_before = _nvidia_used_mb()
        print(f"gpu_mem_used_before_mib: {vram_before}")

        results = []
        for label, user_text in TASKS:
            result = await _chat_call(client, base_url, model, LIGHT_SYSTEM_PROMPT, user_text)
            result["label"] = label
            results.append(result)
            print(
                f"{label:<22} {result['total_ms']:>9.1f}ms  "
                f"prompt={result['prompt_tokens']:<5} out={result['output_tokens']:<5} "
                f"{result['tps']:>7.1f} tok/s  think_est={result['thinking_tokens_est']:<5} "
                f"json={'OK' if result['json_valid'] else result['note']}"
            )

        first_token = await _first_token_ms(
            client, base_url, model, LIGHT_SYSTEM_PROMPT, TASKS[0][1]
        )
        print(f"first_token_ms (task A, streaming): {first_token}")

        vram_after = _nvidia_used_mb()
        vram_delta = (
            (vram_after - vram_before)
            if (vram_before is not None and vram_after is not None)
            else None
        )
        print(f"gpu_mem_used_after_mib: {vram_after}")
        print(f"gpu_mem_delta_mib: {vram_delta}")

        split = _ollama_ps_split()
        if split:
            print(f"ollama_ps: {split}")

        json_ok = sum(1 for r in results if r["json_valid"])
        print(
            f"summary: json_ok={json_ok}/{len(results)} "
            f"total_out_tokens={sum(r['output_tokens'] for r in results)} "
            f"total_think_tokens_est={sum(r['thinking_tokens_est'] for r in results)}"
        )

        print("\n--- raw responses ---")
        for r in results:
            print(f"\n[{r['label']}] note={r['note']}")
            print(r["content"])
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ChronOS LIGHT-tier benchmark")
    parser.add_argument("--model", default="qwen3:4b", help="Ollama model to test")
    args = parser.parse_args()
    return asyncio.run(run(args.model))


if __name__ == "__main__":
    sys.exit(main())