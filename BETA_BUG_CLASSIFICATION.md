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