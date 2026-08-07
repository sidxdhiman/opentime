"use client";

import React from "react";
import { UserCheck, Sparkles, Target, Compass, Heart, Award, RefreshCw, MessageSquare } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { IdentityProfile } from "@/lib/chronosApi";

interface IdentityModelCardProps {
  identity: IdentityProfile | null;
  onRefresh?: () => void;
}

export function IdentityModelCard({ identity, onRefresh }: IdentityModelCardProps) {
  if (!identity) {
    return (
      <Card className="border-border/60 p-6 text-center text-xs text-muted">
        Loading Evolving Identity Profile...
      </Card>
    );
  }

  const {
    interests,
    goals,
    values,
    emotional_tendencies,
    skills,
    decision_patterns,
    communication_style,
    version,
    last_updated,
  } = identity;

  return (
    <Card className="border-border/80 bg-card/90 shadow-xl overflow-hidden">
      <div className="bg-gradient-to-r from-violet-900/30 to-indigo-900/20 px-6 py-4 border-b border-border/60 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600 text-white font-bold text-xs shadow-md shadow-violet-600/30">
            <UserCheck className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-bold tracking-tight text-foreground">Identity Model</h3>
            <p className="text-xs text-muted">Continuously Evolving Profile (v{version})</p>
          </div>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            className="flex items-center gap-1 rounded-lg border border-border bg-secondary px-2.5 py-1 text-xs text-muted hover:text-foreground transition-colors"
          >
            <RefreshCw className="h-3 w-3" /> Sync Profile
          </button>
        )}
      </div>

      <CardContent className="p-6 space-y-6">
        {/* Emotional Tendencies */}
        <div className="space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
            <Heart className="h-3.5 w-3.5 text-rose-400" /> Emotional & Mindset Posture
          </span>

          <div className="grid grid-cols-2 gap-3">
            {Object.entries(emotional_tendencies || {}).map(([key, score]) => (
              <div key={key} className="rounded-xl border border-border/60 bg-secondary/30 p-3">
                <div className="flex items-center justify-between text-xs font-semibold mb-1.5 capitalize text-foreground">
                  <span>{key}</span>
                  <span className="text-violet-400">{(score * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-700"
                    style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Active Goals */}
        <div className="space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5 text-amber-400" /> Active Evolution Goals
          </span>
          <div className="space-y-1.5">
            {goals && goals.length > 0 ? (
              goals.map((goal, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs font-medium text-amber-200"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
                  <span>{goal}</span>
                </div>
              ))
            ) : (
              <span className="text-xs text-muted">No goals recorded</span>
            )}
          </div>
        </div>

        {/* Interests & Skills */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-violet-400" /> Core Interests
            </span>
            <div className="flex flex-wrap gap-1.5">
              {interests?.map((interest) => (
                <span
                  key={interest}
                  className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-0.5 text-xs text-violet-300"
                >
                  {interest}
                </span>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
              <Award className="h-3.5 w-3.5 text-emerald-400" /> Key Skills & Crafts
            </span>
            <div className="flex flex-wrap gap-1.5">
              {skills?.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs text-emerald-300"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Communication & Decision Patterns */}
        <div className="rounded-xl border border-border/80 bg-secondary/30 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-sky-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-foreground">
              Communication & Decision Style
            </span>
          </div>
          <p className="text-xs text-muted leading-relaxed">
            <strong className="text-foreground">Style:</strong> {communication_style}
          </p>
          {decision_patterns && decision_patterns.length > 0 && (
            <p className="text-xs text-muted leading-relaxed">
              <strong className="text-foreground">Decision Pattern:</strong> {decision_patterns[0]}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
