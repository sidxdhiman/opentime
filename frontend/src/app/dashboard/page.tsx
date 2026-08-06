"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowUpRight,
  BookHeart,
  BrainCircuit,
  CalendarDays,
  Footprints,
  MessageSquareText,
  Sparkles,
  Tags,
  TrendingUp,
  WandSparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";

const chapters = [
  {
    date: "Mar 2024",
    title: "The threshold",
    body: "First entries about leaving the familiar path. A lot of uncertainty — the memory analysis reads a leap, not a break.",
    tags: [
      { label: "Career", tone: "text-sky bg-sky/10 border-sky/30" },
      { label: "Courage", tone: "text-violet bg-violet/10 border-violet/30" },
    ],
    accent: "#0284c7",
    phase: 0,
  },
  {
    date: "Jul 2024",
    title: "Building in public",
    body: "Daily notes on shipping the early product. This is where the discipline of a weekly reflection formed.",
    tags: [
      { label: "Craft", tone: "text-emerald bg-emerald/10 border-emerald/30" },
      { label: "Discipline", tone: "text-amber bg-amber/10 border-amber/30" },
    ],
    accent: "#059669",
    phase: 1,
  },
  {
    date: "Nov 2024",
    title: "The slow season",
    body: "Quieter months about burnout and rest. The engine flagged this as a turning point — growth stopped being linear.",
    tags: [
      { label: "Rest", tone: "text-rose bg-rose/10 border-rose/30" },
      { label: "Reflection", tone: "text-violet bg-violet/10 border-violet/30" },
    ],
    accent: "#e11d48",
    phase: 2,
  },
  {
    date: "Feb 2025",
    title: "Recommitment",
    body: "You returned with clearer values than you left with. Your writing shifted from 'should' to 'want'.",
    tags: [
      { label: "Values", tone: "text-amber bg-amber/10 border-amber/30" },
      { label: "Focus", tone: "text-sky bg-sky/10 border-sky/30" },
    ],
    accent: "#d97706",
    phase: 3,
  },
  {
    date: "Today",
    title: "Who you are now",
    body: "Your most recent memories feel lighter. Gratitude and teaching keep surfacing — the engine sees your current self.",
    tags: [
      { label: "Gratitude", tone: "text-emerald bg-emerald/10 border-emerald/30" },
      { label: "Mentorship", tone: "text-sky bg-sky/10 border-sky/30" },
    ],
    accent: "#7c3aed",
    phase: 4,
  },
];

const insights = [
  {
    icon: TrendingUp,
    text: "Your writing has shifted from 'should' to 'want' — a sign of growing intrinsic motivation.",
  },
  {
    icon: MessageSquareText,
    text: "Mentorship appears 3.2× more often in the last 6 months than in the year before.",
  },
  {
    icon: BookHeart,
    text: "You mention 'rest' more after demanding seasons — you have built recovery into your rhythm.",
  },
];

const themes = [
  { label: "Career & craft", pct: 82, tone: "bg-sky" },
  { label: "Rest & recovery", pct: 64, tone: "bg-rose" },
  { label: "Relationships", pct: 57, tone: "bg-violet" },
  { label: "Creativity", pct: 43, tone: "bg-emerald" },
];

const stats = [
  { icon: BookHeart, label: "Memories captured", value: "128" },
  { icon: Tags, label: "Themes discovered", value: "34" },
  { icon: WandSparkles, label: "Insights generated", value: "12" },
  { icon: CalendarDays, label: "Days tracked", value: "412" },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
};

function initials(name?: string | null, email?: string) {
  if (!name) return email?.[0]?.toUpperCase() ?? "?";
  return name
    .split(" ")
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
}

export default function DashboardPage() {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    }
  }, [user, isLoading, router]);

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  const firstName = user.full_name?.split(" ")[0] ?? user.email;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-border/80 bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-foreground text-xs font-bold text-background">
              T
            </span>
            <span className="text-base font-semibold tracking-tight">OpenTime</span>
            <span className="ml-1 hidden rounded-full border border-border px-2 py-0.5 text-[11px] text-muted sm:inline">
              Evolution Engine
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-secondary-foreground">
                {initials(user.full_name, user.email)}
              </div>
              <span className="hidden text-sm text-muted sm:inline">
                {user.full_name ?? user.email}
              </span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => logout()}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <motion.main
        variants={container}
        initial="hidden"
        animate="show"
        className="mx-auto max-w-6xl px-6 py-10"
      >
        {/* Hero */}
        <motion.section variants={item} className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs text-muted">
              <Sparkles className="h-3.5 w-3.5 text-amber" />
              Preview — memory upload lands in Phase 2
            </span>
          </div>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            Your evolution,{" "}
            <span className="bg-gradient-to-br from-foreground via-foreground to-muted bg-clip-text text-transparent">
              as one timeline
            </span>
          </h1>
          <p className="max-w-2xl text-lg leading-relaxed text-muted">
            Welcome back, {firstName}. OpenTime reads your memories, finds the themes that
            matter to you, and shows how you changed through them — one reflection at a
            time.
          </p>
        </motion.section>

        {/* Stats */}
        <motion.section
          variants={item}
          className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4"
        >
          {stats.map((s) => (
            <Card key={s.label} className="p-4">
              <div className="flex items-center gap-2 text-muted">
                <s.icon className="h-4 w-4" />
                <span className="text-[11px] uppercase tracking-wide">{s.label}</span>
              </div>
              <p className="mt-3 text-3xl font-semibold tracking-tight">{s.value}</p>
            </Card>
          ))}
        </motion.section>

        <div className="mt-10 grid gap-8 lg:grid-cols-3">
          {/* Timeline */}
          <motion.section variants={item} className="lg:col-span-2">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight">
                <Footprints className="h-5 w-5" />
                Your chapters
              </h2>
              <span className="text-sm text-muted-foreground">5 of 5 reflections</span>
            </div>

            <div className="relative">
              <div
                className="absolute bottom-3 left-[9px] top-3 w-px bg-gradient-to-b from-sky/60 via-rose/40 to-violet"
                aria-hidden
              />
              <ol className="space-y-6">
                {chapters.map((c) => (
                  <motion.li
                    key={c.title}
                    variants={item}
                    className="group relative pl-9"
                  >
                    <span
                      className="absolute left-0 top-2 h-[18px] w-[18px] rounded-full border-4 border-background shadow"
                      style={{ backgroundColor: c.accent }}
                      aria-hidden
                    />
                    <Card className="transition-colors group-hover:border-border">
                      <CardContent className="p-5">
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                          <span className="text-xs font-medium uppercase tracking-wide text-muted">
                            {c.date}
                          </span>
                          <h3 className="text-base font-semibold">{c.title}</h3>
                        </div>
                        <p className="mt-2 text-sm leading-relaxed text-muted">{c.body}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {c.tags.map((t) => (
                            <span
                              key={t.label}
                              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${t.tone}`}
                            >
                              {t.label}
                            </span>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </motion.li>
                ))}
              </ol>
            </div>
          </motion.section>

          {/* Right rail */}
          <div className="flex flex-col gap-6">
            {/* AI reflections */}
            <motion.section variants={item}>
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold tracking-tight">
                <BrainCircuit className="h-5 w-5" />
                Reflections
              </h2>
              <Card>
                <CardContent className="divide-y divide-border p-0">
                  {insights.map((insight) => (
                    <div key={insight.text} className="flex gap-3 p-4">
                      <insight.icon className="mt-0.5 h-4 w-4 shrink-0 text-amber" />
                      <p className="text-sm leading-relaxed text-foreground">
                        {insight.text}
                      </p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </motion.section>

            {/* Themes */}
            <motion.section variants={item}>
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold tracking-tight">
                <Tags className="h-5 w-5" />
                What you care about
              </h2>
              <Card>
                <CardContent className="space-y-4 p-5">
                  {themes.map((t) => (
                    <div key={t.label}>
                      <div className="mb-1.5 flex items-center justify-between text-sm">
                        <span>{t.label}</span>
                        <span className="text-muted">{t.pct}%</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                        <motion.div
                          className={`h-full rounded-full ${t.tone}`}
                          initial={{ width: 0 }}
                          whileInView={{ width: `${t.pct}%` }}
                          viewport={{ once: true }}
                          transition={{ duration: 0.9, ease: "easeOut" }}
                        />
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </motion.section>

            {/* CTA */}
            <motion.section variants={item}>
              <Card className="bg-foreground text-background">
                <CardContent className="p-6">
                  <h3 className="text-lg font-semibold tracking-tight">
                    Capture tomorrow
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-background/70">
                    The more you record, the sharper your story becomes. Your first
                    memory becomes the seed of every insight.
                  </p>
                  <Button
                    className="mt-5 w-full bg-background text-foreground hover:bg-background/90"
                    disabled
                  >
                    <ArrowUpRight className="h-4 w-4" />
                    Add a memory — coming soon
                  </Button>
                </CardContent>
              </Card>
            </motion.section>
          </div>
        </div>
      </motion.main>

      <footer className="mx-auto max-w-6xl px-6 pb-10 pt-4 text-center text-sm text-muted-foreground">
        Your data stays yours. OpenTime only reads what you choose to share.
      </footer>
    </div>
  );
}