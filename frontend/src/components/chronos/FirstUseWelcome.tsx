"use client";

import React from "react";
import { GitBranch, MessageSquare, Sparkles } from "lucide-react";

interface FirstUseWelcomeProps {
  firstName: string;
  starterPrompts: string[];
  onPickPrompt: (prompt: string) => void;
}

/**
 * The post-onboarding "first moment" for a brand-new user.
 *
 * Kept intentionally minimal and non-tutorial: a personalized welcome, an
 * honest note about where their context with ChronOS starts, and a small set
 * of optional starter prompts. The single primary action is the conversation
 * input rendered below in the Home tab — this component does not compete with
 * it with a second, larger call-to-action.
 */
export function FirstUseWelcome({ firstName, starterPrompts, onPickPrompt }: FirstUseWelcomeProps) {
  return (
    <div className="rounded-2xl border border-accent/30 bg-gradient-to-br from-accent/10 via-card to-card px-6 py-6 sm:px-8 sm:py-7">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-foreground">
          <Sparkles className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h2 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
            {firstName ? `Welcome, ${firstName}` : "Welcome"}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
            You&apos;ve just given ChronOS its starting point. Right now it knows a little about
            your life, goals, and what matters to you — and it will build on that as you talk.
            The more you share, the more it can connect your conversations across time.
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
        <span className="flex shrink-0 items-center gap-1.5 text-xs font-medium text-accent-foreground">
          <MessageSquare className="h-3.5 w-3.5" />
          Start wherever you are
        </span>
        <div className="flex flex-wrap gap-2">
          {starterPrompts.slice(0, 4).map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onPickPrompt(prompt)}
              className="rounded-full border border-border bg-secondary/40 px-3 py-1.5 text-left text-xs font-medium text-foreground/80 transition-colors hover:border-accent-foreground/40 hover:bg-secondary/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <p className="mt-4 flex items-center gap-1.5 text-xs text-muted/80">
        <GitBranch className="h-3.5 w-3.5" />
        Stories and past-self moments are woven from what you share over time — nothing is invented.
      </p>
    </div>
  );
}
