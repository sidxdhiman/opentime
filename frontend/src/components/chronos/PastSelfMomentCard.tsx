"use client";

import React from "react";
import { Clock } from "lucide-react";
import { PastSelfMoment, TemporalReflection } from "@/lib/chronosApi";

interface PastSelfMomentCardProps {
  moment: PastSelfMoment;
  reflection?: TemporalReflection;
}

export function PastSelfMomentCard({ moment, reflection }: PastSelfMomentCardProps) {
  if (!moment.should_surface) return null;

  const hasReflection =
    reflection?.used && reflection?.success && (reflection.reflection || "").trim().length > 0;

  return (
    <div className="rounded-2xl border border-border/50 bg-secondary/10 p-5 sm:p-6">
      {/* Header */}
      <div className="mb-4 flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-secondary/60">
          <Clock className="h-3.5 w-3.5 text-muted" />
        </div>
        <span className="text-[11px] font-medium uppercase tracking-widest text-muted">
          Something from your past
        </span>
      </div>

      {/* Past context — the earlier moment, grounded */}
      {moment.context && (
        <blockquote className="mb-4 border-l-2 border-border/60 pl-4 text-sm italic leading-relaxed text-foreground/80">
          {moment.context}
        </blockquote>
      )}

      {/* Opening — subtle connector */}
      {moment.opening && (
        <p className="mb-3 text-sm leading-relaxed text-muted">{moment.opening}</p>
      )}

      {/* Bridge — connecting past to present */}
      {moment.bridge && (
        <p className="mb-4 text-sm leading-relaxed text-muted">{moment.bridge}</p>
      )}

      {/* The past-self question */}
      {moment.question && (
        <p className="text-sm font-medium leading-relaxed text-foreground">{moment.question}</p>
      )}

      {/* Optional AI reflection — quiet, beneath the moment */}
      {hasReflection && (
        <p className="mt-4 border-t border-border/40 pt-3 text-xs leading-relaxed italic text-muted/80">
          {reflection.reflection}
        </p>
      )}
    </div>
  );
}
