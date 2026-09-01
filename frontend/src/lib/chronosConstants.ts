/** Shared constants for ChronOS temporal thread/status/type display. */

export const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  OPEN: { bg: "bg-sky-500/10", text: "text-sky-400", label: "Still unfolding" },
  ACTIVE: { bg: "bg-emerald-500/10", text: "text-emerald-400", label: "In progress" },
  RESOLVED: { bg: "bg-purple-500/10", text: "text-purple-400", label: "Resolved" },
  CHANGED: { bg: "bg-amber-500/10", text: "text-amber-400", label: "Evolving" },
  ABANDONED: { bg: "bg-zinc-500/10", text: "text-zinc-400", label: "Set aside" },
  ARCHIVED: { bg: "bg-zinc-500/10", text: "text-zinc-500", label: "Archived" },
};

export const TYPE_LABELS: Record<string, string> = {
  DECISION: "Decision",
  GOAL: "Goal",
  FEAR: "Fear",
  LIFE_EVENT: "Life Event",
  BELIEF: "Belief",
  MILESTONE: "Milestone",
  PREDICTION: "Prediction",
  PROMISE: "Promise",
  FUTURE_EXPECTATION: "Expectation",
  QUESTION: "Question",
};

/** Human-friendly status narrative for journey display. */
export const STATUS_NARRATIVE: Record<string, string> = {
  OPEN: "Still unfolding",
  ACTIVE: "In progress",
  RESOLVED: "Resolved",
  CHANGED: "Evolved over time",
  ABANDONED: "Set aside",
  ARCHIVED: "Archived",
};

/** Human-facing labels for reflection types — observations, never verdicts.
 *  Raw enum values (e.g. "emotional_shift") are never shown to users. */
export const REFLECTION_LABELS: Record<string, string> = {
  belief_shift: "A belief shifted",
  focus_shift: "Your focus moved",
  emotional_shift: "Your mood shifted",
  habit_change: "A habit changed",
};

/** Human-facing labels for detected patterns. The internal category ids are
 *  presentation details; users see the theme, framed as something noticed. */
export const PATTERN_LABELS: Record<string, string> = {
  habit: "Something you do regularly",
  recurring_problem: "A recurring challenge",
  repeated_success: "A repeated success",
  behavior_loop: "A pattern you repeat",
  productivity_trend: "A productivity trend",
  mood_shift: "A shift in mood",
  decision_change: "A change in how you decide",
};

/** Format a date string for display. */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Format a date string with full month name. */
export function formatDateLong(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

/** Format a relative time range between two ISO dates. */
export function formatTimeRange(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const diffMs = end.getTime() - start.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Same day";
  if (diffDays === 1) return "1 day apart";
  if (diffDays < 30) return `${diffDays} days apart`;
  const diffMonths = Math.round(diffDays / 30);
  if (diffMonths === 1) return "1 month apart";
  if (diffMonths < 12) return `${diffMonths} months apart`;
  const diffYears = Math.round(diffMonths / 12);
  return diffYears === 1 ? "1 year apart" : `${diffYears} years apart`;
}
