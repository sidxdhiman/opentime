"use client";

import React from "react";
import { Activity, Repeat, AlertTriangle, Trophy, Zap, TrendingUp, RefreshCcw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { PatternItem } from "@/lib/chronosApi";

interface PatternDetectionViewProps {
  patterns: PatternItem[];
}

export function PatternDetectionView({ patterns }: PatternDetectionViewProps) {
  if (!patterns || patterns.length === 0) {
    return (
      <Card className="border-border/60 p-8 text-center text-xs text-muted">
        No patterns detected yet. ChronOS continuously scans interaction history to surface habits, loops, and productivity trends.
      </Card>
    );
  }

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case "repeated_success":
        return { icon: Trophy, color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" };
      case "recurring_problem":
        return { icon: AlertTriangle, color: "text-rose-400 border-rose-500/30 bg-rose-500/10" };
      case "habit":
        return { icon: Repeat, color: "text-violet-400 border-violet-500/30 bg-violet-500/10" };
      case "productivity_trend":
        return { icon: TrendingUp, color: "text-amber-400 border-amber-500/30 bg-amber-500/10" };
      case "behavior_loop":
        return { icon: RefreshCcw, color: "text-sky-400 border-sky-500/30 bg-sky-500/10" };
      default:
        return { icon: Zap, color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/10" };
    }
  };

  return (
    <Card className="border-border/80 bg-card/90 shadow-xl overflow-hidden">
      <div className="bg-gradient-to-r from-violet-900/30 via-cyan-900/20 to-card px-6 py-4 border-b border-border/60 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-600 text-white font-bold text-xs shadow-md shadow-cyan-600/30">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-bold tracking-tight text-foreground">Pattern Detection System</h3>
            <p className="text-xs text-muted">Behavior Loops, Habits, Trends & Mood Shifts</p>
          </div>
        </div>
        <span className="rounded-full bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 text-xs text-cyan-300 font-semibold">
          {patterns.length} Active Patterns
        </span>
      </div>

      <CardContent className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {patterns.map((pat) => {
          const badge = getCategoryBadge(pat.category);
          const Icon = badge.icon;

          return (
            <div
              key={pat.id}
              className="rounded-xl border border-border/80 bg-secondary/30 p-4 space-y-2 hover:border-cyan-500/30 transition-all"
            >
              <div className="flex items-center justify-between">
                <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${badge.color}`}>
                  <Icon className="h-3 w-3" /> {pat.category.replace("_", " ").toUpperCase()}
                </span>
                <span className="text-[11px] text-muted font-mono">
                  {(pat.confidence_score * 100).toFixed(0)}% Conf
                </span>
              </div>

              <h4 className="text-sm font-bold text-foreground">{pat.title}</h4>
              <p className="text-xs text-muted leading-relaxed">{pat.description}</p>

              <div className="pt-2 flex items-center justify-between text-[10px] text-muted border-t border-border/40 font-mono">
                <span>Frequency: {pat.frequency}</span>
                <span>Supporting memories: {pat.supporting_memory_ids?.length || 1}</span>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
