"use client";

import React, { useState } from "react";
import { Database, Search, FileText, Trash2, X, Check, Music2, Video } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { chronosApi, MemoryItem } from "@/lib/chronosApi";
import { formatDate } from "@/lib/chronosConstants";
import { EmptyState } from "./EmptyState";

interface MemoryGraphViewProps {
  memories: MemoryItem[];
  onDelete?: (memoryId: string) => void;
}

export function MemoryGraphView({ memories, onDelete }: MemoryGraphViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorId, setErrorId] = useState<string | null>(null);

  const filteredMemories = memories.filter((m) =>
    m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.tags?.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const renderMedia = (mem: MemoryItem) => {
    const type = mem.metadata?.input_type;
    const url = chronosApi.mediaUrl(mem.metadata?.media_url);
    if (!url) return null;
    if (type === "video") {
      return (
        <video
          src={url}
          controls
          preload="metadata"
          className="mt-3 w-full rounded-lg border border-border bg-black object-cover"
        />
      );
    }
    if (type === "audio") {
      return (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-border bg-secondary/40 px-3 py-2">
          <Music2 className="h-4 w-4 text-muted" />
          <audio src={url} controls preload="metadata" className="h-8 flex-1" />
        </div>
      );
    }
    return null;
  };

  const handleConfirm = async (mem: MemoryItem) => {
    setDeletingId(mem.id);
    setErrorId(null);
    try {
      await chronosApi.deleteMemory(mem.id);
      // Update local state via the parent's targeted callback — no reload.
      onDelete?.(mem.id);
    } catch {
      setErrorId(mem.id);
    } finally {
      setDeletingId(null);
      setConfirmingId(null);
    }
  };

  const handleCancel = () => {
    setConfirmingId(null);
    setErrorId(null);
  };

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-border/60 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <Database className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Memories</h3>
            <p className="text-xs text-muted">Everything you have shared, in your own words</p>
          </div>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search memories..."
            className="w-full rounded-lg border border-border bg-secondary/40 py-1.5 pl-9 pr-3 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
      </div>

      <CardContent className="p-6">
        {filteredMemories.length === 0 && searchQuery ? (
          <p className="py-6 text-center text-sm text-muted">No memories match your search.</p>
        ) : filteredMemories.length === 0 ? (
          <EmptyState
            icon={Database}
            title="Your memories, in your own words"
            description="Everything you share is kept here exactly as you said it. Add your first one on the Home tab and it will appear here."
          />
        ) : (
          <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
            {filteredMemories.map((mem) => {
              const confirming = confirmingId === mem.id;
              return (
                <div
                  key={mem.id}
                  className="rounded-xl border border-border bg-secondary/20 p-4 transition-all duration-200 hover:bg-secondary/40"
                >
                  {confirming ? (
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-xs font-medium text-foreground">Delete this memory?</p>
                        <p className="mt-1 text-xs leading-relaxed text-muted">
                          This removes it from ChronOS memory permanently and cannot be undone. Your
                          stored moments and past conversations are left intact.
                        </p>
                        {errorId === mem.id && (
                          <p className="mt-1 text-xs text-destructive">Could not delete this memory. Please try again.</p>
                        )}
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleCancel}
                          className="gap-1 text-xs"
                        >
                          <X className="h-3 w-3" /> Keep
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleConfirm(mem)}
                          disabled={deletingId === mem.id}
                          className="gap-1 text-xs"
                        >
                          <Check className="h-3 w-3" />
                          {deletingId === mem.id ? "Deleting..." : "Delete permanently"}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <span className="text-[11px] tabular-nums text-muted">
                          Added {formatDate(mem.timestamp)}
                        </span>
                        <button
                          onClick={() => { setConfirmingId(mem.id); setErrorId(null); }}
                          className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-muted transition-colors hover:bg-secondary/60 hover:text-destructive"
                          aria-label="Delete this memory"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete
                        </button>
                      </div>

                      <p className="text-sm leading-relaxed text-foreground">{mem.content}</p>

                      {renderMedia(mem)}

                      {mem.tags && mem.tags.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {mem.tags.map((tag) => (
                            <span key={tag} className="rounded border border-border bg-secondary/40 px-1.5 py-0.5 text-[11px] text-muted">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
