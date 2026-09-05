# ChronOS — Production / Beta Deployment Guide

**Single authoritative deployment guide for the ChronOS controlled beta.**

Authoritative source of truth: everything in this document is derived from the repository at execution time. Where a fact is confirmed by repo evidence it is labeled `CONFIRMED`. Where a decision must be made during deployment (hosting platform, DNS target addresses, provider credentials, etc.) it is labeled `DEPLOY DECISION` and never invented.

Target beta architecture (per project plan):

* Personal website: `https://sidharthdhiman.com`
* ChronOS frontend: `https://sidharthdhiman.com/chronos`
* ChronOS backend: `https://api.sidharthdhiman.com`
* MongoDB: private, not reachable from the browser
* Media: private, served only through authenticated backend routes
* ChronOS: a controlled beta, not a public unrestricted launch

---

## 1. Repository-derived architecture

### 1.1 Confirmed stack (from repo evidence)

| Layer | Technology | Evidence |
|-------|-----------|----------|
| Backend framework | FastAPI (`>=0.115`) | `backend/pyproject.toml:7` |
| Backend server | Uvicorn (`>=0.32`) | `backend/pyproject.toml:8`, `backend/Dockerfile:20`, `docker-compose.yml:87-88` |
| Backend language | Python 3.12+ | `backend/pyproject.toml:5`, `backend/Dockerfile:1` |
| Backend architecture | Clean Architecture (`api` → `application` → `domain` → `infrastructure`) | `backend/src/opentime/` directory layout |
| AI engine | `chronos_engine` Python package (26 modules) | `backend/src/chronos_engine/` |
| SQL database | SQLAlchemy 2.0 async (Postgres via asyncpg; SQLite/aiosqlite for dev) | `backend/pyproject.toml:9-11`, `backend/src/opentime/infrastructure/database/` |
| SQL migrations | Alembic | `backend/alembic.ini`, `backend/alembic/versions/001_initial_schema.py` |
| NoSQL database | MongoDB 7 via Motor (async) | `backend/pyproject.toml:22`, `docker-compose.yml:19`, `backend/src/opentime/infrastructure/mongodb/` |
| Redis | Redis 7 — configured but **not consumed by any application code** | `docker-compose.yml:31`, `backend/src/opentime/infrastructure/config.py:44` |
| Object storage | MinIO/S3 — configured but **not consumed by any application code** (media is local-disk) | `docker-compose.yml:43`, `backend/src/opentime/infrastructure/config.py:60-64` |
| Auth | JWT (HS256, python-jose) + bcrypt + DB-stored rotating refresh tokens | `backend/src/opentime/infrastructure/security/` |
| AI provider | OpenAI GPT-4o-mini + text-embedding-3-small (falls back to deterministic mocks when no key) | `backend/src/opentime/infrastructure/config.py:66-69`, `backend/src/opentime/infrastructure/services/` |
| Frontend framework | Next.js 15.1 (App Router), React 19, TypeScript | `frontend/package.json:19-21` |
| Frontend styling | Tailwind CSS 4 (`@tailwindcss/postcss`) | `frontend/postcss.config.mjs` |
| Frontend data | TanStack Query | `frontend/package.json:14` |
| Backend tests | pytest + pytest-asyncio + mongomock-motor | `backend/pyproject.toml:27-33`, `backend/tests/` |
| Frontend tests | Vitest | `frontend/package.json:31`, `frontend/vitest.config.ts` |
| Lint/format backend | Ruff | `backend/pyproject.toml:47-52` |
| Package managers | `uv` (Python), `npm` (Node) | `backend/Dockerfile:5`, `frontend/package.json` |

### 1.2 Runtime entrypoints (CONFIRMED)

* **Backend**: `uvicorn opentime.main:app --host 0.0.0.0 --port 8000` — `backend/Dockerfile:20`, `docker-compose.yml:87-88`. Module-level app object at `backend/src/opentime/main.py:85`.
* **Frontend dev**: `npm run dev` → `next dev`; **Frontend prod**: `npm run build` then `npm start` → `next start` (serves from `.next`). `frontend/package.json:5-8`.

### 1.3 API structure (CONFIRMED)

All routes mount under `API_PREFIX = /api/v1` (`backend/src/opentime/infrastructure/config.py:27`, wired in `backend/src/opentime/main.py:80`). Aggregated in `backend/src/opentime/api/v1/router.py`.

**Auth** — `backend/src/opentime/api/v1/auth.py`:
| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/auth/register` | creates account |
| POST | `/api/v1/auth/login` | JWT pair |
| POST | `/api/v1/auth/refresh` | rotates refresh token |
| POST | `/api/v1/auth/logout` | revokes refresh token |
| GET  | `/api/v1/auth/me` | current user (JWT auth) |

**Onboarding** — `backend/src/opentime/api/v1/onboarding.py`:
| Method | Path |
|--------|------|
| POST | `/api/v1/onboarding/start` |
| GET  | `/api/v1/onboarding/status` |
| POST | `/api/v1/onboarding/{session_id}/response` |
| POST | `/api/v1/onboarding/{session_id}/draft` |
| POST | `/api/v1/onboarding/{session_id}/complete` |

**Chronos state** — `backend/src/opentime/api/v1/chronos_state.py`:
`/api/v1/chronos/state`, `/identity`, `/memories`, `/timeline`, `/goals`, `/patterns`, `/preferences`, `POST /context`, goal CRUD + delete, `PATCH /preferences`, `PATCH /genesis`, `PATCH /identity/traits`.

**ChronOS engine** — `backend/src/chronos_engine/api/router.py`:
`/api/v1/chronos/engine/...` — `process` (multipart), `process-json`, `media/{user_id}/{file_name}`, `memories`, `timeline`, `identity`, `reflections`, `patterns`, `providers`, `interactions`, `threads`, memory delete, thread archive/restore, `return-context`, **debug-gated**: `seed`, `metrics/events`, `metrics/beta-summary`; `export`, `feedback`, `DELETE ""` (delete-all).

**Health**: `GET /health` (not under `/api/v1`) — `backend/src/opentime/main.py:72-78`. Returns `{"status":"healthy","app":...,"version":...}`.

### 1.4 Database (CONFIRMED)

* **SQL (auth)**: users + refresh_tokens tables. Postgres for production; SQLite local dev. Migrations via Alembic (`alembic upgrade head` — run at backend container startup in `docker-compose.yml:87`).
* **MongoDB (Chronos)**: database name default `opentime`. Collections: `onboarding_sessions`, `onboarding_responses`, `memories`, `identity_states`, `goals`, `timeline_events`, `patterns`, `analysis_preferences`, `chronos_states`, `product_events`, plus engine-authoritative `engine_*` collections (`engine_memories`, `engine_timeline`, `engine_identity`, `engine_reflections`, `engine_patterns`, `engine_interactions`, `engine_temporal_threads`, `engine_temporal_events`, `engine_temporal_snapshots`, `engine_return_ledgers`).
* Indexes are created automatically at startup by `ensure_indexes()` — `backend/src/opentime/infrastructure/mongodb/client.py:49-117`. This runs in the FastAPI lifespan (`main.py:21`). MongoDB startup failures are logged but **non-fatal** (`main.py:23-25`).

### 1.5 Media / file storage (CONFIRMED — important)

* Uploaded audio/video recordings are written to **local disk** at `{upload_dir}/{user_id}/{file_name}` where `upload_dir` defaults to `./uploads` (`backend/src/opentime/infrastructure/config.py:57`, `_persist_media` in `backend/src/chronos_engine/api/router.py:178-194`).
* Files are served **only** through the authenticated owner-checked route `GET /api/v1/chronos/engine/media/{user_id}/{file_name}` (`serve_user_media`, `router.py:197-219`). Path traversal blocked; auth user must equal path `user_id`.
* **S3/MinIO is configured but not implemented** — no boto3/minio usage anywhere in `src/` (verified by grep). MinIO in docker-compose and the S3_* env vars are currently inert.
* Transcription is a **stub** (`StubMediaService`), so audio/video content is stored but not transcribed — `backend/src/opentime/infrastructure/services/media_service.py`.

### 1.6 Authentication (CONFIRMED)

* JWT access token (HS256; claims `sub`, `email`, `exp`, `type:"access"`) + opaque, DB-stored, rotating refresh tokens.
* `user_id` is always derived from the JWT `sub`, never from request bodies — `backend/src/opentime/api/dependencies.py:23-50`.
* Login/session flow documented in `backend/DEVELOPMENT_TIMELINE.md` (§5 security audits).
* Frontend stores JWT pair in `localStorage` under `opentime_tokens` — `frontend/src/lib/api.ts`. **No cookies; no NextAuth.**

### 1.7 Frontend/backend communication (CONFIRMED)

* All four API client modules build the base URL from `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"`:
  - `frontend/src/lib/api.ts:1`
  - `frontend/src/lib/chronosApi.ts:3`
  - `frontend/src/lib/myDataApi.ts:8`
  - `frontend/src/lib/onboardingApi.ts:8`
* Because it is `NEXT_PUBLIC_`, it is **inlined at build time** — rebuild required to change the backend URL in production.
* CORS controlled by backend `CORS_ORIGINS` (`config.py:54`; middleware `main.py:41-47`, `allow_credentials=True`).

### 1.8 Docker / container setup (CONFIRMED)

* `docker-compose.yml` at repo root: services `postgres`, `mongodb`, `redis`, `minio`, `backend`.
* Backend `Dockerfile` builds a Python 3.12-slim image with uv, installs `-e ".[dev]"`, runs as non-root `appuser`, EXPOSE 8000.
* Compose runs `alembic upgrade head && uvicorn ... --reload` and mounts `./backend:/app` (a dev-style bind mount).
* Frontend is **not** containerized (not in docker-compose).
* Named volumes: `postgres_data`, `mongo_data`, `redis_data`, `minio_data`.
* `UPLOAD_DIR` has **no dedicated named volume** in the compose file. Because the backend container bind-mounts `./backend:/app`, uploads land under `./backend/uploads` on the host and would persist on the host path — but on a clean/production image build with no mount, uploads would be ephemeral inside the container. This is a beta risk (see §7).

### 1.9 Production/static serving behavior (CONFIRMED)

* Backend: Uvicorn serves the API + `/docs` and `/redoc` (Swagger/OpenAPI docs exposed unless disabled — see §5).
* Frontend: `next start` serves the production build. It is a full Node server (not static export — no `output: "export"`, it uses App Router with client components).

### 1.10 Required services (CONFIRMED)

* Postgres (or SQLite — production must use Postgres): auth/users.
* MongoDB: ChronOS state (required — data model is Mongo-centric).
* Media filesystem: required for media persistence (no S3 wiring).
* Redis: configured but **not required** (not consumed by code).
* MinIO/S3: configured but **not required** (not consumed by code).

### 1.11 Required ports (CONFIRMED / DEPLOY DECISION)

* Backend: `8000` (container/uvicorn default). Externally exposed port at the host/proxy is a deployment decision.
* Frontend: `3000` (Next default dev; `next start` serves on `3000` by default). External exposure is a deployment decision.
* Postgres `5432`, MongoDB `27017`, Redis `6379`, MinIO `9000/9001` (docker-compose defaults).

### 1.12 Build artifacts (CONFIRMED)

* Backend: Python packages `src/opentime` + `src/chronos_engine` built into a single wheel (`backend/pyproject.toml:39-40`).
* Frontend: `.next/` build directory (`frontend/.gitignore`).

### 1.13 Architecture diagram

```
Browser
  → https://sidharthdhiman.com/chronos          (frontend, mounted under /chronos)
  → ChronOS frontend  (Next.js 15, React 19)
  → HTTPS API  (CORS-restricted, JWT Bearer)
  → https://api.sidharthdhiman.com              (backend origin)
  → ChronOS backend   (FastAPI + Uvicorn, port 8000)
  → MongoDB (ChronOS state; engine-authoritative collections)
  → Postgres (auth: users, refresh_tokens)
  → local disk media (./uploads) — served only via authenticated media route
```

**Confirmed from repo**: everything above marked CONFIRMED.
**Must be decided at deployment** (DEPLOY DECISION): the hosting platform, exact DNS record targets/IPs, the external backend/frontend listening ports, TLS certificate issuance method, whether to disable `/docs`/`/redoc`, operational log retention location.

---

## 2. Deployment options

### 2.1 Option: Vercel (frontend) + managed backend container/VM

* **Compatibility**: Vercel natively runs Next.js, so `frontend/` builds without changes and supports a `basePath` for `/chronos` (see §3.2 — code changes still required). Backend is a long-running FastAPI process with a persistent filesystem for uploads and needs MongoDB+Postgres — Vercel Functions are not a natural fit for a persistent uvicorn server with local-disk media. So the backend would need a VM/container host or a managed provider.
* **Complexity**: Low for frontend, moderate overall (two providers).
* **Cost**: Frontend on Vercel hobby/free tier is cheap; backend VM/Mongo/Postgres add cost.
* **HTTPS/domain**: First-class on Vercel; backend proxied by a reverse proxy or its own TLS termination.
* **Environment variables**: Vercel dashboard supports `NEXT_PUBLIC_API_URL` per environment.
* **MongoDB connectivity**: works if the DB is reachable from the backend host (e.g. Atlas or a VPS DB).
* **Media persistence**: backend must be on persistent storage (ephemeral function storage would lose uploads). **Risk on Vercel-style compute.**
* **Ease of beta**: High familiarity, good DX.
* **Operational burden**: Low-medium.

### 2.2 Option: Docker-based deployment on a single VPS/cloud VM

* **Compatibility**: Uses the existing `docker-compose.yml` (modulo the dev-style bind mount and the missing persistence for uploads — see §7).
* **Complexity**: Low-medium; one host.
* **Cost**: Single VM (e.g. a modest droplet/instance) — likely the cheapest overall.
* **HTTPS/domain**: Add a reverse proxy (Caddy for automatic TLS, or Nginx + Certbot). Caddy is simplest and gets `sidharthdhiman.com/chronos` + `api.sidharthdhiman.com` on one box.
* **Environment variables**: `.env` / environment injection by compose engine.
* **MongoDB connectivity**: DBs and backend on the same private network — no public exposure (satisfies "MongoDB private").
* **Media persistence**: Bind-mount `./backend/uploads` (or a named volume) to host disk — the most natural fit for the current local-disk media implementation.
* **Ease of beta**: Few moving parts, easy to inspect, one operator.
* **Operational burden**: Medium — you manage the VM, updates, backups, TLS.

### 2.3 Option: Managed backend/container hosting (Railway, Render, Fly, Hetzner, etc.)

* **Compatibility**: Platform-managed Postgres/Mongo add-ons or a single Docker app from the repo's `Dockerfile`.
* **Complexity**: Low-medium; platform handles some ops.
* **Cost**: Pay-per-use; may exceed a single VPS at moderate scale.
* **HTTPS/domain**: Platform-provided TLS; custom domains supported.
* **Environment variables**: Dashboard-injected.
* **MongoDB connectivity**: Atlas or platform Mongo add-on; private networking possible.
* **Media persistence**: Requires a persistent volume attached to the backend service for `./uploads`. **Not automatic on serverless/ephemeral platforms.**
* **Ease of beta**: High.
* **Operational burden**: Low-medium.

### 2.4 Option: Vercel/Netlify static frontend + separate backend hosting

* **Compatibility**: Netlify can serve static/Next output. The backend would still need a persistent host.
* **Complexity**: Two platforms again.
* **Cost**: Similar to Option 2.1.
* **HTTPS/domain**: Supported.
* **MongoDB connectivity**: same as above.
* **Media persistence**: backend-host dependent; unchanged issue.
* **Ease of beta**: High familiarity.
* **Operational burden**: Low-medium.

### 2.5 Recommendation for the first controlled beta

> **Recommended: Single cloud VM (VPS) running Docker via docker-compose, frontend and backend served behind Caddy (automatic HTTPS) with Caddy path-mapping `/chronos` → frontend and `api.sidharthdhiman.com` → backend. MongoDB + Postgres + media all live on the same private VPS network and local disk, bound to private/localhost, not exposed publicly.**

**Why** (not over-engineered for a 5–15 user controlled beta):

* Matches the current repo state with **zero infrastructure redesign**. It is the only option that naturally satisfies all three solved-backend constraints (persistent media on local disk, private MongoDB, private media) without adding an object-store migration or serverless-persistence workarounds that would become **beta blockers**.
* One box = one bill, one firewall, one operator — the simplest surface for a controlled beta.
* Caddy gives automatic HTTPS and the exact `/chronos` + `api.` routing the plan calls for with minimal config.
* Cheap (single small/medium VPS), easy to tear down, easy to backup (DBs + uploads are all on disk).

If you prefer to avoid running a VM, the practical alternative is: **managed Next.js host (Vercel) for the frontend + a small Docker VM (or Railway/Render) for the backend with a persistent volume** — accepting two providers and the same `basePath` code change.

---

## 3. Domain and routing plan

### 3.1 Intended routing

```
https://sidharthdhiman.com/        → personal website (existing site, not ChronOS)
https://sidharthdhiman.com/chronos → ChronOS frontend (mounted under /chronos)
https://api.sidharthdhiman.com     → ChronOS backend (FastAPI, /api/v1, /docs, /health)
```

### 3.2 Does the frontend currently support `/chronos`? — **NO (CONFIRMED, beta blocker for path plan)**

The frontend **does not currently** support being served under `/chronos`. Evidence:

* `frontend/next.config.ts` has only `reactStrictMode: true` — **no `basePath`, no `assetPrefix`**.
* `.next/routes-manifest.json` reports `"basePath": ""` and assets emitted root-relative as `/_next/static/...`, so under `/chronos/*` the assets would 404 unless rewritten.
* `frontend/src/app/error.tsx:29` hard-codes `window.location.href = "/dashboard"` (raw browser navigation that bypasses `basePath`).
* All React navigation (`router.push("/dashboard")`, `<Link href="/...">`) would be auto-prefixed by `basePath`, so only the `error.tsx` raw URL is clearly broken; the rest works once `basePath` is set.

**Required code changes to mount at `/chronos` (not required for a top-level/domain-root frontend):**

1. In `frontend/next.config.ts`, set `basePath: "/chronos"` (and set `assetPrefix: "/chronos"` **or** have the reverse proxy rewrite `/_next/...` — safer to set both basePath and assetPrefix).
2. In `frontend/src/app/error.tsx:29`, replace the raw `window.location.href = "/dashboard"` with `router.push("/chronos/dashboard")` (or a `basePath`-aware relative path). Because `basePath` affects `next/link`/`next/navigation` automatically, only this raw `window.location` line breaks.
3. Configure the reverse proxy to route `sidharthdhiman.com/chronos/*` to the Next server while leaving the rest of `sidharthdhiman.com` on the personal site.

**API URL is independent of the web path** — `NEXT_PUBLIC_API_URL` points straight at `https://api.sidharthdhiman.com/api/v1`, and media URL construction in `chronosApi.ts` derives the backend origin from that same env var (`frontend/src/lib/chronosApi.ts:6`). Mounting the frontend under `/chronos` does **not** change API behavior.

**If you would rather NOT change code** (controlled beta priority), serve the ChronOS frontend at a **subdomain root** (e.g. `https://chronos.sidharthdhiman.com`) instead of `/chronos` — no `basePath` change needed. This is a valid beta alternative. (The plan statement targets `/chronos`; either works at deployment.)

### 3.3 DNS records

Deployment-time decisions (targets depend on chosen host); placeholder targets below:

| Type | Name/host | Target (example) | Source of target |
|------|-----------|------------------|------------------|
| A / AAAA | `api` | `<VPS IPv4/IPv6>` | IP of the VM/host serving the backend |
| A / AAAA | `@` (or `www`) | `<personal site host>` | Whatever hosts `sidharthdhiman.com` today — do NOT move it |
| (optional) A/AAAA | `chronos` | `<VPS>` | Only if you serve frontend on its own subdomain instead of `/chronos` |

If the frontend is served at `/chronos` on the existing `sidharthdhiman.com`, you do **not** add a `chronos` DNS record — the path is handled by the web server/proxy on the personal site origin. Only `api.sidharthdhiman.com` needs a new record.

### 3.4 HTTPS requirements

* `https://api.sidharthdhiman.com` must serve TLS with a valid cert. Caddy (recommended) auto-provisions Let's Encrypt certs; or Nginx + Certbot.
* `https://sidharthdhiman.com/chronos` must be served over HTTPS consistent with the existing personal site (its proxy must terminate TLS and proxy the `/chronos` path to the Next server).
* **Mixed-content precaution**: if the frontend is served at `https://sidharthdhiman.com/chronos` but `NEXT_PUBLIC_API_URL` were `http://...`, browsers would block it. Always use `https://api.sidharthdhiman.com/api/v1`.

### 3.5 CORS (CONFIRMED)

* Backend uses a single `CORSMiddleware` with `allow_origins=settings.cors_origins`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]` (`main.py:41-47`).
* `CORS_ORIGINS` default is `["http://localhost:3000"]` — **must be changed for production**.
* CORS is origin-based (scheme+host+port), not path-based. So a `/chronos` mount on `https://sidharthdhiman.com` and the backend on `https://api.sidharthdhiman.com` are **different origins**: set `CORS_ORIGINS=["https://sidharthdhiman.com"]` in production (a path-based mount does not change the origin). Include `https://www.sidharthdhiman.com` if the site redirects to/from `www`.

### 3.6 Cookies / auth implications

* Auth uses **Bearer JWT in memory + `localStorage`** — no cookies (CONFIRMED, `frontend/src/lib/api.ts`). Same-origin cookie concerns do not apply. The API always carries `Authorization: Bearer <token>`; no CSRF from cookies. Tokens in `localStorage` are accessible to any JS on the same origin — acceptable for a controlled beta; do not also serve untrusted third-party JS on that origin.

---

## 4. Environment variables

### 4.1 Backend (all handled by `backend/src/opentime/infrastructure/config.py` unless noted)

| Variable | Required? | Used by | Example/format | Secret? | Production guidance |
|----------|-----------|---------|----------------|---------|---------------------|
| `DEBUG` | Yes | `config.py:26`; gates `/seed`, `/metrics/events`, `/metrics/beta-summary`; JWT secret validation | `false` | No | **Must be `false` in production.** Enables dev endpoints + weak-secret allowance otherwise. |
| `APP_NAME` | No | `main.py:33`, `/health` | `ChronOS` | No | Cosmetic; matches `/health` output. |
| `API_PREFIX` | No | `main.py:80` | `/api/v1` | No | Keep default. |
| `HOST` | No | `config.py:30` | `0.0.0.0` | No | Keep for container; proxy handles external. |
| `PORT` | No | `config.py:31` | `8000` | No | Container default. |
| `DATABASE_URL` | Yes (prod) | SQLAlchemy (`session.py`) | `postgresql+asyncpg://USER:PASS@HOST:5432/opentime` | Credentials component | Point to private Postgres. Use strong password; non-trivial username. Never use the dev SQLite default in production. |
| `MONGODB_URL` | Yes | Motor (`mongodb/client.py:29`) | `mongodb://USER:PASS@HOST:27017/?authSource=admin` | Credentials component | Private, non-public. Strong auth. |
| `MONGODB_DB_NAME` | No | `mongodb/client.py:35` | `opentime` | No | Keep default unless naming conflict. |
| `REDIS_URL` | No (unused) | `config.py:44` | `redis://localhost:6379/0` | No | Present but not consumed by code; harmless to leave, or remove. |
| `JWT_SECRET_KEY` | Yes | JWT (`security/jwt.py`) | `<GENERATE_STRONG_SECRET>` | **Yes** | Must be a strong random string, e.g. `openssl rand -hex 32`. The config validator **rejects** known-insecure values when `DEBUG=false` (`config.py:71-78`). Never reuse across environments. |
| `JWT_ALGORITHM` | No | `config.py:49` | `HS256` | No | Keep default. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `config.py:50` | `15` | No | Keep default/15 (repo default) unless beta needs longer. Note `.env` example uses 60. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `config.py:51`, `jwt.py:36` | `7` | No | Keep default. |
| `CORS_ORIGINS` | Yes | `main.py:43` | `["https://sidharthdhiman.com"]` (JSON list) | No | Must list only the real frontend origin(s). Restricts cross-origin. |
| `UPLOAD_DIR` | No | `router.py:_upload_dir` | `/app/uploads` (container) or `/data/uploads` | No | Must point to a **persistent** volume (see §7). |
| `S3_ENDPOINT_URL` | No (unused) | `config.py:60` | `http://minio:9000` | No | Inert — no S3 code path. Ignore for beta. |
| `S3_ACCESS_KEY` | No (unused) | `config.py:61` | `minioadmin` | Credentials | Inert. |
| `S3_SECRET_KEY` | No (unused) | `config.py:62` | `minioadmin` | Credentials | Inert. |
| `S3_BUCKET_NAME` | No (unused) | `config.py:63` | `opentime-memories` | No | Inert. |
| `S3_REGION` | No (unused) | `config.py:64` | `us-east-1` | No | Inert. |
| `OPENAI_API_KEY` | Optional | LLM service (`llm_service.py`, `embedding_service.py`) | `sk-...` | **Yes** | Set only to enable real AI; if unset the system uses deterministic mocks (production-safe but minimal). |
| `LLM_MODEL` | No | `config.py:68`, LLM service | `gpt-4o-mini` | No | Keep default or override. |
| `EMBEDDING_MODEL` | No | `config.py:69`, embedding service | `text-embedding-3-small` | No | Keep default or override. |
| `OLLAMA_*` | No (disabled by default) | `chronos_engine/config/ollama.py` | e.g. `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_ENABLED=false` | No (except local secrets if any) | Leave disabled unless operator opts into local inference. Default `OLLAMA_ENABLED=false`. |

### 4.2 Frontend (CONFIRMED)

| Variable | Required? | Used by | Example/format | Secret? | Production guidance |
|----------|-----------|---------|----------------|---------|---------------------|
| `NEXT_PUBLIC_API_URL` | Yes (prod) | `api.ts:1`, `chronosApi.ts:3`, `myDataApi.ts:8`, `onboardingApi.ts:8` | `https://api.sidharthdhiman.com/api/v1` | No | **Build-time** inlined. Set at build; rebuild to change. Must be the full backend base including `/api/v1`. |

### 4.3 Never ship

* Do not commit `backend/.env`, root `.env`, or any `.env.local`/`.env.production` (all gitignored — CONFIRMED `.gitignore`, `backend/.gitignore`, `frontend/.gitignore`).
* The only committed env files are `.env.example` templates (no real secrets).

---

## 5. Production security requirements

All statements below are CONFIRMED from repo behavior and are **mandatory** for the beta:

| Requirement | Repo evidence | Deployment action |
|-------------|---------------|-------------------|
| `DEBUG=false` | Dev endpoints gated on `get_settings().debug` (`router.py:819,837,946`) | Set `DEBUG=false` in prod env. |
| Strong random `JWT_SECRET_KEY` | Validator rejects insecure values unless debug (`config.py:71-78`) | `openssl rand -hex 32`; set as secret. |
| No insecure/default JWT secret | Same validator + documented insecure set `_INSECURE_JWT_SECRETS` (`config.py:6-13`) | Never use `change-me-in-production-use-a-long-random-string`. |
| `/seed` unavailable in prod | 404 unless `debug=True` (`router.py:819-823`) | Auto-satisfied by `DEBUG=false`. Verify with curl (see §13). |
| `/metrics/events` + `/metrics/beta-summary` unavailable in prod | 404 unless `debug=True` (`router.py:826-852, 935-1036`) | Auto-satisfied by `DEBUG=false`. Verify. |
| Beta/operator endpoints not accidentally exposed | All sensitive content-bearing inspects are debug-gated | Confirm 404s in prod. |
| CORS restricted to intended origins | `CORS_ORIGINS` default is `["http://localhost:3000"]` (`config.py:54`) | Set to the real frontend origin(s) only. |
| HTTPS | Plan requirement | TLS on `api.` and on the site path serving `/chronos`. |
| MongoDB not publicly exposed | DB is a dedicated service; no browser path to Mongo | Keep Mongo bound to private/local network only (`mongodb://localhost` or private VPS net). |
| Media not publicly exposed | Media only served via authenticated owner-checked route (`router.py:197-219`) | Do **not** serve `./uploads` from the web server/static root — the API is the only serving path. |
| Authentication enforced | All sensitive routes use `get_current_user` dependency (`dependencies.py:23-50`) | No auth bypass on `/api/v1/*` except `/health`, `/docs`, `/redoc`, auth routes. |
| User identity from JWT | `user_id` derived from `sub`; never from body (`dependencies.py:27`, documented) | Preserve; do not trust client-supplied `user_id`. |
| No user-controlled `user_id` trust boundary | Media route already compares auth user to path `user_id` (`router.py:209-210`) | Set `CORS_ORIGINS`; keep auth enforced. |
| Sanitized error responses | Global handlers return generic 422/500 messages (`main.py:49-70`); `api/errors.py` maps domain errors | Preserve — generic messages don't leak internals. |
| No credentials committed to Git | Missing-key `JWT_SECRET_KEY:?...` in compose; env files gitignored | Never commit real secrets. |
| No `.env` secrets committed | `.gitignore`/`backend/.gitignore`/`frontend/.gitignore` ignore `.env*` | Never commit `.env*` real values. |
| Logs not exposing private content | structlog logs user_id + error strings, not message content (`router.py` logging); interaction persistence does not log raw content | Keep production log verbosity sane; do not add content logging. |
| Correct handling of refresh/access tokens | Rotating refresh tokens, DB-stored/hashed, revoked on logout/refresh (`application/auth/use_cases.py`, `security/jwt.py`) | Preserve; do not expose refresh token in browser logs/localStorage beyond current use. |

Preserved security assumptions documented in `DEVELOPMENT_TIMELINE.md` (§5A–5G security audits) and enforced in `backend/tests/test_security_*.py` — deployment must not regress these.

**Additional production hardening to consider (deploy-time, not code-blocking):**

* `/docs` and `/redoc` (Swagger) are exposed by default (`main.py:36-37`). For a controlled beta you may disable them (set `docs_url=None, redoc_url=None` in `create_app`) or leave them if the API is not sensitive on `api.`. Not a hard beta blocker, but recommended to disable if you want no public API surface browsing.
* Consider rate limiting / brute-force protection on auth routes and media route — none exists in code. Acceptable for controlled beta with limited participants; revisit before GA.
* Ensure the reverse proxy does not expose Postgres/Mongo ports outside the private network.

---

## 6. Database deployment

### 6.1 MongoDB (ChronOS)

* **Requirements**: MongoDB (Motor uses any modern MongoDB; compose pins `mongo:7-jammy`). A single database (default `opentime`).
* **Database name**: `MONGODB_DB_NAME` (default `opentime`).
* **Indexes**: created automatically by `ensure_indexes()` on app startup (`backend/src/opentime/infrastructure/mongodb/client.py:49-117`). This is idempotent. **No manual DDL required** for basic operation.
* **Vector search index**: the `embedding` field is stored per memory (`client.py:66-68` note), but the actual vector index is **not** created automatically — it must be created via Atlas UI/API if used. ChronOS does not currently require it at runtime (embeddings not exposed via API). **Not a beta blocker.**
* **Engine-authoritative collections**: the ChronOS engine writes to `engine_*` collections via `MongoStorageAdapter`/`MongoTemporalStore` (`backend/src/chronos_engine/storage/mongo_repository.py`). These are independent of the application-layer collections and are the authoritative source for engine features. They are created on demand as documents are written; indexes for them are in `ensure_indexes()`.
* **Persistent storage**: use a named volume (`mongo_data` in compose) or managed Atlas cluster with backups.
* **Backups (beta)**: acceptable minimum = nightly `mongodump` of the `opentime` database to the host (or rely on managed cluster snapshots) with a simple retention window (e.g. keep 7 days). Documented runbook: §14.
* **Connection security**: prefer MongoDB with auth + TLS; bind to private network or `localhost` only. Do not expose port 27017 publicly.
* **Network access**: backend must reach Mongo; browsers must not.
* **Migration/init**: none manual — `ensure_indexes()` runs at every startup. Alembic is only for the SQL (auth) schema, not Mongo.
* **Legacy backfill**: `backend/scripts/backfill_legacy.py` migrates application-store data into engine stores. **For a fresh beta database with no legacy users, backfill is NOT needed.** It is only relevant if you import pre-existing users/data. (CONFIRMED — backfill is operator-run, idempotent; `application/migration/legacy_backfill.py`.)

### 6.2 Postgres (auth/users)

* **Requirements**: Postgres (compose pins `postgres:16-alpine`). Database `opentime`, user/password set at creation.
* **Schema**: managed by Alembic — migration `001_initial_schema.py` creates `users` + `refresh_tokens`. Run `alembic upgrade head` at deploy (compose does this at container start, `docker-compose.yml:87`).
* **Persistent storage**: named volume `postgres_data` or managed instance. Backups via `pg_dump`.
* **Connection security**: private network/localhost; credentials via env.
* **Backfill**: N/A for auth (fresh schema).

---

## 7. Media/storage deployment

* **Where media is stored**: local disk under `UPLOAD_DIR` (default `./uploads`), organized as `{user_id}/{file_name}` (`backend/src/chronos_engine/api/router.py:178-194`). `backend/uploads/` is gitignored (`backend/.gitignore`).
* **Is it local filesystem?** Yes — CONFIRMED. There is no S3/MinIO code path.
* **Does it survive container restarts/redeploys?** **Only if `UPLOAD_DIR` is backed by a persistent volume or host bind-mount.** In the current `docker-compose.yml`, the backend bind-mounts `./backend:/app`, so uploads land on the host path `./backend/uploads` and survive locally. For a production/prod Docker image (no bind mount), you **must** add a persistent volume for `UPLOAD_DIR`, otherwise uploads are lost on container recreate. **This is a beta risk / potential beta blocker depending on how you deploy.**
* **Required directories**: `{UPLOAD_DIR}/` is created on demand by `_upload_dir()` (`router.py:171-175`); `{UPLOAD_DIR}/{user_id}/` created in `_persist_media`. The backend process (non-root `appuser` in the Dockerfile) needs write permission on the volume.
* **Permissions**: ensure the runtime user can create/write the upload directory and files. `appuser` in the Dockerfile (`backend/Dockerfile:15-16`).
* **File-size/type constraints**: none enforced in code (only filename sanitization `_SAFE_NAME`, `router.py:168`). No max-size limit present — a deployment concern for a controlled beta (bounded by participants; optional reverse-proxy body-size limit).
* **Authenticated media access**: served only via `GET /api/v1/chronos/engine/media/{user_id}/{file_name}` with owner check + traversal guard (`router.py:197-219`). Do not expose the filesystem via static serving.
* **Backup requirements**: media is part of participant data — back up `UPLOAD_DIR` alongside the DBs.
* **Implications of ephemeral hosting**: if placed on serverless/ephemeral compute, uploads are lost on instance recycle. This forces either persistent storage attachment or an S3/object-store migration (future improvement).

**Assessment for the current implementation** (per the requested classification):

* **Classification: BETA RISK** (not a code-correctness blocker; a deployment-correctness risk). The implementation works and is production-safe for a controlled beta **provided** `UPLOAD_DIR` is bound to a persistent volume. It would become a **beta blocker** only if deployed on storage-less compute without an attached volume. Do not silently redesign it — treat media as filesystem-backed for this beta.

---

## 8. Frontend deployment

### 8.1 Commands (CONFIRMED from `frontend/package.json`)

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Configure environment (build-time)
#   Create .env.production (gitignored) with:
#   NEXT_PUBLIC_API_URL=https://api.sidharthdhiman.com/api/v1

# 3. Build
npm run build          # -> next build (outputs .next/)

# 4. Start / serve (production)
npm start              # -> next start (serves on port 3000 by default)

# Lint / test / leakage check (before shipping)
npm run lint
npm test
npm run check:leakage
```

### 8.2 Configuring `/chronos` (only if using the path plan)

**Required code change** (see §3.2) — edit `frontend/next.config.ts`:

```ts
const nextConfig: NextConfig = {
  reactStrictMode: true,
  basePath: "/chronos",
  assetPrefix: "/chronos",
};
```

and fix `frontend/src/app/error.tsx:29` (`window.location.href = "/dashboard"` → a `basePath`-aware navigation). Then rebuild. Configure Caddy/Nginx to route `sidharthdhiman.com/chronos/*` → the Next server (port 3000). Serving the frontend at a subdomain root requires no code change.

### 8.3 Configuring the API URL

Set `NEXT_PUBLIC_API_URL=https://api.sidharthdhiman.com/api/v1` **at build time**. Because it is public/inlined, it is not a secret, but it must be correct for the deployed environment. Note `frontend/src/lib/chronosApi.ts:6` derives the media backend origin from this same var.

### 8.4 SPA / client routing

Next.js App Router handles routing (`/`, `/login`, `/register`, `/onboarding`, `/dashboard`, `/me`, `/my-data`, `/chronos-*` UI). With `basePath`, `next/link` and `next/navigation` are auto-prefixed; only the raw `window.location` in `error.tsx` needs the manual fix. No static-client fallback is configured (no `middleware.ts`); acceptable as-is for a server-rendered Next app.

### 8.5 Static asset paths

Use `assetPrefix` (for `/chronos`) or proxy `/_next` → `_next` (for subdomain). Without either, `/_next/static` 404s under `/chronos`.

### 8.6 Production build verification

`npm run build` must succeed. Serve a local `npm start` and confirm `/`, `/login`, `/dashboard` render before deploying.

---

## 9. Backend deployment

### 9.1 Commands / entrypoint (CONFIRMED)

```bash
# Local (uv)
cd backend
cp .env.example .env            # then edit .env for production values
uv pip install -e ".[dev]"      # or "uv sync"
alembic upgrade head            # apply Postgres schema
uvicorn opentime.main:app --host 0.0.0.0 --port 8000

# Docker image (from backend/Dockerfile)
#   CMD: uvicorn opentime.main:app --host 0.0.0.0 --port 8000
```

### 9.2 Configure environment

Set all production env vars (§4.1) before start — especially `DEBUG=false`, `DATABASE_URL` (Postgres), `MONGODB_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `UPLOAD_DIR`.

### 9.3 Bind host/port

Container default binds `0.0.0.0:8000`. In production, bind to the private/proxy network and let Caddy/Nginx proxy `api.sidharthdhiman.com` → `127.0.0.1:8000` (do not expose 8000 directly if avoidable, or keep it firewall-restricted).

### 9.4 Health verification

`GET /health` → `{"status":"healthy","app":...,"version":...}` (not under `/api/v1`). Confirmed at `backend/src/opentime/main.py:72-78`, tested in `backend/tests/test_health.py`.

### 9.5 Migrations/initialization

* `alembic upgrade head` for Postgres (compose does this at startup; otherwise run manually).
* MongoDB indexes are created automatically at startup (`ensure_indexes`).
* No other init required for a fresh DB.

### 9.6 Backend tests

```bash
cd backend
uv pip install -e ".[dev]"
uv run pytest            # uses in-memory mongomock; no real Mongo needed
uv run ruff check src    # linter
```

---

## 10. Docker deployment

### 10.1 What exists (CONFIRMED)

* `docker-compose.yml` (root) — services `postgres`, `mongodb`, `redis`, `minio`, `backend`; named volumes `postgres_data`, `mongo_data`, `redis_data`, `minio_data`; healthchecks; backend runs `alembic upgrade head && uvicorn ... --reload`.
* `backend/Dockerfile` — Python 3.12-slim; installs uv; `COPY pyproject.toml alembic.ini ./`, `COPY alembic`, `COPY src`; `uv pip install --system -e ".[dev]"`; `PYTHONPATH=/app/src`; non-root `appuser`; `EXPOSE 8000`; `CMD uvicorn opentime.main:app --host 0.0.0.0 --port 8000`.
* Ports: backend `8000`, postgres `5432`, mongo `27017`, redis `6379`, minio `9000/9001`.
* Frontend is **not** containerized.

### 10.2 Production vs dev differences

The existing compose file is **dev-oriented**: it uses `--reload`, binds `./backend:/app`, uses weak/direct creds (`opentime`/`opentime`, `minioadmin`/`minioadmin`), and exposes DB/minio ports publicly on the host. **Not production-ready as-is.**

### 10.3 What's missing for production (clear statement)

For a safe production/beta Docker deployment you must add/change:
1. **Media persistence**: add a named volume (or host path) for `UPLOAD_DIR` (e.g. `./backend/uploads:/app/uploads` or a named volume). Currently uploads only survive because the bind mount lands under host `./backend/uploads`.
2. **Remove `--reload`** from the prod backend command.
3. **Remove the dev bind mount** `./backend:/app` (or keep only on a dev stack).
4. **Hardened DB/MinIO creds** (not `opentime`/`opentime`, `minioadmin`/`minioadmin`).
5. **Do not publish DB/MinIO/Redis host ports publicly** — bind to internal network / `127.0.0.1` or `internal: true`.
6. Set production env (`DEBUG=false`, real `JWT_SECRET_KEY`, `CORS_ORIGINS`) — compose requires `JWT_SECRET_KEY` via `${JWT_SECRET_KEY:?...}` (`docker-compose.yml:70`).
7. Add a reverse proxy (Caddy/Nginx) container or host service for TLS + routing.

### 10.4 Commands (CONFIRMED from compose)

```bash
docker compose up -d postgres mongodb redis minio   # infra only
docker compose up backend                            # + backend (dev)
docker compose up -d                                 # all (dev)
docker compose down                                  # stop
docker compose down -v                               # stop + remove volumes (DESTROYS DATA)
```

### 10.5 Recommendation

Use the existing compose as a starting point but deploy a production overlay (separate compose file or production-specific values) applying the changes in §10.3. Do not run public beta against the dev compose as-is.

---

## 11. Domain setup — DNS checklist

Targets are DEPLOY DECISION (depend on host IPs); the checklist is the plan:

| Record type | Hostname | Target | Where the target comes from | TLS |
|-------------|----------|--------|------------------------------|-----|
| A / AAAA | `api` | `<VPS host IPv4/IPv6>` | IP of the VM/instance serving the backend | Caddy auto-TLS or Certbot for `api.sidharthdhiman.com` |
| (existing) A/CNAME | `@` / `www` | `<existing personal-site host>` | Whatever already serves `sidharthdhiman.com` — do not change | Existing site TLS |
| (only if frontend is NOT at `/chronos`) A/AAAA | `chronos` | `<VPS host IP>` | IP of the instance serving the Next frontend | Caddy/Nginx TLS for `chronos.sidharthdhiman.com` |

Notes:
* If the frontend is at `sidharthdhiman.com/chronos`, no new `chronos` DNS record is created — the path is served by the existing personal site's web server/proxy.
* Caddy (recommended) obtains Let's Encrypt certs automatically for `api.sidharthdhiman.com`. For the path-served frontend on `sidharthdhiman.com`, the existing site must already have TLS and proxy `/chronos` upstream.
* Do not create provider-specific values that cannot be known until the host is chosen.

---

## 12. Beta deployment checklist

### Before deployment
- [ ] Secrets configured (`.env.production` / secret manager): `JWT_SECRET_KEY=<GENERATE_STRONG_SECRET>`, DB/Mongo passwords
- [ ] `DEBUG=false` in the beta environment
- [ ] Database ready: Postgres schema migrated (`alembic upgrade head`); MongoDB reachable
- [ ] Database backups/retention understood (nightly dump or managed snapshots; retention policy set)
- [ ] Media persistence verified (persistent volume for `UPLOAD_DIR`; write test upload; confirm survives restart)
- [ ] CORS configured: `CORS_ORIGINS=["https://sidharthdhiman.com"]` (and `https://www...` if used)
- [ ] Domains configured: `api.sidharthdhiman.com` DNS; `/chronos` path mapping on the site (or subdomain)
- [ ] HTTPS configured: TLS on `api.` and on the site path serving the frontend
- [ ] Frontend production build passes (`npm run build`)
- [ ] Backend tests pass (`uv run pytest`)

### After deployment
- [ ] Homepage loads (`https://sidharthdhiman.com/`)
- [ ] `/chronos` loads (frontend reachable under the path)
- [ ] Registration works (`POST /api/v1/auth/register`, UI)
- [ ] Login works (`POST /api/v1/auth/login`, UI)
- [ ] Onboarding works (7-step, `/api/v1/onboarding/*`)
- [ ] First conversation works (`POST /api/v1/chronos/engine/process`)
- [ ] AI/deterministic fallback behavior works as expected (mock LLM if no `OPENAI_API_KEY`)
- [ ] Memory creation works (`engine_memories` populated)
- [ ] Stories work (temporal threads/archive/restore)
- [ ] Return context works
- [ ] Media upload works (voice/video recording → `UPLOAD_DIR`)
- [ ] Media retrieval respects ownership (user A cannot fetch user B media → 404)
- [ ] Export works (`GET .../export`)
- [ ] Individual memory deletion works (`DELETE .../memories/{id}`)
- [ ] Delete-all works (`DELETE /api/v1/chronos/engine`)
- [ ] User switching/isolation verified (two accounts don't bleed)
- [ ] Debug endpoints unavailable (see §13 checks)
- [ ] `/seed` unavailable (404 in prod)
- [ ] Error responses don't expose internals (generic 500/422)
- [ ] HTTPS works (no mixed content)
- [ ] CORS rejects unauthorized origins (browser console: blocked)

---

## 13. Smoke-test commands

All commands below are derived from confirmed endpoints/scripts.

### Frontend build
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=https://api.sidharthdhiman.com/api/v1 npm run build
```

### Backend tests / lint
```bash
cd backend
uv pip install -e ".[dev]"
uv run pytest
uv run ruff check src
```

### API health
```bash
curl -s https://api.sidharthdhiman.com/health
# -> {"status":"healthy","app":"...","version":"..."}
```

### Authentication check (register + login + me)
```bash
# Register (replace email/password)
curl -s -X POST https://api.sidharthdhiman.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"<BETA_EMAIL>","password":"<STRONG_PASSWORD>","full_name":"Test"}'

# Login
curl -s -X POST https://api.sidharthdhiman.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<BETA_EMAIL>","password":"<STRONG_PASSWORD>"}'
# -> capture access_token

# Me (with token)
curl -s https://api.sidharthdhiman.com/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Production configuration check
```bash
# Confirm no insecure default is accepted (should start fine because you set a real secret);
# verify via /health + by confirming DEBUG is off through endpoint behavior below.
```

### Debug endpoint checks (must be 404 in production)
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://api.sidharthdhiman.com/api/v1/chronos/engine/seed
# expect 401 (needs auth) then 404 once authed; with an agent token expect 404

curl -s -o /dev/null -w "%{http_code}\n" https://api.sidharthdhiman.com/api/v1/chronos/engine/metrics/events
curl -s -o /dev/null -w "%{http_code}\n" https://api.sidharthdhiman.com/api/v1/chronos/engine/metrics/beta-summary
# expect 401/404 (never 200) when DEBUG=false
```

### `/seed` check
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  https://api.sidharthdhiman.com/api/v1/chronos/engine/seed
# expect 404 when DEBUG=false
```

### CORS check
```bash
# An OPTIONS preflight from a disallowed origin should be rejected (no ACAO header for it)
curl -s -i -X OPTIONS \
  -H "Origin: https://evil.example.com" \
  -H "Access-Control-Request-Method: POST" \
  https://api.sidharthdhiman.com/api/v1/auth/login
# expect NO "access-control-allow-origin: https://evil.example.com" header
```

### Media ownership check
1. Upload a recording as user A (via the frontend `process` with multipart) → note the returned media URL.
2. Try to fetch that media URL with user B's token:
```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer <USER_B_TOKEN>" \
  https://api.sidharthdhiman.com/api/v1/chronos/engine/media/<USER_A_ID>/<FILE>.webm
# expect 404 (not 200)
```

### Deletion check
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  https://api.sidharthdhiman.com/api/v1/chronos/engine
# expect 204 when fully deleted; 500 if any store purge failed
```

---

## 14. Rollback and recovery

Keep this deliberately simple — no elaborate DR platform. Beta-safe approach:

| Scenario | Simplest beta-safe action |
|----------|---------------------------|
| Application rollback | Rebuild/redeploy previous image tag or revert code + rebuild. Since data is DB/media on disk (separate from code), a code rollback does not lose data. Keep release tags. |
| Database recovery | Restore a nightly `mongodump` (Mongo) and/or `pg_dump` (Postgres) snapshot. Keep last N backups. |
| Media recovery | Restore last backup of `UPLOAD_DIR` from nightly tar/rsync of the volume. |
| Bad deployment | Point the proxy back to the previous working backend/frontend (keep two release slots or a stable known-good tag). |
| Broken frontend | Since `NEXT_PUBLIC_API_URL` is build-time, keep the last good `.next` build + build artifacts (or git tag) to redeploy immediately. |
| Broken backend | `docker compose restart backend` or roll to previous image; run `uv run pytest` + `/health` check before re-serving. |
| Compromised secret | Rotate `JWT_SECRET_KEY` (invalidate all access tokens — they'll fail to decode) and force re-login; rotate DB/Mongo passwords; rotate `NEXT_PUBLIC_API_URL` rebuild only if URL reveals internal host. |

**What's recoverable with current architecture:**
* All participant data is in Postgres + MongoDB + `UPLOAD_DIR` on persistent storage → recoverable from nightly backups.
* Access/refresh tokens — recoverable by forcing re-login after secret rotation (users lose active sessions; re-login).

**What's not recoverable / not designed for:**
* There is no built-in multi-region/HA, no automated point-in-time recovery. For a 5–15 user controlled beta that is acceptable; treat backups as the recovery mechanism.
* No paused/deferred A/B routing — rollback means re-deploying previous build.
* No encrypted-at-rest guarantee — ensure the VPS disk + backup storage are encrypted if participant data sensitivity requires it.

---

## 15. Privacy/data-control deployment requirements

Production implications of each data type and how deployment must avoid exposure:

| Data | Stored in | Deployment must ensure NOT exposed via |
|------|-----------|----------------------------------------|
| Conversations | MongoDB `engine_interactions` (raw text) + `product_events` (metadata only); media on disk | DB not public; logs not content-echoing (structlog logs ids/errors, not content); CORS-restricted API |
| Memories | MongoDB `memories` + `engine_memories` | DB private; API user-scoped; embeddings never exposed via API (`export` strips `embedding`) |
| Identity/goals | `identity_states`, `goals`, `engine_identity` | DB private; API user-scoped |
| Temporal stories | `engine_temporal_threads/events/snapshots`, `engine_return_ledgers` | DB private; API user-scoped |
| Patterns | `patterns`, `engine_patterns` | DB private; API user-scoped |
| Media | local disk `UPLOAD_DIR` | NOT static-served; only authenticated owner route; do not expose volume via web server |
| Telemetry | `product_events` (metadata-only, no content) | Debug-gated metrics; prod has no debug endpoint |
| Export | on-demand JSON (in memory/response) | API user-scoped; transport over HTTPS |
| Deletion | `DELETE /api/v1/chronos/engine` purges all stores + media | Ensure delete-all runs fully (204 only on full success) |

Explicit confirmations:
* **No public database access**: keep Postgres/Mongo on private network; no public port mapping.
* **No public filesystem paths**: `UPLOAD_DIR` is served only by the authenticated API route; web server must not serve it as static.
* **No debug endpoints in prod**: `/seed`, `/metrics/events`, `/metrics/beta-summary` return 404 when `DEBUG=false`.
* **Logs**: logging uses structlog with ids/error strings, not message content (CONFIRMED in `router.py` logging + `_persist_interaction` warnings). Do not add content logging.
* **Error responses**: generic 500/422 (CONFIRMED `main.py:49-70`); no stack traces to client.
* **Operator endpoints**: all content-bearing metrics are debug-gated; prod 404.
* **Static file serving**: frontend serves only Next assets; it does not serve backend media/uploads.

---

## 16. Beta operator setup

Referenced from `DEVELOPMENT_TIMELINE.md` → `BETA_OPERATOR_GUIDE.md` (Phase 7 model). The operator model is **Phase 7 operator** (CONFIRMED).

### How an operator verifies system health
1. `curl https://api.sidharthdhiman.com/health` → healthy.
2. Frontend reachable at the beta URL (200).
3. Confirm debug endpoints are 404 (per §13).
4. Confirm each participant's account + onboarding + first conversation recorded (event counts).

### How aggregate beta metrics are accessed
* **Debug-only aggregate**: `GET /api/v1/chronos/engine/metrics/beta-summary` — returns aggregate usage/core-loop/reliability/data-quality counts, **no user IDs or content** (`router.py:935-1036`). Only available when `DEBUG=true`.
* **User-level counts (own account, or participant with their authorization + their JWT)**: `GET /api/v1/chronos/engine/metrics/events`.
* **Full interpretation guide** in `DEVELOPMENT_TIMELINE.md` `BETA_OPERATOR_GUIDE.md` §3 (what to watch: `request_failure_rate`, activation, return).

### What operators should NOT inspect
* Raw participant conversations/content unless authorized for a P0/P1 debug and documented.
* The `interactions` collection at raw level; never dump content to logs.
* Copying participant content into external tools/docs.
* Never inspect without a documented need.

### How to respond to incidents
Follow `DEVELOPMENT_TIMELINE.md` → `BETA_INCIDENT_RESPONSE.md` severity classification (P0 immediate / P1 within 24h / P2 within 1 week / P3 next hardening). First-response flow in `BETA_OPERATOR_GUIDE.md` §6: acknowledge + isolate, check aggregate health, check participant's own telemetry (with permission), reproduce on a test account, file/classify, inform participant.

### How participant data can be deleted/reset
* Self-service via `/me` → Data → "Delete all my ChronOS data" (`DELETE /api/v1/chronos/engine`; 204 on full success).
* Operator-assisted with the participant's JWT if requested.
* Recreate a broken account: delete engine data, re-register with a new email (or delete the SQL user too), re-onboard. Documented in `BETA_OPERATOR_GUIDE.md` §7.

### How to verify the system after a deployment
Re-run §12 (After deployment) checklist, especially: debug endpoints 404, media ownership isolation, delete-all 204, `/health` healthy, CORS rejects disallowed origins.

---

## 17. Exact deployment runbook

Addressing each step with concrete commands/config from the repo.

### Step 1 — Choose hosting
Decision: **Single cloud VPS (Docker + Caddy)** per §2.5. Provision an instance (Linux, Docker + Docker Compose installed). (DEPLOY DECISION — exact provider/instance.)

### Step 2 — Provision services
On the VPS, clone/deploy this repo. Prepare a **production compose file** per §10.3 (add `UPLOAD_DIR` persistent volume, remove `--reload`, harden creds, internal networking). Provision Postgres + MongoDB as compose services (private network) or managed equivalents.

### Step 3 — Configure secrets
```bash
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
export DATABASE_URL="postgresql+asyncpg://<user>:<pass>@<host>:5432/opentime"
export MONGODB_URL="mongodb://<user>:<pass>@<mongo-host>:27017/?authSource=admin"
export CORS_ORIGINS='["https://sidharthdhiman.com"]'
export DEBUG=false
export UPLOAD_DIR=/app/uploads
```
Store in production env / secret manager; never in git. Optionally set `OPENAI_API_KEY` to enable real LLM.

### Step 4 — Configure MongoDB
Ensure reachable by backend on private network; DB name `opentime`; indexes auto-created at startup. No manual Mongo DDL needed. (Backfill not needed for fresh beta.)

### Step 5 — Configure media storage
Ensure `UPLOAD_DIR` is a persistent volume/host path writable by the backend runtime user (`appuser`). Verify upload survives a restart.

### Step 6 — Deploy backend
```bash
docker compose -f docker-compose.prod.yml up -d backend
# or the raw path:
#   cd backend && uv pip install -e ".[dev]" && alembic upgrade head \
#   && uvicorn opentime.main:app --host 0.0.0.0 --port 8000
```
Verify: `curl -s localhost:8000/health`.

### Step 7 — Deploy frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=https://api.sidharthdhiman.com/api/v1 npm run build
npm start   # or containerize / run under the proxy on port 3000
```
(Apply the §8.2 basePath change first if serving at `/chronos`.)

### Step 8 — Configure domains
Add DNS: `api` A/AAAA → VPS IP. Ensure `sidharthdhiman.com` is unchanged. If frontend at `/chronos`, configure site proxy routing `/chronos` → frontend.

### Step 9 — Configure CORS/API URL
Backend env `CORS_ORIGINS=["https://sidharthdhiman.com"]`. Frontend build with `NEXT_PUBLIC_API_URL=https://api.sidharthdhiman.com/api/v1`. Rebuild frontend if URL changes.

### Step 10 — Enable HTTPS
Caddy auto-TLS for `api.sidharthdhiman.com`; ensure site path serving `/chronos` is already HTTPS. Verify no mixed content.

### Step 11 — Run smoke tests
Run §13 commands (health, auth round-trip, debug 404s, media ownership, delete-all, CORS).

### Step 12 — Verify security boundaries
Confirm: `DEBUG=false`, debug endpoints 404, `/seed` 404, CORS restricted, Mongo private, media not static-served, generic errors.

### Step 13 — Create beta operator account if applicable
Create an operator account via normal registration; use it for aggregate checks. (Per `BETA_OPERATOR_GUIDE`, operator uses aggregate endpoints — content endpoints avoided.)

### Step 14 — Create Participant #0
Create Participant #0's account through the normal registration flow and complete onboarding (do not use `/seed` in production). Verify their first conversation, memory, story, media, export, delete features.

### Step 15 — Run the first controlled beta session
Follow `BETA_PARTICIPANT_MODEL.md` onboarding: invite a small group (5–15), register, onboard, first message, observe, debrief. Use `beta-summary` (per participant authorization) for aggregate health.

---

## 18. Blockers and unknowns

| Item | Status | Evidence | Required before beta? | Action |
|------|--------|----------|----------------------|--------|
| Backend builds + runs (FastAPI/Uvicorn) | Confirmed ready | `Dockerfile`, `main.py`, passing `pytest` | Yes | — |
| Backend tests pass | Confirmed ready | `backend/tests/` (47 files), mock Mongo | Yes | — |
| Postgres auth schema + Alembic | Confirmed ready | `alembic/versions/001_initial_schema.py` | Yes | `alembic upgrade head` |
| MongoDB indexes auto-created | Confirmed ready | `ensure_indexes()` `mongodb/client.py` | Yes | none |
| Debug endpoints gated | Confirmed ready | `router.py` debug guards | Yes | set `DEBUG=false` |
| JWT-secret strength enforced | Confirmed ready | `config.py:71-78` validator | Yes | strong secret |
| CORS configurable | Confirmed ready | `config.py:54`, `main.py:41-47` | Yes | set real origins |
| Media owner-check auth | Confirmed ready | `router.py:197-219` | Yes | none (verify) |
| Generic error sanitization | Confirmed ready | `main.py:49-70` | Yes | — |
| Frontend builds + runs | Confirmed ready | `package.json`, `npm run build`, existing `.next` | Yes | — |
| Frontend at `/chronos` | **Requires code changes** | `next.config.ts` (no basePath); `error.tsx:29` raw URL | **Yes (for path plan)** | add `basePath`/`assetPrefix`; fix `error.tsx` |
| Frontend at a subdomain root | Confirmed ready (no change) | none needed | Yes (alternative) | serve at subdomain instead |
| Media persistence | **Requires deployment config** | no volume for `UPLOAD_DIR` in prod image | **Yes** | add persistent volume |
| S3/MinIO wiring | **Not implemented** | no boto3/minio in `src/` | No (unused) | ignore for beta; future GA |
| Redis | Configured but unused | no code consumption | No | ignore |
| Transcription (StubMediaService) | Stub | `media_service.py` | No (feature gap, documented) | accept for beta |
| Vector search index | Not auto-created | `client.py:66-68` note; embeddings not exposed | No | Atlas setup if ever used |
| `/docs`/`/redoc` exposed by default | Configured (decision) | `main.py:36-37` | Optional | disable if desired |
| Rate limiting / brute-force protection | Not implemented | no middleware | Acceptable beta risk | defer; monitor |
| Backend `--reload` + dev bind mount in compose | Dev-oriented | `docker-compose.yml:85-88` | Fix for production path | use prod overlay |
| Compose weak/`minioadmin` creds + public DB ports | Dev-oriented | `docker-compose.yml` | Fix for production path | harden prod compose |
| Exact hosting platform / DNS target IPs | **Requires hosting decision** | — | Yes | choose VPS; set DNS |
| `NEXT_PUBLIC_API_URL` build-time binding | Confirmed | all client modules | Yes | set + rebuild |
| OpenAI key (real AI vs mocks) | Deployment configuration (optional) | `config.py:66-69` | No (mocks safe) | set key for real AI |
| Log retention / backup platform | **Requires hosting decision** | — | Yes (backups) | nightly dump + media tar |

---

## 19. Final deployment recommendation

### Recommended Beta Architecture
A **single cloud VPS** running the ChronOS backend (FastAPI/Uvicorn, port 8000) via Docker, together with private **MongoDB** (ChronOS state, `opentime` DB) and **Postgres** (auth) on the same host's private network, with **media on a persistent local volume** (`UPLOAD_DIR`). A **Caddy** reverse proxy on the same host provides automatic HTTPS and routes:
* `api.sidharthdhiman.com` → backend `https://api.sidharthdhiman.com/api/v1`
* `sidharthdhiman.com/chronos` → the Next.js frontend (port 3000), after applying the small `basePath` code change.

Frontend is built with `NEXT_PUBLIC_API_URL=https://api.sidharthdhiman.com/api/v1` and served by `next start` behind Caddy. All hosting is on the same private VPS network — MongoDB, Postgres, DNS/misconfig of the public browser path never directly reachable by participants.

### Required Before First User
1. Production compose overlay: persistent `UPLOAD_DIR` volume, no `--reload`, harden DB/MinIO creds, private networking.
2. Secrets: strong `JWT_SECRET_KEY`, DB/Mongo credentials, `CORS_ORIGINS=["https://sidharthdhiman.com"]`, `DEBUG=false`.
3. Postgres `alembic upgrade head`; MongoDB reachable + indexes auto-created.
4. **If serving at `/chronos`: apply the `basePath`/`assetPrefix` + `error.tsx` code changes and rebuild.** (Or serve on a subdomain to avoid code changes.)
5. DNS for `api.sidharthdhiman.com`; site proxy path for `/chronos`; TLS via Caddy.
6. Media persistence verified (restart test).
7. Smoke tests pass (health, auth round-trip, debug 404s, media ownership, delete-all, CORS).

### Safe to Defer
* S3/MinIO/object-store migration (currently inert).
* Real OpenAI wiring (mocks are production-safe) — set `OPENAI_API_KEY` only to improve quality.
* Redis usage.
* Transcript/StubMediaService.
* Vector search index.
* Rate limiting / brute-force protection (acceptable for controlled beta).
* `/docs`/`/redoc` disabling (optional).
* Disabling `AAA`/multi-region/HA/point-in-time recovery.

### Known Risks
* **Media persistence** if deployed without a persistent volume (upload loss). Mitigated by §7/§10 changes.
* **`/chronos` code change** is required for the exact path plan; skipping it forces a subdomain alternative.
* **Mocks produce minimal AI output** without `OPENAI_API_KEY` — acceptable but limited value.
* **No built-in rate limiting** — fine for 5–15 users, monitor.
* **Dev-oriented compose** as shipped — a production overlay is required, not the repo compose as-is.
* **Public `/docs`/`/redoc`** by default — disable for a cleaner controlled surface.
* **Backups are operator-owned** — a nightly dump + media tar is the entire recoverability story; no automated HA.

### First Deployment Checklist
1. Provision VPS (Docker + Compose + Caddy).
2. Write production compose overlay (persistent volume, no reload, hardened creds, internal net).
3. Set all production env vars + strong secrets.
4. `alembic upgrade head`; verify Mongo indexes auto-created.
5. Apply `/chronos` basePath code change (if path plan); rebuild frontend with `NEXT_PUBLIC_API_URL=https://api.sidharthdhiman.com/api/v1`.
6. Start backend + frontend; configure Caddy routes + TLS for `api.` and `/chronos`.
7. Add `api` DNS record.
8. Run §13 smoke tests.
9. Verify §12 security boundaries (debug 404, `/seed` 404, media ownership, CORS, delete-all 204).
10. Create operator + Participant #0 via normal registration; complete onboarding; run first conversation.
11. Begin the controlled beta per `BETA_PARTICIPANT_MODEL.md`; monitor via `beta-summary` per participant.

---

*End of authoritative deployment guide. All repo-derived facts labeled CONFIRMED were verified against the codebase at the time of writing; DEPLOY DECISION items must be finalized by the project owner.*
