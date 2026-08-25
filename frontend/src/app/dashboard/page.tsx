"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Cpu,
  UserCheck,
  Clock,
  ArrowRightLeft,
  Activity,
  Database,
  RefreshCw,
  Sparkles,
  User,
  Mic,
  GitBranch,
  Compass,
} from "lucide-react";
import { Button } from "@/components/ui/button";
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
import { TemporalThreadListView } from "@/components/chronos/TemporalThreadListView";
import { TemporalThreadDetailView } from "@/components/chronos/TemporalThreadDetailView";
import { JourneyView } from "@/components/chronos/JourneyView";

type Tab = "overview" | "journey" | "identity" | "timeline" | "threads" | "reflections" | "patterns" | "memories";

const TABS: { key: Tab; label: string; icon: React.ElementType }[] = [
  { key: "overview", label: "Overview", icon: Sparkles },
  { key: "journey", label: "Journey", icon: Compass },
  { key: "identity", label: "Identity Model", icon: UserCheck },
  { key: "timeline", label: "Timeline", icon: Clock },
  { key: "threads", label: "Threads", icon: GitBranch },
  { key: "reflections", label: "Reflections", icon: ArrowRightLeft },
  { key: "patterns", label: "Patterns", icon: Activity },
  { key: "memories", label: "Memories", icon: Database },
];

export default function DashboardPage() {
  const { user, isLoading, logout } = useAuth();
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
  const [isDataLoading, setIsDataLoading] = useState(false);
  const [onboarding, setOnboarding] = useState<OnboardingStatusResponse | null>(null);

  const userId = user?.id || "user_default";

  const loadEngineData = useCallback(async () => {
    setIsDataLoading(true);
    try {
      const [id, mems, time, refs, pats, thrs, ints] = await Promise.all([
        chronosApi.getIdentity(userId).catch(() => null),
        chronosApi.getMemories(userId),
        chronosApi.getTimeline(userId),
        chronosApi.getReflections(userId),
        chronosApi.getPatterns(userId),
        chronosApi.getThreads(userId),
        chronosApi.getInteractions(userId),
      ]);

      setIdentity(id);
      setMemories(mems);
      setTimeline(time);
      setReflections(refs);
      setPatterns(pats);
      setThreads(thrs);
      setInteractions(ints);
    } catch (e) {
      console.error("Error loading ChronOS Engine data:", e);
    } finally {
      setIsDataLoading(false);
    }
  }, [userId]);

  const checkOnboarding = useCallback(async () => {
    try {
      setOnboarding(await onboardingApi.status());
    } catch {
      setOnboarding(null);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    } else if (user) {
      loadEngineData();
      checkOnboarding();
    }
  }, [user, isLoading, router, loadEngineData, checkOnboarding]);

  const handleResponseReceived = async (response: EngineResponse) => {
    setLatestResponse(response);
    await loadEngineData();
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
  const engineStats = [
    { value: memories.length, label: "Memories" },
    { value: timeline.length, label: "Events" },
    { value: reflections.length, label: "Reflections" },
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
              <Button variant="ghost" size="sm" className="h-8 text-xs text-muted hover:text-foreground gap-1.5">
                <User className="h-3.5 w-3.5" /> Me
              </Button>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={loadEngineData}
              disabled={isDataLoading}
              className="h-8 text-xs text-muted hover:text-foreground gap-1.5"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isDataLoading ? "animate-spin" : ""}`} /> Refresh
            </Button>
            <Button variant="ghost" size="sm" onClick={() => logout()} className="h-8 text-xs text-muted hover:text-destructive hover:bg-destructive/10">
              Sign out
            </Button>
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
            <Mic className="h-5 w-5 text-accent-foreground" />
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

        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-8"
          >
            <div className="lg:col-span-7 space-y-6">
              <VoiceVideoRecorder onResponseReceived={handleResponseReceived} userId={userId} />
              <ChronosEngineFeed interactions={interactions} latestResponse={latestResponse} />
            </div>
            <div className="lg:col-span-5 space-y-6">
              <IdentityModelCard identity={identity} onRefresh={loadEngineData} />
              <ReflectionEngineView reflections={reflections.slice(0, 2)} />
            </div>
          </motion.div>
        )}

        {activeTab !== "overview" && (
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            {activeTab === "journey" && (
              <div className="max-w-4xl mx-auto">
                {selectedThread ? (
                  <TemporalThreadDetailView
                    thread={selectedThread}
                    onBack={() => setSelectedThread(null)}
                  />
                ) : (
                  <JourneyView
                    threads={threads}
                    userId={userId}
                    onSelectThread={setSelectedThread}
                  />
                )}
              </div>
            )}
            {activeTab === "identity" && (
              <div className="max-w-4xl mx-auto">
                <IdentityModelCard identity={identity} onRefresh={loadEngineData} />
              </div>
            )}
            {activeTab === "timeline" && (
              <div className="max-w-4xl mx-auto">
                <TimelineEngineView events={timeline} />
              </div>
            )}
            {activeTab === "threads" && (
              <div className="max-w-4xl mx-auto">
                {selectedThread ? (
                  <TemporalThreadDetailView
                    thread={selectedThread}
                    onBack={() => setSelectedThread(null)}
                  />
                ) : (
                  <TemporalThreadListView
                    threads={threads}
                    onSelectThread={setSelectedThread}
                  />
                )}
              </div>
            )}
            {activeTab === "reflections" && (
              <div className="max-w-4xl mx-auto">
                <ReflectionEngineView reflections={reflections} />
              </div>
            )}
            {activeTab === "patterns" && (
              <div className="max-w-4xl mx-auto">
                <PatternDetectionView patterns={patterns} />
              </div>
            )}
            {activeTab === "memories" && (
              <div className="max-w-4xl mx-auto">
                <MemoryGraphView memories={memories} />
              </div>
            )}
          </motion.div>
        )}
      </main>

      <footer className="border-t border-border/60 py-6 text-center text-xs text-muted">
        OpenTime ChronOS Engine
        <span className="mx-2 text-border" aria-hidden>/</span>
        All data belongs to user
      </footer>
    </div>
  );
}