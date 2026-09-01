"use client";

import React from "react";
import { CornerDownRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ReturnContext } from "@/lib/chronosApi";

interface ReturnHookProps {
  context: ReturnContext;
  onContinueStory?: (threadId: string) => void;
}

/**
 * Phase 5D — the in-app return hook.
 *
 * Kept deliberately subordinate to the conversation: a single compact card
 * shown only when ChronOS has a genuinely grounded reason to resurface
 * something. When nothing meaningful changed since the user's last visit it
 * renders nothing (the hero greeting already handles "Welcome back"), so the
 * user is never pressured or guilted. No red dots, no streaks, no urgency.
 */
export function ReturnHook({ context, onContinueStory }: ReturnHookProps) {
  // The hero greeting already welcomes the user back. Only surface a
  // meaningful change or a grounded suggestion here.
  if (!context.has_return_context) return null;

  const change = context.changes?.[0];

  return (
    <div className="rounded-2xl border border-border/50 bg-card p-4 shadow-card sm:p-5">
      <div className="mb-3 flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-accent/10">
          <Sparkles className="h-3.5 w-3.5 text-accent-foreground" />
        </div>
        <span className="text-[11px] font-medium uppercase tracking-widest text-muted">
          While you were away
        </span>
      </div>

      {context.summary_section && (
        <p className="mb-2 text-sm leading-relaxed text-foreground/80">
          {context.summary_section}
        </p>
      )}

      {change && (
        <p className="text-sm font-medium leading-relaxed text-foreground">{change.headline}</p>
      )}

      {change?.detail && (
        <p className="mb-3 mt-1.5 text-sm leading-relaxed text-muted">{change.detail}</p>
      )}

      {context.suggested_thread_id && context.suggested_story_subject && onContinueStory && (
        <Button
          variant="secondary"
          size="sm"
          className="mt-2 gap-1.5"
          onClick={() => onContinueStory(context.suggested_thread_id!)}
        >
          <CornerDownRight className="h-3.5 w-3.5" />
          Continue this story
        </Button>
      )}
    </div>
  );
}
