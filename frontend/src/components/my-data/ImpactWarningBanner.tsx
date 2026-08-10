"use client";

import { AlertTriangle, X } from "lucide-react";
import { useState } from "react";

interface Props {
  onDismiss?: () => void;
}

export function ImpactWarningBanner({ onDismiss }: Props) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  const dismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  return (
    <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/8 px-4 py-3 text-sm text-amber-300">
      <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-400" />
      <div className="flex-1 leading-relaxed">
        <span className="font-semibold text-amber-300">Heads up — editing this data affects Chronos.</span>{" "}
        <span className="text-amber-300/70">
          Chronos uses everything here to understand who you are and how you think.
          Changes will be reflected in future analyses, reflections, and responses.
          Old versions are preserved in the background so nothing is permanently lost.
        </span>
      </div>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss warning"
        className="shrink-0 text-amber-400/60 hover:text-amber-300 transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
