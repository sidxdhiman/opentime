import { EngineResponse, InteractionRecord } from "./chronosApi";

/* ───────────────────────────────────────────────────────────────────────────
 * Explainability builder.
 *
 * Transforms the existing EngineResponse metadata into a short, honest,
 * user-facing explanation. This module is PURE and DETERMINISTIC — it never
 * makes an AI call, never reconstructs hidden reasoning, and only ever uses
 * facts that are actually present for the exact response being inspected.
 *
 * Boundary: everything in this file is treated as user-facing. Raw ids,
 * confidence scores, prompts, providers, models, traces and chain-of-thought
 * never appear here by construction (see sanitizeForUser as final defense).
 * ───────────────────────────────────────────────────────────────────────────
 */

export interface ExplanationSection {
  title: string;
  paragraphs: string[];
}

export interface Explanation {
  lead: string;
  sections: ExplanationSection[];
  sources: string[];
  uncertainty: string;
  limited: boolean;
}

/** Internal identifier prefix conventions — never shown to users. */
const INTERNAL_ID_PATTERN = /\b(?:mem|tevent|thread|resp|evidence|state)_[A-Za-z0-9._-]+/g;

/** Final defense-in-depth: strips any internal identifier that might still be
 *  attached to evidence text before it reaches the UI. User text is never
 *  rewritten beyond removing genuinely internal id tokens. */
export function sanitizeForUser(text: string): string {
  return text.replace(INTERNAL_ID_PATTERN, "").replace(/\s{2,}/g, " ").trim();
}

/* ── Human vocabulary (deterministic, semantically loaded) ───────────────── */

const INTENT_PHRASE: Record<string, string> = {
  QUESTION: "You were asking a question",
  REQUEST: "You were asking for something",
  DECISION: "You were weighing a decision",
  PLANNING: "You were thinking ahead and planning",
  REFLECTION: "You were reflecting on something",
  EMOTIONAL_SUPPORT: "You were carrying something and looking for support",
  INFORMATION: "You were looking for information",
  CREATION: "You were creating something",
  PROBLEM_SOLVING: "You were working through a problem",
  STATUS_UPDATE: "You were updating me on how things are going",
  JOURNAL_ENTRY: "You were writing something down",
  COMMAND: "You were giving a direct instruction",
};

const EMOTION_PHRASE: Record<string, string> = {
  CALM: "calm",
  POSITIVE: "a lighter tone",
  EXCITED: "excitement",
  CONFIDENT: "confidence",
  CURIOUS: "curiosity",
  UNCERTAIN: "uncertainty",
  OVERWHELMED: "a sense of being weighed down",
  FRUSTRATED: "frustration",
  ANXIOUS: "a thread of worry",
  SAD: "sadness",
  TIRED: "tiredness",
  ANGRY: "anger",
  MOTIVATED: "motivation",
  FOCUSED: "focus",
  RELIEVED: "relief",
};

/** A meaningful topic for the intent, derived purely from the current input. */
function intentPhrase(intent?: string | null): string | null {
  if (!intent) return null;
  const phrase = INTENT_PHRASE[intent.toUpperCase()];
  return phrase || null;
}

/** Human-readable emotion from the ingestion signal; null when nothing usable
 *  or the signal is the neutral default (nothing to claim). */
function emotionPhrase(emotionalState?: string | null): string | null {
  if (!emotionalState) return null;
  const lower = emotionalState.toUpperCase();
  if (lower === "NEUTRAL") return null;
  return EMOTION_PHRASE[lower] ?? null;
}

/* ── Evidence extraction ─────────────────────────────────────────────────── */

interface GroundedEvidence {
  memories: string[];
  story?: { subject: string; description?: string };
  pastSelf?: string;
  reflection?: string;
}

function extractEvidence(response: EngineResponse): GroundedEvidence {
  const state = response.chronos_state;
  const context = state?.context;

  const memories = (context?.relevant_memories ?? [])
    .map((m) => m.content)
    .filter((c): c is string => typeof c === "string" && c.trim().length > 0)
    .slice(0, 2);

  const story = response.active_thread_context?.subject
    ? {
        subject: response.active_thread_context.subject,
        description: response.active_thread_context.description,
      }
    : undefined;

  const pastSelfMoment = state?.past_self_conversation;
  const pastSelf =
    pastSelfMoment?.should_surface && pastSelfMoment.context?.trim()
      ? pastSelfMoment.context.trim()
      : undefined;

  const reflection =
    state?.temporal_reflection?.used && state.temporal_reflection.success
      ? state.temporal_reflection.reflection
      : undefined;

  return { memories, story, pastSelf, reflection };
}

/* ── Builder ─────────────────────────────────────────────────────────────── */

/**
 * Build a user-facing explanation for the exact live response object passed
 * in. Every section is emitted only when its underlying fact is actually
 * present for THIS response — nothing is fabricated, and no template section
 * is forced into existence.
 */
export function buildExplainability(response: EngineResponse): Explanation {
  const state = response.chronos_state;
  const intent = state?.intent?.intent ?? null;
  const emotion = state?.user_state?.emotional_state ?? null;
  const { memories, story, pastSelf, reflection } = extractEvidence(response);

  const sources: string[] = ["Your current message"];
  const sections: ExplanationSection[] = [];

  let lead = "This response was based on your current message.";
  if (story) {
    lead = "This response continued a story you're working on together.";
  } else if (pastSelf) {
    lead = "This response reached back to an earlier moment you shared.";
  } else if (memories.length > 0) {
    lead = "This response used something you shared earlier for context.";
  }

  const intentText = intentPhrase(intent);
  const emotionText = emotionPhrase(emotion);
  const noticed: string[] = [];
  if (intentText) {
    noticed.push(
      emotionText
        ? `${intentText}, and your message carried ${emotionText}.`
        : `${intentText}.`,
    );
  } else if (emotionText) {
    noticed.push(`Your message carried ${emotionText}.`);
  }

  if (noticed.length > 0) {
    sections.push({
      title: "What I noticed",
      paragraphs: noticed.map((p) => sanitizeForUser(p)),
    });
  }

  const connected: string[] = [];

  if (memories.length > 0) {
    sources.push("Earlier things you shared");
    if (memories.length === 1) {
      connected.push(`Earlier you shared: "…${ellipsize(sanitizeForUser(memories[0]), 140)}"`);
    } else {
      connected.push(
        `Earlier you shared a few things — including "…${ellipsize(
          sanitizeForUser(memories[0]),
          120,
        )}" and "…${ellipsize(sanitizeForUser(memories[1]), 80)}".`,
      );
    }
  }

  if (story) {
    const storyLine = `You chose to continue a story: "${ellipsize(
      sanitizeForUser(story.subject),
      120,
    )}".`;
    connected.push(
      story.description
        ? `${storyLine} ${sanitizeForUser(story.description)}`
        : storyLine,
    );
    sources.push("A story you're continuing");
  }

  if (pastSelf) {
    connected.push(
      `You'd described an earlier moment: "…${ellipsize(sanitizeForUser(pastSelf), 140)}"`,
    );
    sources.push("An earlier moment you shared");
  }

  if (reflection) {
    connected.push(
      `I also offered a reflection: "…${ellipsize(sanitizeForUser(reflection), 140)}"`,
    );
    sources.push("A comparison with an earlier time");
  }

  if (connected.length > 0) {
    sections.push({ title: "What I connected", paragraphs: connected });
  }

  const hasSubstantiveSource = memories.length > 0 || Boolean(story) || Boolean(pastSelf);
  const uncertainty = hasSubstantiveSource
    ? "Grounded in things you've shared."
    : "Limited context — this stays close to what you said in this message.";

  return {
    lead: sanitizeForUser(lead),
    sections,
    sources,
    uncertainty,
    limited: false,
  };
}

/** Peaceful, honest fallback for historical entries: uses only the stored
 *  fields that exist for that interaction and never reconstructs reasoning. */
export function buildHistoricalExplainability(
  record: InteractionRecord,
): Explanation {
  const pastSelf = record.past_self_context?.trim();

  if (pastSelf) {
    return {
      lead: "This response connected to an earlier moment you shared.",
      sections: [
        {
          title: "What I connected",
          paragraphs: [
            `You'd described an earlier moment: "…${ellipsize(sanitizeForUser(pastSelf), 140)}"`,
          ],
        },
      ],
      sources: ["An earlier moment you shared"],
      uncertainty: "Grounded in things you've shared.",
      limited: false,
    };
  }

  return {
    lead: "ChronOS only keeps full explanations for your latest message.",
    sections: [
      {
        title: "Before we get too deep",
        paragraphs: [
          "The detailed 'why' for this message isn't retained over time — by design, ChronOS remembers the moments, not every step of how each answer was built. This response was based on what you shared here.",
        ],
      },
    ],
    sources: ["Your current message"],
    uncertainty: "Limited context — this stays close to what you said in this message.",
    limited: true,
  };
}

function ellipsize(text: string, max: number): string {
  if (text.length <= max) return text;
  if (max <= 3) return text.slice(0, max);
  return `${text.slice(0, max - 1).trimEnd()}…`;
}