"use client";

import React from "react";
import {
  Compass,
  ChevronRight,
  Circle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { TemporalThread } from "@/lib/chronosApi";
import {
  STATUS_NARRATIVE,
  formatDate,
  formatTimeRange,
} from "@/lib/chronosConstants";

interface JourneyViewProps {
  threads: TemporalThread[];
  onSelectThread: (thread: TemporalThread) => void;
}

/**
 * The Stories view presents temporal threads as living narratives.
 *
 * It renders directly from the thread list — which already carries its
 * chronological moments — so no per-story detail request is needed (N+1 fix).
 * No new intelligence is added; this is purely a presentation layer over the
 * already-persisted temporal data.
 */
export function JourneyView({ threads, onSelectThread }: JourneyViewProps) {
  // Sort stories: most recently updated first.
  const sortedThreads = [...(threads || [])].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  if (!threads || threads.length === 0) {
    return (
      <Card className="overflow-hidden">
        <div className="flex items-center gap-3 border-b border-border/60 px-6 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <Compass className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Your Stories</h3>
            <p className="text-xs text-muted">How your story unfolds over time</p>
          </div>
        </div>
        <CardContent className="flex flex-col items-center justify-center px-6 py-16 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/60">
            <Compass className="h-7 w-7 text-muted" />
          </div>
          <h4 className="text-[15px] font-medium text-foreground">Your stories will take shape here</h4>
          <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">
            As ChronOS notices meaningful changes, decisions, goals, and moments in your life,
            they will appear here as stories that evolve over time. To begin, share a first
            thought on the Home tab — a story only takes shape once you have shared something.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <Compass className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Your Stories</h3>
            <p className="text-xs text-muted">
              {sortedThreads.length} {sortedThreads.length === 1 ? "story" : "stories"} across time
            </p>
          </div>
        </div>
      </div>

      <CardContent className="p-2">
        {sortedThreads.map((thread) => (
          <JourneyThreadCard
            key={thread.id}
            thread={thread}
            onSelect={() => onSelectThread(thread)}
          />
        ))}
      </CardContent>
    </Card>
  );
}

/* ── Story card ───────────────────────────────────────────────────────── */

function JourneyThreadCard({
  thread,
  onSelect,
}: {
  thread: TemporalThread;
  onSelect: () => void;
}) {
  const narrative = STATUS_NARRATIVE[thread.status] || "";

  const events = (thread.events || []).slice().sort(
    (a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime()
  );

  const origin = events[0];
  const latest = events.length > 1 ? events[events.length - 1] : null;
  const hasStory = events.length >= 2;

  return (
    <button
      onClick={onSelect}
      aria-label={`Open story: ${thread.subject}`}
      className="w-full rounded-xl border border-border/60 bg-secondary/10 p-5 text-left transition-all duration-200 hover:bg-secondary/30 hover:border-border group"
    >
      {/* Top row: subject */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0 flex-1">
          <span className="text-sm font-medium text-foreground leading-snug">{thread.subject}</span>
        </div>
        <ChevronRight className="h-4 w-4 shrink-0 mt-0.5 text-muted/40 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-muted" />
      </div>

      {/* Story arc: origin → progression → current */}
      {hasStory && origin && latest && (
        <div className="space-y-2.5">
          {/* Origin moment */}
          <div className="flex items-start gap-3">
            <div className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center">
              <span className="h-2 w-2 rounded-full bg-accent-foreground" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-medium uppercase tracking-wider text-accent-foreground mb-0.5">
                Where it started
              </p>
              <p className="text-xs leading-relaxed text-foreground/80 line-clamp-2">
                {origin.description}
              </p>
              <p className="mt-1 text-[10px] text-muted">{formatDate(origin.occurred_at)}</p>
            </div>
          </div>

          {/* Progression indicator */}
          <div className="flex items-center gap-3 pl-2">
            <div className="flex h-5 w-5 shrink-0 items-center justify-center">
              <div className="flex flex-col items-center gap-0.5">
                <Circle className="h-1 w-1 text-muted/30" />
                <Circle className="h-1 w-1 text-muted/30" />
              </div>
            </div>
            <p className="text-[10px] text-muted italic">
              {events.length - 2 > 0
                ? `${events.length - 2} ${events.length - 2 === 1 ? "moment" : "moments"} in between`
                : "Things changed"}
            </p>
          </div>

          {/* Latest moment */}
          <div className="flex items-start gap-3">
            <div className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-medium uppercase tracking-wider text-emerald-400 mb-0.5">
                Where it is now
              </p>
              <p className="text-xs leading-relaxed text-foreground/80 line-clamp-2">
                {latest.description}
              </p>
              <p className="mt-1 text-[10px] text-muted">{formatDate(latest.occurred_at)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Single moment story — show honestly */}
      {!hasStory && origin && (
        <div className="flex items-start gap-3">
          <div className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center">
            <span className="h-2 w-2 rounded-full bg-accent-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs leading-relaxed text-foreground/80 line-clamp-2">
              {origin.description}
            </p>
            <p className="mt-1 text-[10px] text-muted">{formatDate(origin.occurred_at)}</p>
          </div>
        </div>
      )}

      {/* No moments — a story ChronOS is tracking */}
      {events.length === 0 && (
        <p className="text-xs text-muted pl-8">
          {thread.description || "A story ChronOS is tracking."}
        </p>
      )}

      {/* Footer: time span + narrative */}
      <div className="mt-3 flex items-center gap-3 pl-8 text-[10px] text-muted">
        {hasStory && origin && latest && (
          <span>{formatTimeRange(origin.occurred_at, latest.occurred_at)}</span>
        )}
        {!hasStory && thread.event_count > 0 && (
          <span>{thread.event_count} {thread.event_count === 1 ? "moment" : "moments"}</span>
        )}
        {narrative && (
          <>
            <span className="text-border" aria-hidden>/</span>
            <span className="italic">{narrative}</span>
          </>
        )}
      </div>
    </button>
  );
}
