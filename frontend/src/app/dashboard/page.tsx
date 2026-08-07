"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Cpu,
  UserCheck,
  Clock,
  ArrowRightLeft,
  Activity,
  Database,
  Sparkles,
  RefreshCw,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import {
  chronosApi,
  EngineResponse,
  IdentityProfile,
  MemoryItem,
  PatternItem,
  ReflectionInsight,
  TimelineEvent,
} from "@/lib/chronosApi";

import { VoiceVideoRecorder } from "@/components/chronos/VoiceVideoRecorder";
import { ChronosEngineFeed } from "@/components/chronos/ChronosEngineFeed";
import { IdentityModelCard } from "@/components/chronos/IdentityModelCard";
import { TimelineEngineView } from "@/components/chronos/TimelineEngineView";
import { ReflectionEngineView } from "@/components/chronos/ReflectionEngineView";
import { PatternDetectionView } from "@/components/chronos/PatternDetectionView";
import { MemoryGraphView } from "@/components/chronos/MemoryGraphView";

export default function DashboardPage() {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<"overview" | "identity" | "timeline" | "reflections" | "patterns" | "memories">("overview");

  const [latestResponse, setLatestResponse] = useState<EngineResponse | null>(null);
  const [identity, setIdentity] = useState<IdentityProfile | null>(null);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [reflections, setReflections] = useState<ReflectionInsight[]>([]);
  const [patterns, setPatterns] = useState<PatternItem[]>([]);
  const [isDataLoading, setIsDataLoading] = useState(false);

  const userId = user?.id || "user_default";

  // Fetch engine state
  const loadEngineData = useCallback(async () => {
    setIsDataLoading(true);
    try {
      // First try fetching identity; if fails or empty, seed state
      let id = await chronosApi.getIdentity(userId).catch(() => null);
      if (!id) {
        await chronosApi.seedState(userId);
        id = await chronosApi.getIdentity(userId).catch(() => null);
      }
      setIdentity(id);

      const [mems, time, refs, pats] = await Promise.all([
        chronosApi.getMemories(userId),
        chronosApi.getTimeline(userId),
        chronosApi.getReflections(userId),
        chronosApi.getPatterns(userId),
      ]);

      setMemories(mems);
      setTimeline(time);
      setReflections(refs);
      setPatterns(pats);
    } catch (e) {
      console.error("Error loading ChronOS Engine data:", e);
    } finally {
      setIsDataLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    } else if (user) {
      loadEngineData();
    }
  }, [user, isLoading, router, loadEngineData]);

  const handleResponseReceived = async (response: EngineResponse) => {
    setLatestResponse(response);
    await loadEngineData();
  };

  const handleSeedState = async () => {
    setIsDataLoading(true);
    await chronosApi.seedState(userId);
    await loadEngineData();
  };

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-3 border-violet-500 border-t-transparent" />
          <span className="text-sm font-semibold text-violet-400">Initializing ChronOS Engine...</span>
        </div>
      </div>
    );
  }

  const firstName = user.full_name?.split(" ")[0] ?? user.email;

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-violet-500 selection:text-white">
      {/* Sticky Header */}
      <header className="sticky top-0 z-30 border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 via-indigo-600 to-cyan-500 text-white font-black shadow-lg shadow-violet-600/30">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-white via-violet-200 to-indigo-300 bg-clip-text text-transparent">
                  OpenTime
                </span>
                <span className="rounded-full bg-violet-500/10 border border-violet-500/30 px-2.5 py-0.5 text-[11px] font-bold text-violet-300">
                  ChronOS Core Engine
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSeedState}
              disabled={isDataLoading}
              className="h-8 text-xs border-violet-500/30 bg-violet-500/10 text-violet-300 hover:bg-violet-500/20 gap-1.5"
            >
              <Zap className="h-3.5 w-3.5" /> Seed Historical Context
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={loadEngineData}
              disabled={isDataLoading}
              className="h-8 text-xs gap-1 text-muted hover:text-foreground"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isDataLoading ? "animate-spin" : ""}`} /> Refresh
            </Button>

            <Button variant="ghost" size="sm" onClick={() => logout()} className="h-8 text-xs text-rose-400 hover:bg-rose-500/10">
              Sign out
            </Button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-6 py-8 space-y-8">
        {/* Hero Section */}
        <section className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/60 pb-6">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-foreground">
              Welcome back, <span className="text-violet-400">{firstName}</span>
            </h1>
            <p className="text-sm text-muted mt-1 max-w-2xl leading-relaxed">
              ChronOS is your model-agnostic reasoning, memory, and orchestration layer. Upload or record voice and video notes to continuously evolve your identity profile and timeline.
            </p>
          </div>

          <div className="flex items-center gap-4 bg-secondary/40 border border-border/80 rounded-2xl p-4 shrink-0">
            <div className="text-center px-2">
              <span className="text-2xl font-bold text-violet-400 font-mono">{memories.length}</span>
              <p className="text-[10px] text-muted font-medium uppercase tracking-wider">Memories</p>
            </div>
            <div className="h-8 w-px bg-border" />
            <div className="text-center px-2">
              <span className="text-2xl font-bold text-indigo-400 font-mono">{timeline.length}</span>
              <p className="text-[10px] text-muted font-medium uppercase tracking-wider">Events</p>
            </div>
            <div className="h-8 w-px bg-border" />
            <div className="text-center px-2">
              <span className="text-2xl font-bold text-emerald-400 font-mono">{reflections.length}</span>
              <p className="text-[10px] text-muted font-medium uppercase tracking-wider">Reflections</p>
            </div>
          </div>
        </section>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-border/60">
          <button
            onClick={() => setActiveTab("overview")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === "overview"
                ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                : "text-muted hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <Cpu className="h-4 w-4" /> Overview & Interactive Feed
          </button>
          <button
            onClick={() => setActiveTab("identity")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === "identity"
                ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                : "text-muted hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <UserCheck className="h-4 w-4" /> Identity Model (v{identity?.version || 1})
          </button>
          <button
            onClick={() => setActiveTab("timeline")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === "timeline"
                ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                : "text-muted hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <Clock className="h-4 w-4" /> Timeline Engine
          </button>
          <button
            onClick={() => setActiveTab("reflections")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === "reflections"
                ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                : "text-muted hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <ArrowRightLeft className="h-4 w-4" /> Past vs Current Self
          </button>
          <button
            onClick={() => setActiveTab("patterns")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === "patterns"
                ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                : "text-muted hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <Activity className="h-4 w-4" /> Pattern Detection
          </button>
          <button
            onClick={() => setActiveTab("memories")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === "memories"
                ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                : "text-muted hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <Database className="h-4 w-4" /> Memory Graph ({memories.length})
          </button>
        </div>

        {/* TAB 1: OVERVIEW & INTERACTIVE FEED */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left Column: Multimodal Input & ChronOS Output */}
            <div className="lg:col-span-7 space-y-6">
              <VoiceVideoRecorder onResponseReceived={handleResponseReceived} userId={userId} />
              <ChronosEngineFeed response={latestResponse} />
            </div>

            {/* Right Column: Evolving Identity Profile & Reflection Insights Highlights */}
            <div className="lg:col-span-5 space-y-6">
              <IdentityModelCard identity={identity} onRefresh={loadEngineData} />
              <ReflectionEngineView reflections={reflections.slice(0, 2)} />
            </div>
          </div>
        )}

        {/* TAB 2: IDENTITY MODEL */}
        {activeTab === "identity" && (
          <div className="max-w-4xl mx-auto space-y-6">
            <IdentityModelCard identity={identity} onRefresh={loadEngineData} />
          </div>
        )}

        {/* TAB 3: TIMELINE ENGINE */}
        {activeTab === "timeline" && (
          <div className="max-w-4xl mx-auto space-y-6">
            <TimelineEngineView events={timeline} />
          </div>
        )}

        {/* TAB 4: REFLECTIONS (PAST VS CURRENT SELF) */}
        {activeTab === "reflections" && (
          <div className="max-w-4xl mx-auto space-y-6">
            <ReflectionEngineView reflections={reflections} />
          </div>
        )}

        {/* TAB 5: PATTERN DETECTION */}
        {activeTab === "patterns" && (
          <div className="max-w-4xl mx-auto space-y-6">
            <PatternDetectionView patterns={patterns} />
          </div>
        )}

        {/* TAB 6: MEMORY SYSTEM GRAPH */}
        {activeTab === "memories" && (
          <div className="max-w-4xl mx-auto space-y-6">
            <MemoryGraphView memories={memories} />
          </div>
        )}
      </main>

      <footer className="border-t border-border/60 py-6 text-center text-xs text-muted">
        OpenTime ChronOS Engine • Model-Agnostic Intelligence Layer • All data belongs to user
      </footer>
    </div>
  );
}