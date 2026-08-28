"use client";

import React, { useEffect, useState } from "react";
import {
  Compass,
  ChevronRight,
  Sparkles,
  Circle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { chronosApi, TemporalThread, TemporalEvent } from "@/lib/chronosApi";
import {
  STATUS_STYLES,
  STATUS_NARRATIVE,
  TYPE_LABELS,
  formatDate,
  formatTimeRange,
} from "@/lib/chronosConstants";

interface JourneyViewProps {
  threads: TemporalThread[];
  userId: string;
  onSelectThread: (thread: TemporalThread) => void;
}

/**
 * The Journey view presents temporal threads as living storylines.
 *
 * It uses existing TemporalThread + TemporalEvent data as its source of truth.
 * No new intelligence is added — this is purely a presentation layer over
 * the already-persisted Phase 3 results.
 */
export function JourneyView({ threads, userId, onSelectThread }: JourneyViewProps) {
  const [enrichedThreads, setEnrichedThreads] = useState<TemporalThread[]>([]);
  const [loading, setLoading] = useState(true);

  // Enrich threads with event data so we can show origin/progression
  useEffect(() => {
    if (!threads || threads.length === 0) {
      setEnrichedThreads([]);
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function enrich() {
      const results = await Promise.all(
        threads.map(async (t) => {
          if (t.events && t.events.length > 0) return t;
          try {
            return await chronosApi.getThread(t.id);
          } catch {
            return t;
          }
        })
      );
      if (!cancelled) {
        setEnrichedThreads(results);
        setLoading(false);
      }
    }

    enrich();
    return () => { cancelled = true; };
  }, [threads, userId]);

  // Sort threads: most recently updated first
  const sortedThreads = [...enrichedThreads].sort(
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
            <h3 className="text-[15px] font-semibold">Your Journey</h3>
            <p className="text-xs text-muted">How your story unfolds over time</p>
          </div>
        </div>
        <CardContent className="flex flex-col items-center justify-center px-6 py-16 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/60">
            <Compass className="h-7 w-7 text-muted" />
          </div>
          <h4 className="text-[15px] font-medium text-foreground">Your journey will take shape here</h4>
          <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">
            As ChronOS notices meaningful changes, decisions, goals, and moments in your life,
            they will appear here as stories that evolve over time. To begin, share a first
            thought on the Home tab — a story only takes shape once you have shared something.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card className="overflow-hidden">
        <div className="flex items-center gap-3 border-b border-border/60 px-6 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <Compass className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Your Journey</h3>
            <p className="text-xs text-muted">How your story unfolds over time</p>
          </div>
        </div>
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
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
            <h3 className="text-[15px] font-semibold">Your Journey</h3>
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

/* ── Journey Thread Card ─────────────────────────────────────────────── */

function JourneyThreadCard({
  thread,
  onSelect,
}: {
  thread: TemporalThread;
  onSelect: () => void;
}) {
  const status = STATUS_STYLES[thread.status] || STATUS_STYLES.OPEN;
  const narrative = STATUS_NARRATIVE[thread.status] || "";
  const typeLabel = thread.temporal_type ? TYPE_LABELS[thread.temporal_type] : null;

  const events = (thread.events || []).slice().sort(
    (a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime()
  );

  const origin = events[0];
  const latest = events.length > 1 ? events[events.length - 1] : null;
  const hasStory = events.length >= 2;

  return (
    <button
      onClick={onSelect}
      className="w-full rounded-xl border border-border/60 bg-secondary/10 p-5 text-left transition-all duration-200 hover:bg-secondary/30 hover:border-border group"
    >
      {/* Top row: subject + status */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-medium text-foreground leading-snug">{thread.subject}</h4>
          <div className="mt-1 flex items-center gap-2 flex-wrap">
            <span className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-medium ${status.bg} ${status.text}`}>
              {status.label}
            </span>
            {typeLabel && (
              <span className="shrink-0 rounded-md border border-border bg-secondary/40 px-2 py-0.5 text-[10px] text-muted">
                {typeLabel}
              </span>
            )}
          </div>
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
                Current
              </p>
              <p className="text-xs leading-relaxed text-foreground/80 line-clamp-2">
                {latest.description}
              </p>
              <p className="mt-1 text-[10px] text-muted">{formatDate(latest.occurred_at)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Single event thread — show honestly */}
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

      {/* No events — thread exists but no events loaded yet */}
      {events.length === 0 && (
        <p className="text-xs text-muted pl-8">
          {thread.description || "A story ChronOS is tracking."}
        </p>
      )}

      {/* Footer: time span + narrative */}
      <div className="mt-3 flex items-center gap-3 pl-8 text-[10px] text-muted">
        {hasStory && (
          <span>{formatTimeRange(origin.occurred_at, latest!.occurred_at)}</span>
        )}
        {!hasStory && thread.event_count > 0 && (
          <span>{thread.event_count} {thread.event_count === 1 ? "event" : "events"}</span>
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
