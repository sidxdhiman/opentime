"use client";

import React from "react";
import { Activity, Repeat, AlertTriangle, Trophy, TrendingUp, RefreshCcw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { PatternItem } from "@/lib/chronosApi";
import { EmptyState } from "./EmptyState";

interface PatternDetectionViewProps {
  patterns: PatternItem[];
}

export function PatternDetectionView({ patterns }: PatternDetectionViewProps) {
  if (!patterns || patterns.length === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="Habits and trends, revealed gently"
        description="As you share more of your days, recurring habits and quiet trends will surface here. Nothing is assumed up front — patterns come only from what you actually share, starting on the Home tab."
      />
    );
  }

  const getCategoryMeta = (category: string) => {
    switch (category) {
      case "repeated_success": return Trophy;
      case "recurring_problem": return AlertTriangle;
      case "habit": return Repeat;
      case "productivity_trend": return TrendingUp;
      case "behavior_loop": return RefreshCcw;
      default: return Activity;
    }
  };

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Patterns</h3>
            <p className="text-xs text-muted">Habits, loops and quiet trends</p>
          </div>
        </div>
        <span className="text-xs text-muted">{patterns.length} observed</span>
      </div>

      <CardContent className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-2">
        {patterns.map((pat) => {
          const Icon = getCategoryMeta(pat.category);
          return (
            <div
              key={pat.id}
              className="space-y-3 rounded-xl border border-border bg-secondary/20 p-4 transition-all duration-200 hover:bg-secondary/40"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 rounded-md border border-border bg-secondary/40 px-2 py-0.5 text-[11px] capitalize text-foreground/80">
                  <Icon className="h-3 w-3 text-accent-foreground" />
                  {pat.category.replace("_", " ")}
                </span>
                <span className="text-xs tabular-nums text-muted">
                  {(pat.confidence_score * 100).toFixed(0)}% confidence
                </span>
              </div>

              <h4 className="text-sm font-medium text-foreground">{pat.title}</h4>
              <p className="text-sm leading-relaxed text-muted">{pat.description}</p>

              <p className="pt-3 text-xs text-muted">
                Observed {pat.frequency.toLowerCase()}
                {pat.supporting_memory_ids?.length ? ` — ${pat.supporting_memory_ids.length} supporting memories` : ""}
              </p>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}