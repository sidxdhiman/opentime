# Phase 5B Report — Trust, Security & User Data Control

## Goal
Close the critical security gap found in the Phase 5A audit (engine endpoints trusted a client-supplied `user_id` with no authentication) and deliver user data control — without touching the ChronOS intelligence pipeline.

## What changed

### Security — ChronOS engine endpoints now require JWT auth
`backend/src/chronos_engine/api/router.py`
- Every user-scoped engine endpoint now depends on `Depends(get_current_user)`:
  `POST /process`, `POST /process-json`, `GET /memories`, `GET /timeline`,
  `GET /identity`, `GET /reflections`, `GET /patterns`, `GET /interactions`,
  `GET /threads`, `GET /threads/{thread_id}`, `POST /seed`.
- The authenticated `user_id = str(current_user.id)` is now derived from the
  bearer token; client-supplied `user_id` params were **removed** from all
  request bodies/forms/querystrings. `active_thread_id` remains a resource
  param but is resolved strictly against the authenticated user.
- `ProcessInputRequest.user_id` field removed.
- `GET /providers` intentionally left unauthenticated (no user data).

### Storage — `delete_all_for_user` on all data + temporal stores
`backend/src/chronos_engine/core/interfaces.py`
- Added abstract `delete_all_for_user(user_id)` to `BaseStorageAdapter` and
  `BaseTemporalStore` — additive only, no pipeline changes.

`backend/src/chronos_engine/storage/repository.py` (InMemory)
- `InMemoryStorageAdapter.delete_all_for_user`: purges memories, timeline,
  identity, reflections, patterns, interactions.
- `InMemoryTemporalStore.delete_all_for_user`: purges the user's threads,
  their events (by owned thread ids **and** by ownership mapping), the
  global ownership records, and snapshots — no orphaned events.

`backend/src/chronos_engine/storage/mongo_repository.py` (Mongo)
- `MongoStorageAdapter.delete_all_for_user`: deletes from all six engine
  collections.
- `MongoTemporalStore.delete_all_for_user`: deletes threads, then events
  (by `user_id` **and** owned `thread_id`), snapshots.

### Data control endpoints
`backend/src/chronos_engine/api/router.py`
- `GET /chronos/engine/export` — returns **only** the authenticated user's
  memories, timeline, identity, reflections, patterns, interactions and
  temporal threads/events. Embeddings are stripped; nothing from other users,
  no provider secrets or internal reasoning traces.
- `DELETE /chronos/engine` — permanently deletes the authenticated user's
  engine data via both stores (204).

### Frontend
`frontend/src/lib/chronosApi.ts`
- All engine calls now send the bearer token and **drop** the `user_id`
  argument; added authenticated `exportData()` and `deleteAllData()`.
- Updated callers in `dashboard/page.tsx` and `JourneyView.tsx`.

`frontend/src/components/my-data/DataControls.tsx` (new)
- Export button (downloads a JSON file) + Delete button with an inline
  destructive confirmation step; loading/success/failure states.

`frontend/src/components/my-data/MyDataExplorer.tsx`
- Adds `<DataControls />` to the existing Data section (no duplicating).

`frontend/src/app/error.tsx` (new)
- Client error boundary with recovery + navigation.

## Tests
`backend/tests/test_engine_export_delete.py` (new, 10 tests)
- Unauthenticated requests → 401 (memories / export / delete).
- Cross-user isolation on memories, thread list, and thread detail (404).
- Export returns only the authed user's data with no embeddings.
- Delete removes only the authed user's data; other user untouched; no
  orphaned temporal events.
- Storage-level `delete_all_for_user` (InMemory storage + temporal store).

Updated:
- `tests/conftest.py` — `override_auth` fixture overriding `get_current_user`
  with a deterministic fake `UserResponse` (no Postgres needed); added
  `make_user_response` helper.
- `tests/test_active_thread_context.py` — switched to overridden auth for all
  API calls; removed client-supplied `user_id` from payloads.
- `tests/test_temporal_models.py` — included `delete_all_for_user` in the
  `BaseTemporalStore` abstract-method set (additive interface change).

## Verification
- Backend: `pytest` → **618 passed, 4 skipped** (was 617 + new tests).
- New export/delete/isolation tests: 10 passed.
- Frontend: `npx tsc --noEmit` clean; `next build` succeeds.

## Scope respected
No changes to temporal detection/classification/thread matching/lifecycle/
comparison/past-self/question planning/relevance/composition/reflection/AI
routing/inference/model tier/reasoning planner/memory retrieval. No multi-user,
sharing, social, notifications, return hooks, or 5C/5D/5E work.
