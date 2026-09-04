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