"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, Cpu, Feather, Lock, Mic, Sparkles, Waves } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

const fade = {
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.7, ease: "easeOut" as const },
};

const features = [
  {
    icon: Mic,
    title: "Naturally yours",
    text: "Speak, write, or share a file. ChronOS listens to the shape of your days, not just the words.",
  },
  {
    icon: Feather,
    title: "Reflected, not judged",
    text: "Quiet, private reflections on how you have changed — grounded in what you have actually said.",
  },
  {
    icon: Waves,
    title: "Calm intelligence",
    text: "A memory of your life, organised calmly. See patterns emerge over time, at your own pace.",
  },
  {
    icon: Lock,
    title: "Private by design",
    text: "Your memories stay yours. Local-first processing, with no telemetry and no data sharing.",
  },
];

const steps = [
  {
    step: "01",
    title: "Share something real",
    text: "A voice note, a journal entry, or a passing thought. Anything that reflects your present moment.",
  },
  {
    step: "02",
    title: "ChronOS remembers",
    text: "The quiet engine behind OpenTime records it in your timeline and weaves it into a living memory.",
  },
  {
    step: "03",
    title: "Understand yourself",
    text: "Return later and see how you have grown. Gently, precisely, and entirely on your terms.",
  },
];

export default function HomePage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && user) {
      router.replace("/dashboard");
    }
  }, [user, authLoading, router]);

  return (
    <div className="relative flex min-h-screen flex-col overflow-x-hidden bg-background text-foreground selection:bg-accent selection:text-accent-foreground">
      {/* Quiet ambient glow */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        aria-hidden
        style={{
          background:
            "radial-gradient(70% 45% at 50% -5%, color-mix(in oklab, var(--color-primary) 12%, transparent), transparent 70%)",
        }}
      />

      {/* ── Header ── */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-secondary">
              <Cpu className="h-4 w-4 text-accent-foreground" />
            </div>
            <span className="text-[15px] font-semibold tracking-tight">OpenTime</span>
          </div>

          <nav className="hidden items-center gap-8 text-sm text-muted md:flex">
            <a href="#features" className="transition-colors hover:text-foreground">Features</a>
            <a href="#how" className="transition-colors hover:text-foreground">How it works</a>
          </nav>

          <div className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm">Sign in</Button>
            </Link>
            <Link href="/register">
              <Button size="sm">Start free</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="flex flex-1 flex-col items-center px-6 pt-24 pb-20 sm:pt-28">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="flex max-w-3xl flex-col items-center text-center"
        >
          <span className="mb-7 inline-flex items-center gap-2 rounded-full border border-border bg-secondary/60 px-3.5 py-1.5 text-xs font-medium text-muted">
            <Sparkles className="h-3.5 w-3.5 text-accent-foreground" />
            Your private evolution engine
          </span>

          <h1 className="text-4xl font-semibold leading-[1.08] tracking-tight text-balance sm:text-6xl">
            Remember who you were.
            <br />
            <span className="text-accent-foreground">Understand who you&apos;re becoming.</span>
          </h1>

          <p className="mt-6 max-w-xl text-base leading-relaxed text-muted sm:text-lg">
            OpenTime is a calm, private space to keep a memory of your life. Speak, write, and
            reflect — ChronOS quietly weaves it into a living portrait of how you change.
          </p>

          <div className="mt-9 flex flex-col items-center gap-3 sm:flex-row">
            <Link href="/register">
              <Button size="lg" className="px-7">
                Begin your timeline
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" size="lg" className="px-7">
                Sign in to your space
              </Button>
            </Link>
          </div>

          <dl className="mt-16 flex items-center gap-8 sm:gap-12">
            {[
              { value: "100%", label: "Private" },
              { value: "5+", label: "LLM providers" },
              { value: "Local-first", label: "Your data, yours" },
            ].map((stat, i) => (
              <div key={stat.label} className="flex items-center gap-8 sm:gap-12">
                {i > 0 && <span className="h-8 w-px bg-border" aria-hidden />}
                <div className="text-center">
                  <dt className="text-lg font-semibold text-foreground sm:text-xl">{stat.value}</dt>
                  <dd className="mt-1 text-xs uppercase tracking-widest text-muted">{stat.label}</dd>
                </div>
              </div>
            ))}
          </dl>
        </motion.div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="px-6 pb-24">
        <div className="mx-auto max-w-6xl">
          <motion.div {...fade} className="mb-14 max-w-xl">
            <p className="mb-3 text-xs font-medium uppercase tracking-widest text-accent-foreground">
              Capabilities
            </p>
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Intelligence, kept gentle
            </h2>
            <p className="mt-4 text-base leading-relaxed text-muted">
              OpenTime stays out of the way. It listens, remembers, and offers quiet insight when
              you are ready for it.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, title, text }, i) => (
              <motion.div
                key={title}
                {...fade}
                transition={{ duration: 0.7, ease: "easeOut", delay: i * 0.06 }}
                className="group rounded-2xl border border-border bg-card p-6 shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-border/70 hover:shadow-card-hover"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground transition-transform duration-300 group-hover:scale-105">
                  <Icon className="h-4.5 w-4.5" />
                </div>
                <h3 className="text-[15px] font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how" className="px-6 pb-24">
        <div className="mx-auto max-w-5xl">
          <motion.div {...fade} className="mb-14 text-center">
            <p className="mb-3 text-xs font-medium uppercase tracking-widest text-accent-foreground">
              How it works
            </p>
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              A gentler way to keep your life
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 gap-10 md:grid-cols-3 md:gap-6">
            {steps.map((s, i) => (
              <motion.div
                key={s.step}
                {...fade}
                transition={{ duration: 0.7, ease: "easeOut", delay: i * 0.1 }}
                className="relative text-center md:text-left"
              >
                <div className="mb-5 flex items-center gap-4 md:block">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-card font-mono text-sm text-muted">
                    {s.step}
                  </span>
                  <span className="h-px flex-1 bg-border md:hidden" aria-hidden />
                </div>
                <h3 className="text-[15px] font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{s.text}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="px-6 pb-24">
        <motion.div
          {...fade}
          className="relative mx-auto max-w-3xl overflow-hidden rounded-3xl border border-border bg-card px-8 py-16 text-center shadow-card"
        >
          <div
            className="pointer-events-none absolute inset-0"
            aria-hidden
            style={{
              background:
                "radial-gradient(60% 70% at 50% 0%, color-mix(in oklab, var(--color-primary) 10%, transparent), transparent 70%)",
            }}
          />
          <div className="relative">
            <h2 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
              Your story is still being written
            </h2>
            <p className="mx-auto mt-4 max-w-md text-base leading-relaxed text-muted">
              Start keeping a memory of who you are today, so tomorrow you can meet yourself with
              kindness and clarity.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link href="/register">
                <Button size="lg" className="px-7">
                  Begin your timeline
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="ghost" size="lg" className="px-7">
                  Already a member?
                </Button>
              </Link>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border/60 px-6 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2.5">
            <Cpu className="h-4 w-4 text-muted" />
            <span className="text-sm font-medium">OpenTime</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-muted">
            <span>ChronOS intelligence, kept local</span>
            <span>Privacy by design</span>
          </div>
        </div>
      </footer>
    </div>
  );
}