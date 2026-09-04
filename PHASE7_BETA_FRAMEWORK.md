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
