# ChronOS: Beta Evidence Log

Use this log to record observations from each participant session. **NEVER store raw personal conversation content.** Use participant beta IDs (non-personal), describe observed behavior in aggregate/general terms, and mark severity/confidence.

---

## How to Use

- Assign each participant a non-personal beta ID (e.g., `B001`, `B002`, …).
- NEVER write the participant's real name, email, or other PII in this log.
- Create one log entry per session/observation.
- For incidents, refer to the Bug Classification (P0–P3).
- Update the Product-Loop Validation section at the end of the beta.

---

## Participants

| Beta ID | Status | First Session Date | Notes (general only) |
|---------|--------|-------------------|----------------------|
| B001 | [active / completed / stopped] | YYYY-MM-DD | |
| B002 | | | |

---

## Evidence Entries

### Entry Template

```
## Entry N — <Beta ID> — <Session Type: First / Ongoing / Return / Debrief>

Date: YYYY-MM-DD
Scenario / Feature: <e.g., First conversation, Stories view, Return context>
Observed behavior: <describe what happened, no raw content>
Participant reaction: <set of descriptors: positive/neutral/negative/mixed, with quote if non-sensitive>
Issue / insight: <what it suggests about the product>
Severity: <P0 / P1 / P2 / P3 / N/A>
Confidence: <high / medium / low>
Follow-up: <none / investigate / change / interview again>
```

---

## Incident Log

| Date | Beta ID | Severity | Description (no raw content) | Status | Resolution |
|------|---------|----------|------------------------------|--------|------------|
| | | | | | |

---

## Data-Control Activity Log

| Date | Beta ID | Action | Why (if known) | Outcome |
|------|---------|--------|----------------|---------|
| | | [export / delete memory / delete all / archive / restore / edit goal / edit identity] | | |

---

## Qualitative Interview Log

See BETA_FEEDBACK_PROTOCOL.md for the question set.

| Date | Beta ID | Overall Sentiment | Key Positive | Key Negative | Surprise | Trust OK? | Will Return? |
|------|---------|-------------------|--------------|--------------|----------|-----------|--------------|
| | | | | | | | |

---

## Product-Loop Validation

Update this section as beta evidence accumulates. Mark each stage:

- ✅ CONFIRMED by beta evidence
- ⚠️ PARTIALLY supported / some contradicting evidence
- ❌ CONTRADICTED by beta evidence
- ❓ Requires more evidence

### Stage 1: First Use
- **What we believe from code/tests**: Onboarding → Dashboard → Conversation is smooth and self-explanatory.
- **Beta evidence confirms**: <fill in>
- **Beta evidence contradicts**: <fill in>
- **Remains unknown**: Whether the product is intuitively understood without explanation.

### Stage 2: First Value
- **What we believe**: The first meaningful response arrives promptly via deterministic or AI path.
- **Beta evidence confirms**: <fill in>
- **Beta evidence contradicts**: <fill in>
- **Remains unknown**: Whether the first value is actually valuable to the user.

### Stage 3: Accumulation
- **What we believe**: Memories and stories accumulate naturally through conversations.
- **Beta evidence confirms**: <fill in>
- **Beta evidence contradicts**: <fill in>
- **Remains unknown**: Whether accumulation leads to perceived value rather than perceived clutter.

### Stage 4: Continuity
- **What we believe**: Active story context helps conversation continuity.
- **Beta evidence confirms**: <fill in>
- **Beta evidence contradicts**: <fill in>
- **Remains unknown**: Whether the continuity is noticed / valued by real users.

### Stage 5: Reflection
- **What we believe**: Historical context (past-self moments, reflections) becomes more useful over time.
- **Beta evidence confirms**: <fill in>
- **Beta evidence contradicts**: <fill in>
- **Remains unknown**: Whether reflection actually improves the user's perspective.

### Stage 6: Return
- **What we believe**: Users have a reason to come back.
- **Beta evidence confirms**: <fill in>
- **Beta evidence contradicts**: <fill in>
- **Remains unknown**: Whether users return voluntarily.

### Stage 7: Resurfacing
- **What we believe**: Return context feels meaningful rather than arbitrary.
- **Beta evidence confirms**: <fill in>
- **Beta evidence contradicts**: <fill in>
- **Remains unknown**: Whether resurfacing is seen as helpful vs intrusive.

### Stage 8: Trust
- **What we believe**: The system is grounded and honest (no fabrication).
- **Beta evidence confirms**: <fill in>
- **Beta evidence contradicts**: <fill in>
- **Remains unknown**: Whether users trust the system enough to correct/delete/continue.

---

## Aggregate Telemetry Snapshot (for the end of the beta)

Take a `/metrics/beta-summary` snapshot at the end and record:

| Metric | Value |
|--------|-------|
| Total users created | |
| Total users onboarded | |
| Total users activated (≥1 conversation) | |
| Total users returned | |
| Total conversations processed | |
| Total conversations failed | |
| Request failure rate | |
| Temporal detection users | |
| Story created users | |
| Story progression events | |
| Return context shown | |
| Memories deleted | |
| Stories archived/restored | |
| Data exports | |

---

## Notes

- Store this log **outside** any shared/public repo if participants are real people.
- Do NOT commit this log to a public repository with any participant PII.
- Keep participant beta IDs only; never email/name.
- Update the Product-Loop Validation section weekly during the beta.