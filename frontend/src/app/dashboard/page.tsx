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
  ReturnContext,
  TimelineEvent,
  TemporalThread,
} from "@/lib/chronosApi";
import { onboardingApi, type OnboardingStatusResponse } from "@/lib/onboardingApi";
import { myDataApi, type Goal } from "@/lib/myDataApi";

import { ChronosRecoveryBanner } from "@/components/dashboard/ChronosRecoveryBanner";
import { FirstUseWelcome } from "@/components/chronos/FirstUseWelcome";
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
import { ReturnHook } from "@/components/chronos/ReturnHook";

type Tab = "overview" | "stories" | "timeline" | "insights" | "memories";

const TABS: { key: Tab; label: string; icon: React.ElementType }[] = [
  { key: "overview", label: "Home", icon: Sparkles },
  { key: "stories", label: "Stories", icon: GitBranch },
  { key: "timeline", label: "Timeline", icon: Clock },
  { key: "insights", label: "Insights", icon: Activity },
  { key: "memories", label: "Memories", icon: Database },
];

/**
 * Build optional starter prompts for a first-time user, grounded only in real
 * onboarding data (their active goals) — never hardcoded "assistant" personas
 * and never fabricated claims about the user. Falls back to honest, general
 * reflective prompts when no goal is available.
 */
function deriveStarterPrompts(goals: Goal[]): string[] {
  const prompts: string[] = [];
  const goal = goals.find((g) => g.status === "active") ?? goals[0];
  if (goal?.title?.trim()) {
    const title = goal.title.trim();
    prompts.push(`Let's talk about why "${title}" matters to you right now.`);
    prompts.push(`You set a goal: "${title}". Where would you like to start?`);
  }
  prompts.push("What has your attention today?");
  prompts.push("Tell me about a moment from this week you don't want to lose.");
  return prompts.slice(0, 4);
}

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

  // Phase 5C — first-use experience state
  const [onboardingGoals, setOnboardingGoals] = useState<Goal[]>([]);
  const [goalsLoaded, setGoalsLoaded] = useState(false);
  const [injectedPrompt, setInjectedPrompt] = useState<string | null>(null);
  const [hasFirstStory, setHasFirstStory] = useState(false);

  // Phase 5D — return-loop context (deterministic, grounded, once per visit)
  const [returnContext, setReturnContext] = useState<ReturnContext | null>(null);
  const [returnContextLoaded, setReturnContextLoaded] = useState(false);

  // Phase 5C — First-use detection, derived purely from existing loaded state.
  // A brand-new user (post-onboarding) has no engine conversations or stories.
  const isFirstUse = !isInitialLoad && interactions.length === 0 && threads.length === 0;

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
        chronosApi.getIdentity(signal).catch(() => null),
        chronosApi.getInteractions(20, signal),
        chronosApi.getThreads(signal),
        chronosApi.getMemories(signal),
        chronosApi.getReflections(signal),
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
      const ints = await chronosApi.getInteractions(20);
      setInteractions(ints);
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing interactions:", e);
    }
  }, [userId]);

  const refreshThreads = useCallback(async () => {
    try {
      const thrs = await chronosApi.getThreads();
      setThreads(thrs);
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing threads:", e);
    }
  }, [userId]);

  const refreshIdentity = useCallback(async () => {
    try {
      const id = await chronosApi.getIdentity();
      setIdentity(id);
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing identity:", e);
    }
  }, [userId]);

  const refreshMemories = useCallback(async () => {
    try {
      setMemories(await chronosApi.getMemories());
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing memories:", e);
    }
  }, [userId]);

  const refreshTimeline = useCallback(async () => {
    try {
      setTimeline(await chronosApi.getTimeline());
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing timeline:", e);
    }
  }, [userId]);

  const refreshReflections = useCallback(async () => {
    try {
      setReflections(await chronosApi.getReflections());
    } catch (e: any) {
      if (e.name !== "AbortError") console.error("Error refreshing reflections:", e);
    }
  }, [userId]);

  const refreshPatterns = useCallback(async () => {
    try {
      setPatterns(await chronosApi.getPatterns());
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

  // Phase 5C — Load onboarding goals once, only for a first-time user, to seed
  // grounded starter prompts. This is a single, targeted call (not a reload).
  useEffect(() => {
    if (!isFirstUse || goalsLoaded) return;
    let cancelled = false;
    myDataApi
      .goals(true)
      .then((goals) => {
        if (!cancelled) setOnboardingGoals(goals);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setGoalsLoaded(true);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isFirstUse, goalsLoaded]);

  // ── Phase 5D — Return-loop context, once per visit, only for returning
  // ── users. It is never gating, never pushy: a single grounded card on the
  // ── overview that disappears when nothing genuinely changed. Fetching it
  // ── advances the ledger marker so it renders at most once per session.
  useEffect(() => {
    if (isInitialLoad || isFirstUse || returnContextLoaded) return;
    let cancelled = false;
    chronosApi
      .getReturnContext()
      .then((ctx) => {
        if (!cancelled) setReturnContext(ctx);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setReturnContextLoaded(true);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isInitialLoad, isFirstUse, returnContextLoaded, activeTab]);

  const handleReturnHookContinue = (threadId: string) => {
    const thread = threads.find((t) => t.id === threadId);
    if (thread) handleContinueStory(thread);
  };


  // ── Message submission: targeted state update instead of full reload ────
  const handleResponseReceived = (response: EngineResponse) => {
    setLatestResponse(response);

    // Thinking ends the moment the response is visible — the conversation
    // never waits on secondary refreshes to settle.
    setIsThinking(false);

    // Phase 5C — First-story acknowledgement: only when the engine actually
    // created a new thread (real lifecycle data, not assumed).
    if (response.chronos_state?.temporal_lifecycle?.created) {
      setHasFirstStory(true);
    }

    // Stories: conditionally refresh if temporal lifecycle indicates activity
    const hasTemporalActivity =
      response.chronos_state?.temporal_lifecycle &&
      (response.chronos_state.temporal_lifecycle.created ||
        response.chronos_state.temporal_lifecycle.updated);

    // Targeted refresh: only what may have changed — run in the background so
    // the delivered response is never blocked by secondary data.
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
    void Promise.allSettled(refreshes);
  };

  const handleContinueStory = (thread: TemporalThread) => {
    setActiveThread(thread);
    setSelectedThread(null);
    setActiveTab("overview");
  };

  // Phase 5E-C — targeted, reload-free state updates for Stories/Memories.

  const handleUpdateThread = useCallback((updated: TemporalThread) => {
    setThreads((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    setActiveThread((active) => (active && active.id === updated.id ? updated : active));
  }, []);

  // When a story is archived, it must stop being an active continuation
  // context so the user is not resumed into a story they chose to end.
  const handleStoryArchived = useCallback((thread: TemporalThread) => {
    setActiveThread((active) => (active && active.id === thread.id ? null : active));
  }, []);

  const handleDeleteMemory = useCallback((memoryId: string) => {
    setMemories((prev) => prev.filter((m) => m.id !== memoryId));
  }, []);

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

  const starterPrompts = deriveStarterPrompts(onboardingGoals);

  const handlePickPrompt = (prompt: string) => setInjectedPrompt(prompt);

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
            <Link
              href="/me"
              className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-muted transition-colors hover:text-foreground hover:bg-secondary/60"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-xs font-medium text-accent-foreground">
                {firstName[0]?.toUpperCase() || "U"}
              </span>
              <span className="hidden text-xs font-medium sm:inline">{firstName}</span>
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

        {/* Compact hero — the greeting stays light so the conversation is the
            visual center. Counts live with their collections in each tab, not
            in a stats panel above the conversation. */}
        {!isFirstUse && (
          <section className="mx-auto w-full max-w-2xl">
            <p className="mb-1.5 text-xs font-medium uppercase tracking-widest text-accent-foreground">
              Your timeline
            </p>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Welcome back, <span className="text-accent-foreground">{firstName}</span>
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              A quiet space for everything you have shared. Talk below and ChronOS will build from
              there — one conversation at a time.
            </p>
          </section>
        )}

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

        {/* TAB: HOME (Conversation) — the conversation is the center. */}
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
              <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
                {isFirstUse && (
                  <FirstUseWelcome
                    firstName={firstName}
                    starterPrompts={starterPrompts}
                    onPickPrompt={handlePickPrompt}
                  />
                )}

                {/* Return context — leads the conversation when ChronOS has a
                    meaningful, grounded reason to (never forced, never noisy). */}
                {hasFirstStory && threads.length >= 1 && (
                  <div className="flex items-center gap-3 rounded-xl border border-accent/30 bg-accent/5 px-4 py-3">
                    <GitBranch className="h-4 w-4 shrink-0 text-accent-foreground" />
                    <p className="text-sm leading-relaxed text-foreground">
                      A new story is beginning — ChronOS will keep it connected to your timeline as it grows.
                    </p>
                    <button
                      onClick={() => setHasFirstStory(false)}
                      className="ml-auto shrink-0 rounded-full p-1 text-muted transition-colors hover:text-foreground"
                      aria-label="Dismiss"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                )}

                {!isFirstUse && returnContext && (
                  <ReturnHook
                    context={returnContext}
                    onContinueStory={handleReturnHookContinue}
                  />
                )}

                {/* Active story context — attached to the conversation input,
                    so it is unmistakable but never dominates. */}
                {activeThread && (
                  <div className="flex items-center gap-3 rounded-xl border border-accent/30 bg-accent/5 px-4 py-2.5">
                    <GitBranch className="h-4 w-4 shrink-0 text-accent-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-accent-foreground">
                        Continuing a story
                      </p>
                      <p className="truncate text-sm font-medium text-foreground">{activeThread.subject}</p>
                    </div>
                    <button
                      onClick={() => setActiveThread(null)}
                      className="shrink-0 rounded-full p-1.5 text-muted transition-colors hover:text-foreground"
                      aria-label="Clear active story"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                )}

                {/* Conversation */}
                <VoiceVideoRecorder
                  onResponseReceived={handleResponseReceived}
                  onThinkingStart={() => setIsThinking(true)}
                  onThinkingEnd={() => setIsThinking(false)}
                  userId={userId}
                  activeThread={activeThread}
                  defaultTab={isFirstUse ? "text" : "audio"}
                  injectedPrompt={injectedPrompt}
                  onInjectedPromptConsumed={() => setInjectedPrompt(null)}
                />
                <ChronosEngineFeed interactions={interactions} latestResponse={latestResponse} isThinking={isThinking} />

                {/* Secondary context — below the conversation so it does not
                    compete with it. Deliberately lighter visual weight. */}
                {!isFirstUse && (
                  <div className="mt-4 space-y-6 border-t border-border/40 pt-6">
                    <IdentityModelCard identity={identity} onRefresh={refreshIdentity} />
                    <ReflectionEngineView reflections={reflections.slice(0, 2)} />
                  </div>
                )}
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
                onUpdateThread={handleUpdateThread}
                onArchived={handleStoryArchived}
              />
            ) : (
              <JourneyView
                threads={threads}
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
            <MemoryGraphView memories={memories} onDelete={handleDeleteMemory} />
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