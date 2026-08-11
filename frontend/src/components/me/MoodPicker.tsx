"use client";

import { Check } from "lucide-react";
import { MOODS, useMood } from "@/lib/mood";

export function MoodPicker() {
  const { mood, setMood } = useMood();

  return (
    <div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {MOODS.map((m) => {
          const active = m.key === mood.key;
          return (
            <button
              key={m.key}
              type="button"
              onClick={() => setMood(m.key)}
              aria-pressed={active}
              title={m.description}
              className={`group rounded-2xl border p-3 text-left transition-all duration-200 ${
                active
                  ? "border-accent bg-accent shadow-card"
                  : "border-border bg-card hover:-translate-y-0.5 hover:border-border hover:bg-secondary/40 hover:shadow-card"
              }`}
            >
              <div
                className="mb-3 h-14 w-full rounded-xl border border-border/60"
                style={{ background: m.swatch }}
              />
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
                    <span className="shrink-0">{m.emoji}</span>
                    <span className="truncate">{m.name}</span>
                  </div>
                  <div className="mt-0.5 text-[11px] text-muted truncate">{m.tagline}</div>
                </div>
                {active && <Check className="h-4 w-4 shrink-0 text-accent-foreground" />}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}