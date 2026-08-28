"use client";

import React, { useState } from "react";
import { Database, Search, Link2, FileText, Mic, Video } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { chronosApi, MemoryItem } from "@/lib/chronosApi";
import { formatDate } from "@/lib/chronosConstants";
import { EmptyState } from "./EmptyState";

interface MemoryGraphViewProps {
  memories: MemoryItem[];
}

export function MemoryGraphView({ memories }: MemoryGraphViewProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredMemories = memories.filter((m) =>
    m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.tags?.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const getInputIcon = (type?: string) => {
    if (type === "audio") return <Mic className="h-3.5 w-3.5" />;
    if (type === "video") return <Video className="h-3.5 w-3.5" />;
    return <FileText className="h-3.5 w-3.5" />;
  };

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
        <audio
          src={url}
          controls
          preload="metadata"
          className="mt-3 h-9 w-full"
        />
      );
    }
    return null;
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
            {filteredMemories.map((mem) => (
              <div
                key={mem.id}
                className="rounded-xl border border-border bg-secondary/20 p-4 transition-all duration-200 hover:bg-secondary/40"
              >
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-[11px] text-muted">
                    <span className="flex items-center gap-1 rounded-md border border-border bg-secondary/40 px-2 py-0.5">
                      {getInputIcon(mem.metadata?.input_type)} {mem.metadata?.input_type?.toUpperCase() || "TEXT"}
                    </span>
                    <span>Importance {(mem.importance_score * 100).toFixed(0)}%</span>
                  </div>
                  <span className="text-[11px] tabular-nums text-muted">
                    {formatDate(mem.timestamp)}
                  </span>
                </div>

                <p className="text-sm leading-relaxed text-foreground">{mem.content}</p>

                {renderMedia(mem)}

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border/40 pt-3 text-[11px] text-muted">
                  <span className="flex items-center gap-1">
                    <Link2 className="h-3 w-3" />
                    {mem.linked_memory_ids?.length || 0} connected
                  </span>
                  {mem.tags && mem.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {mem.tags.map((tag) => (
                        <span key={tag} className="rounded border border-border bg-secondary/40 px-1.5 py-0.5">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}