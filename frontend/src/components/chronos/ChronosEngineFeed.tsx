"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Brain,
  Layers,
  Zap,
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
import { EngineResponse, InteractionRecord } from "@/lib/chronosApi";
import { PastSelfMomentCard } from "./PastSelfMomentCard";

interface ChronosEngineFeedProps {
  interactions: InteractionRecord[];
  latestResponse: EngineResponse | null;
}

export function ChronosEngineFeed({ interactions, latestResponse }: ChronosEngineFeedProps) {
  const [showExplainabilityModal, setShowExplainabilityModal] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [interactions.length, latestResponse]);

  const hasHistory = interactions.length > 0;
  const hasLatest = latestResponse !== null;

  // Deduplicate: exclude any persisted interaction whose id matches the
  // in-memory latestResponse to avoid rendering the same message twice.
  const filteredInteractions = hasLatest
    ? interactions.filter((r) => r.id !== latestResponse!.id)
    : interactions;

  if (!hasHistory && !hasLatest) {
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

  return (
    <div className="space-y-4">
      {/* Historical interactions */}
      {filteredInteractions.map((record) => (
        <InteractionBlock key={record.id} record={record} />
      ))}

      {/* Current session response — full experience with explainability */}
      {hasLatest && <LatestResponseBlock response={latestResponse!} onExplain={() => setShowExplainabilityModal(true)} />}

      <div ref={bottomRef} />

      {/* Explainability modal — only for the latest response */}
      {hasLatest && showExplainabilityModal && (
        <ExplainabilityModal
          response={latestResponse!}
          onClose={() => setShowExplainabilityModal(false)}
        />
      )}
    </div>
  );
}

/* ── Historical interaction block ──────────────────────────────────────── */

function InteractionBlock({ record }: { record: InteractionRecord }) {
  const hasMoment =
    (record.past_self_context || "").trim().length > 0 ||
    (record.past_self_question || "").trim().length > 0;

  // Strip the flat past-self section from the displayed response
  const displayResponse = hasMoment
    ? record.final_response.split("\n\nSOMETHING FROM YOUR PAST\n")[0].trimEnd()
    : record.final_response;

  const getInputIcon = (type: string) => {
    if (type === "audio") return <Mic className="h-3.5 w-3.5" />;
    if (type === "video") return <Video className="h-3.5 w-3.5" />;
    return <FileText className="h-3.5 w-3.5" />;
  };

  return (
    <div className="space-y-3">
      {/* User input */}
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md border border-border bg-secondary/30 px-4 py-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            {getInputIcon(record.input_type)}
            <span className="text-[10px] font-medium text-muted">
              {new Date(record.created_at).toLocaleTimeString(undefined, {
                hour: "numeric",
                minute: "2-digit",
              })}
            </span>
          </div>
          <p className="text-sm leading-relaxed text-foreground">&ldquo;{record.user_content}&rdquo;</p>
        </div>
      </div>

      {/* ChronOS response */}
      <div className="flex justify-start">
        <div className="max-w-[85%] space-y-3">
          <div className="rounded-2xl rounded-bl-md border border-border bg-card px-4 py-3">
            <div className="mb-1.5 flex items-center gap-1.5">
              <Brain className="h-3 w-3 text-muted" />
              <span className="text-[10px] font-medium text-muted">ChronOS</span>
            </div>
            <div className="whitespace-pre-line text-sm leading-relaxed text-foreground">
              {displayResponse}
            </div>
          </div>

          {/* Past-Self Moment from historical record */}
          {hasMoment && (
            <PastSelfMomentCard
              moment={{
                should_surface: true,
                opening: record.past_self_opening || "",
                context: record.past_self_context || "",
                bridge: record.past_self_bridge || "",
                question: record.past_self_question || "",
                confidence: 1,
              }}
              reflection={
                record.past_self_reflection
                  ? { used: true, success: true, reflection: record.past_self_reflection }
                  : undefined
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Latest response block — full experience ───────────────────────────── */

function LatestResponseBlock({
  response,
  onExplain,
}: {
  response: EngineResponse;
  onExplain: () => void;
}) {
  const {
    original_input,
    final_response,
    provider_name,
    model_name,
    reasoning_trace,
    validation_result,
    processing_time_ms,
    chronos_state,
  } = response;

  const pastSelf = chronos_state?.past_self_conversation;
  const reflection = chronos_state?.temporal_reflection;
  const hasMoment = pastSelf?.should_surface === true;

  const displayResponse = hasMoment
    ? final_response.split("\n\nSOMETHING FROM YOUR PAST\n")[0].trimEnd()
    : final_response;

  const getInputIcon = (type: string) => {
    if (type === "audio") return <Mic className="h-4 w-4" />;
    if (type === "video") return <Video className="h-4 w-4" />;
    return <FileText className="h-4 w-4" />;
  };

  return (
    <div className="space-y-3">
      {/* User input */}
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md border border-border bg-secondary/30 px-4 py-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            {getInputIcon(original_input.input_type)}
            <span className="text-[10px] font-medium text-muted">Just now</span>
          </div>
          <p className="text-sm leading-relaxed text-foreground">
            &ldquo;{original_input.content}&rdquo;
          </p>
        </div>
      </div>

      {/* ChronOS response */}
      <div className="flex justify-start">
        <div className="max-w-[85%] space-y-3">
          <div className="rounded-2xl rounded-bl-md border border-border bg-card px-4 py-3">
            <div className="mb-1.5 flex items-center gap-1.5">
              <Brain className="h-3 w-3 text-muted" />
              <span className="text-[10px] font-medium text-muted">ChronOS</span>
              <span className="ml-auto flex items-center gap-2">
                <span className="text-[10px] tabular-nums text-muted">{processing_time_ms}ms</span>
                <button
                  onClick={onExplain}
                  className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] text-muted transition-colors hover:bg-secondary hover:text-foreground"
                >
                  <Eye className="h-3 w-3" /> Explain
                </button>
              </span>
            </div>
            <div className="whitespace-pre-line text-sm leading-relaxed text-foreground">
              {displayResponse}
            </div>
          </div>

          {/* Processing stages — compact */}
          <div className="flex flex-wrap gap-1.5">
            {[
              { icon: CheckCircle2, label: "Ingested" },
              { icon: Layers, label: `${reasoning_trace.supporting_memory_ids?.length || 0} memories` },
              { icon: Zap, label: "Composed" },
              {
                icon: Sparkles,
                label: `${(validation_result.personalization_score * 100).toFixed(0)}% personal`,
              },
            ].map(({ icon: Icon, label }) => (
              <span
                key={label}
                className="flex items-center gap-1 rounded-md border border-border bg-secondary/20 px-2 py-0.5 text-[10px] text-muted"
              >
                <Icon className="h-2.5 w-2.5" />
                {label}
              </span>
            ))}
          </div>

          {/* Past-Self Moment */}
          {hasMoment && (
            <PastSelfMomentCard moment={pastSelf!} reflection={reflection} />
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Explainability modal ──────────────────────────────────────────────── */

function ExplainabilityModal({
  response,
  onClose,
}: {
  response: EngineResponse;
  onClose: () => void;
}) {
  const { reasoning_trace, prompt_context } = response;

  return (
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
            onClick={onClose}
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
          <h4 className="text-xs font-medium uppercase tracking-widest text-muted">Reasoning steps</h4>
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
          <h4 className="text-xs font-medium uppercase tracking-widest text-muted">Linked memories</h4>
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
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
