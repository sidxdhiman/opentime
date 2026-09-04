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
