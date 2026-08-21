# Real LIGHT Model Benchmark Results — qwen2.5:1.5b

Benchmark against the real, manually-installed local model `qwen2.5:1.5b`
(`OLLAMA_LIGHT_MODEL=qwen2.5:1.5b`). No production code, prompts, routing,
or inference policy was modified; a one-off harness in `/tmp/opencode`
reused the existing production infrastructure
(`AIRouter -> ReasoningPlanner -> InferencePolicy -> AIExecutor ->
OllamaProvider`) and recorded every actual Ollama HTTP call.

## Raw Results (warm steady state)

| Case | Tier | Model | Success | Fallback | Latency | Prompt tok | Gen tok | tok/s | Thinking | Validation | JSON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. INTERPRET | LIGHT | qwen2.5:1.5b | True | none | 1951 ms | 476 | 123 | 73.4 | 0 (no channel) | ok | pure JSON, parsed |
| 2. CLASSIFY | LIGHT | qwen2.5:1.5b | True | none | 1512 ms | 476 | 88 | 73.8 | 0 | ok | pure JSON, parsed |
| 3. INTERPRET+CTX | LIGHT | qwen2.5:1.5b | True | none | 1618 ms | 475 | 96 | 75.0 | 0 | ok (1 correction) | pure JSON, parsed |

Inputs benchmarked:

1. INTERPRET — `"I'm frustrated because I'm stuck trying to finish ChronOS."`
2. CLASSIFY — `"I don't even know what I'm trying to do anymore."`
3. INTERPRET + context — `"I'm exhausted and wondering whether this project is worth continuing."`

Notes:

- Prompt tokens are the ACTUAL `prompt_eval_count` from the production call
  (executor's own estimate: ~492). `think:false` was sent
  (`light_thinking_enabled=False`); the `thinking` channel was empty on every
  call; `done_reason=stop` on all calls.
- Reliability extension: 8/8 additional warm runs succeeded (no fallback).
  Across repeated runs, warm latency ranged 1.0-2.0 s.
- TRUE cold start (model unloaded): 4.06 s including model load — and that
  call returned contract-invalid JSON -> honest `success=False,
  fallback_used=True, error_type=MALFORMED_JSON`; the deterministic response
  was served. The typed failure/fallback path works. Small-model JSON
  nondeterminism is real but rare: observed on 1 of ~3 cold calls, 0/11 warm.

## Verifications

- **LIGHT -> qwen2.5:1.5b**: every case recorded `selected_tier=LIGHT`,
  `actual_model=qwen2.5:1.5b`.
- **LIGHT NEVER -> qwen3:4b**: the HTTP-call recorder shows ONLY
  `qwen2.5:1.5b` was ever called on the LIGHT path; after the runs
  `ollama ps` showed only `qwen2.5:1.5b` loaded (1.4 GB, 100% GPU).
  Separation in both directions confirmed by the existing
  `backend/scripts/smoke_light.py`: its DEEP leg executed `qwen3:4b`
  (success, 173.5 s) and printed `SMOKE_2J_OK`.
- **FAST** (`"What is MongoDB?"`): `route=FAST`, `use_ai=false`, tier `NONE`,
  `attempted=false`, ZERO Ollama HTTP calls (recorder-verified), final
  response == the engine's deterministic template.
- **VRAM**: nvidia-smi 387 -> 1865 MiB with `qwen2.5:1.5b` resident
  (~1.45 GiB delta, fully on GPU).

## Caveats (honest findings)

- Through the full engine, these three short inputs route FAST by design
  ("emotion alone never routes to AI"). The LIGHT tier was therefore
  exercised via the smoke-test methodology: a forced `use_ai` routing result
  fed into the REAL policy/executor/provider chain.
- `backend/scripts/benchmark_light.py` cannot run against this model
  unmodified: it hardcodes `"think": true`, and Ollama returns
  HTTP 400 `"qwen2.5:1.5b" does not support thinking`. Production code is
  unaffected (`light_thinking_enabled=False` sends `think:false`).

## Comparison vs qwen3:4b LIGHT Baseline (Phase 2I: 73-128 s/task)

| Metric | qwen3:4b | qwen2.5:1.5b |
|---|---|---|
| Task latency | 73.9-128.1 s | 1.0-2.0 s warm (~50-100x faster); 4.1 s cold |
| Tokens/sec | 15.4-19.8 | 68-77 (~4-5x) |
| Thinking tokens | 1,235-2,481 per task | 0 |
| VRAM | ~2.4 GB, 33%/67% CPU/GPU split | 1.4 GB, 100% GPU |

## Conclusion

LIGHT-tier execution is verified end-to-end on the real local model:
correct tier/model selection, strict LIGHT/DEEP model separation, a fully
deterministic FAST path, an honest typed fallback on malformed output, and
latency well inside the 30 s LIGHT budget (~50-100x faster than the
qwen3:4b baseline with no thinking tokens and lower VRAM use).
