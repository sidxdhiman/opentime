# ChronOS: Beta Operator Guide

This guide is for the developer/operator running the beta. It covers environment verification, aggregate health monitoring, failure identification, safe telemetry inspection, incident response, and data management.

---

## 1. Operator Role and Privacy Boundary

The operator's role is to keep the beta environment healthy and to help participants when they report issues. The operator must:

- **Never** inspect raw private conversations unless absolutely necessary for debugging AND explicitly authorized by the participant (or required by law).
- **Never** store raw personal conversation content in logs, documents, or evidence logs.
- **Never** expose participant data to other participants.
- **Always** prefer aggregate/health metrics over per-user inspection.
- **Always** respect the participant's deletion/export requests.

If you must look at a participant's raw data to debug (recommended only for P0/P1 issues), document:
1. Why it was necessary.
2. What you accessed.
3. Who authorized it.
4. How you will ensure it is not needed again.

---

## 2. Verify the Beta Environment

### Pre-session checklist

1. Confirm the backend is accepting connections:
   ```bash
   curl http://<backend-host>:8000/health   # expect {"status":"healthy", ...}
   ```

2. Confirm MongoDB is reachable:
   ```bash
   # Via the app: the /health endpoint reports if Mongo is ready (startup warning only).
   # Or check Mongo directly if exposed.
   ```

3. Confirm the frontend is up and the participant can reach it:
   ```bash
   curl -I http://<frontend-host>:3000   # expect 200
   ```

4. Verify the /metrics/events endpoint is **not** exposed in a non-debug environment:
   - If `DEBUG=false`, `GET /chronos/engine/metrics/beta-summary` must return 404.
   - Same for `/metrics/events` and `/seed`.

5. For each participant, create their account using the **normal registration flow** (do not seed via `/seed` unless you have a specific reason).

6. Verify telemetry is being recorded:
   ```bash
   curl -H "Authorization: Bearer <participant-token>" \
        http://<backend-host>:8000/api/v1/chronos/engine/metrics/events
   ```
   (Only in debug; returns per-user counts. Cross-user isolation gives you **your own** counts only.)

---

## 3. Check Aggregate Health

### The `beta-summary` endpoint

Only available when `DEBUG=true`. Use it to see all-users aggregate health:

```bash
curl -H "Authorization: Bearer <operator-token>" \
     http://<backend-host>:8000/api/v1/chronos/engine/metrics/beta-summary
```

Returns:
```json
{
  "usage": {
    "total_users_created": 5,
    "total_users_onboarded": 4,
    "total_users_activated": 3,
    "total_users_returned": 1,
    "total_conversations_processed": 18,
    "activation_rate": 0.6
  },
  "core_loop": {
    "temporal_detected_users": 3,
    "stories_created_users": 2,
    "stories_progressed_events": 3,
    "total_stories_created": 5,
    "return_context_shown": 2,
    "temporal_engagement_rate": 0.17
  },
  "reliability": {
    "conversation_failures": 1,
    "request_failure_rate": 0.05,
    "memories_deleted": 0,
    "stories_archived": 0,
    "stories_restored": 0,
    "data_exports": 0
  },
  "data_quality": {
    "users_with_memories": 4,
    "users_with_stories": 2,
    "active_stories": 3,
    "users_receiving_return_context": 1
  }
}
```

### What to watch

| Signal | Do This | Interpretation |
|--------|---------|----------------|
| `request_failure_rate` > 0.1 | Investigate which conversations failed | Product is erroring; may need fix |
| `total_users_created` | Ensure each participant's account created | First use working |
| `total_users_onboarded` vs created | Every participant who registered should complete onboarding | Drop-off = activation issue |
| `total_users_activated` | Participant who onboarded should send at least 1 conversation | Drop-off = first-value issue |
| `total_users_returned` | At least some participants returning voluntarily | Return loop working |
| `memories_deleted` / `stories_archived` | Non-zero is OK; investigate if >50% of created | Trust issue possible |
| `stories_progressed_events` | Should increase over time if stories are being used | Temporal loop working |

These are **diagnostic signals**, not product-market-fit proof. Do not over-interpret.

---

## 4. Identify Failures

### Where failures surface

| Surface | How to detect |
|---------|--------------|
| Product fatal | `conversation_failed` in `beta-summary` |
| HTTP errors | Check backend logs (`structlog` output) |
| Client errors | Check network tab in browser / frontend console |
| Startup warning | `mongodb_startup_warning` in backend logs |

### How to investigate a failed conversation (without exposing content)

1. Check `beta-summary` for failure count.
2. Use the failing user's **own** `/metrics/events` endpoint (link to their account) — it shows counts but no content.
3. If you need more, check backend logs — they log `user_id` and error strings but NOT message content.
4. Only go deeper (query Mongo for the specific interaction) if it's a P0/P1 and you have authorization.

---

## 5. Inspect Telemetry Safely

### User-level telemetry (operator's own / participant with authorization)

```
GET /chronos/engine/metrics/events
```
Returns `by_event_type` counts for the authenticated caller. With the participant's permission and their JWT, this shows their own counts.

### Raw aggregate (dev-only)

```
GET /chronos/engine/metrics/beta-summary
```
Only in `DEBUG=true`. Returns aggregate only, no user IDs.

### Rules

- Never query the `product_events` collection directly at raw level unless you have a concrete debugging need.
- Never dump a participant's `interactions` collection to console/log.
- When you must query, use projections that exclude `user_content` and `final_response`:
  ```js
  db.interactions.find({user_id: "...", created_at: {$gt: <date>}}, {_id: 0, input_type: 1, created_at: 1, processing_time_ms: 1})
  ```
- If you must see content, do it in a private session, and do not log/store it in any shared artifact.

---

## 6. Respond to Participant Reporting an Error

### Step 1 — Acknowledge and isolate
- Ask which feature they were using and what error they saw.
- Do not immediately look at raw data.

### Step 2 — Check aggregate health
- Confirm `request_failure_rate` isn't elevated for everyone.
- If it is, pause the beta; file a bug; inform all participants.

### Step 3 — Check the participant's own telemetry
- With their permission, check their event counts.
- Look for unexpected `conversation_failed` counts.

### Step 4 — Reproduce
- Reproduce with a test account (never with the participant's real data) if possible.
- If not reproducible, document the report as a potential issue and move on.

### Step 5 — File / classify
- Use the bug classification (P0/P1/P2/P3).
- Inform the participant of the resolution.

---

## 7. Reset / Delete Participant Data

### If a participant requests deletion
- Direct them to `/me` → Data → "Delete all my ChronOS data" (they can do this themselves).
- OR (with their request) you can run the DELETE endpoint on their behalf with their JWT.
- Confirm deletion completed (the DELETE endpoint returns 204 only when fully complete; it raises 500 if any store purge failed).
- Verify via `product_events` count for that user is 0.

### If a participant's account is broken and you need to recreate
1. Delete the user's data (DELETE `/chronos/engine`).
2. Ask them to re-register with a *new* email (or you delete the SQL user too — but that's the account-auth layer, not covered here).
3. Re-onboard.

### NEVER
- Delete one participant's data to fix another participant.
- Seed test data into a participant's real account.
- Use `/seed` in production.

---

## 8. Anti-Exposure Rules

- Do NOT use `curl db.product_events.find()` to inspect raw event payloads unless debugging.
- Do NOT copy participant content into Slack/Teams/Docs/Jira.
- Do NOT use participant data in demo/automation accounts.
- Do NOT add participant content to the evidence log (BETA_EVIDENCE_LOG.md).
- Do NOT commit real participant JWTs, refresh tokens, or credentials to any repo.
- Do NOT share operator access with non-operator team members.

---

## 9. Environment Safety Checklist

Run before handing the beta URL to participants:

- [ ] `JWT_SECRET_KEY` is a real, strong secret (not the dev placeholder).
- [ ] `DEBUG=false` in the beta environment (unless there is a specific need for dev endpoints).
- [ ] `CORS_ORIGINS` is limited to the beta frontend origin.
- [ ] `/seed`, `/metrics/events`, `/metrics/beta-summary` all return 404 outside debug.
- [ ] Backend logs do not contain secrets.
- [ ] MongoDB connection string uses credentials (not exposed in logs).
- [ ] The participant's frontend URL is distinct from any public/production URL.
- [ ] The `uploads/` directory is not publicly served.

---

## 10. When to Pause the Beta

Pause the beta if:

- A P0 security/privacy/data-loss issue is discovered.
- A P1 issue breaks the product for a significant number of participants.
- The failure rate exceeds ~10% consistently.
- MongoDB/data-store failure means participant data may be at risk.
- Any indication of unauthorized access to participant data.

When you pause:

1. Inform all participants that the beta is temporarily paused.
2. Fix the issue, run full regression, and re-verify.
3. Resume only when the failure is resolved.