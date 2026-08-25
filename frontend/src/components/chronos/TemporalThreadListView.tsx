"use client";

import React from "react";
import { GitBranch, ChevronRight, Circle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { TemporalThread } from "@/lib/chronosApi";

interface TemporalThreadListViewProps {
  threads: TemporalThread[];
  onSelectThread: (thread: TemporalThread) => void;
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  OPEN: { bg: "bg-sky-500/10", text: "text-sky-400", label: "Open" },
  ACTIVE: { bg: "bg-emerald-500/10", text: "text-emerald-400", label: "Active" },
  RESOLVED: { bg: "bg-purple-500/10", text: "text-purple-400", label: "Resolved" },
  CHANGED: { bg: "bg-amber-500/10", text: "text-amber-400", label: "Changed" },
  ABANDONED: { bg: "bg-zinc-500/10", text: "text-zinc-400", label: "Abandoned" },
  ARCHIVED: { bg: "bg-zinc-500/10", text: "text-zinc-500", label: "Archived" },
};

const TYPE_LABELS: Record<string, string> = {
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

export function TemporalThreadListView({ threads, onSelectThread }: TemporalThreadListViewProps) {
  if (!threads || threads.length === 0) {
    return (
      <Card className="p-8 text-center text-sm text-muted">
        No threads yet. ChronOS will start tracking stories as you share moments.
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <GitBranch className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Temporal Threads</h3>
            <p className="text-xs text-muted">Stories ChronOS is tracking across time</p>
          </div>
        </div>
        <span className="text-xs text-muted">{threads.length} threads</span>
      </div>

      <CardContent className="p-2">
        {threads.map((thread) => {
          const status = STATUS_STYLES[thread.status] || STATUS_STYLES.OPEN;
          return (
            <button
              key={thread.id}
              onClick={() => onSelectThread(thread)}
              className="flex w-full items-center gap-4 rounded-xl px-4 py-3.5 text-left transition-all duration-200 hover:bg-secondary/40 group"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/60">
                <Circle className="h-3.5 w-3.5 text-muted" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="text-sm font-medium text-foreground truncate">{thread.subject}</h4>
                  <span className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-medium ${status.bg} ${status.text}`}>
                    {status.label}
                  </span>
                  {thread.temporal_type && (
                    <span className="shrink-0 rounded-md border border-border bg-secondary/40 px-2 py-0.5 text-[10px] text-muted">
                      {TYPE_LABELS[thread.temporal_type] || thread.temporal_type}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-[11px] text-muted">
                  <span>{thread.event_count} {thread.event_count === 1 ? "event" : "events"}</span>
                  <span className="text-border" aria-hidden>|</span>
                  <span>
                    {new Date(thread.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </span>
                </div>
              </div>

              <ChevronRight className="h-4 w-4 shrink-0 text-muted/50 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-muted" />
            </button>
          );
        })}
      </CardContent>
    </Card>
  );
}
