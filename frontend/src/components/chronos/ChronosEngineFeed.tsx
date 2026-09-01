"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Brain,
  Eye,
  X,
  FileText,
  Mic,
  Video,
  MessageSquare,
  Sparkles,
  Link2,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EngineResponse, InteractionRecord } from "@/lib/chronosApi";
import {
  buildExplainability,
  buildHistoricalExplainability,
  Explanation,
} from "@/lib/explainability";
import { PastSelfMomentCard } from "./PastSelfMomentCard";

interface ChronosEngineFeedProps {
  interactions: InteractionRecord[];
  latestResponse: EngineResponse | null;
  isThinking?: boolean;
}

type ExplanationTarget =
  | { kind: "live" }
  | { kind: "history"; record: InteractionRecord };

export function ChronosEngineFeed({ interactions, latestResponse, isThinking }: ChronosEngineFeedProps) {
  const [explanationTarget, setExplanationTarget] = useState<ExplanationTarget | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Keep the newest content in view. block:"end" anchors the feed bottom to
    // the viewport bottom so the latest message stays visible instead of
    // being scrolled past to the top.
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [interactions.length, latestResponse, isThinking]);

  const openLiveExplanation = useCallback(() => setExplanationTarget({ kind: "live" }), []);
  const openHistoryExplanation = useCallback(
    (record: InteractionRecord) => setExplanationTarget({ kind: "history", record }),
    [],
  );
  const closeExplanation = useCallback(() => setExplanationTarget(null), []);

  const hasHistory = interactions.length > 0;
  const hasLatest = latestResponse !== null;

  // Deduplicate: exclude any persisted interaction whose id matches the
  // in-memory latestResponse to avoid rendering the same message twice.
  // The API returns newest-first; render history oldest→newest so the latest
  // message always sits naturally at the bottom of the conversation.
  const filteredInteractions = (hasLatest
    ? interactions.filter((r) => r.id !== latestResponse!.id)
    : interactions
  )
    .slice()
    .sort(
      (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );

  // The modal always explains exactly one inspected message: either the live
  // latest response, or the specific historical record chosen. It can never
  // drift onto another interaction's data.
  const explanationToShow: Explanation | null =
    explanationTarget?.kind === "live" && latestResponse
      ? buildExplainability(latestResponse)
      : explanationTarget?.kind === "history"
        ? buildHistoricalExplainability(explanationTarget.record)
        : null;

  if (!hasHistory && !hasLatest) {
    return (
      <Card>
        <CardContent className="flex min-h-[220px] flex-col items-center justify-center p-8 text-center">
          <MessageSquare className="mb-4 h-9 w-9 text-muted" />
          <h4 className="text-[15px] font-semibold">Say something</h4>
          <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">
            Finish the sentence above or start fresh. ChronOS will meet you here and remember what
            you share — building on it the next time you return.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Historical interactions */}
      {filteredInteractions.map((record) => (
        <InteractionBlock
          key={record.id}
          record={record}
          onExplain={() => openHistoryExplanation(record)}
        />
      ))}

      {/* Current session response — full experience with explainability */}
      {hasLatest && (
        <LatestResponseBlock response={latestResponse!} onExplain={openLiveExplanation} />
      )}

      {/* Thinking bubble — shown while ChronOS is processing a new message */}
      {isThinking && <ThinkingBubble />}

      <div ref={bottomRef} />

      {/* Explainability modal — only for the message being inspected */}
      {explanationToShow && (
        <ExplainabilityModal explanation={explanationToShow} onClose={closeExplanation} />
      )}
    </div>
  );
}

/* ── Historical interaction block ──────────────────────────────────────── */

function InteractionBlock({
  record,
  onExplain,
}: {
  record: InteractionRecord;
  onExplain: () => void;
}) {
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
              <button
                onClick={onExplain}
                className="ml-auto flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] text-muted transition-colors hover:bg-secondary hover:text-foreground"
                title="Why did ChronOS respond this way?"
                aria-label="Why did ChronOS respond this way?"
              >
                <Eye className="h-3 w-3" />
              </button>
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
              <button
                onClick={onExplain}
                className="ml-auto flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] text-muted transition-colors hover:bg-secondary hover:text-foreground"
                title="Why did ChronOS respond this way?"
                aria-label="Why did ChronOS respond this way?"
              >
                <Eye className="h-3 w-3" />
              </button>
            </div>
            <div className="whitespace-pre-line text-sm leading-relaxed text-foreground">
              {displayResponse}
            </div>
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
  explanation,
  onClose,
}: {
  explanation: Explanation;
  onClose: () => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Focus moves into the dialog when it opens, and Escape closes it.
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="explainability-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="relative max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-lift focus:outline-none"
      >
        <div className="mb-5 flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <Brain className="h-4.5 w-4.5" />
            </div>
            <div>
              <h3 id="explainability-title" className="text-[15px] font-semibold">
                Why this response?
              </h3>
              <p className="text-xs text-muted">
                A plain-language look at what ChronOS drew on
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted transition-colors hover:bg-secondary hover:text-foreground"
            aria-label="Close explanation"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-5">
          <p className="text-sm leading-relaxed text-foreground">{explanation.lead}</p>

          {explanation.sections.length > 0 && (
            <div className="space-y-4">
              {explanation.sections.map((section) => (
                <section key={section.title}>
                  <h4 className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted">
                    {section.title === "What I noticed" ? (
                      <Sparkles className="h-3.5 w-3.5 text-accent-foreground" />
                    ) : (
                      <Link2 className="h-3.5 w-3.5 text-accent-foreground" />
                    )}
                    {section.title}
                  </h4>
                  <div className="mt-2 space-y-2">
                    {section.paragraphs.map((paragraph, idx) => (
                      <p
                        key={idx}
                        className="break-words rounded-xl border border-border bg-secondary/20 px-3.5 py-2.5 text-sm leading-relaxed text-foreground/90"
                      >
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}

          <div className="space-y-2.5">
            <h4 className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted">
              <Layers className="h-3.5 w-3.5 text-accent-foreground" /> Based on
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {explanation.sources.map((source) => (
                <span
                  key={source}
                  className="rounded-full border border-border bg-secondary/40 px-2.5 py-1 text-xs text-foreground/80"
                >
                  {source}
                </span>
              ))}
            </div>
          </div>

          {!explanation.limited && (
            <p className="border-t border-border/40 pt-3 text-xs text-muted">
              {explanation.uncertainty}
            </p>
          )}
        </div>

        <div className="mt-6 flex justify-end">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ── Thinking bubble ───────────────────────────────────────────────────── */

function ThinkingBubble() {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl rounded-bl-md border border-border bg-card px-4 py-3">
        <div className="mb-1.5 flex items-center gap-1.5">
          <Brain className="h-3 w-3 text-muted" />
          <span className="text-[10px] font-medium text-muted">ChronOS</span>
        </div>
        <div className="flex items-center gap-1.5 py-1">
          <span className="h-2 w-2 animate-bounce rounded-full bg-muted/60 [animation-delay:0ms]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-muted/60 [animation-delay:150ms]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-muted/60 [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}