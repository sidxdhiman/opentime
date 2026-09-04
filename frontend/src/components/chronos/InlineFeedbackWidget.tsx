"use client";

import React, { useState } from "react";
import { ThumbsUp, ThumbsDown, Check } from "lucide-react";
import { chronosApi } from "@/lib/chronosApi";

interface InlineFeedbackWidgetProps {
  interactionId: string;
}

/**
 * Minimal inline feedback widget for beta validation.
 * Appears after ChronOS responses. Never interrupts the conversation.
 * Feedback is optional and non-blocking.
 */
export function InlineFeedbackWidget({ interactionId }: InlineFeedbackWidgetProps) {
  const [state, setState] = useState<"idle" | "submitted">("idle");

  const handleFeedback = async (rating: "helpful" | "not_helpful") => {
    try {
      await chronosApi.submitFeedback(interactionId, rating);
      setState("submitted");
    } catch {
      // Feedback failure must never affect the user experience
    }
  };

  if (state === "submitted") {
    return (
      <div className="flex items-center gap-1 text-[10px] text-muted">
        <Check className="h-3 w-3" />
        <span>Thanks</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-[10px] text-muted">
      <span>Was this helpful?</span>
      <button
        onClick={() => handleFeedback("helpful")}
        className="rounded-md p-0.5 transition-colors hover:bg-secondary hover:text-foreground"
        aria-label="Yes, this was helpful"
        title="Helpful"
      >
        <ThumbsUp className="h-3 w-3" />
      </button>
      <button
        onClick={() => handleFeedback("not_helpful")}
        className="rounded-md p-0.5 transition-colors hover:bg-secondary hover:text-foreground"
        aria-label="No, this was not helpful"
        title="Not helpful"
      >
        <ThumbsDown className="h-3 w-3" />
      </button>
    </div>
  );
}
