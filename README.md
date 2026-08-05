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
| `infrastructure/` | SQLAlchemy, JWT, S3, AI providers |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend dev)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (for backend dev)

### 1. Environment

```bash
cp .env.example .env
```

### 2. Start infrastructure + backend

```bash
docker compose up -d postgres redis minio
docker compose up backend
```

API available at `http://localhost:8000`  
Docs at `http://localhost:8000/docs`

### 3. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend at `http://localhost:3000`

### Full stack with Docker

```bash
docker compose up
```

## API Endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Sign in |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Revoke refresh token |
| GET | `/api/v1/auth/me` | Current user |

## Local Backend Development

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
uv run alembic upgrade head
uv run uvicorn opentime.main:app --reload
```

## Running Tests

```bash
cd backend
uv run pytest
```

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT
- **Frontend:** Next.js 15, React 19, Tailwind CSS 4, TanStack Query, Framer Motion
- **Database:** PostgreSQL 16
- **Cache/Queue:** Redis 7
- **Storage:** MinIO (S3-compatible)

## Roadmap

- [x] Phase 0: Project foundation
- [x] Phase 1: Authentication
- [ ] Phase 2: Memory upload (text)
- [ ] Phase 3: AI processing pipeline
- [ ] Phase 4: Timeline
- [ ] Phase 5: Search
- [ ] Phase 6: AI Chat
- [ ] Phase 7: Evolution Engine
