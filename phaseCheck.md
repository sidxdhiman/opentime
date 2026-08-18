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