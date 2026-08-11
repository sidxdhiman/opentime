"use client";

import { Check } from "lucide-react";

export interface StepMeta {
  key: string;
  label: string;
  optional?: boolean;
}

interface Props {
  steps: StepMeta[];
  currentIndex: number;
  completedKeys: string[];
}

export function OnboardingProgress({ steps, currentIndex, completedKeys }: Props) {
  return (
    <div className="w-full">
      {/* Progress bar */}
      <div className="relative h-1 bg-border rounded-full overflow-hidden mb-6">
        <div
          className="absolute inset-y-0 left-0 bg-primary transition-all duration-500"
          style={{ width: `${((currentIndex) / (steps.length - 1)) * 100}%` }}
        />
      </div>

      {/* Step dots — hidden on very small screens, shown on sm+ */}
      <div className="hidden sm:flex items-center justify-between">
        {steps.map((step, i) => {
          const isDone = completedKeys.includes(step.key);
          const isCurrent = i === currentIndex;
          const isFuture = i > currentIndex;
          return (
            <div key={step.key} className="flex flex-col items-center gap-1.5 flex-1">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full border-2 text-xs font-medium transition-all duration-300 ${
                  isDone
                    ? "border-primary bg-primary text-primary-foreground"
                    : isCurrent
                    ? "border-accent-foreground bg-accent text-accent-foreground scale-110"
                    : "border-border bg-background text-muted"
                }`}
              >
                {isDone ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </div>
              <span
                className={`text-[10px] font-medium text-center leading-tight max-w-[60px] transition-colors ${
                  isCurrent ? "text-violet-400" : isFuture ? "text-muted/50" : "text-muted"
                }`}
              >
                {step.label}
                {step.optional && (
                  <span className="block text-muted/40">(optional)</span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {/* Mobile: just show step x of y */}
      <div className="sm:hidden text-center text-xs text-muted">
        Step {currentIndex + 1} of {steps.length}
        {steps[currentIndex]?.optional && " (optional)"}
      </div>
    </div>
  );
}
