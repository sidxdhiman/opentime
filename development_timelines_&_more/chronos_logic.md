# ChronOS Engine — Complete Logic & Architecture Reference

> This document describes, in detail, what the ChronOS Engine does: its architecture, every
> module, the exact runtime pipeline, the data models, the storage layout, the HTTP API,
> and the design decisions (and current limitations) behind each piece.
>
> The engine source lives in `backend/src/chronos_engine/`. The frontend that drives it is
> in `frontend/src/lib/chronosApi.ts` and `frontend/src/components/chronos/`.

---

## 1. What is ChronOS?

ChronOS is the **central personal intelligence layer** of OpenTime. It sits between the
user's raw data and language models. Its job is to make any downstream LLM answer with
**high contextual awareness, personal alignment, and deep continuity** across a user's:

- **life timeline** (chronological, phase-tagged events),
- **evolving identity** (interests, goals, values, emotional tendencies, skills),
- **behavioral patterns** (habits, recurring successes, mood shifts, decision changes),
- **semantic memory graph** (memories linked to each other by embedding similarity).

Unlike a stateless chatbot, every response the engine produces is **grounded** in what it
already knows about the user. Every input it receives also *writes back* — it becomes a new
memory, a new timeline event, and an incremental update to the user's identity profile.
The engine is therefore a **read-then-write** system: it reads stored context to answer,
and it stores the new interaction so the next answer is even more personal.

---

## 2. High-Level Architecture

```
                         ┌──────────────────────────────────────────────┐
                         │              HTTP API (FastAPI)              │
                         │         router: /api/v1/chronos/engine/*     │
                         └───────────────────┬──────────────────────────┘
                                             │
                                             ▼
        ┌────────────────────────── ChronosEngine (engine.py) ──────────────────────────┐
        │                                                                               │
        │  1. INPUT PROCESSING LAYER   MediaProcessor (text / audio / video / image)    │
        │  2. MEMORY SYSTEM            MemorySystem + EmbeddingProvider                 │
        │  3. TIMELINE ENGINE          TimelineEngine (phase detection, sentiment)      │
        │  4. IDENTITY MODEL           IdentityModel (profile create + evolve)          │
        │  5. RETRIEVAL ENGINE         RetrievalEngine (assemble context bundle)        │
        │  6. PROMPT ORCHESTRATOR      PromptOrchestrator (system + user prompt)        │
        │  7. LLM PROVIDERS            LLMRegistry (chronos/openai/anthropic/…)         │
        │  8. RESPONSE VALIDATOR       ResponseValidator (grounding, corrections)       │
        │  9. EXPLAINABILITY TRACE     ReasoningTrace (what/why/how it answered)        │
        │                                                                               │
        └───────────────────────────────┬───────────────────────────────────────────────┘
                                        │
                                        ▼
        ┌──────────────────────────── Storage Adapter ─────────────────────────────────┐
        │  BaseStorageAdapter interface:                                               │
        │   ├─ InMemoryStorageAdapter   (repo used for tests / default fallback)       │
        │   └─ MongoStorageAdapter      (production, persistent, per-user collections) │
        └───────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                              MongoDB (opentime database)
                    engine_memories · engine_timeline · engine_identity
                    engine_reflections · engine_patterns
```

The engine is a classic **pipeline with side effects**:

1. Parse the raw input.
2. Persist it as a memory (write path).
3. Update timeline + identity (write path).
4. Retrieve the richest possible context (read path).
5. Build a context-enriched prompt.
6. Ask a model-agnostic LLM provider.
7. Validate/correct the raw LLM output.
8. Package everything into an explainable response.

---

## 3. Directory / Module Map

```
backend/src/chronos_engine/
├── engine.py                  # ChronosEngine — the orchestrator class & public pipeline
├── core/
│   ├── models.py              # All Pydantic domain models & enums (the "schema of reality")
│   └── interfaces.py          # Abstract base classes (the contract every service implements)
├── api/
│   └── router.py              # FastAPI routes under /chronos/engine/*
├── storage/
│   ├── repository.py          # InMemoryStorageAdapter (dev / tests)
│   └── mongo_repository.py    # MongoStorageAdapter (production persistence)
├── memory/
│   └── service.py             # MemorySystem — stores interactions, links, tags, embeddings
├── embeddings/
│   └── provider.py            # DefaultEmbeddingProvider — 128-dim hashed n-gram vectors
├── timeline/
│   └── service.py             # TimelineEngine — phase detection, recurrence, sentiment
├── identity/
│   └── service.py             # IdentityModel — profile creation + rule-based evolution
├── patterns/
│   └── service.py             # PatternDetector — behavior/habit pattern extraction
├── reflection/
│   └── service.py             # ReflectionEngine — past-vs-present insight generation
├── retrieval/
│   └── service.py             # RetrievalEngine — bundles everything for the prompt
├── orchestrator/
│   └── service.py             # PromptOrchestrator — renders the enriched prompt
├── llm/
│   └── providers.py           # LLMRegistry + 5 pluggable providers
├── validators/
│   └── service.py             # ResponseValidator — grounding & correction pass
└── utils/
    └── media_processor.py     # MediaProcessor — input normalization layer
```

---

## 4. Core Domain Models (`core/models.py`)

Everything the engine reasons about is a typed Pydantic model. Fields are described below
exactly as they exist in code.

### 4.1 Enums

| Enum | Values |
|---|---|
| `InputType` | `text`, `audio`, `video`, `image` |
| `MemoryType` | `short_term`, `long_term`, `episodic`, `semantic` |
| `PatternCategory` | `habit`, `recurring_problem`, `repeated_success`, `behavior_loop`, `productivity_trend`, `mood_shift`, `decision_change` |
| `ReflectionInsightType` | `belief_shift`, `focus_shift`, `emotional_shift`, `habit_change` |

### 4.2 `UserInput`

The normalized representation of whatever the user just sent.

- `id` — `in_` + 12 hex chars.
- `user_id` — owner scope.
- `input_type` — `InputType` (default `text`).
- `content` — the text; for audio/video without a note it is the honest placeholder
  `[Voice note - awaiting transcription]` / `[Video note - awaiting transcription]`.
- `media_url` — public path to the stored file (e.g. `/uploads/{user}/{file.webm}`).
- `file_name` — original/derived filename.
- `media_metadata` — dict with `format`, `size_bytes`, `estimated_duration_sec`, `media_type`.
- `timestamp` — defaults to `datetime.now(timezone.utc)`.

### 4.3 `MemoryItem`

One persistent node of the user's memory graph.

- `id` — `mem_` + 12 hex chars.
- `user_id`, `content`, `created_at`, `timestamp`.
- `memory_type` — always `LONG_TERM` in the current implementation.
- `embedding` — `List[float]`, the 128-dim semantic vector.
- `importance_score` — `min(1.0, 0.4 + len(content) / 200)`. Longer inputs → higher importance.
- `linked_memory_ids` — IDs of prior memories whose cosine similarity exceeded `0.45`.
- `tags` — up to 5 tokens longer than 4 characters, extracted from content.
- `metadata` — carries `input_type`, `media_url`, `file_name`, `media_metadata`.

### 4.4 `TimelineEvent`

A chronologically-organized milestone derived from a memory.

- `id` (`evt_` + 12 hex), `user_id`, `title` (first 50 chars + `...` if truncated), `description`.
- `timestamp`, `life_phase`, `is_recurring`, `frequency` (`"Weekly"` when recurring).
- `memory_ids`, `sentiment` (float in `[-1.0, 1.0]`), `belief_evolution_notes`.

### 4.5 `IdentityProfile`

The evolving portrait of the user.

- `user_id`, `version` (starts at 1, incremented on every evolution), `last_updated`.
- `interests`, `goals`, `values`, `skills` — string lists, each capped at 10.
- `emotional_tendencies` — `Dict[str, float]` (e.g. optimism, focus, resilience, curiosity).
- `relationships` — `Dict[str, str]` (e.g. `{"OpenTime Team": "Founder / Architect"}`).
- `preferences` — dict (communication, theme, …).
- `decision_patterns` — list of stated decision styles.
- `communication_style` — e.g. `"Direct, insightful, clear"`.

### 4.6 `ReflectionInsight`

A "past self vs current self" observation.

- `id` (`ref_` + 12 hex), `user_id`, `insight_type`.
- `summary`, `past_state_summary`, `current_state_summary`.
- `confidence_score`, `supporting_memory_ids`, `reasoning_trace` (list of explanation strings).
- `affected_time_range`, `timestamp`.

### 4.7 `PatternItem`

A detected recurring behavior.

- `id` (`pat_` + 12 hex), `user_id`, `category`, `title`, `description`, `frequency`.
- `confidence_score`, `first_detected`, `last_detected`, `supporting_memory_ids`.

### 4.8 `RetrievedContext`

The full context bundle handed to the prompt orchestrator.

- `relevant_memories` — top-k semantic matches.
- `timeline_events` — the most recent 5 events.
- `life_phase` — phase of the most recent timeline event, or `"Initial Phase"`.
- `identity_summary` — dict projection of the identity profile (no secrets, all user-owned).
- `patterns` — up to 4 detected patterns.
- `goals` — list copied from identity.
- `recent_changes` — human-readable strings like
  `"Evolving goal: {goal[0]}"` and `"Emotional posture: Optimism score {n}%"`.

### 4.9 `PromptContext`

The fully assembled prompt plus its source material.

- `current_input` (`UserInput`), `retrieved_context` (`RetrievedContext`).
- `system_prompt`, `user_prompt`, `assembled_at`.

### 4.10 `ReasoningTrace`

The explainability layer — *why* the engine answered the way it did.

- `confidence_score`, `supporting_memory_ids`, `reasoning_steps`, `affected_time_range`, `context_sources`.

### 4.11 `ValidationResult`

Output of the post-LLM validation pass.

- `is_valid`, `validated_response`, `corrections_made`, `contradictions_detected`, `personalization_score`.

### 4.12 `EngineResponse`

The full API response envelope (everything below is returned to the frontend).

- `id` (`resp_` + 12 hex), `user_id`, `original_input`, `raw_llm_response`, `final_response`.
- `provider_name`, `model_name`, `prompt_context`, `reasoning_trace`, `validation_result`.
- `processing_time_ms`, `timestamp`.

---

## 5. The Contracts (`core/interfaces.py`)

The engine is built on abstract base classes so every subsystem is swappable. The contracts:

| Interface | Responsibility |
|---|---|
| `BaseEmbeddingProvider` | `get_embedding(text) → List[float]`, `similarity(v1, v2) → float` |
| `BaseStorageAdapter` | CRUD for memories, timeline, identity, reflections, patterns |
| `BaseMemorySystem` | `add_interaction`, `search_semantic_memories`, `get_short_term_context` |
| `BaseTimelineEngine` | `process_memory`, `get_timeline`, `generate_historical_summary` |
| `BaseIdentityModel` | `get_or_create_profile`, `evolve_profile` |
| `BaseReflectionEngine` | `compare_past_and_present(user_id, days_back=30)` |
| `BasePatternDetector` | `analyze_patterns(user_id)` |
| `BaseRetrievalEngine` | `retrieve_context(user_input) → RetrievedContext` |
| `BasePromptOrchestrator` | `orchestrate_prompt(user_input, retrieved_context) → PromptContext` |
| `BaseLLMProvider` | `provider_name()`, `generate_response(prompt_context, model_name) → str` |
| `BaseResponseValidator` | `validate_response(raw_response, prompt_context) → ValidationResult` |

This is why `ChronosEngine.__init__` accepts any of these as constructor arguments — each
defaults to a concrete implementation but can be overridden per-test or per-deployment.

---

## 6. The Runtime Pipeline — `ChronosEngine.process_user_input`

This is the heart of the engine (`backend/src/chronos_engine/engine.py`). A single call does
all of the following, in order:

### Step 1 — Input Processing Layer
`MediaProcessor.process_raw_input(...)` turns the raw payload into a `UserInput`:
- Resolves the `InputType` from the string; sniffs `audio`/`video` from a base64 data-URI
  header if present.
- For audio/video, generates `media_metadata` (format, size, estimated duration,
  media type) and inserts the honest "awaiting transcription" placeholder if no text note
  was supplied.
- Generates `in_<hex>` id and timestamps the input.

### Step 2 — Store in Memory System (write path)
`memory_system.add_interaction(user_input)`:
1. Computes the semantic embedding of the content (see §8).
2. Loads the user's last 30 memories and links this new memory to any with
   cosine similarity > `0.45` (this builds the **memory graph**).
3. Extracts tags (tokens > 4 chars, max 5).
4. Computes `importance_score = min(1.0, 0.4 + len(content)/200)`.
5. Persists via `storage.save_memory(memory)`.

### Step 3 — Update Timeline & Identity (write path)
- `timeline_engine.process_memory(user_id, memory_item)` → creates a `TimelineEvent` (see §9).
- `identity_model.evolve_profile(user_id, memory_item)` → mutates the `IdentityProfile`
  version and persists it (see §10).

### Step 4 — Retrieval Engine (read path)
`retrieval_engine.retrieve_context(user_input)` assembles the `RetrievedContext` (see §13):
semantic memory hits → short-term fallback → timeline events → life phase → identity profile
→ detected patterns → recent changes.

### Step 5 — Prompt Orchestration
`orchestrator.orchestrate_prompt(user_input, retrieved_context)` renders the fixed
**system prompt** ("You are ChronOS, the central personal intelligence layer for OpenTime…")
plus a structured **user prompt** with sections: current input, identity profile,
life phase, relevant memories, timeline highlights, detected patterns, recent changes,
and a closing instruction to answer using that context (see §14).

### Step 6 — Model-Agnostic LLM Call
- `llm_registry.get_provider(provider_key)` selects the provider (default `"chronos"`).
- The target model is `model_name` if given, else `"chronos-v1-core"` for the native
  provider, else `"gpt-4o"`.
- `provider.generate_response(prompt_context, target_model)` returns the raw LLM text.

### Step 7 — Response Validation & Post-Processing
`validator.validate_response(raw, prompt_context)` checks the response against the most
relevant memory and reports corrections (see §16).

### Step 8 — Explainability Trace
Builds a `ReasoningTrace` with 5 fixed `reasoning_steps` that describe exactly what the
engine did for this request, which memories it used, which provider it called, and how many
corrections were applied. `confidence_score` mirrors the validator's personalization score.

### Step 9 — Response Packaging
Measures elapsed wall time (ms), generates `resp_<hex>` id, and returns an `EngineResponse`
containing the original input, raw + final responses, provider/model names, the full
`PromptContext`, `ReasoningTrace`, `ValidationResult`, and timing.

### Read-only query methods (used by the dashboard)
- `get_memories(user_id, limit=100)` → list memories, newest first.
- `get_timeline(user_id)` → all timeline events, oldest first.
- `get_identity(user_id)` → profile (creates one if missing).
- `get_reflections(user_id, days_back=30)` → runs/completes insight generation.
- `get_patterns(user_id)` → runs/completes pattern analysis.
- `seed_initial_state(user_id)` → writes 4 sample memories (2 text, 1 audio, 1 video),
  evolves timeline + identity for each, then generates reflections and patterns.

---

## 7. Input Processing Layer — `MediaProcessor` (§utils/media_processor.py)

Responsibilities:

- **Type resolution**: accepts the input type string; if `base64_data` is supplied without
  raw bytes, it parses the data-URI header (`data:audio/...`, `data:video/...`) to infer
  `AUDIO`/`VIDEO` and decodes the payload.
- **Audio/video normalization**: if no filename, generates `audio_<hex>.webm` /
  `video_<hex>.webm`; builds `media_metadata`:
  - `format` — file extension (default `webm`),
  - `size_bytes` — actual byte length (fallback 51,200),
  - `estimated_duration_sec` — `max(2.5, size_bytes / 32_000)` (≈256 kbps heuristic),
  - `media_type` — `audio` or `video`.
- **Honest content placeholder**: when a recording has no accompanying text note, the engine
  does **not** fabricate a transcript. It stores `[Voice note - awaiting transcription]` or
  `[Video note - awaiting transcription]` so downstream features (and users) clearly see that
  transcription hasn't happened yet. Real transcription (e.g. Whisper) is a future hook here.
- **Output**: a fully-formed `UserInput` including `media_url` and `file_name`.

The actual file bytes are **not** handled here — persistence of uploaded files happens in the
API layer (§17.3) and the URL is passed in.

---

## 8. Memory System & Embeddings

### 8.1 `DefaultEmbeddingProvider` (§embeddings/provider.py)

A deterministic, lightweight, dependency-free semantic embedder (128-dim):

1. Lowercases text and extracts word tokens (`\w+`).
2. Builds token features: **unigrams + bigrams** (`word` and `word_next`).
3. Projects each token into the 128-dim space using Python's `hash()`:
   - index = `abs(hash(token)) % 128`,
   - value contribution `+1` if `hash > 0` else `-1`.
4. **L2-normalizes** the vector so cosine similarity reduces to a dot product.

Notes: `hash()` is seeded per-process (non-deterministic across restarts) — acceptable for the
current rule-based pipeline, but a swap to a stable model (OpenAI embeddings, sentence
transformers) is the planned upgrade path.

### 8.2 `MemorySystem` (§memory/service.py)

- **`add_interaction`** — builds the `MemoryItem` (§4.3) and persists it. This is the only
  place embeddings, links, tags, and importance scores are computed for a new memory.
- **`search_semantic_memories(user_id, query, top_k=5)`** — embeds the query, computes
  similarity against the user's last 200 memories, sorts descending, returns top-k. If a
  memory lacks an embedding it scores `0.0`.
- **`get_short_term_context(user_id, limit=5)`** — newest memories first; used as a fallback
  when semantic search returns nothing (e.g. very first interaction of a user).

**Memory graph**: linking is purely similarity-based right now (threshold `0.45`). There is
no graph traversal beyond reading `linked_memory_ids`.

---

## 9. Timeline Engine (§timeline/service.py)

For every new memory, `process_memory` builds one `TimelineEvent`:

1. **Life-phase detection** (keyword rules, checked in order):
   - contains `opentime` / `chronos` / `architect` → `"ChronOS Architecture & OpenTime Building"`,
   - contains `learn` / `study` / `research` → `"Exploration & Deep Research"`,
   - contains `build` / `ship` / `code` → `"Active System Execution"`,
   - otherwise inherit the previous phase, or `"Initial Phase"` if there is none.
2. **Recurrence check** — if any existing event's `title` is a substring of the new content,
   the event is marked `is_recurring=True`, `frequency="Weekly"`.
3. **Sentiment heuristic** — token-intersection scoring against a positive lexicon
   (`great, good, excited, love, confident, success, amazing, optimistic`) and a negative
   lexicon (`hard, stuck, tired, anxious, frustrated, bug, issue`):
   `sentiment = (pos - neg) / max(1, pos + neg)` → range `[-1, 1]`.
4. **Title** — first 50 chars (+`...`).
5. **Belief evolution note** — `"Reflects shift towards {life_phase}"`.

`get_timeline` returns all events sorted oldest→newest (this ordering drives the "current
life phase" computation in retrieval). `generate_historical_summary` groups events by phase
and prints one line per phase with its event count and last title.

---

## 10. Identity Model (§identity/service.py)

### `get_or_create_profile`
Loads the profile; if absent, seeds a rich **default profile** (interests in AI systems
architecture, goals around building OpenTime, values of Autonomy/Craftsmanship/Self-Reflection,
emotional tendencies map, skills, relationships, preferences, decision patterns,
communication style), persists it, and returns it. The dashboard always gets *something*.

### `evolve_profile(user_id, memory)`
Rule-based incremental evolution (each call bumps `version` and `last_updated`):

- **Interests**: if content mentions `voice` / `audio` / `video`, appends
  `"Multimodal Interaction"` (dedup, cap 10).
- **Goals**: if content contains `want to` / `goal` / `plan`, appends the first 60 chars of
  the content as a new goal (dedup, cap 10).
- **Emotional tendencies**: `confident`/`optimistic`/`excited` → optimism +0.02 (clamped ≤1.0);
  `anxious`/`tired` → optimism −0.02 (clamped ≥0.0).
- Persists the mutated profile.

This is deliberately heuristic today; the `prompt_context` parameter exists so a future LLM
driven "write a new profile line for this user" can take over without changing the interface.

---

## 11. Pattern Detector (§patterns/service.py)

`analyze_patterns(user_id)`:

- If the user has **no memories and no stored patterns**, it seeds 3 default
  `PatternItem`s (Clean Architecture First / High-Output Deep Work Blocks /
  Model-Agnostic Infrastructure Preference) and returns them — the dashboard is never empty.
- Otherwise it scans the concatenated lowercased content of the last 100 memories:
  - if `voice` or `record` appears, it detects a **HABIT** pattern
    ("Multimodal Voice / Video Input Preference", confidence 0.89) with supporting memory
    IDs for the matching memories, and stores it.
- Returns all stored patterns sorted by confidence (descending).

More categories (`RECURRING_PROBLEM`, `MOOD_SHIFT`, `DECISION_CHANGE`, …) exist in the enum
and are ready to be wired to real detectors.

---

## 12. Reflection Engine (§reflection/service.py)

`compare_past_and_present(user_id, days_back=30)` — the "growth journal" generator:

- **Seed path**: if the user has fewer than 2 memories and no existing reflections, it
  creates two default insights (an `EMOTIONAL_SHIFT` and a `FOCUS_SHIFT`) with reasoning
  traces and saves them.
- **Dynamic path**: splits the (up to 100) memories at the midpoint into *recent* vs *older*,
  joins their texts, and applies keyword heuristics:
  - recent text contains `confident`/`build` → `EMOTIONAL_SHIFT` insight ("become more confident").
  - recent text contains `chronos`/`voice`/`video` → `FOCUS_SHIFT` insight.
- Each generated insight is persisted, then **all** stored reflections are returned newest-first.

Note: this is batch/compute-on-read, not scheduled; the dashboard triggers it on load.

---

## 13. Retrieval Engine (§retrieval/service.py)

`retrieve_context(user_input)` assembles the context bundle in 5 steps:

1. **Semantic retrieval** — `search_semantic_memories(top_k=5)`.
2. **Fallback** — if empty, `get_short_term_context(limit=5)` (recent conversation).
3. **Timeline** — all events; `life_phase` = phase of the last event, else `"Initial Phase"`.
   Only the latest 5 events are put into the context.
4. **Identity** — `get_or_create_profile`, projected into a dict (interests, goals, values,
   emotional_tendencies, communication_style, decision_patterns).
5. **Patterns** — `analyze_patterns`, truncated to 4.

`recent_changes` is synthesized from the identity: the top goal (or `"Establishing core vision"`)
plus the optimism score percentage. This is the exact payload the prompt orchestrator consumes.

---

## 14. Prompt Orchestrator (§orchestrator/service.py)

Builds two prompts:

### System prompt (fixed)
> "You are ChronOS, the central personal intelligence layer for OpenTime. You sit between the
> user's raw data and language models. Your objective is to respond with high contextual
> awareness, personal alignment, and deep continuity across the user's life timeline, evolving
> identity, and behavioral patterns. NEVER treat the user input as a standalone query; ground
> every response in the user's stored memories and evolving identity."

### User prompt (context-enriched template)
Sections, in order:

```
=== CHRONOS ENGINE CONTEXT ENRICHMENT ===
[CURRENT USER INPUT (TYPE)]           <raw content>
[USER EVOLVING IDENTITY PROFILE]      interests / goals / values / communication style / emotions
[CURRENT LIFE PHASE]                  <phase>
[RELEVANT MEMORIES & HISTORICAL CONTEXT]   up to 5 dated memory bullets
[TIMELINE HIGHLIGHTS]                 up to 5 dated phase-tagged events
[DETECTED BEHAVIORAL PATTERNS & HABITS]    up to 4 patterns with confidence %
[RECENT PERSONAL EVOLUTION & GOALS]   recent_changes lines
=== INSTRUCTION TO UNDERLYING LLM ===  "Respond directly … keep the tone aligned …"
```

Empty sections render friendly placeholders (`"No prior closely related memories."`,
`"Timeline initialized."`, `"No active behavioral patterns detected yet."`).

---

## 15. LLM Providers & Registry (§llm/providers.py)

`LLMRegistry` holds five providers under string keys and a `_active_provider_key`
(default `"chronos"`). `get_provider(key)` falls back to `"chronos"` for unknown keys.

| Key | Class | Model default | Behavior |
|---|---|---|---|
| `chronos` | `ChronosNativeLLMProvider` | `chronos-v1-core` | Deterministic template responder; no external API; synthesizes an action plan from identity + goals + values. Runs offline, always works. |
| `openai` | `OpenAILLMProvider` | `gpt-4o` | Real `POST /v1/chat/completions` when `OPENAI_API_KEY` is set; otherwise returns an explicit simulated-response string noting how many memories were retrieved. |
| `anthropic` | `AnthropicLLMProvider` | `claude-3-5-sonnet-20241022` | Real `POST /v1/messages` when `ANTHROPIC_API_KEY` is set; simulated fallback otherwise. |
| `gemini` | `GeminiLLMProvider` | `gemini-1.5-pro` | Simulated response only (no client wired yet). |
| `ollama` | `OllamaLLMProvider` | `llama3:latest` | Simulated response only (no client wired yet). |

The **simulated responses are an explicit, intentional fallback**: the engine never crashes
when a key is missing, and the caller can always tell (the response text starts with
`[Provider … simulated response]`) that it wasn't a real model call.

`register_provider`, `set_active_provider`, and `list_providers` allow runtime extension and
discovery (`GET /chronos/engine/providers`).

---

## 16. Response Validator (§validators/service.py)

`validate_response(raw_response, prompt_context)`:

- Takes the top-relevance memory (`relevant_memories[0]`).
- If the first 30 chars of that memory's content are **not present** in the raw response, it
  records a `corrections_made` entry ("Injected historical continuity link from memory: …")
  — i.e., it detects when the LLM ignored the supplied context. (The response text itself is
  passed through unchanged in the current implementation.)
- `contradictions_detected` starts empty; the negative-preference check slot exists for future
  use.
- Returns `personalization_score = 0.96` (hard-coded for now — a real metric is planned).

---

## 17. HTTP API (§api/router.py)

All routes are under the `APIRouter(prefix="/chronos/engine")`, mounted by the app at
`/api/v1/chronos/engine/...`. This prefix was chosen to avoid colliding with OpenTime's
JWT-protected `/chronos/*` state routes.

### 17.1 Engine instance & media persistence

- A single module-level instance is created at import time:
  `engine_instance = ChronosEngine(storage=MongoStorageAdapter())`.
- `_persist_media(user_id, file_name, media_bytes)`:
  - sanitizes the filename (`[^a-zA-Z0-9._-]` → `_`),
  - writes to `{upload_dir}/{user_id}/{safe_name}` (no overwrites; UUID-prefixes on collision),
  - returns the public URL `/uploads/{user_id}/{safe_name}`.

### 17.2 Endpoints

| Method & Path | Params | Returns |
|---|---|---|
| `POST /process` | multipart form: `user_id` (default `user_default`), `content`, `input_type` (default `text`), `provider_key` (default `chronos`), `model_name`, `base64_data`, `file` (audio/video upload) | Full `EngineResponse` dict |
| `POST /process-json` | JSON body `ProcessInputRequest` (same fields, no file upload) | Full `EngineResponse` dict |
| `GET /memories` | `user_id`, `limit` (default 100) | List of `MemoryItem` dicts **with `embedding` stripped** — embeddings are never exposed over the API |
| `GET /timeline` | `user_id` | List of `TimelineEvent` dicts |
| `GET /identity` | `user_id` | `IdentityProfile` dict |
| `GET /reflections` | `user_id`, `days_back` (default 30) | List of `ReflectionInsight` dicts |
| `GET /patterns` | `user_id` | List of `PatternItem` dicts |
| `GET /providers` | — | `{active, available}` provider map |
| `POST /seed` | `user_id` | `{status, message}` |

### 17.3 Media upload flow (`POST /process`)

1. If `file` is present, read the bytes, persist to disk (§17.1), and — unless the caller
   explicitly set a type — sniff `input_type` from the file's MIME (`audio/*`, `video/*`).
2. Call `engine_instance.process_user_input(..., media_url=…)`.
3. On error, wrap as `HTTPException(500, "ChronOS Engine Error: …")`.
4. Return `response.model_dump()`.

### 17.4 Static media serving (§opentime/main.py)

- `settings.upload_dir` (default `"./uploads"`) is created on startup and mounted as
  `StaticFiles` at **`/uploads`**, so any persisted media is directly fetchable.
- Recordings live at `/uploads/{user_id}/{file}.webm` and are played back in the dashboard.

---

## 18. Storage Layer

### 18.1 The contract (`BaseStorageAdapter`)
10 methods covering memories, timeline events, identity, reflections, and patterns —
each has `save_*` and `get_*`/`get_by_user` variants.

### 18.2 `InMemoryStorageAdapter` (§storage/repository.py)
Plain Python dicts keyed by user, guarded by an `asyncio.Lock`. Used as the default fallback
and in tests. **Data does not survive a restart.**

### 18.3 `MongoStorageAdapter` (§storage/mongo_repository.py) — production
- Uses the shared OpenTime Motor client via `get_mongo_db()`.
- **Own collections** (`engine_*`) because engine documents carry engine-specific shape
  (embeddings, linked memories) distinct from OpenTime's chronos state:
  - `engine_memories`, `engine_timeline`, `engine_identity`, `engine_reflections`, `engine_patterns`.
- All writes are idempotent `replace_one(..., upsert=True)` on `{id, user_id}` (or just
  `user_id` for the identity singleton).
- Reads are scoped by `user_id`:
  - memories: sorted `timestamp` desc, `limit` applied,
  - timeline: sorted `timestamp` asc,
  - reflections: sorted `timestamp` desc,
  - patterns: sorted `confidence_score` desc.
- **Indexes** created in `client.py`'s `ensure_indexes`:
  - `engine_memories`: `user_id`; compound `(user_id, timestamp desc)`,
  - `engine_timeline`: `user_id`,
  - `engine_identity`: `user_id` (unique),
  - `engine_reflections`: `user_id`,
  - `engine_patterns`: `user_id`.

This is what made dashboard memories **persist across refreshes and server restarts**, per
user, ready for the engine's future retrieval/analysis.

---

## 19. Frontend Integration

- `frontend/src/lib/chronosApi.ts` — typed client. All engine calls go to
  `/chronos/engine/...`. Provides:
  - `processInput(userId, {content, inputType, file, base64Data, providerKey, modelName})`
    and the JSON variant,
  - `getMemories`, `getTimeline`, `getIdentity`, `getReflections`, `getPatterns`,
    `getProviders`, `seedState`,
  - `mediaUrl(relativePath)` — resolves `/uploads/...` to the API origin,
  - `MemoryItem.embedding` is optional because the API strips embeddings.
- `frontend/src/components/chronos/VoiceVideoRecorder.tsx` — MediaRecorder UI for audio/video;
  posts the blob via `processInput` (multipart). No-note recordings send empty content so the
  backend stores the "awaiting transcription" placeholder.
- `frontend/src/components/chronos/MemoryGraphView.tsx` — renders the Memories section;
  plays audio (`<audio>`) and video (`<video>`) directly from `metadata.media_url` when
  present.
- `frontend/src/components/chronos/ChronosEngineFeed.tsx` — the input panel that calls
  `processInput`, then triggers `loadEngineData()` so Memories/Timeline/Identity/Reflections/
  Patterns refresh after each response.

---

## 20. Data Flow Diagram (single interaction)

```
User types / records
   │
   ▼
POST /chronos/engine/process  (multipart: content, file?, input_type, provider_key)
   │
   ├─ _persist_media() ───────────────► disk: uploads/{user_id}/{file}.webm
   │
   ▼
MediaProcessor ─► UserInput{content, media_url, media_metadata}
   │
   ▼
MemorySystem.add_interaction ──► embedding ─► links ─► tags ─► importance
   │                                       └────► MongoDB engine_memories (write)
   ▼
TimelineEngine.process_memory ──► phase detection, sentiment, recurrence
   │                                       └────► MongoDB engine_timeline (write)
   ▼
IdentityModel.evolve_profile ──► interests/goals/emotions rules
   │                                       └────► MongoDB engine_identity (write, version++)
   ▼
RetrievalEngine.retrieve_context ──► semantic search ─► timeline ─► identity ─► patterns
   │                                       └──── reads engine_* collections
   ▼
PromptOrchestrator ──► system_prompt + context-enriched user_prompt
   ▼
LLMRegistry.get_provider(key) ──► raw_llm_response (native template or real API)
   ▼
ResponseValidator ──► grounding check ─► corrections ─► personalization_score
   ▼
ReasoningTrace (5 steps) ──► EngineResponse (everything bundled)
   ▼
Dashboard: feed shows final_response; Memories/Timeline/Identity/Reflections/Patterns reload
```

---

## 21. Explainability

Every `EngineResponse` includes a `ReasoningTrace` and the full `PromptContext`, so consumers
can answer:

- *What did the user say?* → `original_input`
- *What did we know about them?* → `prompt_context.retrieved_context`
- *What did the model answer?* → `raw_llm_response`
- *What did we clean up?* → `validation_result.corrections_made`
- *Why this confidence?* → `reasoning_trace.confidence_score` (= validation personalization score)
- *Which memories influenced this?* → `reasoning_trace.supporting_memory_ids`
- *How long did it take?* → `processing_time_ms`

This makes the engine's decisions auditable and debuggable end-to-end.

---

## 22. Design Decisions & Trade-offs

1. **Model-agnostic by construction** — the pipeline never binds to a vendor. Providers are
   keys in a registry; simulated fallbacks keep the system functional without API keys.
2. **Read-then-write** — every interaction both consumes and enriches the user's models,
   which is what gives ChronOS "memory" as opposed to a stateless chat.
3. **Deterministic heuristics over heavy ML** — embeddings, sentiment, phases, and identity
   evolution are rule-based and dependency-free. This keeps the core fast, testable, and
   offline-capable, at the cost of less nuance than an LLM would provide.
4. **Explainability is a first-class output** — the reasoning trace and full prompt context
   are returned to the caller, not logged-and-dropped.
5. **Own storage collections** — the engine keeps `engine_*` collections apart from OpenTime's
   chronos state so the two systems evolve independently without schema coupling.
6. **Honest placeholders for media** — no fake transcripts. The data model already carries
   `media_url` + metadata so real transcription can slot in later without schema changes.
7. **Never expose embeddings** — `GET /memories` strips `embedding` before returning data.
8. **Seeded defaults** — identity, reflections, and patterns all have seed paths so a brand-new
   user's dashboard is never empty and every screen renders on first load.
9. **Per-user isolation** — every read and write is scoped by `user_id`; `user_default` is the
   fallback when the dashboard hasn't authenticated a user yet.

---

## 23. Current Limitations & Roadmap

| Area | Current state | Planned |
|---|---|---|
| Transcription | Recordings stored with "awaiting transcription" placeholder | Whisper / ASR to fill real content on ingest or on-demand |
| Embeddings | `hash()`-based hashed n-gram (non-deterministic across processes) | Stable model embeddings (OpenAI / sentence-transformers) for real semantic retrieval |
| Retrieval | Brute-force similarity over last 200 memories | Vector index / ANN (PGVector, MongoDB Atlas Vector Search) |
| Reflections & patterns | Keyword heuristics + seeded defaults | LLM-driven insight generation with real reasoning traces |
| Validator | Grounding check only; `personalization_score` hard-coded 0.96 | True contradiction detection & computed personalization metric |
| Provider coverage | Gemini & Ollama are simulated-only | Real HTTP clients for both |
| Scheduling | Reflections/patterns computed on-read | Background cron/scheduler |
| Auth | Engine routes are not JWT-protected; `user_id` passed as param | Wire engine behind the same auth as OpenTime state routes |

---

## 24. Configuration

- `OPENAI_API_KEY` — enables the real OpenAI provider.
- `ANTHROPIC_API_KEY` — enables the real Anthropic provider.
- `upload_dir` (`opentime/infrastructure/config.py`, default `"./uploads"`) — disk location
  for recordings; mounted at `/uploads` by `main.py`.
- MongoDB connection is shared via `get_mongo_db()` (OpenTime's existing client/DB config);
  engine collections are auto-indexed by `ensure_indexes`.

---

## 25. How to Extend

- **New LLM provider** → subclass `BaseLLMProvider`, add to `LLMRegistry`. No other change.
- **New storage** → implement `BaseStorageAdapter` (Postgres/PGVector, S3-backed) and pass it
  to `ChronosEngine(storage=...)`.
- **New memory type** → extend `MemoryType`/`InputType` enums and the `MediaProcessor`
  resolution logic.
- **Real transcription** → replace the placeholder in `MediaProcessor.process_raw_input` (or
  add an async post-ingest job) and persist the transcript into `UserInput.content` +
  `MemoryItem.metadata`.
- **New pattern detectors** → add branches in `PatternDetector.analyze_patterns` mapping text
  signals to `PatternCategory` values.
- **Scheduled reflections** → call `ReflectionEngine.compare_past_and_present` from a worker
  (APScheduler / Celery) instead of only on-read.
