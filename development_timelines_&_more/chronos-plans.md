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
