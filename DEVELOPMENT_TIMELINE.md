# BETA_BUG_CLASSIFICATION.md

> **Source:** BETA_BUG_CLASSIFICATION.md

---

# ChronOS: Beta Bug Classification

Simple severity classification for issues found during the beta. Use this to prioritize and decide whether to pause/resume/stop.

---

## Severity Levels

### P0 — Security / Privacy / Data-Loss

**Definition**: An issue that directly compromises participant data, privacy, or system security.

**Examples**:
- Raw user content (messages, memories) exposed to a non-owner.
- Cross-user data leak (User A sees User B's data).
- Deletion fails permanently (data promises are broken).
- Fabrication that cannot be traced to any user input.
- Authentication bypass (unauthorized access to user data).
- Secret/credential leak into logs or user-facing output.
- Debug endpoints accessible in production environment.
- `delete_user_data` fails without raising an error (silent failure).

**Action required**: Pause beta immediately. Inform all participants. Fix before resuming. Document in Incident Log.

---

### P1 — Major Product Failure / Incorrect User Understanding

**Definition**: An issue that significantly breaks the core product experience or leads to a fundamentally incorrect user understanding.

**Examples**:
- Onboarding fails for a specific user and they cannot proceed.
- Conversation processing fails for all users (system-wide outage).
- A story is incorrectly linked to the wrong temporal thread (systematic retrieval error).
- The return context references something the user never discussed.
- Memory deletion returns 204 but data is not actually deleted.
- Frontend shows data from the wrong user account.
- Engine returns an error but the product still "works" (misleading success).

**Action required**: Fix before the affected participant(s) continue. File a bug. May require pausing affected feature only (not the whole beta).

---

### P2 — Significant Usability / Intelligence Issue

**Definition**: An issue that degrades the experience but does not break core functionality or privacy.

**Examples**:
- Slow response times (>3s) consistently for one user.
- Stories are created but feel irrelevant to the user.
- Temporal connections are technically correct but not perceived as useful.
- The "Why?" / explainability panel shows confusing information.
- A specific onboarding step is confusing but can be worked around.
- The Memory Graph does not render correctly on mobile.
- Return context appears but the user doesn't understand what it means.

**Action required**: Record and prioritize. May address during beta if the fix is safe and small. Do NOT pause the beta for P2 issues.

---

### P3 — Polish / Minor Issue

**Definition**: A cosmetic or minor issue that does not affect usability or correctness.

**Examples**:
- Inconsistent styling in a rarely-viewed panel.
- A tooltip has a typo.
- An icon appears slightly off on certain screen sizes.
- A loading skeleton appears briefly before data renders.
- A non-essential component has slightly unexpected padding.
- Minor ruff linter warnings.

**Action required**: Record and address after the beta, or in a future hardening pass. Never pause the beta for P3 issues.

---

## What Is NOT a Bug

The following are observations, not bugs. They are valid beta findings but should NOT be classified as P0–P3:

- **Subjective feedback** ("I don't like this design", "I would prefer darker colors").
- **Feature requests** ("It would be nice if…").
- **Preference differences** ("I don't like that it stores this").
- **Expected limitations** (ChronOS does not predict the future; it tracks and connects information).
- **Sparse data results** (A user who provides very little info will get very few memories/stories — this is correct behavior, not a bug).
- **Temporal connections the user disagrees with** (if technically grounded in their actual memories — this is a perception issue, not a product failure).

These findings should be logged in the Evidence Log as "observation" or "finding" with a clear distinction from bugs.

---

## Escalation Path

| Severity | Who decides | Who must know | Timeframe |
|----------|------------|---------------|-----------|
| P0 | Any operator observing the issue | All participants + creator | Immediate |
| P1 | Any operator | Creator + affected participants | Within 24 hours |
| P2 | Any operator | Creator (at next check-in) | Within 1 week |
| P3 | Any operator | Creator (next hardening pass) | No urgency |

---

## Bug Report Template

```
## Bug Report — <ID>

Date reported: YYYY-MM-DD
Reported by: [Beta ID or "operator observation"]
Severity: P0 / P1 / P2 / P3

Description: <what happened, without raw content>
Expected behavior: <what should have happened>
Actual behavior: <what did happen>
Reproduction: <steps to reproduce, if known>
Backend error (if any): <log excerpt, no secrets>
Resolution: <fix / workaround / no action>
Resolved on: YYYY-MM-DD
Participant informed: [yes / no]
```

# BETA_EVIDENCE_LOG.md

> **Source:** BETA_EVIDENCE_LOG.md

---

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

# BETA_FEEDBACK_PROTOCOL.md

> **Source:** BETA_FEEDBACK_PROTOCOL.md

---

# ChronOS: Feedback Protocol

## Purpose

Collect qualitative feedback from beta participants without biasing toward positive answers. The goal is to understand whether the core temporal-intelligence experience creates value — not to gather applause.

---

## Interview Structure

Conduct this as a **semi-structured conversation** at the end of the participant's involvement (after their return session, or when they stop).

- Keep it open-ended. Let them talk.
- Do NOT lead with "Wasn't it great?"
- Do NOT correct misconceptions during the interview unless the participant is confused in a way that blocks their feedback.
- Record the participant's exact words where possible (paraphrase only if necessary; never store raw personal content in the shared log).

---

## Question Set

### Opening (warm, non-leading)

1. "What do you think ChronOS is for?"
2. "What was your overall experience like?"

### Core Experience

3. "What was the most useful thing it did you."
4. "Was there anything it got wrong or misunderstood?"
5. "Did anything feel surprising?"
6. "Did remembering previous conversations feel useful?"
7. "Did anything feel intrusive?"
8. "Would you use this again without being asked?"

### Value / Retention

9. "What would make you come back?"
10. "What would make you stop using it?"
11. "Is there something you'd want ChronOS to do that it doesn't?"
12. "If you had to describe ChronOS to a friend, what would you say?"

### Trust / Data

13. "Did you ever feel like ChronOS 'knew' something it shouldn't?"
14. "Did you ever want to delete or fix something it remembered? Did you?"
15. "How did you feel about what it stores?"

### Closing

16. "Is there anything we haven't asked that you want to tell us?"
17. "Would you be willing to keep using it for another week?"

---

## Answer-Classification Guide

For each answer, classify:

| Classification | Meaning |
|---------------|---------|
| `positive` | Clear enthusiasm, e.g., "this is great, I could use this every day." |
| `neutral` | Texture but no strong valence, e.g., "it was okay." |
| `negative` | Clear frustration/disappointment, e.g., "it didn't do what I hoped." |
| `mixed` | Balanced pros/cons, e.g., "the memory is nice but the responses are generic." |
| `unclear` | Ambiguous, need follow-up. |

Never force a participant into a category. If they are unclear, probe one more time.

---

## Anti-Bias Rules

- Do NOT ask leading questions like "Wasn't it neat that it remembered your goal?"
- Do NOT offer your own interpretation of their experience first.
- Do NOT steer them toward "positive" outcomes during the interview.
- Do NOT tell them what you hope the answer will be.
- Do NOT reassure them their negative feedback is "fine" in a way that sounds dismissive.
- Do NOT turn the interview into a feature pitch. You are listening, not selling.

---

## When to Ask About Specific Mechanics

Only probe deeper on mechanics if the participant raises them first or if there is a specific confusing behavior you observed:

- "You looked confused when that story appeared. What were you thinking?"
- "You deleted a memory — why?"
- "You didn't use the Stories view much. Why not?"
- "You jumped out right after that response. What happened?"

---

## Debrief Output

After the interview, produce for the evidence log:

```
Participant Beta ID: ______
Interviewed on: ______
Overall sentiment: [positive | neutral | negative | mixed]

Q1 — "What do you think ChronOS is for?"
  Answer (verbatim or close paraphrase): ______
  Classification: ______

Q5 — "Did anything feel surprising?"
  Answer: ______
  Classification: ______

... (repeat as needed for salient answers)

Key insight (no raw content): ______
Follow-up needed: [none | will re-interview | needs technical debug]
```

# BETA_INCIDENT_RESPONSE.md

> **Source:** BETA_INCIDENT_RESPONSE.md

---

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

# BETA_OBSERVER_CHECKLIST.md

> **Source:** BETA_OBSERVER_CHECKLIST.md

---

# ChronOS: Beta Test Protocol

Phase 7 confirmed the product is beta-ready. This protocol defines what to test with real users and how to run the sessions.

---

## First Session

### Setup
1. Confirm the beta environment is operational (see BETA_OPERATOR_GUIDE.md §2).
2. Ensure the participant has the frontend URL and can access it.
3. Sit with them (or observe via a shared screen/log) during the first session.
4. Do NOT coach them through the product. Only help if the product is genuinely broken.

### Test Items

### Registration
- Does the registration flow succeed cleanly?
- Any friction / confusion / errors?
- Does the `account_created` event fire (operator can verify via `/metrics`)?

### Onboarding
- Does the participant complete onboarding from start to finish?
- Which steps caused hesitation or confusion?
- Does the `onboarding_completed` event fire with `chronos_initialised == true`?
- Does the Chronos initialization succeed (per the response message)?

### First Conversation
- Does the participant send a first message within ~1–2 minutes?
- What did they type?
- Does the first message trigger a `conversation_processed` event?
- Does the response arrive timely (< 3s)?

### First Meaningful Response
- Does the first response feel relevant to their input?
- Do they react positively / negatively / neutrally?
- Is any temporal detection reflected in the response (e.g., "this sounds evolving")?
- Does a story/memory get created from the first exchange?

### Comprehension
- After 5 minutes of use, ask: "What do you think ChronOS is for?"
- Write down their answer verbatim (this is the single most diagnostic data point).
- Ask: "What do you think ChronOS remembers about you?"
- Ask: "Where do you think your data goes?"

### Output
For each observation, record:
- **Observed behavior** (what they did)
- **Participant reaction** (what they said/felt)
- **Engine behavior** (what telemetry shows)
- **Issue / insight** (what it means)

Log to BETA_EVIDENCE_LOG.md.

---

## Ongoing Usage

### Instructions to participant
"Use ChronOS whenever you naturally would — if something comes to mind, share it. No need to force frequency. Some people find it interesting to tell ChronOS about something they're navigating — a goal, a decision, a recurring worry."

### Encouraged (but NOT required) scenarios
A participant may naturally cover:
- An **ongoing goal** (career, health, creative).
- A **developing situation** (a move, a new relationship, a project).
- A **decision** (job offer, relationship, purchase).
- A **recurring concern** (anxiety about work, a recurring habit).
- Something that **changes over time** (how they feel about X, how a situation evolves).

### How to encourage without scripting
- Mention one example only if the participant asks for direction.
- Do not prescribe exact prompts.
- Do not require any particular story counts.

### What to observe during ongoing use
- Does the participant continue conversations naturally?
- Do memories accumulate (check via `/chronos/state` on their account)?
- Do stories form / progress (check via `/chronos/engine/threads`)?
- Does the participant refer back to something ChronOS said earlier?
- Any frustration / delight / confusion?

---

## Return Session

### When
- Wait at least 2–3 days (ideally 5–7) after the participant's first session.
- Observe whether the participant returns **voluntarily**.
- If they do not, one gentle nudge is acceptable after 5+ days.

### What to observe
- Did the user return without prompting?
- Does return context appear (`return_context_shown` event; in-app ReturnHook)?
- Does the return context feel **useful** (does it reference something they actually care about)?
- Does it feel **intrusive** (does it feel like "the product is stalking me")?
- Does the participant **recognize** the continuity (do they say "oh, it remembered my goal")?

### Return-session conversation
- Ask: "Did you come back because I asked, or because you wanted to?"
- Ask: "When you saw the return message, did it feel relevant? Did it feel useful?"
- Ask: "Was there anything about it that felt off or intrusive?"

---

## Session Timing / Cadence

| Stage | Suggested | Minimum |
|-------|-----------|---------|
| First session | 15–30 min | 10 min (do not rush onboarding) |
| Follow-up | Within 2 days | — |
| Return session | 5–7 days after first | 2 days |
| Debrief interview | After return session, or when they stop | — |
| Total beta window | 1–3 weeks | — |

---

## What NOT to Do

- Do NOT script the participant's conversations. The goal is natural behavior.
- Do NOT reveal what ChronOS "should" do. Let them experience it.
- Do NOT interpret silence as failure. Sparse users are valid data.
- Do NOT coach them into categories. If they don't talk about goals, that's useful data.
- Do NOT measure against arbitrary growth targets.
- Do NOT promise features or changes based on beta feedback.
- Do NOT store raw conversation content in the evidence log (see BETA_EVIDENCE_LOG.md).

---

## Success / Failure Interpretation

### Interpretable from telemetry without qualitative input
- Did onboarding complete?
- Did a first meaningful conversation happen?
- Did temporal detection occur?
- Did stories form / progress?
- Did the user return?
- Did any memories get deleted / corrected?

### NOT interpretable from telemetry alone
- Was the experience *valuable*?
- Was the output *accurate*?
- Was it *intrusive*?
- Did it *improve* the participant's life?
- Would the participant *use it again*?

These require the qualitative interview.

---

## Post-Session Debrief

1. Thank the participant.
2. Conduct the lightweight interview (see BETA_FEEDBACK_PROTOCOL.md).
3. Log observations to BETA_EVIDENCE_LOG.md.
4. Only after debrief, optionally share the participant's telemetry summary (export) — only at their request.
5. Encourage the participant to use the data-control features (Data tab) if they want to edit/delete/export anything.</think>

<｜DSML｜tool_calls>
<｜DSML｜invoke name="write">
<｜DSML｜parameter name="content" string="true"># ChronOS: Beta Observer Checklist

Use this checklist during each participant session. Fill in observations for each item. Log to BETA_EVIDENCE_LOG.md after the session.

---

## Comprehension

- [ ] Did the participant understand what ChronOS is?
  - What did they think it was for? (write their words verbatim)
  - Did they need explanation? What exactly did they not understand?
  - Was the product self-explanatory, or did they need guidance?
- [ ] Did the participant understand what ChronOS remembers?
  - Did they correctly infer it stores their messages / extracts memories / detects stories?
  - Did they overestimate or underestimate ChronOS's capabilities?
  - Any surprise when they saw the Memory Graph or Stories view?

---

## First Value

- [ ] What was the FIRST moment the participant considered useful?
  - Quote it (without raw personal content — describe what happened).
  - Was it a temporal connection? A memory surfaced? A response they found insightful?
- [ ] Did temporal context materially improve the response?
  - Compare: would the response have been different without the temporal engine?
  - Did the participant notice the difference?
- [ ] Was there any moment where ChronOS's output felt generic or useless?

---

## Continuity

- [ ] Did the participant notice that ChronOS connected conversations?
  - Did they reference an earlier conversation naturally (e.g., "I mentioned this before —")?
  - Or did ChronOS surface a connection the participant was unaware of?
- [ ] Were story/context connections perceived as relevant?
  - Did the participant agree with the connections?
  - Any case where ChronOS connected things the participant thought were unrelated?
- [ ] Did the participant ever mention that ChronOS "forgot" something important?

---

## Trust

- [ ] Did any personalization feel wrong?
  - What was the trigger (a memory, a story, a reflection, an identity trait)?
  - Was the error diagnostic (participant could correct it) or confusing?
- [ ] Did the participant question where information came from?
  - Did they click "Why?" / "Explain"?
  - Did they understand the grounding?
- [ ] Did the participant attempt to correct or delete information?
  - Have they used the Memory Graph delete?
  - Have they visited the Data tab?
  - Have they edited identity, goals, or preferences?

---

## Return

- [ ] Did the participant come back without prompting?
- [ ] Did resurfaced context help?
  - Was the return message useful, weird, or both?
- [ ] Was anything surprising about the return experience?
- [ ] Was anything intrusive?

---

## Friction

- [ ] **Confusing UI**: any screen that did not make sense? What made it confusing?
- [ ] **Slow responses**: any response that took too long (>3s)? Which one?
- [ ] **Errors**: any error messages, 4xx/5xx, or stuck states? What happened?
- [ ] **Unclear terminology**: any Term (Story, Moments, Memory Graph, Past-Self) that confused them? What would they have called it?
- [ ] **Onboarding friction**: which step caused hesitation or getting stuck?
- [ ] **Unnecessary steps**: any step in a flow that felt like wasted effort?

---

## Data-Control Usage

- [ ] Did the participant export their data? Why?
- [ ] Did the participant delete any data? Why?
- [ ] Did the participant correct/edit stored data (goals, identity, preferences)? Why?
- [ ] Did the participant express any concern about what is stored?

---

## Signs That Need Qualitative Investigation (flag for follow-up)

- [ ] Memory deleted shortly after creation → why? Was it wrong? Embarrassing? Confusing?
- [ ] Repeated correction attempts → is the participant unable to edit effectively?
- [ ] Story archived immediately after creation → was it irrelevant/intrusive?
- [ ] Abandoning a conversation after a temporal response → did the response feel off?
- [ ] Negative feedback → was it a real issue, or a misunderstanding?

**Note**: These signals do NOT automatically mean the system is broken. They mean: investigate qualitatively.

---

## Per-Session Summary Section

Complete after each session:

```
Participant Beta ID: ______
Session: (First / Ongoing / Return / Debrief)
Date: ______
Session duration: ______ min

1. Comprehension?
   [ ] clear   [ ] partial   [ ] confused

2. First value?
   [ ] immediate   [ ] within 2 sessions   [ ] not seen

3. Continuity noticed?
   [ ] yes   [ ] no   [ ] unsure

4. Trust intact?
   [ ] yes   [ ] some concerns   [ ] broken

5. Returned voluntarily?
   [ ] yes   [ ] after nudge   [ ] no

6. Friction events?
   [ ] none   [ ] minor (list)   [ ] blocking (list)

7. Key positive observation: (describe, no raw content)
8. Key negative observation: (describe, no raw content)
9. Biggest open question about this participant:
```

# BETA_OPERATOR_GUIDE.md

> **Source:** BETA_OPERATOR_GUIDE.md

---

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

# BETA_PARTICIPANT_MODEL.md

> **Source:** BETA_PARTICIPANT_MODEL.md

---

# ChronOS: Beta Participant Model

## Overview

ChronOS is ready for a small controlled beta of **5–15 users**. This document defines who should participate, what characteristics are useful, how they should be onboarded, what not to promise, what data ChronOS stores, and available data-control features.

---

## Participant Selection

### Who Should Participate Initially

The initial beta should be a small, tightly-controlled group:

1. **People who are genuinely interested in the core hypothesis**: that ChronOS's temporal intelligence creates personal value by connecting conversations across time.
2. **People who are comfortable articulating what they experience** — both positive and negative — in plain language.
3. **People with a realistic relationship to the product**: early users, not "testing managers" or "UX reviewers." The beta validates whether the product creates value, not whether it passes a QA checklist.
4. **People who can reasonably use the product over at least 1–3 weeks** (multiple sessions, growing history).
5. **People who understand the privacy model**: ChronOS stores personal narrative content, and they must be comfortable with that.

### Useful Participant Characteristics

Recruit a spread across these dimensions (but do not over-engineer):

| Dimension | Useful Range |
|-----------|-------------|
| Relationship to creator | Mix of acquaintances and friends-of-friends. No close family. |
| Technical comfort | Mix of technical and non-technical users. Do not bias toward developers. |
| Self-expression habit | Mix of people who journal/reflect vs. those who rarely write about themselves. |
| Life situation | At least 2–3 people engaged in an ongoing situation (job change, goal, relationship, health, creative project). |
| Age/life stage | Spread across at least two life stages (e.g., 20s–30s and 40s+). |
| Communication style | Mix of detail-oriented and brief users. |
| Prior exposure | Ideally people who have NOT seen detailed product docs or phase reports. |

### Who Should NOT Participate Initially

- Close friends/family (they will tell you what you want to hear).
- People whose primary job is software QA/UX review.
- People who would likely treat this as "another chatbot."
- Participants who have reviewed the full architecture/phase documentation.
- More than ~2 people from a single social circle (to avoid echo effects).

---

## Onboarding Participants

### Step 1 — Invitation (controlled, low-friction)

Send a short, personal invitation. Include:

- What ChronOS is: "A personal intelligence system that tracks the temporal threads of your life — goals, decisions, recurring concerns — and connects them across conversations."
- What the beta involves: registering, onboarding (≈10 min), then using it naturally over days/weeks.
- The time commitment: "A few conversations over 1–3 weeks, plus a short interview at the end."
- What you will store: "Your conversations, the memories we extract, and detected temporal patterns. You can delete any or all of it."
- How to opt out or delete data at any time.

Do **not** send a long spec sheet. Keep the invitation under 300 words.

### Step 2 — Short intake (pre-brief)

Before their first session, optionally collect (or note) via a quick chat:

- What they currently use to track goals/life decisions (if anything).
- Their comfort level with personal narrative tools.
- Any privacy concerns up front.

This helps interpret their first-session behavior later.

### Step 3 — First session

- Direct them to the frontend URL.
- Ask them to register, complete onboarding, and send their first message.
- Observe silently during the first session (as the participant model allows).
- Do **not** coach them through the product. If they ask "what should I say?", give a generic prompt: "just talk about whatever is on your mind."

### Step 4 — Ongoing use

- After their first session, send a short follow-up: "Use ChronOS whenever you naturally would — if something comes to mind, share it. No need to force frequency."
- Optionally suggest (as one option among many, not a requirement): "Some people find it interesting to tell ChronOS about something they're navigating — a goal, a decision, a recurring worry."
- Do **not** script their conversations.

### Step 5 — Return session

- After at least 2–3 days have passed (ideally a week), observe whether they return voluntarily.
- If they don't return, one gentle nudge is acceptable: "The beta is still open if you'd like to continue."
- Do not repeatedly prompt.

### Step 6 — Debrief

- Conduct the lightweight interview (see Feedback Protocol).
- Log evidence (see BETA_EVIDENCE_LOG.md).
- Thank them. Consider offering deletion or export if they prefer.

---

## What Should NOT Be Promised to Participants

Do NOT promise:

- That ChronOS "understands you" — it tracks and connects information; it does not comprehend.
- That ChronOS will always be "right" about your situation.
- That it will remember everything — memory extraction is selective and may miss things.
- That responses will always be "smart" or "insightful."
- That early-stage beta bugs won't happen.
- That their data will never be seen by an operator — it is private by default but operators may need to debug at a raw level in rare, authorized cases.
- That features they see will remain unchanged.
- That their design/branding feedback will be implemented.

Do promise:

- Their data stays theirs; they can delete or export any or all of it at any time.
- The beta is about evaluating the core experience, not "performing" for the creator.
- They are free to stop at any time.

---

## What ChronOS Stores

ChronOS stores the following for each user:

### Conversations / Inputs
- The raw text (and media) of each user message sent via `process` endpoint.
- The ChronOS response text.
- Interaction records (matched inputs/outputs, timestamps, provider/model names).

### Extracted Memories
- Memory items (content, memory type, importance score, tags, media URLs).
- Genesis memory (from onboarding step 6).

### Temporal Stories (TemporalThreads)
- Detected stories / moments: subject, description, temporal type, status, timestamps.
- Temporal events (individual moments attached to stories).

### Identity / Profile
- Identity snapshots (versioned traits, skills, etc.).
- Goals, patterns, timeline events.
- Analysis preferences.

### Onboarding
- Onboarding session state and step responses.

### Telemetry (metadata only)
- Product events: conversation_processed (booleans/counts only), memory_deleted, story_archived, etc.
- Never contains conversation content, prompts, AI responses, reasoning, or embeddings.

### Media
- Uploaded audio/video recordings stored under `uploads/{user_id}/`.

---

## Data Control / Deletion Features for Participants

Participants can use the following existing features (no new UI needed):

### By clicking / navigating (UI)
| Action | Where |
|--------|-------|
| Export all data (JSON download) | `/me` → Data/Overview → "Export all my data" |
| Delete all ChronOS data | `/me` → Data/Overview → "Delete all my ChronOS data" (2-step confirm) |
| Delete a single memory | `/chronos` → Memory Graph → per-memory "Delete" |
| Archive / restore a story | `/chronos` → Story detail → "Archive" / "Restore" |

### Data editing (correct, not just delete)
- **Goals**: view/edit/delete in Data/Overview → Goals tab.
- **Preferences**: view/edit in Data/Overview → Preferences tab.
- **Genesis memory**: view/edit in Data/Overview → Genesis tab.
- **Identity traits**: view/edit in Data/Overview → Identity tab.

### Behavior guarantees
- Deleting a memory removes it and purges references (timeline, reflections, patterns, threads).
- Deleting all data permanently removes engine + onboarding + temporal + telemetry data.
- Export never includes embeddings or provider secrets.

---

## Participant Consent / Info at a Glance

Provide each participant a short plain-language note (email or inline):

> ChronOS stores what you tell it: your messages, the memories it extracts, and the patterns it detects in your stories. It stores this per-account and privately. You can export or delete any or all of it at any time from your Data page. During the beta, an operator can access aggregate health metrics and may, with your authorization and only in rare debugging cases, look at your raw data. The beta's goal is to understand whether ChronOS helps — not to collect data for its own sake.

---

## Non-goals for Participant Selection

- Do not pitch "AI that understands you at a deep level."
- Do not promise to build their preferred new feature.
- Do not give them the Phase 1–7 reports or architecture docs.
- Do not imply a large analytics back-end exists.

# BETA_TEST_PROTOCOL.md

> **Source:** BETA_TEST_PROTOCOL.md

---

# ChronOS: Beta Test Protocol

Phase 7 confirmed the product is beta-ready. This protocol defines what to test with real users and how to run the sessions.

---

## First Session

### Setup
1. Confirm the beta environment is operational (see BETA_OPERATOR_GUIDE.md §2).
2. Ensure the participant has the frontend URL and can access it.
3. Sit with them (or observe via a shared screen/log) during the first session.
4. Do NOT coach them through the product. Only help if the product is genuinely broken.

### Test Items

### Registration
- Does the registration flow succeed cleanly?
- Any friction / confusion / errors?
- Does the `account_created` event fire (operator can verify via `/metrics`)?

### Onboarding
- Does the participant complete onboarding from start to finish?
- Which steps caused hesitation or confusion?
- Does the `onboarding_completed` event fire with `chronos_initialised == true`?
- Does the Chronos initialization succeed (per the response message)?

### First Conversation
- Does the participant send a first message within ~1–2 minutes?
- What did they type?
- Does the first message trigger a `conversation_processed` event?
- Does the response arrive timely (< 3s)?

### First Meaningful Response
- Does the first response feel relevant to their input?
- Do they react positively / negatively / neutrally?
- Is any temporal detection reflected in the response (e.g., "this sounds evolving")?
- Does a story/memory get created from the first exchange?

### Comprehension
- After 5 minutes of use, ask: "What do you think ChronOS is for?"
- Write down their answer verbatim (this is the single most diagnostic data point).
- Ask: "What do you think ChronOS remembers about you?"
- Ask: "Where do you think your data goes?"

### Output
For each observation, record:
- **Observed behavior** (what they did)
- **Participant reaction** (what they said/felt)
- **Engine behavior** (what telemetry shows)
- **Issue / insight** (what it means)

Log to BETA_EVIDENCE_LOG.md.

---

## Ongoing Usage

### Instructions to participant
"Use ChronOS whenever you naturally would — if something comes to mind, share it. No need to force frequency. Some people find it interesting to tell ChronOS about something they're navigating — a goal, a decision, a recurring worry."

### Encouraged (but NOT required) scenarios
A participant may naturally cover:
- An **ongoing goal** (career, health, creative).
- A **developing situation** (a move, a new relationship, a project).
- A **decision** (job offer, relationship, purchase).
- A **recurring concern** (anxiety about work, a recurring habit).
- Something that **changes over time** (how they feel about X, how a situation evolves).

### How to encourage without scripting
- Mention one example only if the participant asks for direction.
- Do not prescribe exact prompts.
- Do not require any particular story counts.

### What to observe during ongoing use
- Does the participant continue conversations naturally?
- Do memories accumulate (check via `/chronos/state` on their account)?
- Do stories form / progress (check via `/chronos/engine/threads`)?
- Does the participant refer back to something ChronOS said earlier?
- Any frustration / delight / confusion?

---

## Return Session

### When
- Wait at least 2–3 days (ideally 5–7) after the participant's first session.
- Observe whether the participant returns **voluntarily**.
- If they do not, one gentle nudge is acceptable after 5+ days.

### What to observe
- Did the user return without prompting?
- Does return context appear (`return_context_shown` event; in-app ReturnHook)?
- Does the return context feel **useful** (does it reference something they actually care about)?
- Does it feel **intrusive** (does it feel like "the product is stalking me")?
- Does the participant **recognize** the continuity (do they say "oh, it remembered my goal")?

### Return-session conversation
- Ask: "Did you come back because I asked, or because you wanted to?"
- Ask: "When you saw the return message, did it feel relevant? Did it feel useful?"
- Ask: "Was there anything about it that felt off or intrusive?"

---

## Session Timing / Cadence

| Stage | Suggested | Minimum |
|-------|-----------|---------|
| First session | 15–30 min | 10 min (do not rush onboarding) |
| Follow-up | Within 2 days | — |
| Return session | 5–7 days after first | 2 days |
| Debrief interview | After return session, or when they stop | — |
| Total beta window | 1–3 weeks | — |

---

## What NOT to Do

- Do NOT script the participant's conversations. The goal is natural behavior.
- Do NOT reveal what ChronOS "should" do. Let them experience it.
- Do NOT interpret silence as failure. Sparse users are valid data.
- Do NOT coach them into categories. If they don't talk about goals, that's useful data.
- Do NOT measure against arbitrary growth targets.
- Do NOT promise features or changes based on beta feedback.
- Do NOT store raw conversation content in the evidence log (see BETA_EVIDENCE_LOG.md).

---

## Success / Failure Interpretation

### Interpretable from telemetry without qualitative input
- Did onboarding complete?
- Did a first meaningful conversation happen?
- Did temporal detection occur?
- Did stories form / progress?
- Did the user return?
- Did any memories get deleted / corrected?

### NOT interpretable from telemetry alone
- Was the experience *valuable*?
- Was the output *accurate*?
- Was it *intrusive*?
- Did it *improve* the participant's life?
- Would the participant *use it again*?

These require the qualitative interview.

---

## Post-Session Debrief

1. Thank the participant.
2. Conduct the lightweight interview (see BETA_FEEDBACK_PROTOCOL.md).
3. Log observations to BETA_EVIDENCE_LOG.md.
4. Only after debrief, optionally share the participant's telemetry summary (export) — only at their request.
5. Encourage the participant to use the data-control features (Data tab) if they want to edit/delete/export anything.


# ChronOSPhase5E-A_Audit.md

> **Source:** ChronOSPhase5E-A_Audit.md

---

# CHRONOS — PHASE 5E-A — FINAL PRODUCT AUDIT

**Status:** AUDIT ONLY — no product code modified.
**Verification baseline:** backend `645 passed, 4 skipped`; `npx tsc --noEmit` clean (full `next build` green at end of Phase 5D; no frontend changes since).

---

## 1. Executive assessment

ChronOS is **structurally complete and production-plausible, but not yet polished**. It does the hard part correctly — a real, deterministically-grounded temporal system (Stories/threads, Timeline, Past-Self, return loop, first-use, data control, auth) — and the backend is genuinely trustworthy. What remains is not "missing features"; it is **presentation and trust UX**. Specifically:

1. **Three surfaces still read as an AI developer console, not a personal system** — Insights (Reflections/Patterns), the Identity model card, and the Memories tab all expose raw confidence percentages, internal version numbers, category/enum identifiers, reasoning traces, and memory-connection counts. This is the single largest gap against the product principle.
2. **The explainability modal leaks internal identifiers and the full prompt payload** into the only surface a normal user might open to build trust — actively undermining trust.
3. **The conversation is buried under cards and chrome on Home**, and (Stories) is a strong narrative marred by low-level vocabulary ("event_count", "events", "confidence", internal type labels).
4. **Accessibility has a few genuine HIGH defects** (stop-recording button, modal focus trap/dialog semantics) and broad MED gaps (no `aria-live`, missing labels).
5. **One real performance defect**: the Stories tab does an N+1 fetch of every thread's events.

The core product idea — a personal, connecting, reflecting memory — is well-implemented at the data layer and only inconsistently expressed at the UI layer. It is closer to finished than a "gap" audit would suggest; the work is concentrated and finishable.

---

## 2. Current product map

- **Landing (`/`)** — polished marketing page: hero, features, how-it-works, CTA, footer. Strong and cohesive.
- **Auth (`/register`, `/login`)** — clean forms with proper labels, registration routes to onboarding.
- **Onboarding (`/onboarding`)** — 7-step guided intake (about-you, life-now, on-mind, goals, changes, first-memory, prefs) with autosave, skip, resumable session, recovery banner if abandoned. Well built; long but structured.
- **Home (`/dashboard` overview)** — the conversation surface: hero/greeting, stats bar, active-story banner, past-first-story card, ReturnHook, VoiceVideoRecorder, ChronosEngineFeed (conversation + Past-Self cards), IdentityModelCard, reflection preview. **The most important and most over-decorated surface.**
- **Stories (`/dashboard` stories)** — `JourneyView` (list of narrative story cards) → `TemporalThreadDetailView` (timeline of moments, Continue-this-story). Strong narrative potential; weak vocabulary.
- **Timeline (`/dashboard` timeline)** — `TimelineEngineView`: reverse-chronological life events with sentiment icons. Separated from Stories; no links to conversations/stories.
- **Insights (`/dashboard` insights)** — `ReflectionEngineView` + `PatternDetectionView`. Very analytic presentation.
- **Memories (`/dashboard` memories)** — `MemoryGraphView`: searchable list of everything shared. View/search only — **no manage/delete**.
- **Me (`/me`)** — Profile (name/email/**raw user ID**/mood customization) + **Data** (`MyDataExplorer`: onboarding data + export/delete DataControls).
- **Data Controls** — export JSON + confirm-to-delete-all. Functionally solid.

---

## 3. What is already excellent (do not casually change)

- **Backend trust & data control (5B):** auth-scoped endpoints, export without embeddings, delete clears all temporal + ledger data. Genuinely done.
- **First-use experience (5C):** `FirstUseWelcome`, goal-grounded starter prompts, first-story acknowledgement, recovery banner, `isFirstUse` derived from real state. Tone is right.
- **Return loop (5D):** `ReturnHook` is correctly subordinate, suppresses duplicates via ledger, never fabricated, renders nothing when nothing changed. This is a model implementation of a non-engagement return system.
- **Story narrative model** (JourneyView cards: "Where it started" → moments → "Current", with honest single-event and empty states) is emotionally appropriate and the best-designed surface.
- **Landing page, onboarding structure, Past-Self card** copy ("Something from your past") — appropriate, grounded, non-creepy, non-intrusive.
- **Lazy tab loading** and initial-load batching are well done.
- **Mood customization** — a genuine product personality feature, coherent and contained.

---

## 4. Critical remaining problems (P0 / P1)

**P0 — None blocking trust/correctness/security in a crash sense.** Backend, auth, and deletion are sound.

**P1-1. Explainability modal leaks internals.** `ChronosEngineFeed.tsx` modal shows raw `supporting_memory_ids` (e.g. `mem_xxx`) and the **full `user_prompt` payload** (`ExplainabilityModal`, ~lines 293–318). This is the only "trust" surface and it actively erodes trust by showing implementation internals. Should become layered: simple answer → understandable why → (authorized) technical. *(Workstream E.)*

**P1-2. Analytic-dashboard language on public surfaces.** `IdentityModelCard` shows "Version N, updated date" + percentage bars for "Emotional posture"; `ReflectionEngineView` shows "confidence X%", raw `insight_type`, reasoning traces; `PatternDetectionView` shows "X% confidence" and internal category names (`behavior_loop`, `productivity_trend`); `MemoryGraphView` shows "Importance N%", "N connected", input-type chips. Together these contradict "a personal system, not an analytics dashboard." *(Workstream D.)*

**P1-3. Conversation is secondary on Home.** Before the recorder+feed there are: hero + stats bar card, active-story banner, first-story card, ReturnHook, then a full "Share a moment" Card with internal header. The conversation (the actual product) appears only after ~5 stacked cards. The layout is a dashboard *containing* a conversation rather than a conversation. *(Workstream A.)*

**P1-4. No per-item memory management.** The Memories tab is view/search only. A user who sees an incorrect/unwanted memory cannot delete or edit it in place (deletion is only "delete everything" in Me→Data). This violates the core trust requirement "I can see and control the context." *(Workstream C — memory/timeline usability.)*

**P1-5. Accessibility: modal + stop button.** `ChronosEngineFeed` modal has no `role="dialog"`, `aria-modal`, focus trap, focus restore, or Escape-close (HIGH composite); `VoiceVideoRecorder` in-recording stop button is icon-only with no accessible name (HIGH). *(Workstream F.)*

**P1-6. Performance: N+1 on Stories.** `/threads` returns only `event_count`; `JourneyView` then calls `/threads/{id}` per thread (N+1). On a user with many stories this is slow and chatty. *(Workstream C / G.)*

---

## 5. UX findings (P1 / P2)

- **P1 — Journey/Stories identity conflict.** Tab is "Stories", component heading is "Your Journey"; "Journey" and "Stories" are used interchangeably. This remains unresolved; pick one model ("Your Stories") everywhere.
- **P2 — Story vocabulary is database-y.** `JourneyThreadCard` shows "N events" / "N event"; `TemporalThreadDetailView` shows "N events", "Started {date}", lifecycle statuses ("Open"/"Resolved"/"Archived"), and per-event `TYPE_LABELS` (Decision/Goal/Life Event…) applied as badges. Users should see "moments" and narrative lifecycle, not schema enums. IDs/confidence are already hidden on Journey (good) but `confidence`/`origin_memory_id` still come over the API.
- **P2 — Detail view shows raw lifecycle badges.** "Open"/"ACTIVE" status chips read as internal status; recommend narrative phrasing (e.g., "Still unfolding"/"Resolved").
- **P2 — IdentityModelCard "Version" and Refresh.** Version + auto-refresh button are admin controls; the "Refresh" button re-runs identity analysis. Either hide version or reframe as non-technical.
- **P2 — Return hook is visually near-identical to the other Home cards** — fine functionally, but it competes with the active-story/first-story banners; with 3 similar cards stacking it's visually noisy. Ensure only one such card is prominent at a time.
- **P2 — Timeline is a passive list** disconnected from Stories/conversations. It does not lead anywhere (no click-through). Not redundant, but "useful but poorly tied-in."
- **P2 — No way to remove/archive a Story** from the view (lifecycle statuses exist but are not user-controllable). A resolved story the user disagrees with cannot be corrected.
- **P2 — Conversation has no load-more.** `getInteractions(20)` fixed; long history truncated with no pagination or "show earlier" — past conversations silently vanish.
- **P3 — Duplicate "welcome" content:** hero "Welcome back, X" and ReturnHook header "Welcome back, X" both render on return when a hook is present — mild redundancy.

---

## 6. Mobile findings (prioritized)

- **MED** — `TemporalThreadDetailView` back button is 32px icon-only.
- **MED** — `StepAboutYou` and several onboarding + my-data `grid-cols-2` forms stay 2-up on narrow phones (cramped inputs).
- **MED** — Journey story-card `line-clamp-2` clips origin/current text with no reveal.
- **LOW** — Small hit targets: clear-story/dismiss (`p-1` ×16px icon), discard-recording X, tab bars at ~32px.
- **LOW** — Audio preview row squeezes native `<audio>` in the `[Mic][controls][X]` row on 375px.
- Dashboard 2-col layout correctly stacks; record buttons are 80px (fine). Overall mobile is *decent*, not broken.

---

## 7. Accessibility findings (prioritized)

- **HIGH** — Explainability modal: no dialog role/trap/restore/Escape (see P1-5).
- **HIGH** — Recorder stop button no accessible name (see P1-5).
- **MED** — Many `×`/`+` icon-only remove/add buttons across `GenesisAndIdentity`, `PreferencesSection`, `StepAnalysisPrefs` lack names.
- **MED** — Warm error/status/thinking states have no `aria-live`/`role="alert"` (recorder, feed ThinkingBubble, login/register/onboarding, DataControls, MyDataExplorer).
- **MED** — Many placeholder-only inputs lack labels (recorder textarea/note/file, memory search, onboarding fields).
- **MED** — `dashboard/page.tsx` — a `<button>` nested inside a `<Link>` (invalid nested-interactive).
- **MED** — Eye "View reasoning trace" uses only `title`, not an accessible name.
- **LOW** — Several 1–2-up grids don't collapse; focus-visible ring missing on a couple of raw buttons; color+shape sentiment icons (Timeline) lack sr-only text.

---

## 8. Trust / privacy UX findings (prioritized)

- **P1** — Explainability leaks internals (P1-1) — the opposite of trust.
- **P1** — No per-memory edit/delete (P1-4) — core control gap.
- **P2** — `Me`/profile exposes raw **User ID** in `font-mono` (`me/page.tsx`) — internal metadata on a user surface; should be removed or hidden.
- **P2** — "Importance N%"/"confidence" on Memories/Insights imply a secret scoring model; reframe as neutral context ("Added {date}") rather than confidence scores.
- **P3** — Export is a raw JSON dump (acceptable, but an optional human-readable summary would reassure).

---

## 9. Performance findings

- **P1** — **Stories N+1**: each story triggers a separate `/threads/{id}` fetch on the Stories tab (JourneyView enrichment loop). For many stories this is the dominant cost. Fix at API level (include events in `/threads`) or client batching.
- **P2** — `/threads/{id}` returns full events with every `origin_memory_id`/`related_memory_ids`/`confidence` even though the UI shows little of it (wasted payload + leak risk).
- **P3** — `getInteractions(20)` with no pagination (see conversation truncation).
- Initial-load batching and lazy tabs are otherwise good; no duplicate-request bug found beyond the N+1.

---

## 10. Product coherence assessment (Day 1 → Day 30)

- **Day 1 — Why use this?** Yes: clear CTA "Begin your timeline", first-use welcome, goal-grounded prompts, honest "Story and past-self woven from what you share." Good.
- **Day 3 — What has it learned?** The Identity card and Memories show "something" but framed as scores/confidence, which reads as vague or analytical rather than "it remembers me."
- **Day 7 — What became more useful?** Stories begin appearing as narrative cards — genuinely valuable and coherent.
- **Day 14 — Meaningful stories/changes?** Yes if the user shared across time; return hook + Stories carry this.
- **Day 30 — Feels like it remembers me?** Partially — the return hook and stories do, but the Memories/Insights trust surfaces undercut it with scoring language.
- **If it gets something wrong** — Can the user correct it? **No** for ChronOS memories/stories (only delete-all). ← biggest coherence gap.
- **Understand why something appeared?** The explainability modal exists but shows raw internals (feeble trust).
- **Leave / delete data?** Yes — solid (export + delete-all).

Verdict: Day 1/7/14 are strong; Day 3, Day 30, and "correct it"/"understand why" are the weak points — all trust-surfacing gaps.

---

## 11. Things we should NOT change

- The backend return loop, ledger suppression, first-use and data-deletion logic (correct and well-tested).
- The Landing page, onboarding flow, `FirstUseWelcome`, `PastSelfMomentCard`, and ReturnHook behavioral design.
- The JourneyView story-card narrative structure (origin → moments → current).
- The mood system, lazy tab loading, aborted-request guards.
- Overall information architecture (5 tabs + Me) — do NOT add tabs.

---

## 12. Things we should NOT build

- Notifications, streaks, gamification, social/sharing, collaboration, native app, external integrations, vector search, new temporal intelligence, subscription infrastructure, autonomous agents, complex analytics. None is required by the current product.

---

## 13. Proposed Phase 5E implementation scope (smallest realistic set)

Group into 6 workstreams (others are deferred/declared out-of-scope).

### A. Conversation polish — "it's a conversation, not a console."
- **Goal:** make Home read as a conversation first.
- **Exact scope:** reduce pre-conversation chrome — consolidate hero + stats + banners; let the recorder/feed be the visual center; soften the recorder header; remove nested-button-in-Link.
- **Files:** `dashboard/page.tsx`, `VoiceVideoRecorder.tsx`.
- **Non-goals:** no redesign of media capture, no new components.
- **Acceptance:** above-the-fold on Home is conversation (recorder + one welcome/story context), not a stack of cards; no nested interactive elements.

### C. Story/Timeline vocabulary + memory manage (trust/coherence) — the highest-value workstream.
- **Goal:** Stories feel like narratives; Memories/Stories are user-correctable.
- **Exact scope:**
  1. Rename "Journey"→"Stories" consistently; hide lifecycle/enum badges or rephrase narratively; replace "N events" with "N moments".
  2. Add per-memory and per-story manage actions (delete memory; resolve/remove story) surfaced in the Memories/Story UI, wired to backend endpoints.
  3. Fix `/threads` to include events (kill N+1) as part of the same API touch.
- **Files:** `JourneyView.tsx`, `TemporalThreadDetailView.tsx`, `MemoryGraphView.tsx`, `chronosConstants.ts`, `router.py`, `tests/*`.
- **Non-goals:** no new intelligence; no merging Timeline into Stories.
- **Acceptance:** no internal IDs/confidence/enum labels in user faces; a user can delete a memory and resolve/archive a story; Stories tab issues a single list request (no N+1).

### D. Trust re-labeling of Insights & Identity.
- **Goal:** remove "analytics dashboard" language.
- **Exact scope:** reframe confidence scores/version/raw categories as plain-language ("added {date}", past-vs-present narrative), remove user ID from Profile.
- **Files:** `ReflectionEngineView.tsx`, `PatternDetectionView.tsx`, `IdentityModelCard.tsx`, `me/page.tsx`.
- **Acceptance:** no "confidence %", "Version", or internal enum strings visible to normal users; raw IDs removed from Profile.

### E. Explainability rework (layered).
- **Goal:** trust through understanding without internals.
- **Exact scope:** modal shows (1) plain-language answer, (2) grounded "why" (referenced memory *content*, not IDs), (3) technical detail behind a labeled toggle only for authorized/debug; hide prompt payload by default; add dialog semantics (role/focus/Escape).
- **Files:** `ChronosEngineFeed.tsx`; backend only if needed to provide content-based references.
- **Acceptance:** no raw IDs or full prompt visible at default; modal is accessible (dialog role, focus trap, Escape).

### F. Accessibility pass (targeted).
- **Exact scope:** recorder stop-button name; modal a11y (bundled in E); `aria-live`/`role="alert"` on error & thinking states; missing labels; icon-only button names; touch targets; fix `button`-in-`Link`.
- **Files:** across `ChronosEngineFeed`, `VoiceVideoRecorder`, my-data and onboarding components.
- **Acceptance:** axe/vo sweep on Home + data surfaces returns no HIGH/automated errors.

### G. Performance quick-win (N+1).
- Folded into C3; otherwise no separate workstream.

---

## 14. Definition of "DONE"

- **Product/Coherence:** the app reads as a personal system; no "console" language (confidence/version/enum/IDs) on any normal surface.
- **Conversation:** the conversation is the Home center.
- **Stories:** "Stories" naming coherent, narrative vocabulary, user can resolve/archive.
- **Memories:** user can view/search **and delete** a memory; no scoring language.
- **Timeline:** events presented clearly (no newly introduced internals); at least a story-moment distinction is preserved.
- **Insights:** plain-language, non-confident tone.
- **Return loop:** unchanged behavior, still suppress-after-surfaced.
- **Trust:** modal is layered + accessible; raw user ID removed from Profile; per-item control present.
- **Mobile:** no horizontal overflow; ≥44px key targets on the 3 main flows.
- **Accessibility:** dialog semantics, `aria-live` on errors+thinking, all icon controls named (automated scan clean).
- **Performance:** Stories tab issues one list request (N+1 eliminated).
- **Reliability:** `pytest` green; `tsc` clean; `next build` success.

---

## 15. Final recommendation

> **START NEXT: Phase 5E — Workstream C (Story/Timeline vocabulary + Memory management + N+1 fix), followed immediately by A (conversation polish).**

Rationale: Workstream C is first because it simultaneously (a) makes the product feel like narrative rather than a database (coherence), (b) delivers the *single most-missing trust feature* — per-item memory/story control — which the "correct it" test hinges on, and (c) fixes the real N+1 performance defect in the same API touch. It touches the surfaces a returning user sees most after the conversation itself, and it's a contained, testable change. Workstream A is second because it makes the core conversation feel like the product — the visible first impression on every visit.

**STOP.** Phase 5E-A is complete; no code was modified. Do not begin implementation without explicit go-ahead.


# PHASE7_BETA_FRAMEWORK.md

> **Source:** PHASE7_BETA_FRAMEWORK.md

---

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


# PHASE_4L_REPORT.md

> **Source:** PHASE_4L_REPORT.md

---

# Phase 4L: Performance, Contract Cleanup & FAST Path Audit

**Date:** 2026-08-26
**Phase:** 4L (Phase 4K follow-up)
**Goal:** Resolve remaining inconsistencies found during Phase 4K release readiness audit — redundant loading, stale requests, FAST path cleanup

---

## Summary

Phase 4L addressed the three core inconsistencies identified during the Phase 4K audit. All fixes were surgical and no new features were introduced.

### Changes Made

#### 1. Dashboard Initial Load Optimization (`page.tsx`)
- **Before:** `loadAllData()` fetched all 7 API collections (identity, memories, timeline, reflections, patterns, threads, interactions) on mount
- **After:** `loadAllData()` fetches only identity + interactions + threads + memories + reflections (5 collections)
- **Rationale:** Timeline and patterns are only rendered in their respective tabs (Timeline, Insights). Threads and memories are needed on Home because the stats bar shows Stories/Memories counts
- **Impact:** 2 fewer API calls on initial page load. Lazy tab loading now also covers threads (Stories tab)

#### 2. Request Cancellation / Stale Request Protection (`page.tsx` + `chronosApi.ts`)
- **`chronosApi.ts`:** All 7 GET methods now accept an optional `signal?: AbortSignal` parameter
- **`page.tsx`:**
  - Initial `loadAllData()` call wrapped in an `AbortController`; aborted on unmount
  - All refresh functions catch and ignore `AbortError` to prevent stale state updates
  - `isInitialLoad` only cleared when request is not aborted
- **Impact:** Component unmounts no longer trigger state updates on unmounted components

#### 3. FAST Path LLM Call Removal (`engine.py`)
- **Before:** On FAST path, the engine called `orchestrator.orchestrate_prompt()` + `llm_provider.generate_response()` + `validator.validate_response()` — the LLM call was a real network call to Ollama that produced output which was then discarded
- **After:** Only `orchestrator.orchestrate_prompt()` is called (pure template assembly, no network). `raw_llm_response` is set to `""`. `ValidationResult` is constructed deterministically with `personalization_score=0.96` (matching the validator's hardcoded value). `provider_name` is set to `"deterministic"` and `target_model` to `"chronos-v1-core"`
- **Rationale:** The orchestrator is kept because its output (`PromptContext`) feeds the explainability trace. The LLM call and validator were pure overhead on the FAST path — their outputs were never used for `final_response`
- **Impact:** Eliminates one unnecessary Ollama network round-trip per FAST-path request. Reduces FAST-path latency

#### 4. Test Fix (`test_chronos_engine.py`)
- Updated provider swap assertion to accept `"deterministic"` as valid `provider_name` on FAST path (line 71)
- **608 pass, 0 fail, 4 skip**

---

## Verification Results

| Check | Result |
|-------|--------|
| TypeScript (`npx tsc --noEmit`) | ✅ Clean |
| Python tests (`pytest tests/ -q`) | ✅ 608 pass, 0 fail, 4 skip |
| Python lint (`ruff check`) | ✅ No new errors (102 pre-existing) |
| Frontend build (`npx next build`) | ✅ Clean |

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/app/dashboard/page.tsx` | Trimmed `loadAllData()` from 7→5 collections; added AbortController; added lazy loading for Stories tab; added AbortError guards to all refresh functions |
| `frontend/src/lib/chronosApi.ts` | Added optional `signal?: AbortSignal` to all 7 GET methods |
| `backend/src/chronos_engine/engine.py` | Removed `llm_provider.generate_response()` + `validator.validate_response()` on FAST path; replaced with deterministic stubs |
| `backend/tests/test_chronos_engine.py` | Updated provider swap assertion to accept `"deterministic"` |

---

## Remaining Notes

- The orchestrator call on FAST path is retained for explainability trace metadata (the `prompt_step` references `retrieved_context.identity_summary` which requires the prompt context to be assembled)
- The `raw_llm_response` field in `EngineResponse` is now `""` on FAST path. If the UI ever displays this field for debugging, it will be empty
- No changes to API contracts — all endpoint signatures and response shapes remain identical


# PHASE_5A_AUDIT.md

> **Source:** PHASE_5A_AUDIT.md

---

# PHASE 5A — PRODUCT COMPLETION AUDIT & ROADMAP

## Audit Date: 28 August 2026

---

# PART 1 — COMPLETE USER JOURNEY AUDIT

## 1.1 Landing Page (`/`)

**What the user sees:** Marketing page with hero ("Remember who you were. Understand who you're becoming."), 4 feature cards, 3-step "how it works" section, CTA, and footer. Sticky header with logo, nav links, and Sign in / Start free buttons.

**What can the user do:** Click "Start free" → `/register`, "Sign in" → `/login`, anchor-scroll to Features/How it works.

**ChronOS communicates:** "Your private evolution engine" — positioning as calm, private, local-first. Stats: "100% Private", "5+ LLM providers", "Local-first".

**Next action obvious?** Yes. Two clear CTAs, no ambiguity.

**Dead ends?** None.

**Duplicated functionality?** None.

**Hidden functionality?** None — this is a clean marketing surface.

**Issues found:**
- Landing page says "5+ LLM providers" — this is a technical detail irrelevant to most users. A user doesn't care how many providers exist; they care that it works.
- The "How it works" section says "ChronOS quietly weaves it into a living memory" — good, but the 3 steps don't explain what the user gets back. Step 3 says "see how you have grown" but doesn't show what that looks like.
- No social proof, testimonials, or example output. A new user has no idea what a "reflection" or "story" actually looks like before signing up.

---

## 1.2 Registration (`/register`)

**What the user sees:** Centered card with full name (optional), email, password fields, "Create account" button, link to login.

**What can the user do:** Fill fields, submit, navigate to login.

**ChronOS communicates:** Minimal — just form labels. No explanation of what happens next.

**Next action obvious?** Yes — "Create account" button.

**After action:** Auth tokens stored, redirected to `/onboarding`.

**Dead ends?** None.

**Duplicated functionality?** None.

**Hidden functionality?** None.

**Issues found:**
- No indication that onboarding follows. A user clicking "Create account" doesn't know they're about to go through a 7-step wizard. This could cause abandonment.
- No password strength indicator.
- No email verification flow (user is `is_verified: false` but the app doesn't guide them to verify).

---

## 1.3 Onboarding (`/onboarding`)

**What the user sees:** 7-step wizard with progress bar: About You, Life Now, On Your Mind (optional), Goals, Changes (optional), First Memory, Preferences. Header shows completion count. Each step has title, subtitle, question, and form inputs.

**What can the user do:** Fill each step, skip optional steps, go back to revisit, autosave drafts in background.

**ChronOS communicates:** Step titles/subtitles are warm and clear ("What does your life look like right now?", "Give Chronos something to remember"). Footer reassures: "Your answers are private and belong only to you."

**Next action obvious?** Yes — "Continue" button (or "Skip" on optional steps). Final step: "Finish & launch Chronos".

**After action:** Progresses to next step. Final step calls complete → 2.5s success screen ("Chronos is ready.") → redirect to dashboard.

**Dead ends?** None — can always go back.

**Duplicated functionality?** None.

**Hidden functionality?** Autosave is running silently (1.5s debounce). Communicated only in the footer ("Autosaved as you type").

**Issues found:**
- Step 1 (About You) has all optional fields — the user can skip everything and click Continue. This sets a precedent that onboarding isn't important.
- The "About You" step asks for timezone but says it's "important" — yet the app never uses timezone for anything visible to the user.
- Step 5 (First Memory / Genesis Memory) says audio/video support is "coming soon" — this is dead text in the UI.
- The completion screen says "Chronos is ready" but doesn't explain what Chronos will do or what the user should do next.
- No way to pause and resume later (the recovery banner handles incomplete onboarding, but the wizard itself doesn't have a "Save and come back" affordance).
- 7 steps is long. Steps 1 (About You) and 3 (On Your Mind) and 5 (Changes) are all optional — effectively only 4 required steps, but the wizard still shows 7.

---

## 1.4 Dashboard — First Load (`/dashboard`)

**What the user sees:** Auth guard → spinner "Opening your timeline..." → skeleton layout → full dashboard with:
- Sticky header (logo, "ChronOS" badge, user avatar → `/me`)
- Welcome hero ("Welcome back, {firstName}")
- Stats bar (Stories / Conversations / Memories — all likely 0 or 1 on first load)
- 5-tab navigation (Home, Stories, Timeline, Insights, Memories)
- Home tab: Recorder, Feed ("The engine is listening"), Identity model ("Building your identity model"), Reflections ("No reflections yet")

**What can the user do:** Switch tabs, record first memory, view empty states.

**ChronOS communicates:** "A quiet space for everything you have shared. Record a thought, glance at how you have changed, or revisit an old memory."

**Next action obvious?** Partially. The recorder is prominent ("Share a moment"), but the empty states across all tabs create a sense of "nothing here yet."

**Dead ends?** Timeline, Insights, and Memories tabs are all empty on first load with no actions available.

**Duplicated functionality?** None.

**Hidden functionality?** The "Explain" eye icon on responses is subtle. The "Continue story" feature only appears after a story is created. The mood picker is buried in `/me`.

**Issues found:**
- **Critical: The first-time dashboard experience is underwhelming.** After a thoughtful 7-step onboarding, the user lands on a dashboard where 4 of 5 tabs show empty states. The only interactive element is the recorder. There's no "here's what Chronos learned from your onboarding" summary.
- Stats bar on first load shows "0 Stories, 1 Conversations, 0 Memories" — the conversation count comes from onboarding completion, but "0 Memories" is confusing since the user just gave Chronos their genesis memory.
- The welcome subtitle says "Record a thought, glance at how you have changed, or revisit an old memory" — but the user hasn't changed yet and has no old memories to revisit. This copy is written for a returning user, not a first-time user.
- No guided tour or tooltip explaining what each tab is for.
- The identity model shows "Building your identity model" — but the onboarding already created an identity. This empty state is misleading.

---

## 1.5 Home Tab — Ongoing Use

**What the user sees:** Recorder (voice/video/text/file tabs), Conversation feed (chronological user messages + ChronOS responses), Identity model card, latest 2 reflections.

**What can the user do:** Record/submit memories, view conversation history, see identity evolution, read reflections, explain responses via eye icon, continue stories.

**ChronOS communicates:** Responses are phrased cautiously ("the input suggests...", "based on what you've shared..."). Past-self moments appear as "Something from your past" cards.

**Next action obvious?** Yes — the recorder is the primary action.

**Dead ends?** None — the recorder is always available.

**Duplicated functionality?** Reflections appear both here (2 latest) and in the Insights tab (all). This is intentional (preview vs full), but the relationship isn't explained.

**Hidden functionality?**
- The "Explain" eye icon opens a modal with confidence %, reasoning steps, linked memories, and prompt payload. This is the most technically impressive feature but is hidden behind a tiny icon.
- The "Continue story" chip only appears after a temporal thread is created. Users may not know this feature exists until they stumble upon it.
- The "Clear active story" X button is subtle.

**Issues found:**
- The recorder defaults to "Voice" tab — but text is the most accessible and common input method. New users on desktop may not realize they can type.
- There's no keyboard shortcut or quick-input method. Every submission requires clicking "Remember this."
- After submitting, the thinking bubble appears, then the response. But there's no indication of whether ChronOS detected anything interesting (temporal thread, pattern, etc.). The user has to check other tabs to find out.
- The feed shows "Just now" for the latest response and timestamps for historical ones — but there's no way to scroll back through a long conversation history (the feed is just a flat list).
- The identity model card has a "Refresh" button — but the user doesn't know what refreshing does or why they'd want to.

---

## 1.6 Stories Tab

**What the user sees:** Journey view with temporal threads as cards showing: subject, status badge, type label, story arc (origin → progression → current), time span, narrative. Empty state: "Your journey will take shape here."

**What can the user do:** Click a story card → temporal thread detail view (timeline of events within that story, "Continue this story" button, back button).

**ChronOS communicates:** Story statuses (Open, Active, Resolved, Abandoned, Changed) with narratives. Story arcs show where it started and where it is now.

**Next action obvious?** Clicking a story card is intuitive. "Continue this story" returns to Home tab with active thread context.

**Dead ends?** If no stories exist, the empty state has no action — just an explanation.

**Duplicated functionality?** None.

**Hidden functionality?** "Continue this story" is the most powerful feature for deepening a narrative, but it's buried inside the thread detail view.

**Issues found:**
- The empty state doesn't tell the user how to create a story. It says "As ChronOS notices meaningful changes... they will appear here" — but the user doesn't know what triggers story creation.
- No filtering or sorting by status, type, or date.
- The thread detail view is a vertical list of events — it's functional but not visually compelling. It doesn't feel like a "story."

---

## 1.7 Timeline Tab

**What the user sees:** Vertical timeline of life events with sentiment icons (smile/meh/frown), lifecycle phase badges, belief evolution notes. Empty state: "Your timeline is quiet."

**What can the user do:** Scroll through events. That's it.

**ChronOS communicates:** Event titles, descriptions, timestamps, sentiment, recurring indicators, belief evolution.

**Next action obvious?** No — the timeline is purely read-only. There are no actions, filters, or interactions.

**Dead ends?** Yes — the timeline is a dead end. No way to edit, delete, or act on events.

**Duplicated functionality?** Timeline events also appear in the Stories tab's thread detail view.

**Issues found:**
- The timeline is the weakest tab. It's a flat list with no interactivity.
- No time-based navigation (jump to a specific date, filter by month/year).
- No way to add context or annotations to events.
- The sentiment icons are based on numeric thresholds (>0.2 positive, <-0.2 negative) — the user doesn't know what these mean or how they're calculated.

---

## 1.8 Insights Tab

**What the user sees:** Two sections: Reflections (expandable cards with past vs present comparison, reasoning trace) and Patterns (grid of detected behavioral patterns with category, confidence, frequency). Empty states for both.

**What can the user do:** Expand/collapse reflection cards to see past/present states and reasoning.

**ChronOS communicates:** Summaries, confidence scores, insight types, reasoning traces, pattern categories.

**Next action obvious?** Expand to read more. No other actions.

**Dead ends?** Read-only.

**Duplicated functionality?** Reflections are also shown in the Home tab (limited to 2). Patterns have no other representation.

**Issues found:**
- No explanation of what "confidence score" means to the user. A 72% confidence is meaningless without context.
- Pattern categories (repeated_success, recurring_problem, habit, productivity_trend, behavior_loop) use internal naming that leaks implementation details.
- No way to dismiss, archive, or mark patterns as "not relevant."
- No historical view of how patterns have changed over time.

---

## 1.9 Memories Tab

**What the user sees:** Searchable list of all memories with input type icon, importance score, content, media playback, tag chips, connection count. Empty state: "No memories yet."

**What can the user do:** Search by text/tags, play audio/video media.

**ChronOS communicates:** Content, input type, importance percentage, tags, connections.

**Next action obvious?** Search is clear. Otherwise, read-only.

**Dead ends?** Read-only — no editing, deleting, or annotating memories.

**Duplicated functionality?** None.

**Issues found:**
- Importance score is shown as a percentage but the user doesn't know what it means or how it's calculated.
- No pagination — all memories are loaded at once (limited to 20 by default from the API, but the UI doesn't show this).
- No way to mark a memory as important or unimportant.
- No way to add tags or edit memory content.
- The search is client-side only (filters the already-loaded list), not a server-side search.

---

## 1.10 Me Page (`/me`)

**What the user sees:** Two tabs: Profile (identity card with avatar, name, email, badges, member since, user ID, ChronOS profile tag) and Data (MyDataExplorer with goals, preferences, genesis memory, identity traits). Also: Customization section with mood picker, sign out button.

**What can the user do:** View/edit profile data, manage goals (CRUD), edit preferences, edit genesis memory, edit identity traits, change mood theme, sign out.

**ChronOS communicates:** Account info, customization options, data management.

**Next action obvious?** Sign out is clear. Data management requires exploration.

**Dead ends?** None.

**Duplicated functionality?** `/my-data` redirects here.

**Hidden functionality?**
- Mood picker (5 themes: Night, Daylight, Rain, Cloudy, Sunset) — purely cosmetic, persisted in localStorage.
- Goal management (create, edit, delete) — powerful but nested under Me → Data → Goals tab.
- Genesis memory editing — important but hidden.
- Identity trait editing — allows user to influence their identity model.

**Issues found:**
- The mood picker is the only "fun" personalization feature, but it's buried 2 clicks deep (avatar → Me → Customization).
- No account settings (change email, change password, delete account).
- No data export or backup capability.
- No notification preferences (the app doesn't have notifications, but the user should be able to configure this).
- The "Data" tab is a power-user feature — most users won't discover it.
- User ID is displayed as a raw UUID — meaningless to users.

---

## 1.11 Sign Out

**What the user sees:** Click "Sign out" on Me page → tokens cleared → redirected to `/login`.

**What can the user do:** Sign out.

**ChronOS communicates:** Nothing — just redirects.

**Issues found:**
- No confirmation dialog. Accidental click signs you out.
- No "Are you sure?" or summary of what happens (e.g., "Your data will still be here when you return").

---

# PART 2 — CORE PRODUCT LOOP AUDIT

## 2.1 The Current Loop

```
User returns
→ Opens dashboard
→ Records a thought/memory
→ ChronOS processes (memory + timeline + identity + temporal detection)
→ ChronOS responds with reflection + optional past-self moment
→ User reads response
→ (Sometimes) user checks other tabs
→ User leaves
→ ... no trigger to return ...
→ User may or may not come back
```

## 2.2 What's Working

1. **Input → processing → response is clear.** The recorder is prominent, the thinking bubble provides feedback, and the response appears immediately.
2. **Past-self moments are the key differentiator.** When they fire, they create genuine moments of reflection ("Something from your past...").
3. **Stories accumulate over time.** The temporal thread system creates meaningful narratives that deepen with use.
4. **Identity model evolves.** The user can see their emotional posture, interests, goals, and values change.
5. **Explainability is available.** The reasoning trace gives power users insight into how ChronOS thinks.
6. **The onboarding is thorough.** 7 steps create a rich baseline for the system.

## 2.3 What's Incomplete

1. **No return hook.** After initial conversations, there's nothing pulling the user back. No notifications, no daily prompt, no "check-in" reminder, no weekly summary.
2. **No proactive surfacing.** Insights and patterns are passive — the user must navigate to them. ChronOS never says "Hey, I noticed something interesting."
3. **No time-based reflection.** No "A week ago you said..." or "You've been talking about X for 3 months" or "Your mood shifted after Y."
4. **No settings page.** Account management, notification preferences, data export, privacy controls — none exist.
5. **No mobile-first experience.** The app is responsive but not optimized for mobile. Voice recording works, but the experience isn't designed for phone use.
6. **No onboarding for the dashboard.** After the 7-step wizard, the user is thrown into an empty dashboard with no guidance.
7. **No example content.** A new user can't see what a "mature" ChronOS looks like. The seed endpoint exists but isn't exposed to users.
8. **No way to delete data.** Users can edit goals and preferences, but can't delete memories, threads, or their account.

## 2.4 What Should NOT Be Built Yet

1. **Multi-user / sharing features.** The product isn't mature enough for collaboration.
2. **Advanced analytics / dashboards.** The current data isn't rich enough to warrant complex visualizations.
3. **Natural language querying ("Show me when I was happiest").** The retrieval system isn't sophisticated enough.
4. **Integration with external services (calendar, notes, health data).** Too early — the core loop isn't proven.
5. **Mobile app (React Native / native).** The web app should be polished first.
6. **Advanced AI features (image generation, voice synthesis).** The core temporal intelligence is the differentiator, not flashy AI.

---

# PART 3 — KEY FINDINGS

## 3.1 Critical Product Gaps

| # | Gap | Impact | Effort |
|---|-----|--------|--------|
| 1 | **No return hook** — Nothing pulls the user back after initial use | Critical — the product loop breaks | Medium |
| 2 | **Empty first experience** — Dashboard is barren after onboarding | Critical — first impressions are poor | Medium |
| 3 | **No settings page** — No account management, data export, or privacy controls | High — trust and retention | Low |
| 4 | **No data deletion** — Users can't remove memories or their account | High — privacy and GDPR | Low |
| 5 | **No guided dashboard onboarding** — No tour or explanation of tabs | High — discovery and activation | Medium |

## 3.2 UX Issues

| # | Issue | Severity |
|---|-------|----------|
| 1 | **Empty states dominate early experience** — 4 of 5 tabs show nothing on first load | High |
| 2 | **Tab purpose unclear** — No explanation of what each tab is for | Medium |
| 3 | **Explainability hidden** — Eye icon is too subtle for such an important feature | Medium |
| 4 | **Active thread continuation buried** — Only discoverable after creating a story | Medium |
| 5 | **Stats bar confusing** — "Stories" vs "Conversations" vs "Memories" distinction unclear | Low |
| 6 | **Recorder defaults to Voice** — Text is more accessible for first-time users | Low |
| 7 | **No keyboard shortcuts** — No Cmd+Enter to submit, no navigation shortcuts | Low |
| 8 | **Importance/confidence scores meaningless** — Numbers shown without context | Low |

## 3.3 Technical Gaps

| # | Gap | Severity |
|---|-----|----------|
| 1 | **Engine endpoints unauthenticated** — `user_id` from query param, not JWT | Critical (security) |
| 2 | **No error boundaries** — Inline error handling only, no page-level recovery | Medium |
| 3 | **No `loading.tsx`/`error.tsx`/`not-found.tsx`** — Next.js conventions not used | Low |
| 4 | **No SEO** — All client components, no meta tags | Low (not a content site) |
| 5 | **No data export** — Can't back up or migrate data | Medium |
| 6 | **Client-side memory search only** — No server-side search for large datasets | Low (for now) |

## 3.4 Dead Ends

| # | Location | Issue |
|---|----------|-------|
| 1 | **Timeline tab** | Read-only, no actions, no navigation |
| 2 | **Insights tab** | Read-only, no dismissal or interaction |
| 3 | **Memories tab** | Search only, no editing/deletion |
| 4 | **Empty states** | Most empty states have no actionable guidance |

## 3.5 Hidden Functionality

| # | Feature | Location | Discovery Problem |
|---|---------|----------|-------------------|
| 1 | **Explainability modal** | Home tab, eye icon on latest response | Tiny icon, no tooltip |
| 2 | **Continue story** | Stories → Thread detail → button | Requires 3 clicks to discover |
| 3 | **Mood picker** | Me → Customization | Buried 2 clicks deep |
| 4 | **Data management** | Me → Data tab | Nested under profile page |
| 5 | **Genesis memory editing** | Me → Data → Genesis Memory | Power-user feature |
| 6 | **Identity trait editing** | Me → Data → Identity | Power-user feature |

---

# PART 4 — PHASE 5 ROADMAP

## Prioritization Framework

- **P0 (Must ship):** Blocks the product loop or creates trust/privacy issues
- **P1 (Should ship):** Significantly improves retention and activation
- **P2 (Nice to have):** Polish and delight, but not blocking

---

## Phase 5B — Trust & Safety Foundation (P0)

**Goal:** Make ChronOS trustworthy and safe before asking users to invest more.

### 5B-1: Secure Engine Endpoints
- Move `/chronos/engine/*` routes to use JWT authentication (extract `user_id` from token, not query param)
- Remove the `user_default` fallback
- **Files:** `backend/src/chronos_engine/api/router.py`, `backend/src/opentime/api/dependencies.py`
- **Why:** Critical security gap. Any user can access any other user's data by passing a different `user_id`.

### 5B-2: Account Settings Page (`/settings`)
- New page with sections: Account (change email, change password), Data (export all data, delete account), Privacy (data retention policy)
- Add to navigation (header avatar dropdown or Me page)
- **Files:** New `frontend/src/app/settings/page.tsx`, new components
- **Why:** Users need control over their data to trust the product.

### 5B-3: Data Deletion
- Backend: Add `DELETE /api/v1/chronos/state` endpoint (anonymize or remove all user data)
- Frontend: "Delete my account" button in settings with confirmation dialog
- **Files:** `backend/src/opentime/api/v1/chronos_state.py`, `backend/src/opentime/application/`, new frontend settings page
- **Why:** GDPR compliance and user trust.

### 5B-4: Data Export
- Backend: Add `GET /api/v1/chronos/export` endpoint (returns JSON with all memories, threads, identity, goals, patterns)
- Frontend: "Export my data" button in settings
- **Files:** `backend/src/opentime/api/v1/chronos_state.py`, new frontend settings page
- **Why:** User ownership of data. Also enables power users to back up.

### 5B-5: Error Boundaries
- Add React error boundaries around each tab and the main dashboard
- Add `error.tsx` files for `/dashboard`, `/me`, `/settings`
- Add `not-found.tsx` for 404 pages
- **Files:** New `error.tsx` files, new `not-found.tsx`, wrap tabs in boundaries
- **Why:** Graceful degradation instead of white screens.

---

## Phase 5C — First Experience & Activation (P1)

**Goal:** Make the first 5 minutes magical. Ensure users understand what ChronOS does and why they should return.

### 5C-1: Post-Onboarding Welcome Summary
- After onboarding completion, show a "Here's what Chronos learned about you" summary before the dashboard
- Display: identity snapshot, goals, genesis memory, what ChronOS will track
- Allow user to edit before proceeding
- **Files:** New `frontend/src/components/onboarding/WelcomeSummary.tsx`, modify onboarding completion flow
- **Why:** Bridges the gap between onboarding effort and dashboard payoff.

### 5C-2: Dashboard First-Visit Guided Tour
- On first dashboard load (detect via localStorage flag), show a 4-step tooltip tour:
  1. "This is where you share moments" (point to recorder)
  2. "ChronOS responds here" (point to feed)
  3. "Your identity evolves over time" (point to identity card)
  4. "Stories and insights grow as you share" (point to tabs)
- **Files:** New `frontend/src/components/dashboard/GuidedTour.tsx`, modify dashboard page
- **Why:** Prevents the "what do I do now?" moment.

### 5C-3: Smart Empty States
- Replace generic empty states with contextual, actionable ones:
  - **Home tab (first visit):** "Start by sharing one thing about your day. ChronOS will begin building your timeline."
  - **Stories tab (empty):** "Stories emerge as you share more. Each conversation adds to your narrative."
  - **Timeline tab (empty):** "Your timeline fills as ChronOS learns about your life events."
  - **Insights tab (empty):** "Reflections appear once ChronOS has enough context to compare your past and present."
  - **Memories tab (empty):** "Your memories will appear here after your first conversation."
- **Files:** Modify all empty state components
- **Why:** Sets expectations and reduces confusion.

### 5C-4: Text Default Input Mode
- Change the recorder's default tab from "Voice" to "Text"
- **Files:** `frontend/src/components/chronos/VoiceVideoRecorder.tsx` (line 35: change initial state)
- **Why:** Text is more accessible, works on all devices, and is the most common input method.

### 5C-5: Keyboard Shortcut for Submit
- Add Cmd/Ctrl+Enter shortcut to submit the recorder
- **Files:** `frontend/src/components/chronos/VoiceVideoRecorder.tsx`
- **Why:** Power users expect keyboard shortcuts. Reduces friction.

### 5C-6: Stats Bar Clarity
- Rename stats to be more descriptive:
  - "Stories" → "Narratives" or keep "Stories" but add tooltip: "Ongoing themes in your life"
  - "Conversations" → "Messages" or "Moments shared"
  - "Memories" → "Memories" (clear enough)
- Add tooltips explaining each stat
- **Files:** `frontend/src/app/dashboard/page.tsx`
- **Why:** Reduces confusion about what each number means.

---

## Phase 5D — Return Hook & Engagement (P1)

**Goal:** Give users a reason to come back. Make ChronOS more useful over time.

### 5D-1: Daily Check-In Prompt
- Add a "Check in" button on the Home tab that opens the recorder with a suggested prompt based on time of day and recent activity
- Morning: "How are you starting today?"
- Evening: "How was your day?"
- After gap: "It's been a while. What's been on your mind?"
- **Files:** New `frontend/src/components/dashboard/CheckInPrompt.tsx`, modify Home tab
- **Why:** Creates a daily ritual and return habit.

### 5D-2: Weekly Reflection Summary
- New "Weekly" section in Insights tab (or new tab)
- Auto-generated (via cron or on-demand) summary of the week: themes, mood trends, goal progress, notable moments
- Backend: New endpoint or computed on-the-fly from existing data
- **Files:** New backend endpoint, new frontend component
- **Why:** Gives users a reason to return weekly. Shows value of accumulated data.

### 5D-3: "Since Last Visit" Digest
- On dashboard load, if user hasn't visited in >24 hours, show a subtle banner:
  - "Since your last visit: 2 new patterns detected, your identity evolved, 1 story progressed"
- **Files:** Modify dashboard page, new `SinceLastVisit.tsx` component
- **Why:** Shows progress and creates FOMO (in a healthy way).

### 5D-4: Proactive Pattern Surfacing
- When a new pattern is detected, show a non-intrusive notification card at the top of the Home tab
- "ChronOS noticed: You've been consistently talking about [topic] this week"
- **Files:** Modify dashboard page, new notification component
- **Why:** Makes the system feel alive and attentive.

### 5D-5: Notification Preferences
- New section in Settings: configure what triggers notifications (new pattern, weekly summary, inactivity reminder)
- Backend: Store preferences in user settings
- **Files:** New backend model, new settings section
- **Why:** Gives users control over engagement frequency.

---

## Phase 5E — Polish & Interaction (P2)

**Goal:** Make the existing experience feel finished. Reduce friction, add delight.

### 5E-1: Explainability Modal Enhancement
- Make the eye icon more discoverable: add a tooltip "See how ChronOS thinks" and make it slightly larger
- Add a "What does this mean?" help text in the modal
- **Files:** `frontend/src/components/chronos/ChronosEngineFeed.tsx`
- **Why:** The explainability feature is impressive but hidden.

### 5E-2: Story Continuation UX Improvement
- After a temporal thread is created/updated, show a subtle "Continue this story →" link directly in the response
- Instead of requiring 3 clicks (Stories tab → thread detail → Continue), make it 1 click
- **Files:** `frontend/src/components/chronos/ChronosEngineFeed.tsx`, `frontend/src/components/chronos/PastSelfMomentCard.tsx`
- **Why:** The most powerful feature for deepening narratives should be more accessible.

### 5E-3: Timeline Interactivity
- Add click-to-expand on timeline events to show full details
- Add date range filter (dropdown or slider)
- Add "Jump to today" button
- **Files:** `frontend/src/components/chronos/TimelineEngineView.tsx`
- **Why:** The timeline tab is currently a dead end.

### 5E-4: Memory Management
- Allow users to edit memory content (inline edit)
- Allow users to delete memories (with confirmation)
- Allow users to add/remove tags
- Backend: Add PATCH and DELETE endpoints for memories
- **Files:** `backend/src/opentime/api/v1/chronos_state.py`, `frontend/src/components/chronos/MemoryGraphView.tsx`
- **Why:** Users need control over their data.

### 5E-5: Mood Picker Accessibility
- Move mood picker to dashboard header (as a subtle icon/dropdown)
- Or: add a "Theme" option in the dashboard settings gear icon
- **Files:** `frontend/src/app/dashboard/page.tsx`, new component
- **Why:** The only personalization feature shouldn't be buried.

### 5E-6: Responsive Mobile Optimization
- Optimize recorder for mobile (larger touch targets, swipe between modes)
- Optimize tab navigation for mobile (horizontal scroll with indicators)
- Optimize memory cards for mobile (stack vertically, reduce padding)
- **Files:** Various component files
- **Why:** Many users will access via phone.

### 5E-7: Conversation History Improvements
- Add infinite scroll or pagination to the feed
- Add "Load more" button for older conversations
- Add date separators between conversation days
- **Files:** `frontend/src/components/chronos/ChronosEngineFeed.tsx`
- **Why:** The feed becomes unusable with many conversations.

### 5E-8: Sign Out Confirmation
- Add a confirmation dialog before signing out
- **Files:** `frontend/src/app/me/page.tsx`
- **Why:** Prevents accidental sign-out.

### 5E-9: Landing Page Social Proof
- Add example outputs (anonymized reflections, story arcs) to the landing page
- Show what a "mature" ChronOS looks like after weeks of use
- **Files:** `frontend/src/app/page.tsx`
- **Why:** New users need to see the value before committing.

---

# PART 5 — WHAT SHOULD NOT BE BUILT YET

| Feature | Why Not Now |
|---------|-------------|
| Multi-user / sharing | Product isn't mature enough for collaboration |
| Advanced visualizations (graphs, charts) | Data isn't rich enough yet |
| Natural language querying | Retrieval system isn't sophisticated enough |
| External integrations (calendar, health) | Core loop isn't proven |
| Mobile native app | Web app should be polished first |
| AI image/voice generation | Core temporal intelligence is the differentiator |
| Gamification (streaks, badges) | Premature — the product needs to prove value first |
| Social features (comments, reactions) | Privacy-first product shouldn't have social pressure |
| Advanced onboarding (interactive tutorial) | Current 7-step flow is sufficient |
| Real-time sync / WebSocket updates | Not needed at current scale |

---

# PART 6 — RECOMMENDED PHASE SEQUENCE

```
Phase 5B (Trust & Safety)     → 1-2 weeks
  ↓
Phase 5C (First Experience)   → 1-2 weeks
  ↓
Phase 5D (Return Hook)        → 2-3 weeks
  ↓
Phase 5E (Polish)             → 2-3 weeks
  ↓
Phase 6 (New Intelligence)    → TBD after 5B-5E complete
```

**Total estimated effort:** 6-10 weeks

**Key principle:** Ship trust and safety first, then fix the first experience, then build return hooks, then polish. Never add new intelligence until the product loop is proven.


# PHASE_5B_REPORT.md

> **Source:** PHASE_5B_REPORT.md

---

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


# PHASE_5C_PLAN.md

> **Source:** PHASE_5C_PLAN.md

---

# Phase 5C — First Experience & Activation: Implementation Plan

## Audit findings (current state)

1. **Flow**: register → `/onboarding` (7 steps) → `complete` → "Chronos is ready" → `/dashboard`.
2. **Onboarding completion** writes REAL data to the **opentime-domain** MongoDB store:
   `memories` (genesis + per-step), `identity_states`, `goals`, `timeline_events`,
   `patterns`, `analysis_preferences`, `chronos_states`. No engine store writes.
3. **Dashboard** reads the **engine** store (`/chronos/engine/*`): identity
   (lazily auto-creates a hardcoded **Founder** profile), memories `[]`, threads `[]`,
   interactions `[]`, reflections `[]`, patterns (lazy). → A brand-new user sees
   **0 Stories / 0 Conversations / 0 Memories** and a **fabricated Founder identity**.
4. **No onboarding-response GET endpoint** exists (preferred_name unreachable by API);
   only the auth `User.full_name` is available client-side for personalization.
5. **VoiceVideoRecorder defaults to `"audio"` tab** — Phase 5C wants **text** as the clear primary.
6. **Empty states** exist but are generic; several already reference engine concepts
   (confidence, reasoning trace) that are out of scope to change.
7. **First-story data** IS available: `response.chronos_state.temporal_lifecycle` with
   `created` / `updated` / `thread_id`.
8. **PastSelfMomentCard** exists and is grounded; header "Something from your past".

## Decisions

- **First-use detection is derived, not a new backend subsystem.** A user is
  "first-use" when `interactions.length === 0 && threads.length === 0` (pure client
  derivation from state the dashboard already loads). Returning users with history
  never match. No new endpoint.
- **No conflation of engine vs domain stores.** The dashboard tabs legitimately read
  engine data; bringing in domain onboarding data would add endpoints and confuse the
  two models. Instead, the first-use Home is **honest**: it personalizes with the
  user's name, explains what ChronOS has so far, and leads with one primary action.
- **Fix the fabricated identity**: for first-use users the Identity sidebar shows a
  building-an-identity empty state instead of the Founder profile (the dashboard
  already passes `identity`; we gate rendering at first-use).
- **Text is the default input** for first-use (VoiceVideoRecorder gains an optional
  default tab; first-use passes `"text"`).
- **Reuse existing components** (Button, Card, EmptyState) — no new design system.

## Implementation

1. `dashboard/page.tsx`: derive `isFirstUse`; personalized first-use hero + one primary
   action; gate IdentityModelCard in first-use; pass `defaultTab="text"` to recorder.
2. New `FirstUseWelcome` component (welcome copy, "what ChronOS has so far" summary,
   optional starter prompts). Starter prompts derived from real state (name, goals
   when available); fallback allowed; grounded only in real data.
3. Starter prompts render inside/above the recorder; clicking fills the text input and
   focuses it (frictionless, reuses existing submission path — no duplicate logic).
4. `VoiceVideoRecorder`: add `defaultTab` prop; default stays `"audio"` for returning
   users, `"text"` for first-use via dashboard.
5. **Smart empty states** (still reads engine data): improve the copy of
   Timeline/Reflections/Patterns/Memories/Journey empty states to the 3-point format
   (what appears → how it's created → what to do), human language, no internal concepts.
6. **First-story acknowledgement**: in `handleResponseReceived`, when
   `temporal_lifecycle.created` is true, surface a quiet "A new story is beginning" note
   (derived from real lifecycle data only).
7. **First Past-Self moment**: `PastSelfMomentCard` gains a subtle one-time contextual
   line when it is the first surfaced moment (no engine IDs/confidence shown).
8. Responsive + semantic buttons; text default keeps mobile simple.

## Tests
- Backend: no intelligence changed; run full pytest (regression).
- Frontend: `tsc --noEmit` + `next build`. No frontend test framework exists;
  verify first-use derivation via TypeScript and build, document the limitation.


# PHASE_5C_REPORT.md

> **Source:** PHASE_5C_REPORT.md

---

# Phase 5C Report — First Experience & Activation

## Goal
Make the first 5–10 minutes after onboarding a genuinely good experience for a
brand-new user: a grounded, honest, and low-friction first encounter with ChronOS —
without touching the ChronOS intelligence pipeline, without gamification, and
without inventing anything about the user.

## What changed

### First-use detection (derived, no new backend)
`frontend/src/app/dashboard/page.tsx`
- A user is treated as **first-use** purely from existing loaded state:
  `isFirstUse = !isInitialLoad && interactions.length === 0 && threads.length === 0`.
- No new endpoint and no new backend state was introduced (per scope: prefer
  deriving first-use from existing product state). Returning users (with engine
  conversations or stories) never match, so the existing experience is preserved.

### Post-onboarding Home activation
`frontend/src/app/dashboard/page.tsx`, `frontend/src/components/chronos/FirstUseWelcome.tsx` (new)
- Personalized hero copy for first-use ("Welcome, {name}" instead of "Welcome
  back") and a first-use-specific subtitle.
- The all-zero stats card (0 Stories / 0 Conversations / 0 Memories) is **hidden
  for first-use** so a fresh user is not greeted by discouraging empty zeros.
- New `FirstUseWelcome` component: a compact, non-tutorial welcome that states
  honestly what ChronOS has so far (their onboarding starting point) and what it
  builds from. It does **not** compete with the conversation input with a second
  large call-to-action — the single primary action is the input below it.
- Progressive disclosure is respected: only the Home tab changes for first-use;
  tabs are still lazy-loaded with no refetch-all-after-every-message.

### Personalized starter prompts (grounded, honest)
`dashboard/page.tsx`
- On first use only, a single targeted call to the existing `myDataApi.goals(true)`
  returns the user's real onboarding goals. Starter prompts are built from them,
  e.g. `Let's talk about why "<goal>" matters to you right now.`
- When a goal exists it is used (grounded in real data, never fabricated). If none
  exists, honest general reflective prompts are used instead (no persona claim).
- Clicking a prompt is **fill-input only**: it injects the text into the recorder's
  text field and switches it to text mode. It reuses the existing submission path —
  no duplicate submission logic.

### Text as the clearest default first interaction
`frontend/src/components/chronos/VoiceVideoRecorder.tsx`
- Added optional `defaultTab` prop (default stays `"audio"` for returning users).
  The dashboard passes `defaultTab="text"` for first-use, so writing is the primary
  first interaction; voice/video remain available one tap away.
- Added `injectedPrompt` / `onInjectedPromptConsumed` so a picked starter prompt is
  placed into the input and consumed (avoids re-fill loops).

### Smart empty states
`TimelineEngineView.tsx`, `ReflectionEngineView.tsx`, `PatternDetectionView.tsx`,
`MemoryGraphView.tsx`, `JourneyView.tsx`, `ChronosEngineFeed.tsx`
- Rewrote empty-state copy using a consistent, human pattern:
  what appears → how it is created → what to do, always leading back to the Home
  conversation. No internal concepts (embeddings, retrieval, thresholds, lifecycle,
  vector search, inference) are exposed. No user data is assumed.
- The engine feed's listening copy now leads with writing a thought (text-first).

### First-story handling
`dashboard/page.tsx`
- When `response.chronos_state.temporal_lifecycle.created` is true (a thread is
  actually created), a quiet, dismissible note appears: "A new story is beginning…".
  This is driven strictly by real lifecycle data — a story is acknowledged only
  when ChronOS truly created it, never manufactured.

### First-use identity honesty
`dashboard/page.tsx`
- For first-use users, the identity sidebar shows a "Your identity, taking shape"
  card instead of the engine's hardcoded **Founder** profile (which is fabricated
  for a new user and would have implied a profile that doesn't exist). The card
  explains honestly that ChronOS doesn't assume who the user is. Returning users
  still see the full `IdentityModelCard`.

### Past-Self moment
- No fabricated past-self moments were introduced. First-use messaging in
  `FirstUseWelcome` (and the existing `PastSelfMomentCard`) already explains, in
  plain language, that stories and past-self moments are woven only from what the
  user shares over time. The card's existing grounded rendering is unchanged.

### First-use vs returning-user states
- First-use: personalized welcome, starter prompts, text-first input, honest
  identity, no zero-stats, first-story note.
- Returning: "Welcome back", stats bar, full `IdentityModelCard`, audio-first
  recorder, richer feed — unchanged from prior phases.

### Responsive + accessibility
- FirstUseWelcome stacks cleanly on mobile and uses semantic buttons with
  focus rings for prompt chips and dismiss actions; dismiss buttons have
  `aria-label`s. Text default keeps the first interaction simple on small screens.

## Files changed
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/components/chronos/FirstUseWelcome.tsx` (new)
- `frontend/src/components/chronos/VoiceVideoRecorder.tsx`
- `frontend/src/components/chronos/TimelineEngineView.tsx`
- `frontend/src/components/chronos/ReflectionEngineView.tsx`
- `frontend/src/components/chronos/PatternDetectionView.tsx`
- `frontend/src/components/chronos/MemoryGraphView.tsx`
- `frontend/src/components/chronos/JourneyView.tsx`
- `frontend/src/components/chronos/ChronosEngineFeed.tsx`
- `PHASE_5C_PLAN.md` (new, implementation plan)

## Verification
- Backend: `pytest` → **618 passed, 4 skipped** (no regressions; no pipeline edits).
- Frontend: `npx tsc --noEmit` clean; `next build` succeeds for all routes.
- No frontend test framework exists in this repo; first-use behavior is verified
  through TypeScript correctness and the production build. (Known limitation.)

## Scope respected
No changes to temporal detection/classification/thread matching/lifecycle/
comparison/past-self/question planning/relevance/composition/reflection/AI
routing/inference/model tier/reasoning planner/memory retrieval. No gamification
(XP/levels/streaks/badges/points/fake progress). No fabricated psychological
profile, thread, or past-self moment. No new backend endpoints were added (first-use
is derived from existing data; goals come from the existing data API). No duplicate
submission logic. Phase 5D and 5E were not started. Phase 4I/4L performance is
preserved (no refetch-all-after-every-message, no duplicate rendering, lazy tab
loading intact).


# PHASE_7_5_FINAL_REPORT.md

> **Source:** PHASE_7_5_FINAL_REPORT.md

---

# Phase 7.5 — Controlled Beta Launch Preparation: Final Report

## 1. What Was Added

**Documentation only** — no code was changed this session:

| File | Purpose |
|------|---------|
| `BETA_PARTICIPANT_MODEL.md` | Who should participate, selection criteria, onboarding flow, what to promise/not promise, data stored, data-control features available |
| `BETA_TEST_PROTOCOL.md` | First-session, ongoing-usage, and return-session protocols; what to test and how |
| `BETA_OBSERVER_CHECKLIST.md` | Structured checklist for each participant session: comprehension, value, continuity, trust, return, friction |
| `BETA_FEEDBACK_PROTOCOL.md` | 17-question interview protocol with anti-bias rules and answer-classification guide |
| `BETA_SUCCESS_FRAMEWORK.md` | Extended Phase 7 framework with signal classification (diagnostic / beta success criterion / qualitative validation required) |
| `BETA_OPERATOR_GUIDE.md` | Environment verification, aggregate health checking, failure identification, safe telemetry inspection, data management, anti-exposure rules |
| `BETA_INCIDENT_RESPONSE.md` | First-response protocols for auth failures, server errors, stuck UI, incorrect personalization, incorrect temporal continuity, deletion problems, privacy/security reports; pause/resume/stop decision framework |
| `BETA_BUG_CLASSIFICATION.md` | P0–P3 severity definitions, what is NOT a bug, escalation path, bug report template |
| `BETA_EVIDENCE_LOG.md` | Structured log for recording observations, incidents, data-control activity, qualitative interviews, and product-loop validation |
| `PHASE7_BETA_FRAMEWORK.md` | Extended with signal classification framework (§5 of this task) |

---

## 2. What Was Deliberately NOT Changed

- **No code was modified** — all additions are documentation.
- No temporal intelligence, retrieval, reasoning, reflection, story, memory, return-context, or matching behavior was touched.
- No UI redesign, gamification, analytics infrastructure, or vanity-metric optimization was added.
- No invitation/account-management system was built — the existing normal registration flow is sufficient for a 5–15 person beta.
- No changes to deletion guarantees, authentication, or privacy boundaries.

---

## 3. Beta Participant Model

Defined in `BETA_PARTICIPANT_MODEL.md`:

- **Initial group**: 5–15 people, recruited for genuine interest in the temporal-intelligence hypothesis.
- **Selection dimensions**: technical/non-technical mix, self-expression habits, ongoing life situations, age spread, communication styles, 2–3 people max from one social circle.
- **Onboarding**: controlled invitation → short intake → first session (observed, not coached) → ongoing natural use → return session → debrief interview.
- **What NOT to promise**: that ChronOS "understands" them, that it will always be "right", that features will remain unchanged.
- **What IS promised**: data stays theirs (export/delete at any time); they are free to stop.
- **Data stored**: conversations, memories, temporal stories, identity/goals/patterns, onboarding, telemetry (metadata only), media uploads.
- **Existing data-control features**: export all data, delete all data, delete individual memories, archive/restore stories, edit goals/preferences/identity — all already built in the frontend `/me` and `/chronos` pages.

---

## 4. Beta Test Protocol

Defined in `BETA_TEST_PROTOCOL.md`:

- **First session**: test registration, onboarding, first conversation, first meaningful response; observe comprehension via direct questions.
- **Ongoing use**: encourage (but don't require) scenarios involving goals, decisions, recurring concerns, changing situations.
- **Return session**: wait 5–7 days; observe voluntary return; evaluate return context; interview on usefulness/intrusiveness/continuity recognition.
- **No scripting**: participants use the product naturally; observer notes behavior without coaching.
- **Anti-patterns**: don't reveal what ChronOS "should" do; don't measure against growth targets; don't store raw conversation content in the evidence log.

---

## 5. Observer Checklist

Defined in `BETA_OBSERVER_CHECKLIST.md`:

Structured checklist for: comprehension (what did they think it was for), first value (what was the first useful moment), continuity (did they notice connections), trust (any personalization feel wrong), return (did they come back voluntarily), friction (UI/speed/errors/terminology), and data-control usage. Includes a per-session summary template.

---

## 6. Feedback Protocol

Defined in `BETA_FEEDBACK_PROTOCOL.md`:

17 open-ended questions including "What do you think ChronOS is for?", "What was the most useful thing?", "Was there anything it got wrong?", "Did remembering previous conversations feel useful?", "Did anything feel intrusive?", "Would you use this again without being asked?", "What would make you come back / stop using it?".

Anti-bias rules enforced: no leading questions, no steering toward positive answers, no offering the operator's interpretation first, no turning the interview into a feature pitch.

---

## 7. Operator Guide

Defined in `BETA_OPERATOR_GUIDE.md`:

Covers: operator role and privacy boundary, environment verification checklist, aggregate health via `/metrics/beta-summary` with interpretation guide, how to identify failures, safe telemetry inspection rules (never expose raw content without authorization), how to handle participant error reports, data reset/deletion procedures, anti-exposure rules, environment safety checklist, and when to pause the beta.

---

## 8. Incident Process

Defined in `BETA_INCIDENT_RESPONSE.md`:

First-response protocols for 7 incident types (auth failures, server errors, stuck UI, incorrect personalization, incorrect temporal continuity, deletion problems, privacy/security reports), each with specific steps and severity classification.

Decision framework: when to pause (P0, widespread P1, >10% failure, data corruption), when to stop (multiple P0s, participant withdrawal, no value after 2+ weeks), when to resume (root cause fixed, regression passes, participant informed).

Participant communication templates for P0/P1/P2/P3 bugs.

---

## 9. Evidence Log Structure

Defined in `BETA_EVIDENCE_LOG.md`:

Includes: participant table (beta IDs only, no PII), evidence entry template, incident log, data-control activity log, qualitative interview log, and a **Product-Loop Validation** section with 8 stages (First Use → First Value → Accumulation → Continuity → Reflection → Return → Resurfacing → Trust) — each with "what we believe from code/tests", "beta evidence confirms", "beta evidence contradicts", and "remains unknown" fields. Ends with an aggregate telemetry snapshot template for the end of the beta.

---

## 10. Code Changes

**None.** This session was entirely documentation. No `.py`, `.ts`, `.tsx`, or `.mjs` files were modified or created.

---

## 11. Test Results

| Check | Baseline | Current | Delta |
|-------|----------|---------|-------|
| Backend pytest | 754 passed / 4 skipped | **754 passed / 4 skipped** | 0 |
| Ruff | 926 errors | **926 errors** | 0 |
| Frontend TypeScript | pass (pre-existing .next/types warning) | **pass** | 0 |
| Frontend build | pass | **pass** | 0 |
| Frontend leakage | pass | **pass** | 0 |
| Frontend Vitest | 14 passed | **14 passed** | 0 |

Zero regressions. Codebase is untouched.

---

## 12. Remaining Blockers

**None.**

- All documentation needed to run a controlled beta is in place.
- The existing data-control features (export, delete, archive, edit) are sufficient — no new UI is required.
- The existing telemetry infrastructure (Phase 6) covers all health signals needed.
- The existing authentication system supports controlled account creation (normal registration, no invitation platform needed).
- The beta environment only needs `DEBUG=false`, a real `JWT_SECRET_KEY`, and the frontend/backend URLs configured.

---

## 13. Whether ChronOS Is Ready to Begin the First Controlled Real-User Sessions

**READY FOR FIRST BETA SESSION**

ChronOS has:
- A fully instrumented product with privacy-safe metadata telemetry.
- Complete beta documentation: participant model, test protocol, observer checklist, feedback protocol, success framework, operator guide, incident response, bug classification, and evidence log structure.
- Existing data-control features (export, delete, archive, edit) that satisfy participant consent requirements.
- A safe environment separation model (debug endpoints gated, JWT validated, CORS configured).
- Zero regressions across all checks.
- No code changes this session — the product is exactly as it was after Phase 7.

The only remaining step is to provision the beta environment with production-safe configuration (`DEBUG=false`, real `JWT_SECRET_KEY`, appropriate `CORS_ORIGINS`) and invite the first participant.

# Phase2JAcceptanceEvidence.md

> **Source:** Phase2JAcceptanceEvidence.md

---

# Phase 2J — Real LIGHT Model Benchmark (Acceptance Evidence)

Benchmark against the real, manually-installed local model `qwen2.5:1.5b`
(`OLLAMA_LIGHT_MODEL=qwen2.5:1.5b`). No production code or architecture was
modified; the one-off harness in `/tmp` reuses the existing executor, policy,
provider, and engine infrastructure.

## Environment

- Ollama `qwen2.5:1.5b` (986 MB disk) and `qwen3:4b` (2.5 GB) installed.
- RTX 3050 Laptop GPU (4096 MiB), Ryzen 5 5600H, 14 GB RAM.
- Working tree clean (`ac383c9 chronosPhase2I&2J`); no new repo files.

## Raw Results (warm steady-state, model pre-loaded)

| Case | Tier | Model | Success | Fallback | Latency | Prompt tok | Gen tok | tok/s | Thinking | Validation | JSON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| INTERPRET | LIGHT | qwen2.5:1.5b | True | none | 1152 ms | 476 | 100 | 108.6 | n/a (no channel) | ok | ok* |
| CLASSIFY | LIGHT | qwen2.5:1.5b | True | none | 770 ms | 476 | 55 | 110.6 | n/a | ok | ok* |
| INTERPRET+CTX | LIGHT | qwen2.5:1.5b | True | none | 966 ms | 475 | 80 | 95.3 | n/a | ok | ok* |

\* Raw content carries prose around the embedded JSON; the executor's
`ResponseValidator` (authoritative) accepted it.

- Inputs benchmarked:
  1. INTERPRET — `"I'm frustrated because I'm stuck trying to finish ChronOS."`
  2. CLASSIFY — `"I don't even know what I'm trying to do anymore."`
  3. INTERPRET + context — `"I'm exhausted and wondering whether this project is worth continuing."`
- Cold first call: 14.06 s (model load). Cold CLASSIFY run once returned
  non-JSON -> `success=False, fallback_used=True, error_type=MALFORMED_JSON`
  (honest, non-deterministic model output); all warm runs validated ok.

## Verifications

- **LIGHT -> qwen2.5:1.5b**: all 3 cases `selected_tier=LIGHT`,
  `actual_model=qwen2.5:1.5b`.
- **LIGHT NEVER -> qwen3:4b**: recorder showed only
  `['qwen2.5:1.5b', 'qwen2.5:1.5b', 'qwen2.5:1.5b']`; `ollama ps` after the run:
  only `qwen2.5:1.5b` loaded (1.4 GB, 100% GPU), `qwen3:4b` never loaded.
- **FAST** (`"What is MongoDB?"`): `route=FAST`, `use_ai=False`,
  `ai_execution.attempted=False`, `tier=NONE`, `ollama_called=[]`, final
  response = engine's deterministic template ("USER SIGNAL / WHAT CHRONOS
  UNDERSTANDS ...").
- **VRAM**: qwen2.5:1.5b -> 1.4 GB / 100% GPU (peak ~2.45 GB incl. Ollama);
  qwen3:4b baseline was 2.4 GB / 33% CPU-67% GPU.

## Comparison vs qwen3:4b LIGHT Baseline (Phase 2I)

| Metric | qwen3:4b (2I) | qwen2.5:1.5b (now) |
|---|---|---|
| Task latency | 73.9-128.1 s | 0.77-1.15 s (~110-160x faster) |
| Tokens/sec | 15.4-19.8 | 95-111 (~5x) |
| Thinking tokens | 6,746 (4 tasks) | none (no thinking channel) |
| VRAM | ~2.4 GB loaded | 1.4 GB (100% GPU) |

## Conclusion

LIGHT-tier execution is verified end-to-end on the real local model: correct
tier/model selection, model separation, no qwen3:4b involvement, FAST
determinism, and a large latency/VRAM improvement over the qwen3:4b LIGHT
baseline.

# Phase5_Final_Release_Audit.md

> **Source:** Phase5_Final_Release_Audit.md

---

# PHASE 5 FINAL RELEASE AUDIT — FULL-SYSTEM HOSTILE AUDIT

**Target:** `chronos_engine` + `opentime` (backend), Next.js chat/web app (frontend), `docker-compose.yml`
**Mode:** READ-ONLY. Zero code changes, zero commits, zero Phase 6 work.
**Run by:** opencode · **Date:** 2026-09-01

---

## 1. Executive Summary

The system is functionally complete, well-architected in places, and the entire Phase 5 accessibility/AI-integrity work is committed with a clean tree and a green verification suite. However, the hostile audit found **one P1 (fabrication of a human user's data, presented indistinguishably as real)** and a **P2 cluster around data visibility, secret handling, and race conditions**.

The single most serious finding: when an account has never shared anything, three backend services **fabricate a complete founder persona** ("Founder / Architect", interests, goals, relationships, emotional tendency scores), plus **fake reflection insights** with invented confidence scores and fake reasoning traces, plus **invented behavioral patterns** — all labeled in the UI as observed "from what you've shared." A brand-new user sees the product confidently claiming they are "Founder / Architect of OpenTime" who "builds world-class platforms," and the root-cause system removes almost nothing when the user wipes their data (the fabrication regenerates).

Per the mandatory rubric, the presence of a P1 → **NOT RELEASE READY**.

---

## 2. Verdict

> ## NOT RELEASE READY
>
> **Blocking:** 1 x P1 (fabricated founder-persona seeding). Release is blocked until the seeding is removed (or gated behind an explicit opt-in "demo/sample data" flag that is visibly labeled, suppressible, and deleted on wipe).
>
> **Must also be fixed before GA (P2):** known-default JWT secret without fail-fast, unauthenticated `/uploads` media serving, the two-store divergence that makes My Data edits invisible to the dashboard's ChronOS surfaces, stuck-thinking race, silent-empty data wipe on transient errors, exposed `/seed` endpoint.
>
> **Everything else** (P3/P4 list) is non-blocking and can ship as follow-up backlog.

---

## 3. Scope, Method & Constraints

- **Scope:** all read paths (memories, timeline, identity, reflections, patterns, threads, ReturnLoop, interactions, insights, context assembly), all write paths (`/process`, `/seed`, my-data edits, deletion, export), authn/authz, storage adapters (in-memory + Mongo), the explainability leak-checker script itself, Docker/config, and the frontend state machine.
- **Method:** 5 parallel hostile subagent audits (storage/limits; API contract + frontend races; temporal/past-self/return-loop/insights; explainability/AI-failure/performance/a11y-mobile; deployment/tests/secrets/inventory) + direct source verification of every claimed severity finding by the auditor.
- **Constraints honored:** no source file modified (`git status` clean before and after); nothing committed; no Phase 6 work started.
- Subagent output was **adversarially re-checked**; one agent claim (InteractionRecord.user_id) proved false and was struck (see section 23).

---

## 4. Repository & Release Hygiene

- Branch working tree **clean**; latest commit `8945328 chronosPhase5E-F`.
- Full Phase-5 lineage present: `chronosPhase5E-F -> E -> D -> A -> C -> A_Audit -> 5D -> 5C -> 5A&5B -> 4L`, plus earlier phase history.
- Two backend virtualenvs coexist (`backend/.venv`, `backend/venv`) — hygiene smell, not a defect.
- **Secrets:** git grep across the tree found **no private keys or live API keys**; only `.env.example` / `backend/.env.example` are tracked. `.env`, `.pem`, logs, and build artifacts are absent from the repo. (PASS)

---

## 5. Verification Suite Results

| Check | Command | Result |
|---|---|---|
| Backend tests | `python -m pytest tests/ -q` | **662 passed, 4 skipped** |
| Lint (phase diff) | `ruff check src tests` | **0 new**; 929 pre-existing errors (baseline) |
| Frontend typecheck | `npx tsc --noEmit` | **clean (exit 0)** |
| Frontend build | `npx next build` | **green**, 8 static routes |
| Leak checker | `npm run check:leakage` | **PASS, 58 files scanned** |

All verifications pass. The 929 pre-existing ruff errors are a **Phase 1..4 inheritance**, not introduced by Phase 5 (confirmed 0 diff).

---

## 6. Severity Inventory — P0 / P1

### P1-1 — Fabricated founder persona, reflections & patterns presented as the user's own data (BLOCKER)

Three services seed hard-coded content the moment an account has none, with no marker and no consent:

- `backend/src/chronos_engine/identity/service.py:11-28` — `get_or_create_profile()` inserts a full **"Founder / Architect"** profile (`interests: ["AI Systems Architecture", ...]`, `goals: ["Build OpenTime into a world-class platform", ...]`, `relationships: {"OpenTime Team": "Founder / Architect"}`, values, `v1`). Reached on **every** `process_user_input` (`engine.py:272` evolve), `get_or_create` (~`engine.py:297`), and `GET /chronos/engine/identity` (~`engine.py:982`).
- `backend/src/chronos_engine/reflection/service.py:17+` — seeds fabricated insights when fewer than 2 memories ("You have become significantly more optimistic...", `confidence: 0.92`, plus **invented reasoning traces** like "Detected 35% increase in positive sentiment indicators" over data that does not exist).
- `backend/src/chronos_engine/patterns/service.py:15+` — seeds "Clean Architecture First" (`conf 0.95`) and "High-Output Deep Work Blocks" (`conf 0.90`) with **empty `supporting_memory_ids`** when no memories exist.

The frontend renders this **indistinguishably from real findings**: `IdentityModelCard.tsx` ("from what you've shared", "based on what you've shared"), `ReflectionEngineView.tsx` ("Changes ChronOS has noticed across what you've shared"), `PatternDetectionView.tsx` ("Recurring themes ChronOS has noticed in what you've shared").

Aggravators:

- **Contradicts the product's own wording**: `PatternDetectionView` empty state promises "Nothing is assumed up front — patterns come only from what you actually share." The backend seeds patterns for the same users that message would target.
- **Deletion is ineffective**: `engine.delete_memory` purges memories, but `get_or_create_profile` then **regenerates the founder profile** — the fabrication is effectively undeletable.
- The two P3s in section 8 (S3 transport of reasoning traces, I3 dead empty-states) are consequences of this design.

Classification rationale: rubric P1 explicitly covers fabricated output presented as real user/derived data; this is fabrication of a **human's biography** with no opt-in.

### P2-1 — Known-default JWT secret with no fail-fast guard

- `backend/src/opentime/infrastructure/config.py:38` defaults `JWT_SECRET_KEY` to `"change-me-in-production-use-a-long-random-string"`.
- `docker-compose.yml:70` hardcodes `JWT_SECRET_KEY: dev-secret-change-in-production` in the shipped deployment artifact.
- No startup check rejects the known default. If the compose artifact is deployed unchanged, token forgery/account takeover is trivial (access 15 min, refresh 7 d).

Not raised to P1 because bypass requires the **operator** to deploy the default; classified P2 (config-level) with strong GA gate.

---

## 7. Severity Inventory — P2 (Medium)

| ID | Finding | Location |
|---|---|---|
| **P2-1** | Known-default JWT secret; no fail-fast (see section 6) | `config.py:38`, `docker-compose.yml:70` |
| **P2-2** | `/uploads` static mount with **no auth dependency** — all user media served to anyone who can guess `{user_id}/{name}`. Mitigated: IDs are UUIDs, filenames sanitized, no enumeration. Still violates media-is-private expectations | `backend/src/opentime/main.py:59-62` |
| **P2-3** | **Two-store divergence**: My Data + onboarding use domain collections (`memories`, `identity_states`, `patterns`, `goals`, `analysis_preferences`, `timeline_events`, `chronos_states`); Dashboard ChronOS surfaces use `engine_*` collections. Edits to my identity/traits/genesis (`PATCH /chronos/identity/traits`, `/genesis`, `/preferences`, `/goals`) are **never reflected** in the dashboard's identity/patterns/insights — and the dashboard may instead show the fabricated founder profile | `chronos_state.py` vs `engine router.py` + `mongo_repository.py` |
| **P2-4** | **Stuck-thinking race**: `VoiceVideoRecorder` fires `onThinkingStart`; switching tabs unmounts it; the resolved fetch hits `if (!isMountedRef.current) return` -> `onResponseReceived`/`onThinkingEnd` skipped -> dashboard `isThinking` stays true until reload | `VoiceVideoRecorder.tsx:~269`, `dashboard/page.tsx:299-337` |
| **P2-5** | **Silent-empty data wipe**: `reqNoThrow` returns `[]` on ANY error (including 401, network, 5xx). Lazy tabs set `loadedTabs` *before* the fetch resolves, so a transient failure renders "no data" permanently with no retry | `chronosApi.ts:32-38`, `dashboard/page.tsx` loadedTabs |
| **P2-6** | **Live `/seed` endpoint**: `POST /chronos/engine/seed` writes 4 hard-coded memories through the real pipeline (`mem_` ids, no marker, no warning) | `router.py:588-592`, `engine.py:990-1004` |
| **P2-7** | `500` handler returns `str(e)` (raw exception/abs-path leakage toward client) | `router.py:284` |
| **P2-8** | Right-to-be-forgotten incomplete: domain collections (`memories`, `identity_states`, `goals`, `patterns`, `analysis_preferences`) are **not in any engine wipe path**; a user who used My Data leaves trails behind. Additionally, after a full wipe, `get_or_create_profile` regenerates the fabricated founder profile — the fabrication is undeletable | `router.py:649-661`, `engine.py:949-959`, `identity/service.py:11-28` |

---

## 8. Severity Inventory — P3 (Low) & P4 (Info)

### P3 (bug class, fixable in follow-up)

| ID | Finding | Location |
|---|---|---|
| P3-1 | `purge_memory_references()` bumps `updated_at` in-memory but **not** in Mongo — parity drift | `storage/repository.py:286-288` vs `storage/mongo_repository.py:322-343` |
| P3-2 | `/process` response body transports the **entire `prompt_context`** (system prompt, user prompt, retrieved memory context) and provider `raw_llm_response` + `reasoning_trace` (with `confidence_score`, `supporting_memory_ids`) to the browser; the leak-checker guards **rendering only, not transport** | `router.py` EngineErrorResponse model, `chronosApi.ts:279-298` |
| P3-3 | `GET /chronos/engine/providers` is **unauthenticated** and discloses `_active_provider_key` | `router.py:372-377` |
| P3-4 | Threads list = **N+1 queries** (1 + n per thread timeline); benign at personal scale | `router.py:447-451` |
| P3-5 | Every user message rebuilds the **entire timeline snapshot** (`timeline/service.py:12`) — unbounded read that grows with account history | `engine.py:271` -> TimelineService |
| P3-6 | Delete drives full recompute of descendants on next message only; identity/stories/timeline stay **stale** until then | `engine.py:949-959` + recompute path |
| P3-7 | `get_candidate_threads` limit fallback to 25 — latent; no caller passes <=0 today | `router.py` / threads service |
| P3-8 | Interactions responses include `provider_name`, `model_name`, `processing_time_ms` over the API (not rendered; transport-only exposure) | interactions serializer (`router.py:390-407`) |

### P4 (hygiene / dead code / notes)

- `InteractionRecord.genesis()` unused (`chronosApi.ts:176-186`); `buildMemoryContext(_limit)` unused; unused model imports in `MemoryPromptTemplate`/`Temporal` templates — all confirmed by subagent + tsc would flag usage only.
- Type drift: `EngineResponse` type omits `raw_llm_response`/`prompt_context` it can actually receive.
- `ReflectionEngineView`/`PatternDetectionView` empty states ("Reflections build as you share...") can never appear post-seeding — dead messaging (consequence of P1-1).
- Leak-checker blind spots — see section 18.

---

## 9. Backend API Security

- **Authz is sound.** `get_current_user` (`dependencies.py`): HTTPBearer -> `decode_access_token` -> `sub` must parse as UUID -> DB load. All engine endpoints bind `current_user.id`; `_resolve_active_thread` enforces thread ownership (`router.py:180-187`). No query/body/path `user_id` is trusted by read/write engine endpoints.
- Cross-user isolation verified by inspection on every engine read path (memory/timeline/identity/reflection/pattern/thread/return-ledger all query by `user_id`).
- **Leaks outside the auth wall:** `/uploads` files (P2-2) and `/chronos/engine/providers` (P3-3) have no auth dependency.
- `POST /seed` is authenticated but live (P2-6).

---

## 10. Authentication & Token Handling

- Token envelope: access 15 min + rotating refresh 7 d; refresh rotates on each API auto-refresh (PASS).
- **Frontend storage:** tokens live in `localStorage` (`opentime_tokens`) — XSS-exfiltration surface; acceptable for near-zero-risk context but flagged.
- **Refresh asymmetry:** only `lib/api.ts` auto-refreshes on 401. `chronosApi.ts`, `myDataApi.ts`, `onboardingApi.ts` do not — a 401 in those layers yields generic errors (already absorbs into P2-5 empty-wipe; P3 note for the generic-error UX on process).

---

## 11. Fabricated Founder Data Seeding (Truthfulness) — deep dive

See P1-1. Escalation matrix across the product's three "insight" tabs:

| Surface | Real backfill intent | Actual seeded result | Rendered as |
|---|---|---|---|
| Identity | derived from memories | Founder/Architect profile | "How ChronOS sees you — from what you've shared" |
| Reflections | only with >=2 memories | fake optimism insight, conf 0.92, fake trace | "Changes ChronOS has noticed across what you've shared" |
| Patterns | only with >=1 memory | 2 invented patterns, conf 0.95/0.90, no grounding | "Recurring themes ChronOS has noticed in what you've shared" |

Impact: a brand-new user is shown a confident, specific, fabricative account of their own personality and history with **no visual, textual, or consent signal** that it is sample/synthetic data. This is the release blocker.

---

## 12. Data Control: Delete / Export / Right-to-be-Forgotten

- `DELETE /chronos/engine` (`router.py:649-661`) -> `delete_all_user_data` wipes engine memories, timeline, threads, events, snapshots, return ledger, identity, reflections, patterns (per `mongo_repository.py:201-206`, `382-390`) — engine-side complete (PASS).
- **But:** domain collections (`memories`, `identity_states`, `goals`, `patterns`, `analysis_preferences`, `chronos_states`) are **NOT in any engine wipe path** — a user who used My Data leaves trails behind. Unverified for a hypothetical user-service-level delete; noted as "verification gap" (P2-8).
- **Re-seeding:** after a full wipe, next engine identity read **re-creates the fabricated founder profile** (P1-1). A user who wiped "everything" is immediately re-fabricated.
- **Export** (`router.py:596-646`): excludes `prompt_context`/raw internals — export is **clean** (memory/timeline/identity/reflection/pattern/thread/return-ledger only) (PASS).

---

## 13. Two-Store Split: My Data vs Dashboard Surfaces

Confirmed two independent Mongo collection families in one database:

```
Domain (opentime)           Engine (chronos_engine)
-------------------         ----------------------
memories                    engine_memories
timeline_events             engine_timeline
identity_states             engine_identity
patterns                    engine_patterns
(unknown for reflections)   engine_reflections
goals                       (no engine analog)
analysis_preferences        (no engine analog)
chronos_states              engine_interactions
                            engine_temporal_*
                            engine_return_ledgers
```

- **My Data** (`/my-data` UI) reads/writes **domain** only (`myDataApi` -> `chronos_state.py`). **Dashboard** ChronOS tabs read/write **engine** only (`chronosApi` -> engine router).
- Consequences: user edits to traits/genesis/preferences/goals **never reach** the identity/insights surfaces; a user's mental model ("I told ChronOS who I am") is silently violated.
- `POST /chronos/context` (ChronosContextBuilder) does assemble LLM context from domain repos, and `/process` context comes from engine — so prompt context and displayed insights can disagree as well.

**P2-3** is the finding; it is a design-debt/data-visibility defect, not a crash.

---

## 14. Frontend Race & State Conditions

Verified race inventory (all reproduced by code-path reading):

1. **Stuck thinking** (P2-4) — unmount during in-flight process -> permanent thinking bubble until reload.
2. **Empty-wipe on transient error** (P2-5) — `reqNoThrow->[]` + pre-marked `loadedTabs` -> blank tab that looks like "no data"; no retry affordance.
3. **Stale identity** (P3-6) — unsequenced async refreshes can interleave; self-heals on next cycle.
4. **Stale Stories/Timeline** (P3-6) — after memory delete, dependent views refresh only on next message.
5. **MyData post-delete stale rows** (P3, minor).

No P0/P1 crash-level races found; no memory-leak/fetch-loop issues.

---

## 15. Storage Map & Persistence Gaps

- In-memory adapter is complete for the full engine model; Mongo mirror is **feature-complete** — every engine entity has a Mongo write path (replace_one upsert-insert pattern) (PASS).
- **Gap:** `purge_memory_references.updated_at` parity (P3-1).
- **Gap:** no failover/consistency check between the two adapters at runtime (single-adapter per deployment, so latent).
- All Mongo writes keyed by `user_id`; every `replace_one` uses composite `{user_id, _id}` — no cross-user overwrite hazard found.

---

## 16. Temporal / PastSelf / ReturnLoop / Insights

- `engine_temporal_threads`, `engine_temporal_events`, `engine_temporal_snapshots`, `engine_return_ledgers` — full write/read/delete coverage verified structurally.
- ReturnLoop open-thread fallback (`limit<=0 -> 25`), thread resolution, and the chronos-api triggered query all verified sound.
- Remaining-loop threads computed, no user-boundary leaks.
- **No finding beyond P3-7/P3-4 N+1** and the generic delete-staleness (P3-6). The Temporal UI (map + PastSelf card + ReturnLoop panel) renders only aggregated public fields — no internal identifiers/traces rendered (PASS).

---

## 17. Explainability & Prompt-Leakage Checker

- `npm run check:leakage` **PASS (58 files)**: no `engine_`/`mem_`/`tevent_`/`thread_`/`resp_`/`evidence_`/`state_` id-literal prefixes, no `model_name`/`prompt`/`confidence_score`/`supporting_memory_ids` renders, no "mongo"/"embedding"/"system prompt" strings in UI, no inline `matchMedia`/`prefers-reduced-motion`/raw `fetch` bypasses. Comment-stripped scan catches comment-only leaks too.
- **Blind spots (documented, not blockers):**
  1. `SKIP_IDENTIFIER_SCAN` exempts `lib/chronosApi.ts` and `lib/explainability.ts` — precisely the modules that define the client-bound response shapes.
  2. Static scan cannot catch **transport-level** exposure: `raw_llm_response`, full `prompt_context` (incl. system prompt + retrieved memory content), and reasoning traces with confidence scores are delivered to the browser in every `/process` body (P3-2) yet never flagged.
  3. `.next` build output and SSR payloads not scanned (sourced from same files, so low risk).
  4. Dynamically assembled strings at runtime are unscannable by design.

---

## 18. AI Failure Handling & Performance

- Timeouts on context build (10 s) + message (60 s); validation-blocked on completion + on tokens consumed (PASS).
- Graceful temp-failure paths when `/process` body is partially formed; N routes covered by tests (PASS).
- **Performance:** timeline full rebuild per message (P3-5), threads N+1 (P3-4), identity/reflection/pattern recompute on message — linear-growth cost; acceptable for a personal-scale app, tracked as P3 debt.
- No unbounded loop/recursion/animation hazards found; no runaway client retry.

---

## 19. Accessibility & Mobile

Carried forward from the Phase 5E-F report (verified then): all dialogs keyboard-closeable, landmark count green, reduced-motion respected, large touch targets, `aria` labels on all map/recorder/dialog controls, no focus traps. HTMLLandmarkCheck, semantics walk, mobile viewport, and `prefers-reduced-motion` walk all **PASS**. Leak-checker a11y scan PASS.

**No new findings** in this audit.

---

## 20. Deployment, Config & Secrets

- compose artifact runs backend with bind-mount + reload runner + **dev secret** (P2-1) — unsuitable for prod as-shipped.
- CORS/origins: verified local-restricted; cookies not used (bearer localStorage) (PASS).
- `.env.example` files only; no `.env` committed (PASS).
- No CI pipeline visible in repo; lint baseline backlog (929) means `ruff check` cannot gate releases today (note, not a defect).

---

## 21. Test Quality & Coverage

| Area | Status |
|---|---|
| Backend suite | 662 pass / 4 skip — strong for read/write paths, thread lifecycle, rejection paths, engine+API via in-memory adapters |
| **`MongoStorageAdapter`** | **ZERO direct tests** (only `MongoTemporalStore` covered via mongomock); upsert/delete/parity cases run only against in-memory |
| **Auth tests** | **ZERO** — no `get_current_user` unit tests, no cross-user isolation integration tests |
| **Deletion-completeness** | **ZERO** — no test asserts post-wipe emptiness/re-seeding behavior (would have caught P1-1 regenerate) |
| **Frontend tests** | **NONE** — `package.json` has no test runner; race findings (P2-4/P2-5) untested |
| Static | `tsc` clean; ruff 929 pre-existing |

---

## 22. Blocked Items, Corrections & Final Ledger

**Unverifiable / blocked:**

- Runner env (& `opentime-anthropic/opentime.goals` backing via go test 4.13) — attempted, not available.
- Actual `.env` presence in a real deploy — intentionally never present in repo.
- Mongo parity behavior under concurrent multiuser load — untested infra, out of credential scope.

**Corrected subagent claim:** an agent reported frontend `InteractionRecord.user_id` mis-typed/leaky — **FALSE**. `chronosApi.ts:265` is `user_content`; the type carries no `user_id`. Struck from ledger.

**Final severity ledger:**

- **P0:** 0
- **P1:** 1 (fabricated founder persona/reflections/patterns — P1-1)
- **P2:** 8 (P2-1 through P2-8 incl. two-store divergence, media serving, races, seed, exception leakage, rtbf gap)
- **P3:** 8 (parity, transport, providers endpoint, N+1, timeline rebuild, staleness, limit alias, interaction fields)
- **P4:** 4 (dead code, type drift, dead empty-states, checker blind spots)

**Release decision:** **NOT RELEASE READY** — blocked solely by P1-1. Recommended unblock path (for a future, explicitly-authorized change phase — **not performed here**): gate seeding behind an explicit opt-in sample-data flag, visibly label it, exclude it from delete-surviving regeneration, and wire P2-1/P2-3/P2-4/P2-5/P2-6 before GA.

---

*Audit complete. No files changed, nothing committed, Phase 6 not started. The next step requires your direction (e.g., authorize fix commits for the P1/P2 set, or deploy-with-blockers).*


# chronos-plans.md

> **Source:** chronos-plans.md

---

# ChronOS Engine — Implementation Plan

## 0. Purpose

ChronOS should become a **fast personal reasoning engine**, not merely a memory layer or an LLM wrapper.

The engine must work in two modes:

1. **Deterministic / AI-off mode**
   - ChronOS must still produce a useful result.
   - It should infer a cautious description of the user's apparent emotional state, intent, context, relevant memories, patterns, and an internal engine assessment.
   - It must never pretend that an inferred emotion is a fact.

2. **AI-assisted mode**
   - A local LLM should be used only where language understanding, nuanced interpretation, or deeper reasoning is actually useful.
   - The engine controls the reasoning procedure.
   - The LLM is a reasoning component inside ChronOS, not the entire engine.

The existing architecture already has memory, timeline, identity, retrieval, patterns, reflections, providers, validation, and explainability. The next phase should therefore **extend the existing architecture rather than replace it**.

---

# 1. Current ChronOS Baseline

The current pipeline is:

```text
Input
  ↓
Media Processing
  ↓
Memory
  ↓
Timeline
  ↓
Identity
  ↓
Retrieval
  ↓
Prompt Orchestration
  ↓
LLM
  ↓
Validation
  ↓
Reasoning Trace
  ↓
Response
```

This is already a strong foundation.

Current limitations that matter most for the next phase:

- Sentiment is currently keyword-based.
- Life-phase detection is currently keyword-based.
- Identity evolution is currently keyword-based.
- Pattern detection covers only a small number of patterns.
- Reflection generation is heuristic.
- The Ollama provider is currently simulated rather than a real local model call.
- The validator does not yet perform real contradiction detection.
- The reasoning trace describes the pipeline but is not yet a genuine structured reasoning state.
- The engine does not yet have a formal decision/workflow layer.
- There is no explicit deterministic "ChronOS interpretation" produced before an LLM is called.
- There is no fast routing layer deciding whether a request actually needs an LLM.

These are the primary areas to build next.

---

# 2. New Core Concept: ChronOS Reasoning Cycle

Add a formal reasoning cycle between input processing/retrieval and final response.

```text
USER INPUT
   ↓
1. NORMALIZE
   ↓
2. UNDERSTAND
   ↓
3. RETRIEVE CONTEXT
   ↓
4. DETECT USER STATE
   ↓
5. DETECT INTENT
   ↓
6. DETECT PATTERNS
   ↓
7. APPLY RULES
   ↓
8. BUILD CHRONOS STATE
   ↓
9. DECIDE IF AI IS NEEDED
   ↓
10. OPTIONAL LOCAL AI REASONING
   ↓
11. VALIDATE
   ↓
12. GENERATE FINAL RESPONSE
   ↓
13. WRITE BACK TO MEMORY
```

This becomes the canonical ChronOS processing procedure.

---

# 3. Step 1 — Input Normalization

Keep the existing `MediaProcessor`, but make its output more useful.

For every input, produce:

```json
{
  "content": "...",
  "input_type": "text",
  "timestamp": "...",
  "source": "user",
  "language": "...",
  "metadata": {}
}
```

For future audio/video:

```text
Audio
 ↓
Transcription
 ↓
Normalized text
 ↓
Same ChronOS pipeline
```

Do not create separate reasoning systems for text, audio, and video.

All modalities should eventually converge into the same normalized input representation.

---

# 4. Step 2 — User Intent Detection

Add an `IntentDetector`.

The detector should identify what the user is trying to accomplish.

Start with a manageable intent taxonomy:

```text
QUESTION
REQUEST
DECISION
PLANNING
REFLECTION
EMOTIONAL_SUPPORT
INFORMATION
CREATION
PROBLEM_SOLVING
STATUS_UPDATE
JOURNAL_ENTRY
COMMAND
UNKNOWN
```

The detector should return:

```json
{
  "intent": "DECISION",
  "confidence": 0.86,
  "signals": [
    "user asks whether they should do X"
  ]
}
```

This can initially be deterministic.

Later, a local LLM can improve intent detection.

---

# 5. Step 3 — User State Detection

Add a dedicated `UserStateDetector`.

Do not call this "emotion detection" only.

The state should describe multiple dimensions:

```json
{
  "emotional_state": {
    "label": "frustrated",
    "confidence": 0.72,
    "valence": -0.55
  },
  "energy": {
    "label": "low",
    "confidence": 0.64
  },
  "cognitive_state": {
    "label": "uncertain",
    "confidence": 0.78
  },
  "urgency": 0.61,
  "engagement": 0.84
}
```

Possible emotional labels:

```text
calm
positive
excited
confident
curious
neutral
uncertain
overwhelmed
frustrated
anxious
sad
tired
angry
motivated
focused
```

Important:

ChronOS must say:

> "The input suggests frustration."

Not:

> "The user is frustrated."

The engine is making an inference, not diagnosing a fact.

---

# 6. Deterministic Emotional Signal Engine

The first implementation must work **without AI**.

Expand the existing sentiment lexicon into weighted signals.

Example:

```text
"stuck"       → frustration +0.35
"annoying"    → frustration +0.40
"excited"     → excitement +0.45
"love"        → positive +0.30
"confused"    → uncertainty +0.35
"don't know"  → uncertainty +0.30
"exhausted"   → fatigue +0.45
"can't"       → difficulty +0.20
"finally"     → relief +0.30
```

Also detect:

- repetition
- punctuation intensity
- question density
- negative/positive language
- self-references
- urgency words
- uncertainty words
- action-oriented language
- changes compared with previous interactions

Do not make this a medical or psychological diagnosis system.

It is an **interaction-state inference system**.

---

# 7. Step 4 — Context Retrieval

Keep the existing RetrievalEngine.

Improve it to rank context using multiple signals:

```text
semantic similarity
+
recency
+
importance
+
same topic
+
same goal
+
same life phase
+
same pattern
```

Do not retrieve memories only because they contain similar words.

The ideal ranking should answer:

> "Which previous information would actually change the current response?"

Add a `relevance_score` explaining why each memory was retrieved.

---

# 8. Step 5 — Goal Detection

ChronOS already stores goals, but it should distinguish:

```text
ACTIVE GOAL
COMPLETED GOAL
ABANDONED GOAL
BLOCKED GOAL
POSSIBLE GOAL
LONG-TERM GOAL
SHORT-TERM GOAL
```

For every new input, determine whether it:

- introduces a goal
- updates a goal
- progresses a goal
- conflicts with a goal
- completes a goal
- abandons a goal

This will make ChronOS much more useful for decisions and planning.

---

# 9. Step 6 — Pattern Detection

Expand `PatternDetector`.

The existing enum already provides the foundation.

Implement detectors for:

```text
HABIT
RECURRING_PROBLEM
REPEATED_SUCCESS
BEHAVIOR_LOOP
PRODUCTIVITY_TREND
MOOD_SHIFT
DECISION_CHANGE
```

Every pattern should have:

```json
{
  "title": "...",
  "description": "...",
  "confidence": 0.81,
  "frequency": "...",
  "supporting_memory_ids": []
}
```

Never create a strong pattern from one isolated interaction.

Use a minimum evidence threshold.

---

# 10. Step 7 — Contradiction Detection

Add a `ConsistencyEngine`.

ChronOS should check:

```text
Current input
      ↓
Current identity
      ↓
Current goals
      ↓
Past memories
      ↓
Known preferences
```

Look for contradictions such as:

```text
"I don't want X anymore."

Previous:
"X is my main goal."
```

Return:

```json
{
  "contradiction_detected": true,
  "type": "GOAL_CHANGE",
  "previous": "...",
  "current": "...",
  "confidence": 0.91
}
```

This is more important than the current validator's simple grounding check.

---

# 11. Step 8 — ChronOS State

This is the most important new component.

Create:

```text
chronos/state/
```

or an equivalent module.

Define a `ChronosState` object representing what ChronOS currently understands.

Example:

```json
{
  "user_state": {
    "emotional_signal": "frustrated",
    "cognitive_signal": "uncertain",
    "energy_signal": "medium",
    "urgency": 0.72
  },

  "intent": {
    "type": "PROBLEM_SOLVING",
    "confidence": 0.91
  },

  "context": {
    "life_phase": "...",
    "active_goals": [],
    "relevant_memories": [],
    "patterns": []
  },

  "changes": [],
  "contradictions": [],
  "recommended_action": "...",

  "engine_state": {
    "status": "concerned",
    "confidence": 0.79,
    "reason": "The current input conflicts with an active goal and contains repeated frustration signals."
  }
}
```

This state must exist **even when no AI is available**.

---

# 12. "What Is the User Feeling?" Output

Every processed request should have a deterministic human-readable interpretation.

Example:

```text
ChronOS Interpretation

You appear to be somewhat frustrated and uncertain about the current situation.
The strongest signal is repeated problem-focused language combined with uncertainty.

ChronOS also noticed that this is related to your current goal of finishing the
project and resembles a problem pattern seen in previous interactions.
```

The wording can be generated from templates.

Do not require an LLM.

---

# 13. "What Is ChronOS Feeling?" Output

ChronOS does not actually have emotions.

Therefore do not represent this as literal machine emotion.

Instead create an `engine_state`.

Example:

```text
ChronOS State

I am moderately concerned about this situation because the current input conflicts
with a previously stated goal.

Confidence: 79%
Context strength: High
Historical relevance: High
Actionability: Medium
```

The UI may visually present this as:

```text
ChronOS feels:
🟡 Concerned
```

but internally it should be:

```json
{
  "engine_state": "CONCERNED",
  "confidence": 0.79
}
```

Possible engine states:

```text
NEUTRAL
CURIOUS
CONFIDENT
CAUTIOUS
CONCERNED
UNCERTAIN
ALERT
POSITIVE
FOCUSED
WAITING_FOR_CONTEXT
```

These are **operational states**, not claims of consciousness.

---

# 14. Deterministic Response Generator

Add a fallback response generator.

It should work if:

```text
Ollama is offline
AND
no API key exists
AND
no external LLM exists
```

The engine should still return:

```text
User signal:
You appear frustrated and uncertain.

What ChronOS understands:
This is related to your active project goal.

What ChronOS noticed:
You have encountered a similar problem before.

ChronOS state:
Cautious — historical context suggests this may become a recurring blocker.

Suggested next step:
Clarify the blocking issue before making a decision.
```

This is the **minimum viable intelligence** of ChronOS.

---

# 15. AI Routing Layer

Add:

```text
AIRouter
```

Its job is NOT to answer the user.

Its job is to decide:

> "Does this request need an LLM?"

Example:

```text
Simple factual transformation
        ↓
NO AI
        ↓
Rules

Ambiguous request
        ↓
LOCAL AI

Complex personal reasoning
        ↓
LOCAL AI

Simple status update
        ↓
NO AI
```

Return:

```json
{
  "requires_ai": true,
  "reason": "Ambiguous intent and nuanced personal interpretation required.",
  "complexity": "medium",
  "preferred_provider": "ollama"
}
```

This is essential for speed.

---

# 16. Local AI Provider

The existing Ollama provider must become a real provider instead of a simulated response.

Implement:

```text
ChronOS
  ↓
Ollama Provider
  ↓
Local Model
```

The provider should be configurable:

```text
OLLAMA_BASE_URL
OLLAMA_MODEL
OLLAMA_TIMEOUT
```

Recommended initial model target:

```text
Qwen3 4B
```

Allow the model to be changed without changing ChronOS.

---

# 17. AI Should Follow the ChronOS Procedure

Do not send the raw user input directly to the model.

Send:

```text
CHRONOS STATE
+
RELEVANT MEMORY
+
GOALS
+
PATTERNS
+
CURRENT INPUT
+
REASONING TASK
```

The AI should be instructed to perform only the reasoning task assigned by ChronOS.

Example:

```text
You are the reasoning module inside ChronOS.

ChronOS has already:
1. normalized the input
2. detected intent
3. retrieved context
4. detected user state
5. identified goals
6. detected patterns
7. checked contradictions

Your task:
Interpret the supplied ChronOS state and produce a concise response.

Do not invent memories.
Do not override deterministic facts.
Do not claim certainty about inferred emotions.
```

This keeps the engine in control.

---

# 18. AI Reasoning Modes

Create explicit AI modes:

```text
NONE
CLASSIFY
INTERPRET
REASON
REFLECT
GENERATE
```

Examples:

```text
Intent unclear
→ CLASSIFY

User state nuanced
→ INTERPRET

Decision involving multiple goals
→ REASON

Past-vs-present analysis
→ REFLECT

Natural-language final response
→ GENERATE
```

Do not use the most expensive reasoning mode for every request.

---

# 19. Fast Path vs Deep Path

Create two execution paths.

## Fast Path

```text
Input
 ↓
Intent
 ↓
User state
 ↓
Retrieve context
 ↓
Rules
 ↓
ChronOS State
 ↓
Template response
```

Target:

```text
very low latency
```

No LLM required.

## Deep Path

```text
Input
 ↓
Intent
 ↓
User state
 ↓
Retrieve context
 ↓
Rules
 ↓
ChronOS State
 ↓
AI Router
 ↓
Local LLM
 ↓
Validator
 ↓
Response
```

Only use this when required.

---

# 20. Improved Reasoning Trace

The current trace should evolve from a fixed five-step description into an actual execution trace.

Example:

```json
{
  "steps": [
    {
      "step": "INPUT_ANALYSIS",
      "result": "Problem-solving request",
      "confidence": 0.91
    },
    {
      "step": "USER_STATE",
      "result": "Frustration + uncertainty",
      "confidence": 0.76
    },
    {
      "step": "CONTEXT",
      "result": "3 relevant memories found"
    },
    {
      "step": "PATTERN",
      "result": "Recurring project blocker detected",
      "confidence": 0.83
    },
    {
      "step": "DECISION",
      "result": "Local AI reasoning required"
    }
  ]
}
```

The trace should describe **what ChronOS actually did**, not expose hidden chain-of-thought.

---

# 21. Improved Validation

Replace the current hard-coded personalization score.

Create real metrics:

```text
context_relevance
memory_relevance
goal_alignment
contradiction_score
pattern_support
response_grounding
```

Then calculate:

```text
overall_confidence
```

from those signals.

Never return a hard-coded `0.96`.

---

# 22. Memory Improvements

Keep the current memory system, but add:

```text
memory importance
memory confidence
memory source
memory topic
memory goal association
memory emotional signal
memory life phase
```

Also make embeddings stable across restarts.

The current Python `hash()` embedding approach is intentionally lightweight but is not stable between processes.

Eventually replace it with a real local embedding model.

---

# 23. Memory Write Policy

Not every interaction should become equally important long-term memory.

Classify memories:

```text
EPHEMERAL
SHORT_TERM
IMPORTANT
LONG_TERM
IDENTITY_RELEVANT
GOAL_RELEVANT
```

Example:

```text
"what time is it?"
→ EPHEMERAL

"I want to build ChronOS into a personal reasoning engine."
→ GOAL_RELEVANT + LONG_TERM

"I hate working with this framework."
→ PREFERENCE_RELEVANT
```

This will prevent memory pollution.

---

# 24. Identity Evolution

Keep the existing IdentityModel but make updates evidence-based.

Instead of:

```text
contains "want to"
→ add goal
```

use:

```text
GoalDetector
+
confidence
+
existing goals
+
contradiction check
→ identity update
```

Every identity change should record:

```json
{
  "field": "goals",
  "change": "added",
  "value": "...",
  "confidence": 0.88,
  "supporting_memory_ids": []
}
```

This creates an auditable identity history.

---

# 25. Reflection Engine

Keep reflections but change them from simple keyword checks toward:

```text
Past state
+
Current state
+
Goal changes
+
Pattern changes
+
Emotional signal changes
=
Reflection
```

Example:

```text
Earlier:
User was exploring whether to build the system.

Now:
User is actively defining the architecture.

ChronOS reflection:
The user's relationship with the project appears to have shifted
from exploration toward active execution.
```

This can initially be deterministic.

Later, the local LLM can make the language more nuanced.

---

# 26. Output Contract

Every ChronOS response should expose a stable structure.

Recommended:

```json
{
  "response": "...",

  "chronos_interpretation": {
    "user_state": "...",
    "intent": "...",
    "summary": "..."
  },

  "chronos_state": {
    "status": "...",
    "confidence": 0.0,
    "reason": "..."
  },

  "context": {
    "memories_used": [],
    "goals_used": [],
    "patterns_used": [],
    "timeline_events_used": []
  },

  "reasoning": {
    "path": "FAST|DEEP",
    "ai_used": false,
    "steps": []
  },

  "performance": {
    "processing_time_ms": 0
  }
}
```

The frontend should be able to render this independently of whether AI was used.

---

# 27. Recommended Final User-Facing Output

The UI should eventually be able to show something like:

```text
┌─────────────────────────────────────────┐
│ ChronOS                                  │
│                                          │
│ User signal                              │
│ You appear somewhat frustrated and       │
│ uncertain about this situation.          │
│                                          │
│ What I understand                        │
│ You're trying to solve a recurring       │
│ problem related to your current goal.    │
│                                          │
│ ChronOS state                            │
│ 🟡 Cautious                              │
│                                          │
│ This appears related to a previous       │
│ pattern, so I am treating it as more     │
│ significant than an isolated issue.     │
│                                          │
│ AI reasoning                             │
│ Not required                             │
│                                          │
│ Confidence                               │
│ 82%                                      │
└─────────────────────────────────────────┘
```

This should work **without an LLM**.

With AI enabled, the same structure can contain a richer interpretation.

---

# 28. Build Order

Implement in this order.

## Phase 1 — Core deterministic intelligence

- [ ] Create `ChronosState`.
- [ ] Create `IntentDetector`.
- [ ] Create `UserStateDetector`.
- [ ] Create `GoalDetector`.
- [ ] Expand `PatternDetector`.
- [ ] Create `ConsistencyEngine`.
- [ ] Create deterministic `ResponseGenerator`.
- [ ] Produce user-state interpretation without AI.
- [ ] Produce operational ChronOS state without AI.
- [ ] Add structured output to `EngineResponse`.

## Phase 2 — Reasoning orchestration

- [ ] Create `AIRouter`.
- [ ] Create Fast Path.
- [ ] Create Deep Path.
- [ ] Replace fixed reasoning trace with execution trace.
- [ ] Add real confidence calculation.
- [ ] Add memory relevance scoring.
- [ ] Add goal alignment scoring.

## Phase 3 — Local AI

- [ ] Implement real Ollama HTTP client.
- [ ] Make model configurable.
- [ ] Add Qwen3 4B as the initial local model option.
- [ ] Add AI modes: CLASSIFY, INTERPRET, REASON, REFLECT, GENERATE.
- [ ] Give the model ChronOS State rather than raw unstructured context.
- [ ] Ensure AI cannot invent stored memories.
- [ ] Ensure deterministic facts take precedence over AI guesses.

## Phase 4 — Memory intelligence

- [ ] Replace unstable hash embeddings with stable local embeddings.
- [ ] Improve retrieval ranking.
- [ ] Add memory importance classification.
- [ ] Add memory confidence.
- [ ] Add topic/goal associations.
- [ ] Add memory consolidation.

## Phase 5 — Long-term intelligence

- [ ] Improve identity evolution.
- [ ] Improve reflection generation.
- [ ] Add historical pattern detection.
- [ ] Add goal progression tracking.
- [ ] Add meaningful contradiction detection.
- [ ] Add scheduled/background reflection processing.
- [ ] Add real transcription.

---

# 29. Non-Negotiable Design Principles

1. **ChronOS must work without AI.**

2. **AI must enhance ChronOS, not replace ChronOS.**

3. **Rules should handle deterministic facts.**

4. **LLMs should handle ambiguity, interpretation, and nuanced reasoning.**

5. **Never claim inferred emotions as objective facts.**

6. **Never invent memories, goals, preferences, or history.**

7. **Every important inference should have supporting evidence.**

8. **The engine should know when it does not know.**

9. **Fast requests should not unnecessarily invoke an LLM.**

10. **The output contract must remain stable regardless of provider.**

11. **The local model must be replaceable.**

12. **ChronOS should own the reasoning workflow; the LLM should execute assigned reasoning tasks.**

---

# 30. Definition of Done for the Next Major Version

ChronOS v2 is ready when this works:

```text
User input
    ↓
ChronOS understands the request
    ↓
ChronOS identifies the user's apparent state
    ↓
ChronOS retrieves relevant personal context
    ↓
ChronOS identifies goals and patterns
    ↓
ChronOS checks for contradictions
    ↓
ChronOS builds a structured ChronosState
    ↓
ChronOS decides whether AI is necessary
    ↓
If not necessary:
    deterministic response

If necessary:
    ChronosState → local LLM → validated response
    ↓
ChronOS writes meaningful information back to memory
    ↓
Frontend receives the same structured output
```

The most important test is:

> **Turn off every external LLM and Ollama. ChronOS should still be able to receive an input, understand basic intent, infer cautious user-state signals, retrieve context, identify patterns/goals, produce an operational ChronOS state, and return a useful human-readable response.**

Then turn on the local model.

The output should become **more nuanced**, not fundamentally functional.

That is the architecture that makes ChronOS an actual reasoning engine rather than an LLM wrapper.


# chronos_logic.md

> **Source:** chronos_logic.md

---

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


# phaseCheck.md

> **Source:** phaseCheck.md

---

# ChronOS Phase Check

## chronosPhase2F — Completed

Local LLM integration audited and benchmarked against the real runtime
(`qwen3:4b`, Ollama 0.20.5, RTX 3050 4GB):

- Deterministic routing (`AIRoutingResult`) works end-to-end: FAST path skips AI,
  DEEP path runs a single AI call with a `ReasoningPlan`.
- Structured output validation + safe fallback verified: parser/validator errors
  fall back to the deterministic response instead of failing the request.
- Baseline established at 240s timeout:
  - INTERPRET ~148s, eval 4004 tokens (~3819 thinking).
  - REASON ~102s, eval 3407 tokens (~3186 thinking).
  - REFLECT ~158s, eval 4160 tokens (~3916 thinking).
- `OLLAMA_TIMEOUT` was too low at the 60s default (all cases timed out); 240s is
  required, and budget-derived timeouts now protect larger output budgets.
- Runtime facts: thinking accounts for ~93-95% of generated tokens; the model
  template always emits the ` thinking` prefix, so thinking cannot be disabled
  (only channel-switched via the `think` field).

## chronosPhase2G — Completed

Controlled local inference for Qwen3 thinking, with the REASON/REFLECT
structured-output failures fixed:

- Root cause of REASON/REFLECT failures: the model emits evidence tags as
  `memory:mem_x` (no brackets); the strict bracketed regex rejected them as
  `HALLUCINATED_EVIDENCE`. Parser now normalizes bracketed/unbracketed tags
  while keeping the fabricated-evidence guardrail.
- New `InferenceOptions` model threads per-call knobs from the `ReasoningPlan`
  to the provider: `thinking_enabled`, `num_predict`, `num_ctx`, `temperature`.
- New `OllamaConfig` knobs: `thinking_enabled`, `mode_thinking_enabled`,
  `mode_num_predict`, `min_tokens_per_sec`, `timeout_margin` (all env-driven,
  defaults preserve prior behavior).
- Provider sends the supported `think` field and applies per-mode budgets;
  `_effective_timeout` raises the request timeout to
  `num_predict / min_tokens_per_sec + timeout_margin` so budgets are never
  silently cut off.
- Prompt directive added: the supplied CHRONOS STATE is the complete final
  analysis; the model must only perform the specific reasoning task.
- Verified on the real model: all three benchmark cases now succeed with no
  fallback (defaults and configured runs); the configured run applied
  `num_predict=4608` with `effective_timeout=490.8s` and `done_reason=stop`.
- Backend tests: 186 passed. Frontend typecheck (`tsc --noEmit`): clean.

## chronosPhase2H — Completed

Architecture + local model audit (inference policy). No model was installed and
no execution behavior changed:

- Local model audit: only `qwen3:4b` is installed (2.5 GB, Q4_K_M, 4.0B params,
  262144 context, thinking capability). It does NOT fit substantially better
  within 4 GB VRAM (observed ~82% GPU / 18% CPU offload), so it stays the DEEP
  model. No LIGHT model is available.
- New `ModelCapability` abstraction: honest per-model metadata (parameter
  count, quantization, estimated memory, context, JSON/thinking support, tier);
  unknown values stay `None`, never fabricated.
- New deterministic `InferencePolicy` (pure computation, never invokes a
  provider): FAST → NONE, INTERPRET/CLASSIFY/GENERATE → LIGHT when a suitable
  configured light model exists (`OLLAMA_LIGHT_MODEL`), REASON/REFLECT → DEEP,
  no light model → DEEP fallback with `light_requested=True`, AI disabled →
  NONE. Optional latency budget handled via `expected_latency_class`, never a
  latency promise.
- Light-model thresholds are configurable on `OllamaConfig`
  (`light_max_parameters`, `light_max_memory_gb`, `light_min_context`,
  `light_max_latency_seconds`, `available_vram_gb`).
- Additive `EngineResponse.inference_policy` records the decision; it is
  observational only — execution stays FAST → deterministic, DEEP → configured
  `qwen3:4b`. `ai_routing` / `ai_execution` fields unchanged.
- Backend tests: 206 passed (186 prior + 20 new policy tests). Frontend
  typecheck (`tsc --noEmit`): clean.

## chronosPhase2I — Completed

Research-only LIGHT-tier model selection. No model was installed and no
production component changed (engine, policy, executor, routing, validator,
state all untouched). A single isolated benchmark script was added.

### Baseline measurement (MEASURED — only installed model, `qwen3:4b`)

`backend/scripts/benchmark_light.py` (ruff-clean) runs the four LIGHT tasks
(A INTERPRET, B INTERPRET+GENERATE, C SIMPLE CLASSIFY, D CONTEXTUAL) directly
against Ollama `/api/chat` with `format: json` and the LIGHT contract
`{"answer", "uncertainties", "evidence_used"}`:

| task | latency | t/s | thinking (est tokens) | JSON |
| --- | ---: | ---: | ---: | --- |
| A.INTERPRET | 80.5s | 19.8 | 1,235 | ok |
| B.INTERPRET+GENERATE | 128.1s | 17.2 | 2,481 | ok |
| C.SIMPLE CLASSIFY | 89.0s | 16.5 | 1,622 | ok |
| D.CONTEXTUAL | 73.9s | 15.4 | 1,408 | ok |

- 6,746 thinking tokens across the four tasks; every task runs 73–128s,
  far above the 30s LIGHT budget.
- First token ~278ms but content arrives only after the long thinking phase.
- GPU: +2,358 MiB delta; `ollama ps` reports 3.6 GB loaded at a 33%/67%
  CPU/GPU split, leaving only ~453 MiB free. `qwen3:4b` nearly saturates the
  4 GB card (free VRAM measured ~2.7 GB with desktop overhead).
- JSON contract was satisfied 4/4, but the cost makes it unusable for LIGHT.

### Candidate table (DOCUMENTED from official Ollama library / model cards unless noted)

| model | params | size | ctx | thinking | policy-eligible (≤3.0B) | license |
| --- | ---: | ---: | ---: | --- | --- | --- |
| qwen2.5:0.5b | 0.49B | 398MB | 32K | no | yes | Apache-2.0 |
| qwen2.5:1.5b | 1.54B | 986MB | 32K | no | yes | Apache-2.0 |
| qwen2.5:3b | 3.09B | 1.9GB | 32K | no | no (>3.0) | Qwen |
| gemma3:1b | 1.0B | 815MB | 32K | no | yes | Gemma ToU |
| gemma3:270m | 0.27B | ~200MB (EST.) | 32K | no | yes | Gemma ToU |
| llama3.2:1b | 1.24B | 1.3GB | 128K | no | yes | Llama |
| llama3.2:3b | 3.21B | 2.0GB | 128K | no | no (>3.0) | Llama |
| gemma2:2b | 2.61B | 1.6GB | 8K | no | yes | Gemma ToU |
| qwen3:0.6b | 0.6B | 523MB | 40K | default ON (runtime risk) | yes | Apache-2.0 |
| qwen3:1.7b | 1.7B | 1.4GB | 40K | default ON (runtime risk) | yes | Apache-2.0 |
| phi4-mini | 3.8B | 2.5GB | 128K | no | no (>3.0) | MIT |
| gemma3:4b | 4.0B | ~2.5GB (EST.) | 128K | no | no (>3.0) | Gemma ToU |

Thinking note: `qwen3:0.6b/1.7b` use the same Qwen3 template family as the
installed `qwen3:4b`; on this runtime (Ollama 0.20.5) thinking cannot be truly
disabled (measured), so they inherit hidden-reasoning-token risk — a LIGHT-tier
disqualifier despite fitting VRAM.

Hardware fit (ESTIMATED VRAM on the ~2.7GB-free RTX 3050 Laptop): 0.5–1.9GB
models (qwen2.5 0.5b/1.5b, gemma3 1b, llama3.2 1b, gemma2 2b) fit fully on GPU
with headroom for KV cache; 2.2GB+ models (qwen2.5 3b, llama3.2 3b) fit but
tight; phi4-mini (~3.2GB) does NOT fit → CPU offload, and it is policy-
ineligible anyway.

### Decision matrix (12 ChronOS LIGHT criteria, 1–5 each; M=MEASURED, D=DOCUMENTED, E=ESTIMATED)

Criteria: 1 response validity, 2 JSON reliability, 3 evidence grounding,
4 hallucination resistance, 5 instruction following, 6 concept coverage,
7 conciseness, 8 no thinking tokens, 9 generation speed, 10 first-token latency,
11 VRAM fit, 12 low CPU-offload risk.

| model | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | total |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| qwen2.5:1.5b | 4 | 5 | 3 | 3 | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 4 | **48** |
| gemma3:1b | 4 | 4 | 3 | 3 | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 5 | **47** |
| llama3.2:1b | 4 | 4 | 3 | 3 | 4 | 3 | 4 | 5 | 4 | 4 | 4 | 4 | **45** |
| qwen2.5:0.5b | 3 | 4 | 2 | 2 | 3 | 3 | 4 | 5 | 5 | 5 | 5 | 5 | **44** |
| gemma2:2b | 4 | 4 | 3 | 3 | 4 | 4 | 4 | 5 | 3 | 3 | 4 | 4 | **43** |
| qwen3:0.6b | 3 | 4 | 3 | 3 | 3 | 3 | 2 | 1 | 3 | 2 | 5 | 5 | **34** |
| qwen3:1.7b | 3 | 4 | 3 | 3 | 4 | 4 | 2 | 1 | 3 | 2 | 4 | 4 | **33** |

Basis: JSON reliability from Qwen2.5's documented structured-output strength
(D) and Gemma/Llama general `format: json` support (D); speed/first-token/VRAM
from model-size scaling (E); thinking column from architecture (D) plus the
installed-runtime measurement on qwen3:4b (M). Scores 1–8 are quality signals
that still need on-device confirmation once a model is installed.

### Conclusion

- **Recommended ChronOS LIGHT model: `qwen2.5:1.5b`** (1.54B, ~986MB disk,
  ~1.2GB VRAM, 32K ctx, Apache-2.0). It fully fits the free VRAM with
  headroom, produces NO thinking tokens, has the best documented JSON /
  structured-output reliability (critical for the LIGHT contract), and its
  predicted per-task latency (~1–3s, ESTIMATED) is well inside the 30s LIGHT
  budget.
- Runner-up: `gemma3:1b` (smaller, slightly faster, Gemma ToU; slightly weaker
  documented JSON/structured-output behavior).
- Avoid for LIGHT on this runtime: `qwen3:0.6b/1.7b` (always-on thinking),
  `phi4-mini`/`qwen2.5:3b`/`llama3.2:3b`/`gemma3:4b` (exceed the 3.0B
  `light_max_parameters` policy threshold).
- OPTIONAL install command (documented, NOT executed, no model was installed):
  `ollama pull qwen2.5:1.5b` — then set `OLLAMA_LIGHT_MODEL=qwen2.5:1.5b`.
  The policy will pick it up automatically once installed; no code changes
  required.
- No models were installed and no production behavior changed during Phase 2I;
  the only artifact added is the isolated `backend/scripts/benchmark_light.py`.
- PHASE 2I COMPLETE.

## chronosPhase2J — Completed

LIGHT-model execution activated. The `InferencePolicy` decision now dictates
the actual model the `AIExecutor` calls — no model-selection logic is
duplicated in the executor. No model was installed automatically; execution
follows the configured models (`OLLAMA_LIGHT_MODEL`, `OLLAMA_MODEL`).

- Flow: `AIRouter -> ReasoningPlanner -> InferencePolicy -> AIExecutor ->
  selected provider/model -> Ollama`. The engine computes the decision and
  passes it to the executor, which resolves `(tier, provider, model)` solely
  from that decision (`_resolve_target`).
- FAST: policy `NONE`, executor never invoked, Ollama never called,
  deterministic response.
- LIGHT (INTERPRET / CLASSIFY / GENERATE-only plan): executes
  `OLLAMA_LIGHT_MODEL` (`qwen2.5:1.5b`); `qwen3:4b` is never called.
- DEEP (REASON / REFLECT): executes `OLLAMA_MODEL` (`qwen3:4b`); unchanged
  behavior.
- LIGHT failure (model unavailable / connection / timeout / validation) →
  honest deterministic fallback (`fallback_used=True`,
  `error_type=<typed name>`); the executor NEVER automatically escalates a
  LIGHT failure to DEEP, and the latency budget semantics are unchanged
  (a tight budget without a light model -> `NONE`).
- New LIGHT-specific inference knobs on `OllamaConfig`:
  `light_thinking_enabled` (default `False` — qwen2.5:1.5b has no thinking
  channel; LIGHT must not inherit qwen3:4b's thinking config) and
  `light_format_json` (default `False`; the global `format_json` default stays
  OFF per Phase 2G). `InferenceOptions` gained a `format_json` field so the
  LIGHT tier can opt in per-model without changing the global default.
- `AIExecutionResult` gained `tier` and records the ACTUAL tier/provider/model
  executed, plus latency/success/fallback/error_type/inference_options (no
  fabricated latency).
- `capabilities_from_config(config)` builds the model catalog from the
  configured DEEP + LIGHT models with honest (unknown) metadata; the engine's
  default `InferencePolicy` reads the executor's own config so the recorded
  decision and the executed model always agree.
- Tests: 225 passed (206 prior + 19 new in `tests/test_light_execution.py`
  covering FAST->NONE, INTERPRET/CLASSIFY->LIGHT, REASON/REFLECT->DEEP, all
  LIGHT failure fallbacks, model-separation both directions, execution
  metadata, tier-appropriate inference options, and policy/execution
  agreement). Frontend typecheck (`tsc --noEmit`): clean.
- Manual real-model smoke test: `backend/scripts/smoke_light.py` (ruff-clean,
  NOT in CI) runs INTERPRET + CLASSIFY against the LIGHT model and one DEEP
  request, recording model, prompt/generated tokens, latency, tokens/sec,
  success/fallback/validation, and VRAM; it refuses to run until
  `ollama pull qwen2.5:1.5b` is done manually.
- Performance note: qwen2.5:1.5b real latency/tokens-per-sec is NOT yet
  measured because the model is not installed — no improvement is claimed.
  Measured Phase 2I baseline for the same LIGHT tasks on `qwen3:4b` was
  73–128s/task at 15–20 tok/s with ~2.4GB VRAM; the installed-models check in
  `smoke_light.py` (`ollama pull qwen2.5:1.5b` required) is the AFTER
  measurement path.
- No model was automatically installed and no router/planner/validator/
  state/architecture changed during Phase 2J.
- PHASE 2J COMPLETE.

# reallightmodelbenchmarkresults.md

> **Source:** reallightmodelbenchmarkresults.md

---

# Real LIGHT Model Benchmark Results — qwen2.5:1.5b

Benchmark against the real, manually-installed local model `qwen2.5:1.5b`
(`OLLAMA_LIGHT_MODEL=qwen2.5:1.5b`). No production code, prompts, routing,
or inference policy was modified; a one-off harness in `/tmp/opencode`
reused the existing production infrastructure
(`AIRouter -> ReasoningPlanner -> InferencePolicy -> AIExecutor ->
OllamaProvider`) and recorded every actual Ollama HTTP call.

## Raw Results (warm steady state)

| Case | Tier | Model | Success | Fallback | Latency | Prompt tok | Gen tok | tok/s | Thinking | Validation | JSON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. INTERPRET | LIGHT | qwen2.5:1.5b | True | none | 1951 ms | 476 | 123 | 73.4 | 0 (no channel) | ok | pure JSON, parsed |
| 2. CLASSIFY | LIGHT | qwen2.5:1.5b | True | none | 1512 ms | 476 | 88 | 73.8 | 0 | ok | pure JSON, parsed |
| 3. INTERPRET+CTX | LIGHT | qwen2.5:1.5b | True | none | 1618 ms | 475 | 96 | 75.0 | 0 | ok (1 correction) | pure JSON, parsed |

Inputs benchmarked:

1. INTERPRET — `"I'm frustrated because I'm stuck trying to finish ChronOS."`
2. CLASSIFY — `"I don't even know what I'm trying to do anymore."`
3. INTERPRET + context — `"I'm exhausted and wondering whether this project is worth continuing."`

Notes:

- Prompt tokens are the ACTUAL `prompt_eval_count` from the production call
  (executor's own estimate: ~492). `think:false` was sent
  (`light_thinking_enabled=False`); the `thinking` channel was empty on every
  call; `done_reason=stop` on all calls.
- Reliability extension: 8/8 additional warm runs succeeded (no fallback).
  Across repeated runs, warm latency ranged 1.0-2.0 s.
- TRUE cold start (model unloaded): 4.06 s including model load — and that
  call returned contract-invalid JSON -> honest `success=False,
  fallback_used=True, error_type=MALFORMED_JSON`; the deterministic response
  was served. The typed failure/fallback path works. Small-model JSON
  nondeterminism is real but rare: observed on 1 of ~3 cold calls, 0/11 warm.

## Verifications

- **LIGHT -> qwen2.5:1.5b**: every case recorded `selected_tier=LIGHT`,
  `actual_model=qwen2.5:1.5b`.
- **LIGHT NEVER -> qwen3:4b**: the HTTP-call recorder shows ONLY
  `qwen2.5:1.5b` was ever called on the LIGHT path; after the runs
  `ollama ps` showed only `qwen2.5:1.5b` loaded (1.4 GB, 100% GPU).
  Separation in both directions confirmed by the existing
  `backend/scripts/smoke_light.py`: its DEEP leg executed `qwen3:4b`
  (success, 173.5 s) and printed `SMOKE_2J_OK`.
- **FAST** (`"What is MongoDB?"`): `route=FAST`, `use_ai=false`, tier `NONE`,
  `attempted=false`, ZERO Ollama HTTP calls (recorder-verified), final
  response == the engine's deterministic template.
- **VRAM**: nvidia-smi 387 -> 1865 MiB with `qwen2.5:1.5b` resident
  (~1.45 GiB delta, fully on GPU).

## Caveats (honest findings)

- Through the full engine, these three short inputs route FAST by design
  ("emotion alone never routes to AI"). The LIGHT tier was therefore
  exercised via the smoke-test methodology: a forced `use_ai` routing result
  fed into the REAL policy/executor/provider chain.
- `backend/scripts/benchmark_light.py` cannot run against this model
  unmodified: it hardcodes `"think": true`, and Ollama returns
  HTTP 400 `"qwen2.5:1.5b" does not support thinking`. Production code is
  unaffected (`light_thinking_enabled=False` sends `think:false`).

## Comparison vs qwen3:4b LIGHT Baseline (Phase 2I: 73-128 s/task)

| Metric | qwen3:4b | qwen2.5:1.5b |
|---|---|---|
| Task latency | 73.9-128.1 s | 1.0-2.0 s warm (~50-100x faster); 4.1 s cold |
| Tokens/sec | 15.4-19.8 | 68-77 (~4-5x) |
| Thinking tokens | 1,235-2,481 per task | 0 |
| VRAM | ~2.4 GB, 33%/67% CPU/GPU split | 1.4 GB, 100% GPU |

## Conclusion

LIGHT-tier execution is verified end-to-end on the real local model:
correct tier/model selection, strict LIGHT/DEEP model separation, a fully
deterministic FAST path, an honest typed fallback on malformed output, and
latency well inside the 30 s LIGHT budget (~50-100x faster than the
qwen3:4b baseline with no thinking tokens and lower VRAM use).


# todo.md

> **Source:** todo.md

---

1 the onboarding flow must save and show the inputs from the user somewhere because as a user i want to see what i have inputed through the flow
2 the main dashboard must be working correctly - this has to be done later
3 need api credits from some ai to make this app work
4 chron os admin page must be made - this is to check whether the os is working fine or is lagging at any point which might affect the user
5 need a user profile as well
