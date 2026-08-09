# OpenTime

**Personal Evolution Engine** — understand how you change over time through AI-powered memory analysis.

## Architecture

```
opentime/
├── backend/          FastAPI + Clean Architecture (Python 3.12+)
├── frontend/         Next.js App Router (TypeScript)
└── docker-compose.yml
```

### Backend Layers

| Layer | Responsibility |
|-------|---------------|
| `api/` | HTTP routes, middleware, dependencies |
| `application/` | Use cases, DTOs |
| `domain/` | Entities, repository interfaces, business rules |
| `infrastructure/` | SQLAlchemy (auth), Motor/MongoDB (Chronos), JWT, AI providers |

### Databases

| Store | Purpose |
|-------|---------|
| SQLite / PostgreSQL | User accounts and auth tokens (SQLAlchemy) |
| MongoDB | Chronos state — onboarding, memories, identity, goals, timeline, patterns |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend dev)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (for backend dev)

### 1. Environment

```bash
cp .env.example .env
cd backend && cp .env.example .env
```

### 2. Start all infrastructure + backend

```bash
docker compose up -d postgres mongodb redis minio
docker compose up backend
```

API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

### 3. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`

### Full stack with Docker

```bash
docker compose up
```

## Running Tests

```bash
cd backend

# Install dev deps (includes mongomock-motor, pytest-mock)
uv pip install -e ".[dev]"

# Run all tests (no real MongoDB needed — uses in-memory mock)
uv run pytest

# With verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_onboarding_service.py
uv run pytest tests/test_chronos_init.py
```

Linter: `uv run ruff check src`

---

## New User Flow

```
Register → /onboarding (7 steps) → Chronos Init → /dashboard
```

A new user who registers is redirected to `/onboarding`. Returning users with a completed onboarding session go directly to `/dashboard`.

---

## Onboarding Steps

| # | Key | Title | Optional |
|---|-----|-------|----------|
| 1 | `about_you` | Let's get to know you | Yes (all fields) |
| 2 | `life_right_now` | What does your life look like right now? | No |
| 3 | `whats_on_mind` | What's taking up most of your mind? | Yes |
| 4 | `where_going` | What are you trying to change or achieve? | No |
| 5 | `how_changed` | How have you changed recently? | Yes |
| 6 | `first_memory` | Give Chronos something to remember | No (Genesis Memory) |
| 7 | `analysis_prefs` | What do you want OpenTime to help you understand? | No |

Features: progress bar, back/next navigation, autosave (1.5s debounce), resume on refresh, skip for optional steps, animated transitions.

---

## Chronos Initialization Pipeline

After `POST /api/v1/onboarding/{session_id}/complete`, the backend runs:

```
RAW ONBOARDING RESPONSES
  ↓ Memory Extraction       (one Memory per meaningful response)
  ↓ Genesis Memory          (Step 6 → is_genesis=true, source="genesis")
  ↓ Identity Extraction     (LLM extracts traits/interests/values from steps 1,2,5)
  ↓ Goal Extraction         (Step 4 structured goals → Goal entities)
  ↓ Timeline Creation       (Step 5 changes + "Joined OpenTime" event)
  ↓ Analysis Preferences    (Step 7)
  ↓ Pattern Baseline        (low-confidence baseline from steps 2,3)
  ↓ ChronosState            (master snapshot, is_initialised=true)
  ↓ MongoDB
```

**Idempotent** — calling complete twice will not create duplicate data.

---

## MongoDB Collections

| Collection | Purpose |
|-----------|---------|
| `onboarding_sessions` | Session tracking (resume support) |
| `onboarding_responses` | Raw user answers — append-only, never overwritten |
| `memories` | All extracted memories including genesis |
| `identity_states` | Versioned identity snapshots |
| `goals` | Individual goal records |
| `timeline_events` | Significant life events |
| `patterns` | Behavioural pattern baselines |
| `analysis_preferences` | User's Chronos preferences |
| `chronos_states` | Master Chronos state per user |

All collections include a `user_id` index. Every query is scoped by `user_id`.

---

## API Endpoints

### Auth (existing)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account → redirects to onboarding |
| POST | `/api/v1/auth/login` | Sign in |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Revoke refresh token |
| GET  | `/api/v1/auth/me` | Current user |

### Onboarding (new)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/onboarding/start` | Start or resume session |
| GET  | `/api/v1/onboarding/status` | Get current onboarding status |
| POST | `/api/v1/onboarding/{id}/response` | Save a step response |
| POST | `/api/v1/onboarding/{id}/draft` | Autosave draft |
| POST | `/api/v1/onboarding/{id}/complete` | Complete → trigger Chronos init |

### Chronos State (new)

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/v1/chronos/state` | Full Chronos state |
| GET  | `/api/v1/chronos/identity` | Latest identity snapshot |
| GET  | `/api/v1/chronos/memories` | Paginated memories (embedding omitted) |
| GET  | `/api/v1/chronos/timeline` | Paginated timeline events |
| GET  | `/api/v1/chronos/goals` | Active (or all) goals |
| GET  | `/api/v1/chronos/patterns` | Behavioural patterns |
| POST | `/api/v1/chronos/context` | Full context snapshot for LLM |

---

## LLM & Embeddings

The system uses a clean abstraction — no hard dependency on any provider.

| Env Var | Effect |
|---------|--------|
| `OPENAI_API_KEY` not set | Uses `MockLLMService` + `MockEmbeddingService` (deterministic, safe) |
| `OPENAI_API_KEY=sk-...` | Uses GPT-4o-mini + text-embedding-3-small |
| `LLM_MODEL=gpt-4o` | Override LLM model |
| `EMBEDDING_MODEL=text-embedding-3-large` | Override embedding model |

Mock implementations are production-safe — they return structurally valid but minimal/empty responses, so the pipeline completes without crashing.

---

## Privacy

- Raw onboarding responses are stored separately from Chronos interpretations
- Embeddings are never exposed through the public API
- Every query is scoped by `user_id` from the JWT — no cross-user data leakage
- All inferred attributes carry `claim_type` (FACT / USER_STATEMENT / INFERENCE / HYPOTHESIS) and `confidence` scores
- Architecture supports future full data export and deletion per user

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | SQLite | SQL DB for auth |
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB for Chronos |
| `MONGODB_DB_NAME` | `opentime` | MongoDB database name |
| `JWT_SECRET_KEY` | (change me) | JWT signing key |
| `OPENAI_API_KEY` | — | Enables real LLM+embeddings |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model name |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed frontend origins |

---

## What Remains for the Next Chronos Phase

- **Real LLM provider wiring**: `OPENAI_API_KEY` → full extraction quality
- **Audio/video genesis memory**: replace `StubMediaService` with Whisper transcription
- **Chronos chat**: POST `/api/v1/chronos/chat` — uses `ChronosContextBuilder` + LLM
- **Memory update flow**: new user inputs update existing Chronos state (not just onboarding)
- **Reflection engine**: periodic "how have you changed since X" comparisons using identity version diffs
- **Pattern strengthening**: increment evidence counts as new inputs confirm baseline patterns
- **MongoDB Atlas Vector Search**: `embedding` field is already in the schema — add the index in Atlas UI
- **Data export / deletion**: `DELETE /api/v1/user/data` — repos already have `delete_all_for_user`
- **Onboarding re-entry**: allow users to update onboarding answers and trigger a Chronos re-analysis

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, Motor (MongoDB), Alembic, Pydantic v2, JWT
- **Frontend:** Next.js 15, React 19, Tailwind CSS 4, Framer Motion, lucide-react
- **Database:** PostgreSQL 16 (auth) + MongoDB 7 (Chronos)
- **Cache/Queue:** Redis 7
- **Storage:** MinIO (S3-compatible)
- **AI:** Pluggable — OpenAI GPT-4o-mini / text-embedding-3-small (or mock for dev)

## Roadmap

- [x] Phase 0: Project foundation
- [x] Phase 1: Authentication
- [x] Phase 2: New user onboarding (7-step) + Chronos initialization
- [ ] Phase 3: Memory upload (text + audio/video)
- [ ] Phase 4: Chronos chat
- [ ] Phase 5: Timeline UI
- [ ] Phase 6: Reflection engine
- [ ] Phase 7: Evolution Engine
