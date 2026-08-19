# ChronOS Phase Check

## chronosPhase2F — Completed

Local LLM integration audited and benchmarked against the real runtime
(`qwen3:4b`, Ollama 0.20.5, RTX 3050 4GB):

- Deterministic routing (`AIRoutingResult`) works end-to-end: FAST path skips AI,
  DEEP path runs a single AI call with a `ReasoningPlan`.
- Structured output validation + safe fallback verified: parser/validator errors
  fall back to the deterministic response instead of failing the request.
- Baseline established at 240s timeout:
  - INTERPRET ~148s, eval 4004 tokens (~3819 thinking).
  - REASON ~102s, eval 3407 tokens (~3186 thinking).
  - REFLECT ~158s, eval 4160 tokens (~3916 thinking).
- `OLLAMA_TIMEOUT` was too low at the 60s default (all cases timed out); 240s is
  required, and budget-derived timeouts now protect larger output budgets.
- Runtime facts: thinking accounts for ~93-95% of generated tokens; the model
  template always emits the ` thinking` prefix, so thinking cannot be disabled
  (only channel-switched via the `think` field).

## chronosPhase2G — Completed

Controlled local inference for Qwen3 thinking, with the REASON/REFLECT
structured-output failures fixed:

- Root cause of REASON/REFLECT failures: the model emits evidence tags as
  `memory:mem_x` (no brackets); the strict bracketed regex rejected them as
  `HALLUCINATED_EVIDENCE`. Parser now normalizes bracketed/unbracketed tags
  while keeping the fabricated-evidence guardrail.
- New `InferenceOptions` model threads per-call knobs from the `ReasoningPlan`
  to the provider: `thinking_enabled`, `num_predict`, `num_ctx`, `temperature`.
- New `OllamaConfig` knobs: `thinking_enabled`, `mode_thinking_enabled`,
  `mode_num_predict`, `min_tokens_per_sec`, `timeout_margin` (all env-driven,
  defaults preserve prior behavior).
- Provider sends the supported `think` field and applies per-mode budgets;
  `_effective_timeout` raises the request timeout to
  `num_predict / min_tokens_per_sec + timeout_margin` so budgets are never
  silently cut off.
- Prompt directive added: the supplied CHRONOS STATE is the complete final
  analysis; the model must only perform the specific reasoning task.
- Verified on the real model: all three benchmark cases now succeed with no
  fallback (defaults and configured runs); the configured run applied
  `num_predict=4608` with `effective_timeout=490.8s` and `done_reason=stop`.
- Backend tests: 186 passed. Frontend typecheck (`tsc --noEmit`): clean.

## chronosPhase2H — Completed

Architecture + local model audit (inference policy). No model was installed and
no execution behavior changed:

- Local model audit: only `qwen3:4b` is installed (2.5 GB, Q4_K_M, 4.0B params,
  262144 context, thinking capability). It does NOT fit substantially better
  within 4 GB VRAM (observed ~82% GPU / 18% CPU offload), so it stays the DEEP
  model. No LIGHT model is available.
- New `ModelCapability` abstraction: honest per-model metadata (parameter
  count, quantization, estimated memory, context, JSON/thinking support, tier);
  unknown values stay `None`, never fabricated.
- New deterministic `InferencePolicy` (pure computation, never invokes a
  provider): FAST → NONE, INTERPRET/CLASSIFY/GENERATE → LIGHT when a suitable
  configured light model exists (`OLLAMA_LIGHT_MODEL`), REASON/REFLECT → DEEP,
  no light model → DEEP fallback with `light_requested=True`, AI disabled →
  NONE. Optional latency budget handled via `expected_latency_class`, never a
  latency promise.
- Light-model thresholds are configurable on `OllamaConfig`
  (`light_max_parameters`, `light_max_memory_gb`, `light_min_context`,
  `light_max_latency_seconds`, `available_vram_gb`).
- Additive `EngineResponse.inference_policy` records the decision; it is
  observational only — execution stays FAST → deterministic, DEEP → configured
  `qwen3:4b`. `ai_routing` / `ai_execution` fields unchanged.
- Backend tests: 206 passed (186 prior + 20 new policy tests). Frontend
  typecheck (`tsc --noEmit`): clean.

## chronosPhase2I — Completed

Research-only LIGHT-tier model selection. No model was installed and no
production component changed (engine, policy, executor, routing, validator,
state all untouched). A single isolated benchmark script was added.

### Baseline measurement (MEASURED — only installed model, `qwen3:4b`)

`backend/scripts/benchmark_light.py` (ruff-clean) runs the four LIGHT tasks
(A INTERPRET, B INTERPRET+GENERATE, C SIMPLE CLASSIFY, D CONTEXTUAL) directly
against Ollama `/api/chat` with `format: json` and the LIGHT contract
`{"answer", "uncertainties", "evidence_used"}`:

| task | latency | t/s | thinking (est tokens) | JSON |
| --- | ---: | ---: | ---: | --- |
| A.INTERPRET | 80.5s | 19.8 | 1,235 | ok |
| B.INTERPRET+GENERATE | 128.1s | 17.2 | 2,481 | ok |
| C.SIMPLE CLASSIFY | 89.0s | 16.5 | 1,622 | ok |
| D.CONTEXTUAL | 73.9s | 15.4 | 1,408 | ok |

- 6,746 thinking tokens across the four tasks; every task runs 73–128s,
  far above the 30s LIGHT budget.
- First token ~278ms but content arrives only after the long thinking phase.
- GPU: +2,358 MiB delta; `ollama ps` reports 3.6 GB loaded at a 33%/67%
  CPU/GPU split, leaving only ~453 MiB free. `qwen3:4b` nearly saturates the
  4 GB card (free VRAM measured ~2.7 GB with desktop overhead).
- JSON contract was satisfied 4/4, but the cost makes it unusable for LIGHT.

### Candidate table (DOCUMENTED from official Ollama library / model cards unless noted)

| model | params | size | ctx | thinking | policy-eligible (≤3.0B) | license |
| --- | ---: | ---: | ---: | --- | --- | --- |
| qwen2.5:0.5b | 0.49B | 398MB | 32K | no | yes | Apache-2.0 |
| qwen2.5:1.5b | 1.54B | 986MB | 32K | no | yes | Apache-2.0 |
| qwen2.5:3b | 3.09B | 1.9GB | 32K | no | no (>3.0) | Qwen |
| gemma3:1b | 1.0B | 815MB | 32K | no | yes | Gemma ToU |
| gemma3:270m | 0.27B | ~200MB (EST.) | 32K | no | yes | Gemma ToU |
| llama3.2:1b | 1.24B | 1.3GB | 128K | no | yes | Llama |
| llama3.2:3b | 3.21B | 2.0GB | 128K | no | no (>3.0) | Llama |
| gemma2:2b | 2.61B | 1.6GB | 8K | no | yes | Gemma ToU |
| qwen3:0.6b | 0.6B | 523MB | 40K | default ON (runtime risk) | yes | Apache-2.0 |
| qwen3:1.7b | 1.7B | 1.4GB | 40K | default ON (runtime risk) | yes | Apache-2.0 |
| phi4-mini | 3.8B | 2.5GB | 128K | no | no (>3.0) | MIT |
| gemma3:4b | 4.0B | ~2.5GB (EST.) | 128K | no | no (>3.0) | Gemma ToU |

Thinking note: `qwen3:0.6b/1.7b` use the same Qwen3 template family as the
installed `qwen3:4b`; on this runtime (Ollama 0.20.5) thinking cannot be truly
disabled (measured), so they inherit hidden-reasoning-token risk — a LIGHT-tier
disqualifier despite fitting VRAM.

Hardware fit (ESTIMATED VRAM on the ~2.7GB-free RTX 3050 Laptop): 0.5–1.9GB
models (qwen2.5 0.5b/1.5b, gemma3 1b, llama3.2 1b, gemma2 2b) fit fully on GPU
with headroom for KV cache; 2.2GB+ models (qwen2.5 3b, llama3.2 3b) fit but
tight; phi4-mini (~3.2GB) does NOT fit → CPU offload, and it is policy-
ineligible anyway.

### Decision matrix (12 ChronOS LIGHT criteria, 1–5 each; M=MEASURED, D=DOCUMENTED, E=ESTIMATED)

Criteria: 1 response validity, 2 JSON reliability, 3 evidence grounding,
4 hallucination resistance, 5 instruction following, 6 concept coverage,
7 conciseness, 8 no thinking tokens, 9 generation speed, 10 first-token latency,
11 VRAM fit, 12 low CPU-offload risk.

| model | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | total |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| qwen2.5:1.5b | 4 | 5 | 3 | 3 | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 4 | **48** |
| gemma3:1b | 4 | 4 | 3 | 3 | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 5 | **47** |
| llama3.2:1b | 4 | 4 | 3 | 3 | 4 | 3 | 4 | 5 | 4 | 4 | 4 | 4 | **45** |
| qwen2.5:0.5b | 3 | 4 | 2 | 2 | 3 | 3 | 4 | 5 | 5 | 5 | 5 | 5 | **44** |
| gemma2:2b | 4 | 4 | 3 | 3 | 4 | 4 | 4 | 5 | 3 | 3 | 4 | 4 | **43** |
| qwen3:0.6b | 3 | 4 | 3 | 3 | 3 | 3 | 2 | 1 | 3 | 2 | 5 | 5 | **34** |
| qwen3:1.7b | 3 | 4 | 3 | 3 | 4 | 4 | 2 | 1 | 3 | 2 | 4 | 4 | **33** |

Basis: JSON reliability from Qwen2.5's documented structured-output strength
(D) and Gemma/Llama general `format: json` support (D); speed/first-token/VRAM
from model-size scaling (E); thinking column from architecture (D) plus the
installed-runtime measurement on qwen3:4b (M). Scores 1–8 are quality signals
that still need on-device confirmation once a model is installed.

### Conclusion

- **Recommended ChronOS LIGHT model: `qwen2.5:1.5b`** (1.54B, ~986MB disk,
  ~1.2GB VRAM, 32K ctx, Apache-2.0). It fully fits the free VRAM with
  headroom, produces NO thinking tokens, has the best documented JSON /
  structured-output reliability (critical for the LIGHT contract), and its
  predicted per-task latency (~1–3s, ESTIMATED) is well inside the 30s LIGHT
  budget.
- Runner-up: `gemma3:1b` (smaller, slightly faster, Gemma ToU; slightly weaker
  documented JSON/structured-output behavior).
- Avoid for LIGHT on this runtime: `qwen3:0.6b/1.7b` (always-on thinking),
  `phi4-mini`/`qwen2.5:3b`/`llama3.2:3b`/`gemma3:4b` (exceed the 3.0B
  `light_max_parameters` policy threshold).
- OPTIONAL install command (documented, NOT executed, no model was installed):
  `ollama pull qwen2.5:1.5b` — then set `OLLAMA_LIGHT_MODEL=qwen2.5:1.5b`.
  The policy will pick it up automatically once installed; no code changes
  required.
- No models were installed and no production behavior changed during Phase 2I;
  the only artifact added is the isolated `backend/scripts/benchmark_light.py`.
- PHASE 2I COMPLETE.

## chronosPhase2J — Completed

LIGHT-model execution activated. The `InferencePolicy` decision now dictates
the actual model the `AIExecutor` calls — no model-selection logic is
duplicated in the executor. No model was installed automatically; execution
follows the configured models (`OLLAMA_LIGHT_MODEL`, `OLLAMA_MODEL`).

- Flow: `AIRouter -> ReasoningPlanner -> InferencePolicy -> AIExecutor ->
  selected provider/model -> Ollama`. The engine computes the decision and
  passes it to the executor, which resolves `(tier, provider, model)` solely
  from that decision (`_resolve_target`).
- FAST: policy `NONE`, executor never invoked, Ollama never called,
  deterministic response.
- LIGHT (INTERPRET / CLASSIFY / GENERATE-only plan): executes
  `OLLAMA_LIGHT_MODEL` (`qwen2.5:1.5b`); `qwen3:4b` is never called.
- DEEP (REASON / REFLECT): executes `OLLAMA_MODEL` (`qwen3:4b`); unchanged
  behavior.
- LIGHT failure (model unavailable / connection / timeout / validation) →
  honest deterministic fallback (`fallback_used=True`,
  `error_type=<typed name>`); the executor NEVER automatically escalates a
  LIGHT failure to DEEP, and the latency budget semantics are unchanged
  (a tight budget without a light model -> `NONE`).
- New LIGHT-specific inference knobs on `OllamaConfig`:
  `light_thinking_enabled` (default `False` — qwen2.5:1.5b has no thinking
  channel; LIGHT must not inherit qwen3:4b's thinking config) and
  `light_format_json` (default `False`; the global `format_json` default stays
  OFF per Phase 2G). `InferenceOptions` gained a `format_json` field so the
  LIGHT tier can opt in per-model without changing the global default.
- `AIExecutionResult` gained `tier` and records the ACTUAL tier/provider/model
  executed, plus latency/success/fallback/error_type/inference_options (no
  fabricated latency).
- `capabilities_from_config(config)` builds the model catalog from the
  configured DEEP + LIGHT models with honest (unknown) metadata; the engine's
  default `InferencePolicy` reads the executor's own config so the recorded
  decision and the executed model always agree.
- Tests: 225 passed (206 prior + 19 new in `tests/test_light_execution.py`
  covering FAST->NONE, INTERPRET/CLASSIFY->LIGHT, REASON/REFLECT->DEEP, all
  LIGHT failure fallbacks, model-separation both directions, execution
  metadata, tier-appropriate inference options, and policy/execution
  agreement). Frontend typecheck (`tsc --noEmit`): clean.
- Manual real-model smoke test: `backend/scripts/smoke_light.py` (ruff-clean,
  NOT in CI) runs INTERPRET + CLASSIFY against the LIGHT model and one DEEP
  request, recording model, prompt/generated tokens, latency, tokens/sec,
  success/fallback/validation, and VRAM; it refuses to run until
  `ollama pull qwen2.5:1.5b` is done manually.
- Performance note: qwen2.5:1.5b real latency/tokens-per-sec is NOT yet
  measured because the model is not installed — no improvement is claimed.
  Measured Phase 2I baseline for the same LIGHT tasks on `qwen3:4b` was
  73–128s/task at 15–20 tok/s with ~2.4GB VRAM; the installed-models check in
  `smoke_light.py` (`ollama pull qwen2.5:1.5b` required) is the AFTER
  measurement path.
- No model was automatically installed and no router/planner/validator/
  state/architecture changed during Phase 2J.
- PHASE 2J COMPLETE.