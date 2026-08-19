# Phase 2J — Real LIGHT Model Benchmark (Acceptance Evidence)

Benchmark against the real, manually-installed local model `qwen2.5:1.5b`
(`OLLAMA_LIGHT_MODEL=qwen2.5:1.5b`). No production code or architecture was
modified; the one-off harness in `/tmp` reuses the existing executor, policy,
provider, and engine infrastructure.

## Environment

- Ollama `qwen2.5:1.5b` (986 MB disk) and `qwen3:4b` (2.5 GB) installed.
- RTX 3050 Laptop GPU (4096 MiB), Ryzen 5 5600H, 14 GB RAM.
- Working tree clean (`ac383c9 chronosPhase2I&2J`); no new repo files.

## Raw Results (warm steady-state, model pre-loaded)

| Case | Tier | Model | Success | Fallback | Latency | Prompt tok | Gen tok | tok/s | Thinking | Validation | JSON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| INTERPRET | LIGHT | qwen2.5:1.5b | True | none | 1152 ms | 476 | 100 | 108.6 | n/a (no channel) | ok | ok* |
| CLASSIFY | LIGHT | qwen2.5:1.5b | True | none | 770 ms | 476 | 55 | 110.6 | n/a | ok | ok* |
| INTERPRET+CTX | LIGHT | qwen2.5:1.5b | True | none | 966 ms | 475 | 80 | 95.3 | n/a | ok | ok* |

\* Raw content carries prose around the embedded JSON; the executor's
`ResponseValidator` (authoritative) accepted it.

- Inputs benchmarked:
  1. INTERPRET — `"I'm frustrated because I'm stuck trying to finish ChronOS."`
  2. CLASSIFY — `"I don't even know what I'm trying to do anymore."`
  3. INTERPRET + context — `"I'm exhausted and wondering whether this project is worth continuing."`
- Cold first call: 14.06 s (model load). Cold CLASSIFY run once returned
  non-JSON -> `success=False, fallback_used=True, error_type=MALFORMED_JSON`
  (honest, non-deterministic model output); all warm runs validated ok.

## Verifications

- **LIGHT -> qwen2.5:1.5b**: all 3 cases `selected_tier=LIGHT`,
  `actual_model=qwen2.5:1.5b`.
- **LIGHT NEVER -> qwen3:4b**: recorder showed only
  `['qwen2.5:1.5b', 'qwen2.5:1.5b', 'qwen2.5:1.5b']`; `ollama ps` after the run:
  only `qwen2.5:1.5b` loaded (1.4 GB, 100% GPU), `qwen3:4b` never loaded.
- **FAST** (`"What is MongoDB?"`): `route=FAST`, `use_ai=False`,
  `ai_execution.attempted=False`, `tier=NONE`, `ollama_called=[]`, final
  response = engine's deterministic template ("USER SIGNAL / WHAT CHRONOS
  UNDERSTANDS ...").
- **VRAM**: qwen2.5:1.5b -> 1.4 GB / 100% GPU (peak ~2.45 GB incl. Ollama);
  qwen3:4b baseline was 2.4 GB / 33% CPU-67% GPU.

## Comparison vs qwen3:4b LIGHT Baseline (Phase 2I)

| Metric | qwen3:4b (2I) | qwen2.5:1.5b (now) |
|---|---|---|
| Task latency | 73.9-128.1 s | 0.77-1.15 s (~110-160x faster) |
| Tokens/sec | 15.4-19.8 | 95-111 (~5x) |
| Thinking tokens | 6,746 (4 tasks) | none (no thinking channel) |
| VRAM | ~2.4 GB loaded | 1.4 GB (100% GPU) |

## Conclusion

LIGHT-tier execution is verified end-to-end on the real local model: correct
tier/model selection, model separation, no qwen3:4b involvement, FAST
determinism, and a large latency/VRAM improvement over the qwen3:4b LIGHT
baseline.