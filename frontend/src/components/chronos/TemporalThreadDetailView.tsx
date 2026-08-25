"use client";

import React, { useEffect, useState } from "react";
import { ArrowLeft, Circle, Calendar, Zap } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { chronosApi, TemporalThread, TemporalEvent } from "@/lib/chronosApi";

interface TemporalThreadDetailViewProps {
  thread: TemporalThread;
  onBack: () => void;
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

export function TemporalThreadDetailView({ thread: initialThread, onBack }: TemporalThreadDetailViewProps) {
  const [thread, setThread] = useState<TemporalThread>(initialThread);
  const [loading, setLoading] = useState(!initialThread.events || initialThread.events.length === 0);

  useEffect(() => {
    if (!initialThread.events || initialThread.events.length === 0) {
      chronosApi
        .getThread(initialThread.id)
        .then(setThread)
        .catch(() => setThread(initialThread))
        .finally(() => setLoading(false));
    }
  }, [initialThread]);

  const status = STATUS_STYLES[thread.status] || STATUS_STYLES.OPEN;
  const events = thread.events || [];

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-3 border-b border-border/60 px-6 py-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="h-8 w-8 p-0 text-muted hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="text-[15px] font-semibold truncate">{thread.subject}</h3>
            <span className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-medium ${status.bg} ${status.text}`}>
              {status.label}
            </span>
          </div>
          <p className="text-xs text-muted">
            {events.length} {events.length === 1 ? "event" : "events"}
            {" \u00b7 "}
            Started{" "}
            {new Date(thread.created_at).toLocaleDateString(undefined, {
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </p>
        </div>
      </div>

      <CardContent className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : events.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">No events recorded for this thread yet.</p>
        ) : (
          <div className="relative space-y-6 pl-5 before:absolute before:bottom-2 before:left-[5px] before:top-2 before:w-px before:bg-border">
            {events.map((event, i) => (
              <div key={event.id} className="relative">
                <span className="absolute -left-5 top-1.5 h-2.5 w-2.5 rounded-full border-2 border-background bg-foreground/30" />

                <div className="rounded-xl border border-border bg-secondary/20 p-4 transition-all duration-200 hover:bg-secondary/40">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      {event.temporal_type && (
                        <span className="rounded-md border border-border bg-secondary/40 px-2 py-0.5 text-[11px] text-muted">
                          {TYPE_LABELS[event.temporal_type] || event.temporal_type}
                        </span>
                      )}
                      {i === 0 && (
                        <span className="rounded-md bg-sky-500/10 px-2 py-0.5 text-[10px] font-medium text-sky-400">
                          Origin
                        </span>
                      )}
                      {i === events.length - 1 && events.length > 1 && (
                        <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                          Latest
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] tabular-nums text-muted">
                      <Calendar className="h-3 w-3" />
                      {new Date(event.occurred_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </div>
                  </div>

                  <p className="text-sm leading-relaxed text-foreground">{event.description}</p>

                  {event.confidence > 0 && (
                    <div className="mt-2 flex items-center gap-1.5 text-[10px] text-muted">
                      <Zap className="h-3 w-3" />
                      Confidence: {Math.round(event.confidence * 100)}%
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
