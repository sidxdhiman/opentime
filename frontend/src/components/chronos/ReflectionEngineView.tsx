"use client";

import React, { useState } from "react";
import {
  ArrowRightLeft,
  ChevronDown,
  ChevronUp,
  History,
  Compass,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { ReflectionInsight } from "@/lib/chronosApi";
import { REFLECTION_LABELS } from "@/lib/chronosConstants";
import { EmptyState } from "./EmptyState";

interface ReflectionEngineViewProps {
  reflections: ReflectionInsight[];
}

/** Present reflections as observations ChronOS has noticed across the user's
 *  shared history — never as verdicts. Confidence scores are non-calibrated
 *  and are not shown; reasoning traces belong to the dedicated explainability
 *  surface (5E-E) and are never rendered here. */
export function ReflectionEngineView({ reflections }: ReflectionEngineViewProps) {
  const [expandedId, setExpandedId] = useState<string | null>(reflections[0]?.id || null);

  if (!reflections || reflections.length === 0) {
    return (
      <EmptyState
        icon={ArrowRightLeft}
        title="Reflections build as you share across time"
        description="Once ChronOS has more than one point in your story, it will gently show how your past self and present self compare. It happens naturally as you talk on the Home tab — there is no need to force it."
      />
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
            <p className="text-xs text-muted">Changes ChronOS has noticed across what you&apos;ve shared</p>
          </div>
        </div>
        <span className="text-xs text-muted">{reflections.length} observations</span>
      </div>

      <CardContent className="space-y-3 p-6">
        {reflections.map((ref) => {
          const isExpanded = expandedId === ref.id;
          const typeLabel = REFLECTION_LABELS[ref.insight_type] ?? "Something you shared";
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
                  <ArrowRightLeft className="mt-0.5 h-4 w-4 shrink-0 text-accent-foreground" />
                  <div>
                    <span className="mb-1 inline-block rounded-md border border-border bg-secondary/40 px-2 py-0.5 text-[11px] text-muted">
                      {typeLabel}
                    </span>
                    <h4 className="text-sm font-medium leading-snug text-foreground">{ref.summary}</h4>
                    {ref.affected_time_range && (
                      <p className="mt-1 text-xs text-muted">{ref.affected_time_range}</p>
                    )}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
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
                        <History className="h-3 w-3" /> Then
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-muted">
                        {ref.past_state_summary}
                      </p>
                    </div>
                    <div className="rounded-xl border border-border bg-accent/40 p-4">
                      <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-widest text-accent-foreground">
                        <Compass className="h-3 w-3" /> Now
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-foreground">
                        {ref.current_state_summary}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}