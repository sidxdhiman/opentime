"use client";

import React, { useState } from "react";
import {
  Brain,
  Layers,
  Zap,
  ChevronRight,
  Eye,
  FileCode,
  Sparkles,
  X,
  FileText,
  Mic,
  Video,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EngineResponse } from "@/lib/chronosApi";
import { PastSelfMomentCard } from "./PastSelfMomentCard";

interface ChronosEngineFeedProps {
  response: EngineResponse | null;
}

export function ChronosEngineFeed({ response }: ChronosEngineFeedProps) {
  const [showExplainabilityModal, setShowExplainabilityModal] = useState(false);

  if (!response) {
    return (
      <Card>
        <CardContent className="flex min-h-[220px] flex-col items-center justify-center p-8 text-center">
          <Brain className="mb-4 h-9 w-9 text-muted" />
          <h4 className="text-[15px] font-semibold">The engine is listening</h4>
          <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">
            Record a voice note or write a thought above. ChronOS will quietly process it and show
            you the result here.
          </p>
        </CardContent>
      </Card>
    );
  }

  const {
    original_input,
    final_response,
    provider_name,
    model_name,
    reasoning_trace,
    validation_result,
    processing_time_ms,
    prompt_context,
    chronos_state,
  } = response;

  const pastSelf = chronos_state?.past_self_conversation;
  const reflection = chronos_state?.temporal_reflection;
  const hasMoment = pastSelf?.should_surface === true;

  // When a structured past-self moment is available, strip the flat-text
  // section that the backend appended to final_response to avoid duplication.
  const displayResponse = hasMoment
    ? final_response.split("\n\nSOMETHING FROM YOUR PAST\n")[0].trimEnd()
    : final_response;

  const getInputIcon = (type: string) => {
    if (type === "audio") return <Mic className="h-4 w-4" />;
    if (type === "video") return <Video className="h-4 w-4" />;
    return <FileText className="h-4 w-4" />;
  };

  return (
    <div className="space-y-4">
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <Brain className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-semibold">ChronOS output</p>
              <p className="text-xs text-muted">
                {provider_name} — {model_name}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs tabular-nums text-muted">{processing_time_ms}ms</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowExplainabilityModal(true)}
              className="h-8 gap-1.5 text-xs"
            >
              <Eye className="h-3.5 w-3.5" /> Explainability
            </Button>
          </div>
        </div>

        <CardContent className="space-y-5 p-6">
          {/* User input */}
          <div className="rounded-xl border border-border bg-secondary/30 p-4">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="flex items-center gap-1.5 text-xs font-medium text-muted">
                {getInputIcon(original_input.input_type)}
                Your {original_input.input_type}
              </span>
              <span className="text-[11px] tabular-nums text-muted">
                {new Date(original_input.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="text-sm leading-relaxed text-foreground">“{original_input.content}”</p>
          </div>

          {/* Processing stages */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              { icon: CheckCircle2, label: "Ingested", detail: `${original_input.input_type} received` },
              { icon: Layers, label: "Retrieved", detail: `${reasoning_trace.supporting_memory_ids?.length || 0} linked memories` },
              { icon: Zap, label: "Orchestrated", detail: "Context composed" },
              { icon: Sparkles, label: "Validated", detail: `${(validation_result.personalization_score * 100).toFixed(0)}% personalised` },
            ].map(({ icon: Icon, label, detail }) => (
              <div key={label} className="flex items-start gap-2.5 rounded-xl border border-border bg-secondary/20 p-3">
                <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
                <div>
                  <p className="text-xs font-medium text-foreground">{label}</p>
                  <p className="mt-0.5 text-[11px] leading-snug text-muted">{detail}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Response */}
          <div className="rounded-xl border border-border bg-secondary/20 p-5">
            <div className="mb-3 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent-foreground" />
              <h4 className="text-sm font-semibold">Response</h4>
            </div>
            <div className="whitespace-pre-line text-sm leading-relaxed text-foreground">
              {displayResponse}
            </div>
          </div>

          {/* Past-Self Moment — structured, emotionally distinct */}
          {hasMoment && (
            <PastSelfMomentCard moment={pastSelf!} reflection={reflection} />
          )}
        </CardContent>
      </Card>

      {/* Explainability modal */}
      {showExplainabilityModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 p-4 backdrop-blur-sm">
          <div className="relative max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-lift">
            <div className="mb-5 flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <Brain className="h-4.5 w-4.5" />
                </div>
                <div>
                  <h3 className="text-[15px] font-semibold">Explainability trace</h3>
                  <p className="text-xs text-muted">Why ChronOS answered the way it did</p>
                </div>
              </div>
              <button
                onClick={() => setShowExplainabilityModal(false)}
                className="rounded-lg p-1.5 text-muted transition-colors hover:bg-secondary hover:text-foreground"
                aria-label="Close trace"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-border bg-secondary/30 p-4">
                <p className="text-xs text-muted">Confidence</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {(reasoning_trace.confidence_score * 100).toFixed(0)}%
                </p>
              </div>
              <div className="rounded-xl border border-border bg-secondary/30 p-4">
                <p className="text-xs text-muted">Time window</p>
                <p className="mt-1 text-sm font-medium">{reasoning_trace.affected_time_range}</p>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              <h4 className="text-xs font-medium uppercase tracking-widest text-muted">
                Reasoning steps
              </h4>
              <ol className="space-y-2">
                {reasoning_trace.reasoning_steps.map((step, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-3 rounded-xl border border-border bg-secondary/20 px-3.5 py-3 text-sm text-foreground"
                  >
                    <span className="mt-0.5 text-xs font-medium tabular-nums text-muted">
                      {String(idx + 1).padStart(2, "0")}
                    </span>
                    <span className="leading-relaxed">{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            <div className="mt-5 space-y-3">
              <h4 className="text-xs font-medium uppercase tracking-widest text-muted">
                Linked memories
              </h4>
              <div className="flex flex-wrap gap-2">
                {reasoning_trace.supporting_memory_ids.length > 0 ? (
                  reasoning_trace.supporting_memory_ids.map((id) => (
                    <span
                      key={id}
                      className="rounded-md border border-border bg-secondary/40 px-2.5 py-1 font-mono text-xs text-muted"
                    >
                      {id}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-muted">Initial memory linked</span>
                )}
              </div>
            </div>

            <div className="mt-5 space-y-2 border-t border-border pt-4">
              <h4 className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted">
                <FileCode className="h-3.5 w-3.5" /> Prompt payload
              </h4>
              <pre className="max-h-48 overflow-y-auto rounded-xl border border-border bg-secondary/40 p-4 font-mono text-[11px] leading-relaxed text-muted whitespace-pre-wrap">
                {prompt_context?.user_prompt || "Prompt payload logged."}
              </pre>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowExplainabilityModal(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}