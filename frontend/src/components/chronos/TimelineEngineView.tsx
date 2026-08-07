"use client";

import React from "react";
import { Clock, Calendar, Sparkles, Repeat, Smile, Meh, Frown, Layers } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { TimelineEvent } from "@/lib/chronosApi";

interface TimelineEngineViewProps {
  events: TimelineEvent[];
}

export function TimelineEngineView({ events }: TimelineEngineViewProps) {
  if (!events || events.length === 0) {
    return (
      <Card className="border-border/60 p-8 text-center text-xs text-muted">
        No timeline events detected yet. Input voice, video, or text to start building your chronological narrative.
      </Card>
    );
  }

  const getSentimentIcon = (sentiment: number) => {
    if (sentiment > 0.2) return <Smile className="h-3.5 w-3.5 text-emerald-400" />;
    if (sentiment < -0.2) return <Frown className="h-3.5 w-3.5 text-rose-400" />;
    return <Meh className="h-3.5 w-3.5 text-amber-400" />;
  };

  return (
    <Card className="border-border/80 bg-card/90 shadow-xl overflow-hidden">
      <div className="bg-gradient-to-r from-violet-900/30 via-indigo-900/20 to-card px-6 py-4 border-b border-border/60 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-xs shadow-md shadow-indigo-600/30">
            <Clock className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-bold tracking-tight text-foreground">Timeline Engine</h3>
            <p className="text-xs text-muted">Chronological Life Phase & Event Evolution</p>
          </div>
        </div>
        <span className="rounded-full bg-secondary px-2.5 py-1 text-xs text-muted font-medium">
          {events.length} Recorded Events
        </span>
      </div>

      <CardContent className="p-6">
        <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gradient-to-b before:from-violet-500 before:via-indigo-500 before:to-transparent">
          {events.map((event) => (
            <div key={event.id} className="relative group">
              {/* Timeline dot */}
              <div className="absolute -left-6 top-1 h-3.5 w-3.5 rounded-full border-2 border-background bg-violet-500 group-hover:scale-125 transition-transform" />

              <div className="rounded-xl border border-border/80 bg-secondary/30 p-4 transition-all hover:border-violet-500/40 hover:bg-secondary/50">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-violet-500/10 border border-violet-500/20 px-2.5 py-0.5 text-[11px] font-semibold text-violet-300 flex items-center gap-1">
                      <Layers className="h-3 w-3" /> {event.life_phase}
                    </span>

                    {event.is_recurring && (
                      <span className="rounded-full bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-medium text-amber-300 flex items-center gap-1">
                        <Repeat className="h-3 w-3" /> {event.frequency || "Recurring"}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-[11px] text-muted">
                    {getSentimentIcon(event.sentiment)}
                    <span className="font-mono">{new Date(event.timestamp).toLocaleDateString()}</span>
                  </div>
                </div>

                <h4 className="text-sm font-semibold text-foreground mb-1">{event.title}</h4>
                <p className="text-xs text-muted leading-relaxed">{event.description}</p>

                {event.belief_evolution_notes && (
                  <div className="mt-3 flex items-center gap-1.5 text-[11px] font-medium text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 rounded-lg px-2.5 py-1">
                    <Sparkles className="h-3 w-3 text-indigo-400 shrink-0" />
                    <span>{event.belief_evolution_notes}</span>
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
