# Phase 7: Beta Success Framework & Meaningful Usage Definitions

## Beta Success Questions

### Activation
- Do users understand what ChronOS is?
- Do they complete onboarding?
- Do they send a first meaningful message?

### Engagement
- Do they continue conversations?
- Do they provide additional context?
- Do memories accumulate naturally?

### Temporal Value
- Does ChronOS detect meaningful temporal information?
- Do stories actually form?
- Do stories progress?
- Does historical context improve later conversations?

### Return Value
- Do users come back?
- Does resurfacing happen when meaningful evidence exists?
- Do users continue interacting after resurfacing?

### Trust
- Do users believe ChronOS accurately understands them?
- Do users correct/delete memories?
- Do users encounter anything that feels fabricated or intrusive?

### Retention
- Do users return after the first session?
- Does usage become more valuable as history accumulates?

---

## Meaningful Usage Definitions

Do NOT equate page opens, button clicks, or request attempts with meaningful usage.
Prefer confirmed backend events.

### Meaningful Conversation
A conversation counts as meaningful ONLY when:
- `conversation_processed` event is emitted (backend confirmed success)
- The response contains a non-empty `final_response`
- Processing completed without error

### Story Creation
A story counts as created ONLY when:
- `temporal_lifecycle.created == true` in the `conversation_processed` metadata
- A `TemporalThread` document exists in `engine_temporal_threads` for the user

### Story Progression
A story counts as progressed ONLY when:
- `temporal_lifecycle.updated == true` or `temporal_lifecycle.transitioned == true`
- The thread's `updated_at` is newer than its `created_at`
- The thread has more than one `TemporalEvent` attached

### Memory Creation
A memory counts as created ONLY when:
- A `MemoryItem` document exists in `engine_memories` for the user
- The memory was persisted by the engine (not just detected)

### Return Context Shown
Return context counts as meaningful ONLY when:
- `return_context_shown` event is emitted
- The `ReturnContext` has `has_return_context == true`

### Activation
A user counts as activated ONLY when:
- `account_created` event exists
- `onboarding_completed` event exists with `chronos_initialised == true`
- At least one `conversation_processed` event exists (first meaningful message)

### Returning User
A user counts as returning ONLY when:
- They have more than one distinct session (interaction `created_at` on different days)
- OR they have a `return_context_shown` event after their first session

---

## Beta Health Signals

### Error Rate
- `conversation_failed` count / (`conversation_processed` + `conversation_failed`) count

### Activation Rate
- Users with `conversation_processed` / Users with `account_created`

### Temporal Engagement
- `conversation_processed` events with `temporal_detected == true` / total `conversation_processed`

### Story Formation
- Distinct threads created (from `temporal_lifecycle.created`) / activated users

### Story Progression
- `conversation_processed` events with `thread_updated == true` or `thread_transitioned == true` / total `conversation_processed` with `thread_match_attempted == true`

### Return Loop
- `return_context_shown` events / activated users

### Data Control Activity
- (`memory_deleted` + `story_archived` + `story_restored`) / activated users

---

## Signal Classification Framework

Every quantitative metric is classified into one of three types:

* **DIAGNOSTIC** — A signal that reveals something about the product, but does NOT indicate success/failure on its own.
* **BETA SUCCESS CRITERION** — A measurable bar that must be met for the beta to be considered useful.
* **REQUIRES QUALITATIVE VALIDATION** — A dimension that cannot be judged from numbers alone; requires participant interview/observation.

### Activation

| Signal | Type | Definition |
|--------|------|------------|
| Registration completes | DIAGNOSTIC | `account_created` event exists |
| Onboarding completes | DIAGNOSTIC | `onboarding_completed` with `chronos_initialised == true` |
| First conversation | DIAGNOSTIC | `conversation_processed` exists for the user |
| **Activation rate ≥ 60%** | BETA SUCCESS CRITERION | Users who registered → activated (≥1 meaningful conversation). There is no prior benchmark — 60% is an exploratory floor, not a growth target. |
| User understands what ChronOS is | REQUIRES QUALITATIVE VALIDATION | From interview question 1. |
| User understands what ChronOS remembers | REQUIRES QUALITATIVE VALIDATION | From interview question 2. |
| Onboarding friction observed | DIAGNOSTIC | Any step causing hesitation/getting stuck; count per-participant. |

### First Value

| Signal | Type | Definition |
|--------|------|------------|
| Time to first meaningful response | DIAGNOSTIC | Backend processing time for first `conversation_processed` |
| First response contains temporal reference | DIAGNOSTIC | `temporal_detected` in first event metadata |
| **Participant identifies a "useful" moment** | REQUIRES QUALITATIVE VALIDATION | From interview question 3. |
| Temporal context materially improves response | REQUIRES QUALITATIVE VALIDATION | From interview question 4 + observer. |
| First value reached within first session | BETA SUCCESS CRITERION | Observational: participant shows recognition of value within the first session. |

### Temporal Value

| Signal | Type | Definition |
|--------|------|------------|
| Temporal detection occurs | DIAGNOSTIC | % of conversations with `temporal_detected == true` |
| Stories form | DIAGNOSTIC | `thread_created` events / activated users |
| Stories progress | DIAGNOSTIC | `thread_updated` or `thread_transitioned` events |
| **Temporal detection feels meaningful** | REQUIRES QUALITATIVE VALIDATION | From interview questions 4–7. |
| **Stories feel like real continuity** | REQUIRES QUALITATIVE VALIDATION | From interview + observer. |
| Temporal engagement occurs across ≥2 sessions | BETA SUCCESS CRITERION | Temporal detection in at least 2 distinct sessions for the same user. |

### Continuity

| Signal | Type | Definition |
|--------|------|------------|
| Active story context used in later conversations | DIAGNOSTIC | `active_story_context` in metadata |
| **Participant notices connections between conversations** | REQUIRES QUALITATIVE VALIDATION | From interview question 8 + observer. |
| **Connections are perceived as relevant** | REQUIRES QUALITATIVE VALIDATION | From observer + interview. |
| Continuity recognized across sessions | BETA SUCCESS CRITERION | Observational: participant references earlier ChronOS output in a later session. |

### Return Value

| Signal | Type | Definition |
|--------|------|------------|
| User returns voluntarily | DIAGNOSTIC | `user_returned` event OR interaction on a later day |
| Return context shown | DIAGNOSTIC | `return_context_shown` event |
| **Return context feels useful** | REQUIRES QUALITATIVE VALIDATION | From interview question. |
| **Return context feels intrusive** | REQUIRES QUALITATIVE VALIDATION | From interview + observer. |
| At least 30% of participants return voluntarily | BETA SUCCESS CRITERION | Exploratory floor for a small beta; not a growth mandate. |

### Trust

| Signal | Type | Definition |
|--------|------|------------|
| Memory deleted shortly after creation | DIAGNOSTIC | `memory_deleted` event within 24h of a memory creation |
| Story archived | DIAGNOSTIC | `story_archived` event |
| User edited stored data | DIAGNOSTIC | Data editor actions (goals, identity, preferences) |
| **User believes ChronOS is accurate** | REQUIRES QUALITATIVE VALIDATION | From interview questions 9–11. |
| **Personalization feels wrong** | REQUIRES QUALITATIVE VALIDATION | From observer + interview. |
| No fabricated or intrusive claim reported | BETA SUCCESS CRITERION | Zero qualitative reports of fabrication/intrusion by the end of the beta. |

### Voluntary Retention

| Signal | Type | Definition |
|--------|------|------------|
| Return without prompting | DIAGNOSTIC | `user_returned` event |
| Conversations spread across ≥2 days | DIAGNOSTIC | Interaction timestamps |
| **Would use again without being asked** | REQUIRES QUALITATIVE VALIDATION | From interview question 10. |
| At least 40% of participants return for a second session | BETA SUCCESS CRITERION | Exploratory floor; not a growth mandate. |

### Reliability

| Signal | Type | Definition |
|--------|------|------------|
| Request failure rate | DIAGNOSTIC | `conversation_failed` / total requests |
| Server errors | DIAGNOSTIC | 5xx in backend logs |
| **Failure rate ≤ 5%** | BETA SUCCESS CRITERION | Exploratory floor. Pauses beta above ~10%. |
| No data-loss incidents | BETA SUCCESS CRITERION | Zero complaints of lost content (qualitative or quantitative). |

### Data-Control Usage

| Signal | Type | Definition |
|--------|------|------------|
| Export used | DIAGNOSTIC | `data_exported` event |
| Delete used | DIAGNOSTIC | `memory_deleted` / account delete |
| Archive used | DIAGNOSTIC | `story_archived` / `story_restored` events |
| **Data-control was discoverable** | REQUIRES QUALITATIVE VALIDATION | Did participants find/use these features naturally? |
| Users understand deletion consequences | REQUIRES QUALITATIVE VALIDATION | From interview question 16. |

---

## How Not to Interpret

- These are diagnostic signals, not proof of product-market fit.
- Do NOT adjust product behavior because a metric is low in the early beta.
- No metric is a "target" — they are observational. We have no baseline.
- Any interpretation requires triangulation with qualitative feedback.
- A "fail" on a BETA SUCCESS CRITERION is a finding, not a bug. It tells us what to investigate — it does not by itself mean the product is broken.
