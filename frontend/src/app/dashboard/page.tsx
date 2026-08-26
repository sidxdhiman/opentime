"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Cpu,
  Clock,
  Activity,
  Database,
  Sparkles,
  GitBranch,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import {
  chronosApi,
  EngineResponse,
  IdentityProfile,
  InteractionRecord,
  MemoryItem,
  PatternItem,
  ReflectionInsight,
  TimelineEvent,
  TemporalThread,
} from "@/lib/chronosApi";
import { onboardingApi, type OnboardingStatusResponse } from "@/lib/onboardingApi";

import { ChronosRecoveryBanner } from "@/components/dashboard/ChronosRecoveryBanner";
import { VoiceVideoRecorder } from "@/components/chronos/VoiceVideoRecorder";
import { ChronosEngineFeed } from "@/components/chronos/ChronosEngineFeed";
import { IdentityModelCard } from "@/components/chronos/IdentityModelCard";
import { TimelineEngineView } from "@/components/chronos/TimelineEngineView";
import { ReflectionEngineView } from "@/components/chronos/ReflectionEngineView";
import { PatternDetectionView } from "@/components/chronos/PatternDetectionView";
import { MemoryGraphView } from "@/components/chronos/MemoryGraphView";
import { TemporalThreadDetailView } from "@/components/chronos/TemporalThreadDetailView";
import { JourneyView } from "@/components/chronos/JourneyView";
import { OverviewSkeleton } from "@/components/chronos/OverviewSkeleton";

type Tab = "overview" | "stories" | "timeline" | "insights" | "memories";

const TABS: { key: Tab; label: string; icon: React.ElementType }[] = [
  { key: "overview", label: "Home", icon: Sparkles },
  { key: "stories", label: "Stories", icon: GitBranch },
  { key: "timeline", label: "Timeline", icon: Clock },
  { key: "insights", label: "Insights", icon: Activity },
  { key: "memories", label: "Memories", icon: Database },
];

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const [latestResponse, setLatestResponse] = useState<EngineResponse | null>(null);
  const [interactions, setInteractions] = useState<InteractionRecord[]>([]);
  const [identity, setIdentity] = useState<IdentityProfile | null>(null);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [reflections, setReflections] = useState<ReflectionInsight[]>([]);
  const [patterns, setPatterns] = useState<PatternItem[]>([]);
  const [threads, setThreads] = useState<TemporalThread[]>([]);
  const [selectedThread, setSelectedThread] = useState<TemporalThread | null>(null);
  const [activeThread, setActiveThread] = useState<TemporalThread | null>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [isThinking, setIsThinking] = useState(false);
  const [onboarding, setOnboarding] = useState<OnboardingStatusResponse | null>(null);

  // Track which tabs have been loaded for lazy loading
  const [loadedTabs, setLoadedTabs] = useState<Set<Tab>>(new Set(["overview"]));

  // Abort controller for cancelling stale requests on unmount
  const abortRef = useRef<AbortController | null>(null);

  const userId = user?.id || "user_default";

  // ── Initial load: only data needed for the Home tab ────────────────────
  // Timeline, patterns are deferred to their respective tabs.
  // Threads and memories are loaded here because the Home stats bar shows
  // Stories and Memories counts.
  const loadAllData = useCallback(async (signal?: AbortSignal) => {
    try {
      const [id, ints, thrs, mems, refs] = await Promise.all([
        chronosApi.getIdentity(userId, signal).catch(() => null),
        chronosApi.getInteractions(userId, 20, signal),
        chronosApi.getThreads(userId, signal),
        chronosApi.getMemories(userId, signal),
        chronosApi.getReflections(userId, signal),
      ]);

      // Guard: don't update state if request was aborted (component unmounted)
      if (signal?.aborted) return;

      setIdentity(id);
      setInteractions(ints);
      setThreads(thrs);
      setMemories(mems);
      setReflections(refs);
    } catch (e: any) {
      if (e.name === "AbortError") return;
      console.error("Error loading ChronOS Engine data:", e);
    } finally {
      if (!signal?.aborted) setIsInitialLoad(false);
    }
  }, [userId]);

  // ── Targeted refresh functions (post-message, per-collection) ──────────
  // These silently ignore AbortError to prevent stale state updates after
  // the component unmounts or a newer request supersedes the old one.
  const refreshInteractions = useCallback(async () => {
    try {
      const ints = await chronosApi.getInteractions(userId);
      setInteractions(ints);
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing interactions:", e);
    }
  }, [userId]);

  const refreshThreads = useCallback(async () => {
    try {
      const thrs = await chronosApi.getThreads(userId);
      setThreads(thrs);
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing threads:", e);
    }
  }, [userId]);

  const refreshIdentity = useCallback(async () => {
    try {
      const id = await chronosApi.getIdentity(userId);
      setIdentity(id);
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing identity:", e);
    }
  }, [userId]);

  const refreshMemories = useCallback(async () => {
    try {
      setMemories(await chronosApi.getMemories(userId));
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing memories:", e);
    }
  }, [userId]);

  const refreshTimeline = useCallback(async () => {
    try {
      setTimeline(await chronosApi.getTimeline(userId));
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing timeline:", e);
    }
  }, [userId]);

  const refreshReflections = useCallback(async () => {
    try {
      setReflections(await chronosApi.getReflections(userId));
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing reflections:", e);
    }
  }, [userId]);

  const refreshPatterns = useCallback(async () => {
    try {
      setPatterns(await chronosApi.getPatterns(userId));
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing patterns:", e);
    }
  }, [userId]);

  const checkOnboarding = useCallback(async () => {
    try {
      setOnboarding(await onboardingApi.status());
    } catch {
      setOnboarding(null);
    }
  }, []);

  // ── Initial load ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    } else if (user) {
      const controller = new AbortController();
      abortRef.current = controller;
      loadAllData(controller.signal);
      checkOnboarding();
      return () => controller.abort();
    }
  }, [user, isLoading, router, loadAllData, checkOnboarding]);

  // ── Tab switch: lazy-load data for newly opened tabs ───────────────────
  useEffect(() => {
    if (isInitialLoad) return;

    // Each tab has data that may not have been fetched yet.
    // Only fetch when the tab is first opened.
    const tabDataLoaders: Partial<Record<Tab, () => Promise<void>>> = {
      stories: refreshThreads,
      timeline: refreshTimeline,
      insights: async () => {
        await Promise.all([refreshReflections(), refreshPatterns()]);
      },
      memories: refreshMemories,
    };

    if (!loadedTabs.has(activeTab) && tabDataLoaders[activeTab]) {
      setLoadedTabs((prev) => new Set(prev).add(activeTab));
      tabDataLoaders[activeTab]();
    }
  }, [activeTab, isInitialLoad, loadedTabs, refreshThreads, refreshTimeline, refreshReflections, refreshPatterns, refreshMemories]);

  // ── Message submission: targeted state update instead of full reload ────
  const handleResponseReceived = async (response: EngineResponse) => {
    setLatestResponse(response);

    // Update stats: conversations always increments
    // Stories: conditionally refresh if temporal lifecycle indicates activity
    const hasTemporalActivity =
      response.chronos_state?.temporal_lifecycle &&
      (response.chronos_state.temporal_lifecycle.created ||
        response.chronos_state.temporal_lifecycle.updated);

    // Targeted refresh: only what may have changed
    const refreshes: Promise<void>[] = [];

    // Identity always changes (evolves every message)
    refreshes.push(refreshIdentity());

    // Threads: refresh if temporal activity was detected
    if (hasTemporalActivity) {
      refreshes.push(refreshThreads());
    }

    // Interactions: not needed immediately — the response is already displayed
    // via latestResponse, and the full list will be used when the feed re-renders.
    // However, for stats accuracy (conversation count), refresh in background.
    refreshes.push(refreshInteractions().catch(() => {}));

    // Do NOT refresh: memories, timeline, reflections, patterns
    // These are either deferred to their tab or not per-message mutations.

    // Run targeted refreshes in parallel; conversation is already visible
    await Promise.allSettled(refreshes);

    // Always clear thinking state — even if refreshes threw internally
    setIsThinking(false);
  };

  const handleContinueStory = (thread: TemporalThread) => {
    setActiveThread(thread);
    setSelectedThread(null);
    setActiveTab("overview");
  };

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm font-medium text-muted">Opening your timeline...</span>
        </div>
      </div>
    );
  }

  const firstName = user.full_name?.split(" ")[0] ?? user.email;

  // Count conversations: interactions + latestResponse if it hasn't been
  // persisted into the interactions list yet (avoids double-counting).
  const latestIsPersisted = latestResponse
    ? interactions.some((i) => i.id === latestResponse.id)
    : false;
  const conversationCount = interactions.length + (latestResponse && !latestIsPersisted ? 1 : 0);

  const engineStats = [
    { value: threads.length, label: "Stories" },
    { value: conversationCount, label: "Conversations" },
    { value: memories.length, label: "Memories" },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-accent selection:text-accent-foreground">
      {/* Sticky Header */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-secondary">
              <Cpu className="h-5 w-5 text-accent-foreground" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <span className="text-lg font-semibold tracking-tight">OpenTime</span>
                <span className="rounded-full border border-border bg-secondary/60 px-2.5 py-0.5 text-[11px] font-medium text-muted">
                  ChronOS
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <Link href="/me">
              <button className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-muted transition-colors hover:text-foreground hover:bg-secondary/60">
                <div className="h-7 w-7 rounded-full bg-accent flex items-center justify-center text-xs font-medium text-accent-foreground">
                  {firstName[0]?.toUpperCase() || "U"}
                </div>
                <span className="text-xs font-medium hidden sm:inline">{firstName}</span>
              </button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-6 py-10 space-y-8">
        {onboarding && !onboarding.has_completed_session && (
          <ChronosRecoveryBanner
            hasActiveSession={onboarding.has_active_session}
            onRetry={checkOnboarding}
          />
        )}

        {/* Hero Section */}
        <section className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-widest text-accent-foreground">
              Your timeline
            </p>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Welcome back, <span className="text-accent-foreground">{firstName}</span>
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
              A quiet space for everything you have shared. Record a thought, glance at how you
              have changed, or revisit an old memory.
            </p>
          </div>

          <div className="flex items-center gap-6 rounded-2xl border border-border bg-card px-5 py-4 shadow-card">
            <GitBranch className="h-5 w-5 text-accent-foreground" />
            {engineStats.map((s, i) => (
              <React.Fragment key={s.label}>
                {i > 0 && <span className="h-8 w-px bg-border" aria-hidden />}
                <div>
                  <div className="text-xl font-semibold tabular-nums">{s.value}</div>
                  <div className="text-[10px] font-medium uppercase tracking-wider text-muted">
                    {s.label}
                  </div>
                </div>
              </React.Fragment>
            ))}
          </div>
        </section>

        {/* Tab Navigation */}
        <nav className="flex items-center gap-1 overflow-x-auto border-b border-border/60 pb-3">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-medium transition-all duration-200 ${
                activeTab === key
                  ? "bg-accent text-accent-foreground"
                  : "text-muted hover:bg-secondary/60 hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </nav>

        {/* TAB: HOME (Overview + Conversation) */}
        {activeTab === "overview" && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            {isInitialLoad ? (
              <OverviewSkeleton />
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-7 space-y-6">
              {activeThread && (
                <div className="flex items-center gap-3 rounded-xl border border-accent/30 bg-accent/5 px-4 py-3">
                  <GitBranch className="h-4 w-4 shrink-0 text-accent-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-muted">Continuing story</p>
                    <p className="text-sm font-medium text-foreground truncate">{activeThread.subject}</p>
                  </div>
                  <button
                    onClick={() => setActiveThread(null)}
                    className="shrink-0 rounded-full p-1 text-muted transition-colors hover:text-foreground"
                    aria-label="Clear active story"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}
              <VoiceVideoRecorder
                onResponseReceived={handleResponseReceived}
                onThinkingStart={() => setIsThinking(true)}
                onThinkingEnd={() => setIsThinking(false)}
                userId={userId}
                activeThread={activeThread}
              />
              <ChronosEngineFeed interactions={interactions} latestResponse={latestResponse} isThinking={isThinking} />
            </div>
            <div className="lg:col-span-5 space-y-6">
              <IdentityModelCard identity={identity} onRefresh={refreshIdentity} />
              <ReflectionEngineView reflections={reflections.slice(0, 2)} />
            </div>
              </div>
            )}
          </motion.div>
        )}

        {/* TAB: STORIES (Journey + Thread detail) */}
        {activeTab === "stories" && (
          <motion.div
            key="stories"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="max-w-4xl mx-auto"
          >
            {selectedThread ? (
              <TemporalThreadDetailView
                thread={selectedThread}
                onBack={() => setSelectedThread(null)}
                onContinueStory={handleContinueStory}
              />
            ) : (
              <JourneyView
                threads={threads}
                userId={userId}
                onSelectThread={setSelectedThread}
              />
            )}
          </motion.div>
        )}

        {/* TAB: TIMELINE */}
        {activeTab === "timeline" && (
          <motion.div
            key="timeline"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="max-w-4xl mx-auto"
          >
            <TimelineEngineView events={timeline} />
          </motion.div>
        )}

        {/* TAB: INSIGHTS (Reflections + Patterns) */}
        {activeTab === "insights" && (
          <motion.div
            key="insights"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="max-w-4xl mx-auto space-y-6"
          >
            <ReflectionEngineView reflections={reflections} />
            <PatternDetectionView patterns={patterns} />
          </motion.div>
        )}

        {/* TAB: MEMORIES */}
        {activeTab === "memories" && (
          <motion.div
            key="memories"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="max-w-4xl mx-auto"
          >
            <MemoryGraphView memories={memories} />
          </motion.div>
        )}
      </main>

      <footer className="border-t border-border/60 py-6 text-center text-xs text-muted">
        OpenTime
        <span className="mx-2 text-border" aria-hidden>/</span>
        All data belongs to you
      </footer>
    </div>
  );
}