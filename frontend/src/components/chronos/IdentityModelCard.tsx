"use client";

import React from "react";
import { UserCheck, Target, Sparkles, Award, MessageSquare, HeartHandshake, Compass } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { IdentityProfile } from "@/lib/chronosApi";
import { formatDate } from "@/lib/chronosConstants";
import { EmptyState } from "./EmptyState";

interface IdentityModelCardProps {
  identity: IdentityProfile | null;
}

/**
 * ChronOS's current understanding of the user — deliberately framed as an
 * evolving picture built from what they've shared, never as a verdict.
 * Technical metadata (version numbers, confidence scores, refresh controls)
 * is intentionally hidden: scores are non-calibrated and would imply a
 * precision the system does not claim.
 */
export function IdentityModelCard({ identity }: IdentityModelCardProps) {
  if (!identity) {
    return (
      <EmptyState
        icon={UserCheck}
        title="ChronOS is still getting to know you"
        description="Keep talking on the Home tab — ChronOS builds this picture only from what you share, over time. There is nothing to fill in here."
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
    last_updated,
  } = identity;

  const tendencies = Object.keys(emotional_tendencies || {});

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <UserCheck className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Your evolving profile</h3>
            <p className="text-xs text-muted">
              How ChronOS currently sees you — from what you&apos;ve shared
            </p>
          </div>
        </div>
      </div>

      <CardContent className="space-y-6 p-6">
        {/* Grounding note — sets the expectation up front. */}
        <p className="rounded-xl border border-border/60 bg-secondary/20 px-4 py-3 text-xs leading-relaxed text-muted">
          This is ChronOS&apos;s understanding of you right now, not a test result or a verdict. It
          changes as you share more, and you&apos;re always in control of what it&apos;s built from.
        </p>

        {/* What matters right now */}
        <div className="space-y-2.5">
          <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-widest text-muted">
            <Target className="h-3.5 w-3.5 text-accent-foreground" /> What matters to you right now
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
            <p className="text-sm text-muted">Not yet — it will grow from your conversations</p>
          )}
        </div>

        {/* How you tend to approach things */}
        <div className="space-y-2.5">
          <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-widest text-muted">
            <HeartHandshake className="h-3.5 w-3.5 text-accent-foreground" /> How you tend to approach things
          </p>
          {tendencies.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {tendencies.map((t) => (
                <span
                  key={t}
                  className="rounded-full border border-border bg-secondary/40 px-2.5 py-1 text-xs text-foreground/80"
                >
                  {t}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">Emerging from what you share</p>
          )}
        </div>

        {/* Interests & skills */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div className="space-y-2.5">
            <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-widest text-muted">
              <Sparkles className="h-3.5 w-3.5 text-accent-foreground" /> What you&apos;re drawn to
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
              <p className="text-sm text-muted">Emerging from what you share</p>
            )}
          </div>

          <div className="space-y-2.5">
            <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-widest text-muted">
              <Award className="h-3.5 w-3.5 text-accent-foreground" /> What you lean on
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
              <p className="text-sm text-muted">Emerging from what you share</p>
            )}
          </div>
        </div>

        {/* Values */}
        {values && values.length > 0 && (
          <div className="space-y-2.5">
            <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-widest text-muted">
              <Compass className="h-3.5 w-3.5 text-accent-foreground" /> What you value
            </p>
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

        {/* Communication — framed as an observation */}
        {(communication_style || decision_patterns?.length) && (
          <div className="rounded-xl border border-border bg-secondary/20 p-4">
            <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted">
              <MessageSquare className="h-3.5 w-3.5 text-accent-foreground" />
              How you tend to communicate
            </p>
            {communication_style && (
              <p className="mt-3 text-sm leading-relaxed text-foreground">{communication_style}</p>
            )}
            {decision_patterns && decision_patterns.length > 0 && (
              <p className="mt-2 text-sm text-muted">{decision_patterns[0]}</p>
            )}
          </div>
        )}

        <p className="border-t border-border/40 pt-4 text-xs text-muted/80">
          <span className="font-medium text-muted">It evolves as you do.</span> Updated{" "}
          {last_updated ? formatDate(last_updated) : "recently"} — based on what you&apos;ve shared
          in conversation.
        </p>
      </CardContent>
    </Card>
  );
}