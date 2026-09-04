# ChronOS: Beta Incident Handling

Lightweight process for responding to issues reported during the controlled beta.

---

## Incident Categories and First Response

### 1. Authentication Failures

**Symptoms**: Participant cannot log in, is repeatedly logged out, sees 401/403.

**First response** (within 1 hour):
1. Ask participant: "What exactly did you see?" (error message, screen, behavior).
2. Check backend logs for their `user_id` in auth-related errors.
3. Try to reproduce with a test account.
4. If the issue is a missing/expired refresh token: guide them to log out and log back in.
5. If the issue is a backend bug: file P1 bug, disable the participant's broken token if needed, ask them to re-register if that resolves it.

**If issue is persistent**: escalate to a P1 bug; pause the participant (ask them to stop using until fixed).

---

### 2. Server Errors (5xx)

**Symptoms**: Participant sees "An internal error occurred" or the UI is stuck.

**First response** (within 1 hour):
1. Confirm via backend logs whether the error is per-user or system-wide.
2. If system-wide: **pause the beta immediately**. Inform all participants.
3. If per-user: investigate with their `user_id`. Determine if it's data-specific or reproducible.
4. File a bug (P0 if widespread, P1 if per-user).

**If issue is persistent**: ask participant to wait. Do NOT let them keep hitting the broken endpoint if it's generating data corruption.

---

### 3. Stuck UI / Loading State

**Symptoms**: UI shows spinner indefinitely; responses never appear; a tab is blank.

**First response** (within 2 hours):
1. Ask: "What were you doing before it got stuck?" (which screen, what message, etc.)
2. Ask them to refresh the page (full reload). Does the issue resolve?
3. Check backend logs: is the request hanging? Is there a timeout?
4. If it resolves after refresh: file P3 (transient UI issue). Ask them to report if it happens again.
5. If it does not resolve: file P2; ask them to stop using the affected feature; investigate with their account.

---

### 4. Incorrect Personalization

**Symptoms**: ChronOS says something factually wrong about the user (wrong name, wrong goal, wrong context).

**First response** (within 24 hours):
1. Do NOT assume the system is "wrong" — first confirm the participant did NOT provide that information earlier.
2. If the error is a misunderstanding: record it as a finding. May be a prompt or retrieval issue (P2).
3. If the error is fabricated: **immediately escalate to P0**. Fabricated personalization is a trust/security issue.
4. Direct the participant to correct/delete the information via Memory Graph.

**If the participant is upset**: acknowledge the error. Do not justify. Offer to delete the memory immediately.

---

### 5. Incorrect Temporal Continuity

**Symptoms**: ChronOS references a "story" that doesn't exist, connects unrelated things, or links to something the participant doesn't recognize.

**First response** (within 24 hours):
1. Confirm the story exists in the system (query `engine_temporal_threads` for their `user_id`).
2. Confirm the connections: are they based on actual memories? Or extrapolated?
3. If based on real memories but the participant disagrees: record as a finding (P2). The connection is technically correct but perceived as wrong.
4. If the connection is hallucinated or wrong: escalate to P1.
5. Direct the participant to archive the story if it's unwanted.

---

### 6. Deletion Problems

**Symptoms**: Participant tries to delete data but it fails or the data reappears.

**First response** (within 1 hour — deletion is a critical trust feature):
1. Ask exactly what they did (which delete action).
2. Check backend logs for DELETE failures (500 on delete endpoints).
3. If the delete failed (500): investigate immediately; this is a P1. The system made a promise ("you can delete this") and failed.
4. If data reappears after deletion: escalate to P0. This is a data integrity / privacy issue.
5. After fixing, manually verify deletion completed via MongoDB (delete_all_for_user).

---

### 7. Privacy / Security Reports

**Symptoms**: Participant believes their data was exposed, seen by unauthorized parties, or used inappropriately.

**First response** (within 1 hour):
1. Take it seriously. Do not dismiss.
2. Ask: "What makes you believe this?" (specifically what happened).
3. Check: did any operator look at their data? (if yes, was it authorized and documented?)
4. If exposure is confirmed: escalate to **P0**. Pause the beta. Begin incident response.
5. If exposure is NOT confirmed: acknowledge their concern. Explain what you know. Offer to delete their data immediately.
6. Log the incident in the Incident Log (BETA_EVIDENCE_LOG.md).

---

## Decision Framework: Pause / Resume / Stop

### When to PAUSE the beta

| Trigger | Action |
|---------|--------|
| P0 issue (security/privacy/data-loss) | Pause immediately. Inform all participants. |
| Widespread P1 issue (>50% of participants) | Pause after confirming scope. Inform participants. |
| Failure rate >10% across participants | Investigate before it gets worse; pause if cannot fix quickly. |
| Data corruption detected | Pause. Investigate. Restore from backup if available. |
| Participant reports data they should never have seen | Investigate; pause if it's a systemic bug. |

### When to STOP the beta (temporarily or permanently)

| Trigger | Action |
|---------|--------|
| Multiple P0 issues within a short period | Stop and do a full hardening pass before resuming. |
| Participant requests to withdraw | Respect immediately; delete their data. Do not pressure them to stay. |
| No participant has shown value after 2+ weeks | Pause and reassess whether the product hypothesis is viable. |
| Negative qualitative feedback is pervasive | Pause. Investigate. Determine if changes are needed before continuing. |

### When to RESUME after pause

1. Root cause is identified and fixed.
2. Full regression suite passes (no new regressions).
3. The affected participant(s) are informed of the fix.
4. The beta is resumed only if the operator is confident the issue will not recur.

---

## Bug Communication to Participants

### For P2/P3 bugs
"The team is aware of the issue. It should not affect your experience significantly. Thank you for reporting it."

### For P1 bugs
"We've found an issue that affects how [feature] works. We've stopped using [affected feature] while we fix it. We'll let you know when it's ready again."

### For P0 bugs
"The beta is paused. Your data is secure. We will notify you before the beta resumes. If you'd like us to delete your data now, just let us know."

Do NOT provide technical details about the bug to participants unless they specifically ask and the disclosure is safe.