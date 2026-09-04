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