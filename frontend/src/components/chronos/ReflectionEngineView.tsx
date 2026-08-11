"use client";

import React, { useState } from "react";
import {
  Sparkles,
  ArrowRightLeft,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  History,
  Compass,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { ReflectionInsight } from "@/lib/chronosApi";

interface ReflectionEngineViewProps {
  reflections: ReflectionInsight[];
}

export function ReflectionEngineView({ reflections }: ReflectionEngineViewProps) {
  const [expandedId, setExpandedId] = useState<string | null>(reflections[0]?.id || null);

  if (!reflections || reflections.length === 0) {
    return (
      <Card className="p-8 text-center text-sm text-muted">
        No reflections yet. Keep sharing and ChronOS will quietly notice how you change.
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <ArrowRightLeft className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Reflections</h3>
            <p className="text-xs text-muted">Past self, compared with today</p>
          </div>
        </div>
        <span className="text-xs text-muted">{reflections.length} insights</span>
      </div>

      <CardContent className="space-y-3 p-6">
        {reflections.map((ref) => {
          const isExpanded = expandedId === ref.id;
          return (
            <div
              key={ref.id}
              className="overflow-hidden rounded-xl border border-border bg-secondary/20 transition-colors"
            >
              <button
                onClick={() => setExpandedId(isExpanded ? null : ref.id)}
                className="flex w-full items-center justify-between gap-3 p-4 text-left transition-colors hover:bg-secondary/40"
              >
                <div className="flex items-start gap-3">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-accent-foreground" />
                  <div>
                    <h4 className="text-sm font-medium leading-snug text-foreground">{ref.summary}</h4>
                    <p className="mt-1 text-xs tabular-nums text-muted">
                      {ref.affected_time_range} — confidence {(ref.confidence_score * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="hidden rounded-md border border-border bg-secondary/40 px-2 py-0.5 text-[11px] text-muted capitalize sm:inline">
                    {ref.insight_type.replace("_", " ")}
                  </span>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 text-muted" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-muted" />
                  )}
                </div>
              </button>

              {isExpanded && (
                <div className="space-y-4 border-t border-border/60 bg-background/40 p-5">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-border bg-secondary/30 p-4">
                      <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-widest text-muted">
                        <History className="h-3 w-3" /> Past
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-muted">
                        {ref.past_state_summary}
                      </p>
                    </div>
                    <div className="rounded-xl border border-border bg-accent/40 p-4">
                      <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-widest text-accent-foreground">
                        <Compass className="h-3 w-3" /> Present
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-foreground">
                        {ref.current_state_summary}
                      </p>
                    </div>
                  </div>

                  {ref.reasoning_trace && ref.reasoning_trace.length > 0 && (
                    <div>
                      <p className="text-[11px] font-medium uppercase tracking-widest text-muted">
                        Reasoning
                      </p>
                      <ul className="mt-2 space-y-1.5">
                        {ref.reasoning_trace.map((step, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-xs text-muted">
                            <ChevronRight className="mt-0.5 h-3 w-3 shrink-0" />
                            <span className="leading-relaxed">{step}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}