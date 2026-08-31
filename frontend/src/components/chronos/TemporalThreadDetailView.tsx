"use client";

import React, { useEffect, useState } from "react";
import { ArrowLeft, Calendar, MessageSquare, Archive, RotateCcw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { chronosApi, TemporalThread } from "@/lib/chronosApi";
import {
  STATUS_STYLES,
  STATUS_NARRATIVE,
  formatDate,
  formatDateLong,
} from "@/lib/chronosConstants";

interface TemporalThreadDetailViewProps {
  thread: TemporalThread;
  onBack: () => void;
  onContinueStory?: (thread: TemporalThread) => void;
  onUpdateThread?: (updated: TemporalThread) => void;
  onArchived?: (thread: TemporalThread) => void;
}

export function TemporalThreadDetailView({
  thread: initialThread,
  onBack,
  onContinueStory,
  onUpdateThread,
  onArchived,
}: TemporalThreadDetailViewProps) {
  const [thread, setThread] = useState<TemporalThread>(initialThread);
  const [loading, setLoading] = useState(!initialThread.events || initialThread.events.length === 0);
  const [acting, setActing] = useState(false);

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
  const narrative = STATUS_NARRATIVE[thread.status] || "";
  const events = (thread.events || []).slice().sort(
    (a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime()
  );
  const isArchived = thread.user_archived === true;

  const handleArchiveToggle = async () => {
    setActing(true);
    try {
      const updated = isArchived
        ? await chronosApi.restoreStory(thread.id)
        : await chronosApi.archiveStory(thread.id);
      setThread(updated);
      onUpdateThread?.(updated);
      if (!isArchived) onArchived?.(updated);
    } catch {
      // leave state unchanged; the action simply did not apply
    } finally {
      setActing(false);
    }
  };

  return (
    <Card className="overflow-hidden">
      {/* Header */}
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
            {narrative && <>{narrative} {" \u00b7 "}</>}
            {events.length} {events.length === 1 ? "moment" : "moments"}
            {" \u00b7 "}
            Started {formatDateLong(thread.created_at)}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleArchiveToggle}
            disabled={acting}
            className="gap-1.5 text-xs text-muted hover:text-foreground"
          >
            {isArchived ? <RotateCcw className="h-3.5 w-3.5" /> : <Archive className="h-3.5 w-3.5" />}
            {isArchived ? "Restore" : "Archive"}
          </Button>
          {onContinueStory && !isArchived && (
            <Button
              variant="default"
              size="sm"
              onClick={() => onContinueStory(thread)}
              className="gap-1.5 text-xs"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Continue this story
            </Button>
          )}
        </div>
      </div>
      <CardContent className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : events.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-sm text-muted">No moments recorded for this story yet.</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Moments will appear here as ChronOS notices meaningful changes connected to this story.
            </p>
          </div>
        ) : (
          <div className="relative space-y-0">
            {events.map((event, i) => {
              const isOrigin = i === 0;
              const isLatest = i === events.length - 1;
              const isSingle = events.length === 1;

              return (
                <div key={event.id} className="relative flex gap-4 pb-6 last:pb-0">
                  {/* Vertical timeline line */}
                  {i < events.length - 1 && (
                    <div className="absolute left-[11px] top-6 bottom-0 w-px bg-border" />
                  )}

                  {/* Timeline dot */}
                  <div className="relative z-10 mt-1.5 flex h-6 w-6 shrink-0 items-center justify-center">
                    <span
                      className={`h-2.5 w-2.5 rounded-full ${
                        isOrigin
                          ? "bg-accent-foreground"
                          : isLatest
                            ? "bg-emerald-400"
                            : "bg-muted/50"
                      }`}
                    />
                  </div>

                  {/* Moment content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      {isOrigin && !isSingle && (
                        <span className="rounded-md bg-accent/60 px-2 py-0.5 text-[10px] font-medium text-accent-foreground">
                          Where it started
                        </span>
                      )}
                      {isOrigin && isSingle && (
                        <span className="rounded-md bg-accent/60 px-2 py-0.5 text-[10px] font-medium text-accent-foreground">
                          The moment
                        </span>
                      )}
                      {isLatest && !isOrigin && (
                        <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                          Where it is now
                        </span>
                      )}
                    </div>

                    <div className="rounded-xl border border-border bg-secondary/20 p-4 transition-all duration-200 hover:bg-secondary/30">
                      <p className="text-sm leading-relaxed text-foreground">{event.description}</p>
                      <div className="mt-2.5 flex items-center gap-1.5 text-[11px] text-muted">
                        <Calendar className="h-3 w-3" />
                        {formatDate(event.occurred_at)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
