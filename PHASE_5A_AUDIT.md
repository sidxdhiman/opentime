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
