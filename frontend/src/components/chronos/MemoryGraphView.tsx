"use client";

import React, { useState } from "react";
import { Database, Search, Link2, Tag, Mic, Video, FileText } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { MemoryItem } from "@/lib/chronosApi";

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
    if (type === "audio") return <Mic className="h-3.5 w-3.5 text-rose-400" />;
    if (type === "video") return <Video className="h-3.5 w-3.5 text-indigo-400" />;
    return <FileText className="h-3.5 w-3.5 text-sky-400" />;
  };

  return (
    <Card className="border-border/80 bg-card/90 shadow-xl overflow-hidden">
      <div className="bg-gradient-to-r from-violet-900/30 via-slate-900/40 to-card px-6 py-4 border-b border-border/60 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600 text-white font-bold text-xs shadow-md shadow-violet-600/30">
            <Database className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-bold tracking-tight text-foreground">User Memory System</h3>
            <p className="text-xs text-muted">Semantic Vector Store & Memory Link Graph</p>
          </div>
        </div>

        {/* Semantic Search Box */}
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search semantic memories..."
            className="w-full rounded-lg border border-border bg-secondary/60 pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-violet-500"
          />
        </div>
      </div>

      <CardContent className="p-6">
        {filteredMemories.length === 0 ? (
          <p className="text-center text-xs text-muted py-6">No matching memories found.</p>
        ) : (
          <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
            {filteredMemories.map((mem) => (
              <div
                key={mem.id}
                className="rounded-xl border border-border/80 bg-secondary/30 p-4 space-y-2 hover:border-violet-500/40 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5 text-[10px] font-mono text-muted">
                      {getInputIcon(mem.metadata?.input_type)} {mem.metadata?.input_type?.toUpperCase() || "TEXT"}
                    </span>
                    <span className="font-mono text-[10px] text-violet-400 font-semibold">
                      Importance: {(mem.importance_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <span className="text-[10px] text-muted font-mono">
                    {new Date(mem.timestamp).toLocaleString()}
                  </span>
                </div>

                <p className="text-xs text-foreground leading-relaxed font-medium">{mem.content}</p>

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/40 text-[10px]">
                  {/* Memory Links */}
                  <div className="flex items-center gap-1 text-muted font-mono">
                    <Link2 className="h-3 w-3 text-indigo-400" />
                    <span>
                      {mem.linked_memory_ids?.length || 0} Connected Memory Nodes
                    </span>
                  </div>

                  {/* Tags */}
                  <div className="flex items-center gap-1 flex-wrap">
                    {mem.tags?.map((tag) => (
                      <span
                        key={tag}
                        className="rounded bg-violet-500/10 border border-violet-500/20 px-1.5 py-0.5 text-[9px] text-violet-300"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
