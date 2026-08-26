"use client";

import React from "react";
import { UserCheck, Target, Sparkles, Award, RefreshCw, MessageSquare } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { IdentityProfile } from "@/lib/chronosApi";
import { formatDate } from "@/lib/chronosConstants";
import { EmptyState } from "./EmptyState";

interface IdentityModelCardProps {
  identity: IdentityProfile | null;
  onRefresh?: () => void;
}

export function IdentityModelCard({ identity, onRefresh }: IdentityModelCardProps) {
  if (!identity) {
    return (
      <EmptyState
        icon={UserCheck}
        title="Building your identity model"
        description="Share a few thoughts and ChronOS will build a portrait of who you are."
      />
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
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <UserCheck className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Identity model</h3>
            <p className="text-xs text-muted">
              Version {version}, updated {formatDate(last_updated)}
            </p>
          </div>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary/40 px-2.5 py-1.5 text-xs text-muted transition-colors hover:text-foreground"
          >
            <RefreshCw className="h-3 w-3" /> Refresh
          </button>
        )}
      </div>

      <CardContent className="space-y-6 p-6">
        {/* Emotional tendencies */}
        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-widest text-muted">
            Emotional posture
          </p>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(emotional_tendencies || {}).map(([key, score]) => (
              <div key={key} className="rounded-xl border border-border bg-secondary/20 p-3">
                <div className="mb-2 flex items-center justify-between text-xs font-medium">
                  <span className="capitalize text-foreground">{key}</span>
                  <span className="tabular-nums text-accent-foreground">
                    {(score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-1 w-full overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-700"
                    style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Goals */}
        <div className="space-y-2.5">
          <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-widest text-muted">
            <Target className="h-3.5 w-3.5 text-accent-foreground" /> Active goals
          </p>
          {goals && goals.length > 0 ? (
            <div className="space-y-1.5">
              {goals.map((goal, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-border bg-secondary/20 px-3 py-2 text-sm text-foreground"
                >
                  {goal}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">No goals recorded yet</p>
          )}
        </div>

        {/* Interests & skills */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div className="space-y-2.5">
            <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-widest text-muted">
              <Sparkles className="h-3.5 w-3.5 text-accent-foreground" /> Interests
            </p>
            {interests && interests.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {interests.map((interest) => (
                  <span
                    key={interest}
                    className="rounded-full border border-border bg-secondary/40 px-2.5 py-1 text-xs text-foreground/80"
                  >
                    {interest}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted">Nothing inferred yet</p>
            )}
          </div>

          <div className="space-y-2.5">
            <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-widest text-muted">
              <Award className="h-3.5 w-3.5 text-accent-foreground" /> Skills
            </p>
            {skills && skills.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {skills.map((skill) => (
                  <span
                    key={skill}
                    className="rounded-full border border-border bg-secondary/40 px-2.5 py-1 text-xs text-foreground/80"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted">Nothing inferred yet</p>
            )}
          </div>
        </div>

        {/* Communication & decisions */}
        {(communication_style || decision_patterns?.length) && (
          <div className="rounded-xl border border-border bg-secondary/20 p-4">
            <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted">
              <MessageSquare className="h-3.5 w-3.5 text-accent-foreground" />
              Communication & decision style
            </p>
            <p className="mt-3 text-sm leading-relaxed text-foreground">{communication_style}</p>
            {decision_patterns && decision_patterns.length > 0 && (
              <p className="mt-2 text-sm text-muted">{decision_patterns[0]}</p>
            )}
          </div>
        )}

        {values && values.length > 0 && (
          <div className="space-y-2.5">
            <p className="text-xs font-medium uppercase tracking-widest text-muted">Values</p>
            <div className="flex flex-wrap gap-1.5">
              {values.map((v) => (
                <span
                  key={v}
                  className="rounded-full border border-border bg-secondary/40 px-2.5 py-1 text-xs text-foreground/80"
                >
                  {v}
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}