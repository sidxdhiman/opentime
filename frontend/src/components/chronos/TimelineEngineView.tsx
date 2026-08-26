"use client";

import React from "react";
import { Clock, Repeat, Smile, Meh, Frown, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { TimelineEvent } from "@/lib/chronosApi";
import { formatDate } from "@/lib/chronosConstants";
import { EmptyState } from "./EmptyState";

interface TimelineEngineViewProps {
  events: TimelineEvent[];
}

export function TimelineEngineView({ events }: TimelineEngineViewProps) {
  if (!events || events.length === 0) {
    return (
      <EmptyState
        icon={Clock}
        title="Your timeline is quiet"
        description="Share a memory and it will appear here as part of your life story."
      />
    );
  }

  const getSentimentIcon = (sentiment: number) => {
    if (sentiment > 0.2) return <Smile className="h-3.5 w-3.5 text-emerald-400/80" />;
    if (sentiment < -0.2) return <Frown className="h-3.5 w-3.5 text-rose-400/80" />;
    return <Meh className="h-3.5 w-3.5 text-amber-400/80" />;
  };

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <Clock className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Timeline</h3>
            <p className="text-xs text-muted">Your life, in order</p>
          </div>
        </div>
        <span className="text-xs text-muted">{events.length} events</span>
      </div>

      <CardContent className="p-6">
        <div className="relative space-y-6 pl-5 before:absolute before:bottom-2 before:left-[5px] before:top-2 before:w-px before:bg-border">
          {events.map((event) => (
            <div key={event.id} className="relative">
              <span className="absolute -left-5 top-1.5 h-2.5 w-2.5 rounded-full border-2 border-background bg-foreground/30 transition-transform duration-300 group-hover:scale-110" />

              <div className="rounded-xl border border-border bg-secondary/20 p-4 transition-all duration-200 hover:bg-secondary/40">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    {event.life_phase && (
                      <span className="rounded-md border border-border bg-secondary/40 px-2 py-0.5 text-[11px] capitalize text-muted">
                        {event.life_phase}
                      </span>
                    )}
                    {event.is_recurring && (
                      <span className="flex items-center gap-1 rounded-md border border-border bg-secondary/40 px-2 py-0.5 text-[11px] text-muted">
                        <Repeat className="h-3 w-3" />
                        {event.frequency || "Recurring"}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-[11px] tabular-nums text-muted">
                    {getSentimentIcon(event.sentiment)}
                    {formatDate(event.timestamp)}
                  </div>
                </div>

                <h4 className="mb-1 text-sm font-medium text-foreground">{event.title}</h4>
                <p className="text-sm leading-relaxed text-muted">{event.description}</p>

                {event.belief_evolution_notes && (
                  <div className="mt-3 flex items-start gap-2 rounded-lg border border-border bg-secondary/30 px-3 py-2 text-xs leading-relaxed text-muted">
                    <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-foreground" />
                    {event.belief_evolution_notes}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}