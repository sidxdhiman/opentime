# Phase 4L: Performance, Contract Cleanup & FAST Path Audit

**Date:** 2026-08-26
**Phase:** 4L (Phase 4K follow-up)
**Goal:** Resolve remaining inconsistencies found during Phase 4K release readiness audit — redundant loading, stale requests, FAST path cleanup

---

## Summary

Phase 4L addressed the three core inconsistencies identified during the Phase 4K audit. All fixes were surgical and no new features were introduced.

### Changes Made

#### 1. Dashboard Initial Load Optimization (`page.tsx`)
- **Before:** `loadAllData()` fetched all 7 API collections (identity, memories, timeline, reflections, patterns, threads, interactions) on mount
- **After:** `loadAllData()` fetches only identity + interactions + threads + memories + reflections (5 collections)
- **Rationale:** Timeline and patterns are only rendered in their respective tabs (Timeline, Insights). Threads and memories are needed on Home because the stats bar shows Stories/Memories counts
- **Impact:** 2 fewer API calls on initial page load. Lazy tab loading now also covers threads (Stories tab)

#### 2. Request Cancellation / Stale Request Protection (`page.tsx` + `chronosApi.ts`)
- **`chronosApi.ts`:** All 7 GET methods now accept an optional `signal?: AbortSignal` parameter
- **`page.tsx`:**
  - Initial `loadAllData()` call wrapped in an `AbortController`; aborted on unmount
  - All refresh functions catch and ignore `AbortError` to prevent stale state updates
  - `isInitialLoad` only cleared when request is not aborted
- **Impact:** Component unmounts no longer trigger state updates on unmounted components

#### 3. FAST Path LLM Call Removal (`engine.py`)
- **Before:** On FAST path, the engine called `orchestrator.orchestrate_prompt()` + `llm_provider.generate_response()` + `validator.validate_response()` — the LLM call was a real network call to Ollama that produced output which was then discarded
- **After:** Only `orchestrator.orchestrate_prompt()` is called (pure template assembly, no network). `raw_llm_response` is set to `""`. `ValidationResult` is constructed deterministically with `personalization_score=0.96` (matching the validator's hardcoded value). `provider_name` is set to `"deterministic"` and `target_model` to `"chronos-v1-core"`
- **Rationale:** The orchestrator is kept because its output (`PromptContext`) feeds the explainability trace. The LLM call and validator were pure overhead on the FAST path — their outputs were never used for `final_response`
- **Impact:** Eliminates one unnecessary Ollama network round-trip per FAST-path request. Reduces FAST-path latency

#### 4. Test Fix (`test_chronos_engine.py`)
- Updated provider swap assertion to accept `"deterministic"` as valid `provider_name` on FAST path (line 71)
- **608 pass, 0 fail, 4 skip**

---

## Verification Results

| Check | Result |
|-------|--------|
| TypeScript (`npx tsc --noEmit`) | ✅ Clean |
| Python tests (`pytest tests/ -q`) | ✅ 608 pass, 0 fail, 4 skip |
| Python lint (`ruff check`) | ✅ No new errors (102 pre-existing) |
| Frontend build (`npx next build`) | ✅ Clean |

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/app/dashboard/page.tsx` | Trimmed `loadAllData()` from 7→5 collections; added AbortController; added lazy loading for Stories tab; added AbortError guards to all refresh functions |
| `frontend/src/lib/chronosApi.ts` | Added optional `signal?: AbortSignal` to all 7 GET methods |
| `backend/src/chronos_engine/engine.py` | Removed `llm_provider.generate_response()` + `validator.validate_response()` on FAST path; replaced with deterministic stubs |
| `backend/tests/test_chronos_engine.py` | Updated provider swap assertion to accept `"deterministic"` |

---

## Remaining Notes

- The orchestrator call on FAST path is retained for explainability trace metadata (the `prompt_step` references `retrieved_context.identity_summary` which requires the prompt context to be assembled)
- The `raw_llm_response` field in `EngineResponse` is now `""` on FAST path. If the UI ever displays this field for debugging, it will be empty
- No changes to API contracts — all endpoint signatures and response shapes remain identical
