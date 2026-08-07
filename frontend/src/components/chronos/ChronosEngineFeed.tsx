"use client";

import React, { useState } from "react";
import {
  Brain,
  ShieldCheck,
  Zap,
  Layers,
  ChevronRight,
  Eye,
  FileCode,
  Sparkles,
  Clock,
  Check,
  HelpCircle,
  FileText,
  Mic,
  Video,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EngineResponse } from "@/lib/chronosApi";

interface ChronosEngineFeedProps {
  response: EngineResponse | null;
}

export function ChronosEngineFeed({ response }: ChronosEngineFeedProps) {
  const [showExplainabilityModal, setShowExplainabilityModal] = useState(false);

  if (!response) {
    return (
      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-8 text-center flex flex-col items-center justify-center min-h-[220px]">
          <Brain className="h-10 w-10 text-muted/40 mb-3 animate-pulse" />
          <h4 className="text-base font-semibold text-foreground">ChronOS Engine Standby</h4>
          <p className="text-xs text-muted max-w-sm mt-1">
            Record voice, video, or submit a note above to observe the ChronOS intelligence pipeline, memory RAG retrieval, and explainability trace.
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
  } = response;

  const getInputIcon = (type: string) => {
    if (type === "audio") return <Mic className="h-4 w-4 text-rose-400" />;
    if (type === "video") return <Video className="h-4 w-4 text-indigo-400" />;
    return <FileText className="h-4 w-4 text-sky-400" />;
  };

  return (
    <div className="space-y-4">
      <Card className="border-violet-500/30 bg-card/90 shadow-xl overflow-hidden">
        {/* Header Ribbon */}
        <div className="bg-gradient-to-r from-violet-900/40 via-indigo-900/30 to-background px-6 py-3 border-b border-violet-500/20 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-xs font-semibold uppercase tracking-wider text-violet-300">
              ChronOS Intelligence Output
            </span>
            <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] text-muted font-mono">
              {processing_time_ms}ms
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-muted font-mono">{provider_name} ({model_name})</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowExplainabilityModal(true)}
              className="h-7 text-xs border-violet-500/40 bg-violet-500/10 text-violet-300 hover:bg-violet-500/20 gap-1.5"
            >
              <Eye className="h-3.5 w-3.5" /> Explainability Trace
            </Button>
          </div>
        </div>

        <CardContent className="p-6 space-y-5">
          {/* User Input Banner */}
          <div className="rounded-xl border border-border/80 bg-secondary/30 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-muted uppercase tracking-wide flex items-center gap-1.5">
                {getInputIcon(original_input.input_type)} Input Processing Layer ({original_input.input_type.toUpperCase()})
              </span>
              <span className="text-[11px] text-muted font-mono">
                {new Date(original_input.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="text-sm font-medium text-foreground italic">
              "{original_input.content}"
            </p>
          </div>

          {/* ChronOS Multi-Stage Execution Steps Visualizer */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-2.5 flex items-center gap-2">
              <Check className="h-4 w-4 text-emerald-400 shrink-0" />
              <div>
                <p className="text-[11px] font-semibold text-emerald-400">Input Layer</p>
                <p className="text-[10px] text-muted">{original_input.input_type.toUpperCase()} Processed</p>
              </div>
            </div>

            <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 p-2.5 flex items-center gap-2">
              <Layers className="h-4 w-4 text-violet-400 shrink-0" />
              <div>
                <p className="text-[11px] font-semibold text-violet-400">Memory Retrieval</p>
                <p className="text-[10px] text-muted">
                  {reasoning_trace.supporting_memory_ids?.length || 0} Nodes Linked
                </p>
              </div>
            </div>

            <div className="rounded-lg border border-indigo-500/30 bg-indigo-500/5 p-2.5 flex items-center gap-2">
              <Zap className="h-4 w-4 text-indigo-400 shrink-0" />
              <div>
                <p className="text-[11px] font-semibold text-indigo-400">Prompt Orchestrated</p>
                <p className="text-[10px] text-muted">Rich Context Injected</p>
              </div>
            </div>

            <div className="rounded-lg border border-sky-500/30 bg-sky-500/5 p-2.5 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-sky-400 shrink-0" />
              <div>
                <p className="text-[11px] font-semibold text-sky-400">Response Validated</p>
                <p className="text-[10px] text-muted">
                  {(validation_result.personalization_score * 100).toFixed(0)}% Score
                </p>
              </div>
            </div>
          </div>

          {/* ChronOS Synthesized Response */}
          <div className="rounded-xl border border-violet-500/30 bg-gradient-to-b from-violet-950/20 to-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="h-4 w-4 text-violet-400" />
              <h4 className="text-sm font-semibold text-violet-300">ChronOS Engine Response</h4>
            </div>
            <div className="text-sm leading-relaxed text-foreground whitespace-pre-line font-sans">
              {final_response}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* EXPLAINABILITY MODAL / DRAWER */}
      {showExplainabilityModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border border-violet-500/40 bg-card p-6 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-2.5">
                <Brain className="h-6 w-6 text-violet-400" />
                <div>
                  <h3 className="text-lg font-bold text-foreground">ChronOS Explainability Trace</h3>
                  <p className="text-xs text-muted">Full reasoning trace, memory linkage & prompt payload</p>
                </div>
              </div>
              <button
                onClick={() => setShowExplainabilityModal(false)}
                className="rounded-lg p-1.5 text-muted hover:bg-secondary hover:text-foreground"
              >
                ✕
              </button>
            </div>

            {/* Confidence & Time Window */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-border bg-secondary/40 p-4">
                <span className="text-xs text-muted font-medium">Confidence Score</span>
                <p className="text-2xl font-bold text-emerald-400 mt-1">
                  {(reasoning_trace.confidence_score * 100).toFixed(0)}%
                </p>
                <p className="text-[11px] text-muted mt-1">Factually grounded & personalized</p>
              </div>

              <div className="rounded-xl border border-border bg-secondary/40 p-4">
                <span className="text-xs text-muted font-medium">Affected Time Range</span>
                <p className="text-lg font-semibold text-violet-300 mt-1">
                  {reasoning_trace.affected_time_range}
                </p>
                <p className="text-[11px] text-muted mt-1">Context window span</p>
              </div>
            </div>

            {/* Step-by-Step Reasoning Trace */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-2">
                <Clock className="h-4 w-4 text-violet-400" /> System Reasoning Steps
              </h4>
              <ol className="space-y-2">
                {reasoning_trace.reasoning_steps.map((step, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-secondary/20 p-3 text-xs text-foreground"
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-500/20 text-[10px] font-bold text-violet-300">
                      {idx + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Supporting Memory Nodes */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-2">
                <Layers className="h-4 w-4 text-indigo-400" /> Linked Supporting Memory Nodes
              </h4>
              <div className="flex flex-wrap gap-2">
                {reasoning_trace.supporting_memory_ids.length > 0 ? (
                  reasoning_trace.supporting_memory_ids.map((id) => (
                    <span
                      key={id}
                      className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 font-mono text-xs text-indigo-300"
                    >
                      {id}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-muted">Initial session memory node linked</span>
                )}
              </div>
            </div>

            {/* Full Orchestrated User Prompt Preview */}
            <div className="space-y-2 border-t border-border pt-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-2">
                <FileCode className="h-4 w-4 text-sky-400" /> Orchestrated Prompt Payload Sent to LLM
              </h4>
              <pre className="h-48 overflow-y-auto rounded-xl border border-border bg-black/60 p-4 font-mono text-[11px] leading-relaxed text-emerald-400 whitespace-pre-wrap">
                {prompt_context?.user_prompt || "Prompt payload logged."}
              </pre>
            </div>

            <div className="flex justify-end pt-2">
              <Button onClick={() => setShowExplainabilityModal(false)}>Close Trace</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
