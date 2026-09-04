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
