"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRightLeft, ShieldCheck, CheckCircle2, ChevronDown, ChevronUp, History, Compass } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { ReflectionInsight } from "@/lib/chronosApi";

interface ReflectionEngineViewProps {
  reflections: ReflectionInsight[];
}

export function ReflectionEngineView({ reflections }: ReflectionEngineViewProps) {
  const [expandedId, setExpandedId] = useState<string | null>(reflections[0]?.id || null);

  if (!reflections || reflections.length === 0) {
    return (
      <Card className="border-border/60 p-8 text-center text-xs text-muted">
        No reflection insights generated yet. Add more inputs to enable Past Self vs Current Self differential analysis.
      </Card>
    );
  }

  return (
    <Card className="border-border/80 bg-card/90 shadow-xl overflow-hidden">
      <div className="bg-gradient-to-r from-indigo-900/40 via-violet-900/30 to-card px-6 py-4 border-b border-border/60 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600 text-white font-bold text-xs shadow-md shadow-emerald-600/30">
            <ArrowRightLeft className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-bold tracking-tight text-foreground">Reflection Engine</h3>
            <p className="text-xs text-muted">Past Self vs. Current Self Differential Analysis</p>
          </div>
        </div>
        <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 text-xs text-emerald-300 font-semibold">
          AI Auto-Reflections Active
        </span>
      </div>

      <CardContent className="p-6 space-y-4">
        {reflections.map((ref) => {
          const isExpanded = expandedId === ref.id;
          return (
            <div
              key={ref.id}
              className="rounded-xl border border-violet-500/30 bg-secondary/30 transition-all overflow-hidden"
            >
              {/* Card Header */}
              <div
                onClick={() => setExpandedId(isExpanded ? null : ref.id)}
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-secondary/50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <Sparkles className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-foreground">{ref.summary}</h4>
                    <span className="text-xs text-muted font-mono">{ref.affected_time_range} • Confidence: {(ref.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-violet-500/10 border border-violet-500/20 px-2 py-0.5 text-[10px] uppercase font-bold text-violet-300">
                    {ref.insight_type.replace("_", " ")}
                  </span>
                  {isExpanded ? <ChevronUp className="h-4 w-4 text-muted" /> : <ChevronDown className="h-4 w-4 text-muted" />}
                </div>
              </div>

              {/* Expanded Comparison Details */}
              {isExpanded && (
                <div className="px-5 pb-5 border-t border-border/60 pt-4 space-y-4 bg-background/50">
                  {/* Past vs Current Side-by-Side */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="rounded-lg border border-border/80 bg-secondary/30 p-3">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-rose-400 flex items-center gap-1">
                        <History className="h-3 w-3" /> Past Self
                      </span>
                      <p className="text-xs text-muted mt-1.5 leading-relaxed">{ref.past_state_summary}</p>
                    </div>

                    <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1">
                        <Compass className="h-3 w-3" /> Current Self
                      </span>
                      <p className="text-xs text-emerald-200 mt-1.5 leading-relaxed">{ref.current_state_summary}</p>
                    </div>
                  </div>

                  {/* Reasoning Trace */}
                  {ref.reasoning_trace && ref.reasoning_trace.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-muted">Reasoning Trace & Evidence:</span>
                      <ul className="space-y-1">
                        {ref.reasoning_trace.map((step, idx) => (
                          <li key={idx} className="text-xs text-muted flex items-center gap-1.5 font-mono">
                            <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />
                            <span>{step}</span>
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
