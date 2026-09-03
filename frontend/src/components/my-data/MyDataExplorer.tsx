"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { myDataApi, type Goal, type AnalysisPref, type GenesisMemory, type IdentityState, type Pattern } from "@/lib/myDataApi";
import { GoalsSection } from "./GoalsSection";
import { PreferencesSection } from "./PreferencesSection";
import { GenesisSection, IdentitySection } from "./GenesisAndIdentity";
import { SectionCard } from "./SectionCard";
import { DataControls } from "./DataControls";

type Tab = "overview" | "goals" | "preferences" | "genesis" | "identity";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "goals", label: "Goals" },
  { key: "preferences", label: "Preferences" },
  { key: "genesis", label: "Genesis Memory" },
  { key: "identity", label: "Identity" },
];

export function MyDataExplorer() {
  const { user, isLoading: authLoading } = useAuth();

  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [goals, setGoals] = useState<Goal[]>([]);
  const [prefs, setPrefs] = useState<AnalysisPref[]>([]);
  const [genesis, setGenesis] = useState<GenesisMemory | null>(null);
  const [identity, setIdentity] = useState<IdentityState | null>(null);
  const [patterns, setPatterns] = useState<Pattern[]>([]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [g, p, id, pat, mems] = await Promise.all([
        myDataApi.goals(false),
        myDataApi.preferences(),
        myDataApi.identity().catch(() => null),
        myDataApi.patterns().catch(() => []),
        myDataApi.memories(20, 0),
      ]);
      setGoals(g);
      setPrefs(p);
      setIdentity(id);
      setPatterns(pat);
      const gen = mems.find((m) => m.is_genesis) ?? null;
      setGenesis(gen);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load your data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    loadAll();
  }, [authLoading, loadAll]);

  const activeGoals = goals.filter((g) => g.status === "active");
  const firstName = user?.full_name?.split(" ")[0] ?? user?.email ?? "you";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Your Data</h1>
        <p className="text-sm text-muted mt-1">
          Everything Chronos remembers from your onboarding and beyond. You own this data — view, edit, and correct it any time.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex gap-1 overflow-x-auto border-b border-border/60 pb-px flex-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              aria-pressed={tab === t.key}
              className={`shrink-0 px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-all ${
                tab === t.key
                  ? "border-accent-foreground text-accent-foreground"
                  : "border-transparent text-muted hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={loadAll}
          disabled={loading}
          className="gap-1.5 text-xs text-muted hover:text-foreground shrink-0"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin motion-reduce:animate-none" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Loading skeleton */}
      {loading ? (
        <div role="status" className="space-y-4">
          <span className="sr-only">Loading your data...</span>
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-2xl border border-border bg-card h-32 animate-pulse motion-reduce:animate-none" />
          ))}
        </div>
      ) : (
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* ── Overview ── */}
          {tab === "overview" && (
            <div className="space-y-4">
              {/* Stats row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "Active goals", value: activeGoals.length },
                  { label: "Total goals", value: goals.filter((g) => g.status !== "abandoned").length },
                  { label: "Preferences", value: prefs.length },
                  { label: "Patterns", value: patterns.length },
                ].map((s) => (
                  <div key={s.label} className="rounded-xl border border-border bg-card px-4 py-3 text-center shadow-card">
                    <div className="text-2xl font-semibold tabular-nums text-foreground">{s.value}</div>
                    <div className="text-xs text-muted mt-0.5">{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Identity summary */}
              {identity && (
                <SectionCard title="Identity snapshot" description={`Version ${identity.version}`}>
                  <div className="flex flex-wrap gap-2">
                    {(identity.skills?.length ? identity.skills : (identity.traits ?? []).map((t) => t.trait)).slice(0, 8).map((t) => (
                      <span key={t} className="rounded-full border border-border bg-secondary/30 px-3 py-1 text-xs text-foreground/80">
                        {t}
                      </span>
                    ))}
                    {!identity.skills?.length && !identity.traits?.length && <p className="text-sm text-muted">No traits detected yet.</p>}
                  </div>
                </SectionCard>
              )}

              {/* Goals preview */}
              <SectionCard
                title="Active goals"
                action={
                  <button type="button" onClick={() => setTab("goals")} className="text-xs text-accent-foreground hover:underline">
                    Edit all →
                  </button>
                }
              >
                <div className="space-y-2">
                  {activeGoals.length === 0 && <p className="text-sm text-muted">No active goals.</p>}
                  {activeGoals.slice(0, 4).map((g) => (
                    <div key={g.id} className="flex items-center justify-between gap-3">
                      <span className="text-sm text-foreground/80 truncate">{g.title}</span>
                      <span className="text-xs text-muted shrink-0 border border-border rounded-full px-2 py-0.5">
                        {g.category.replace("_", " ")}
                      </span>
                    </div>
                  ))}
                </div>
              </SectionCard>

              {/* Patterns */}
              {patterns.length > 0 && (
                <SectionCard title="Behavioural patterns" description="Low-confidence baselines — strengthen over time as you add more memories.">
                  <div className="space-y-2">
                    {patterns.map((p) => (
                      <div key={p.id} className="flex items-start justify-between gap-3">
                        <span className="text-sm text-foreground/70">{p.pattern}</span>
                        <span className="shrink-0 text-xs text-muted">{Math.round(p.confidence * 100)}%</span>
                      </div>
                    ))}
                  </div>
                </SectionCard>
              )}

              {/* Data control (export / delete) */}
              <DataControls />
            </div>
          )}

          {tab === "goals" && <GoalsSection initialGoals={goals} />}
          {tab === "preferences" && <PreferencesSection initialPrefs={prefs} />}
          {tab === "genesis" && <GenesisSection initialMemory={genesis} />}
          {tab === "identity" && <IdentitySection initialIdentity={identity} />}

          {!loading && (
            <p className="pt-2 text-xs text-muted/70">
              Answers from {firstName}&apos;s onboarding, plus insights Chronos has added since.
            </p>
          )}
        </motion.div>
      )}
    </div>
  );
}