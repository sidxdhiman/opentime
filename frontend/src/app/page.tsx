"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  Brain,
  Cpu,
  Layers,
  Mic,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import DecryptedText from "@/components/ui/DecryptedText";
import SpotlightCard from "@/components/ui/SpotlightCard";
import AuroraBackground from "@/components/ui/Aurora";
import NeuralBrainCanvas from "@/components/ui/NeuralBrain";
import { useAuth } from "@/lib/auth";

// Particle field effect for the background
function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const setSize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    setSize();
    window.addEventListener("resize", setSize);

    const particles: { x: number; y: number; vx: number; vy: number; alpha: number; r: number }[] = [];
    for (let i = 0; i < 80; i++) {
      particles.push({
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        alpha: 0.1 + Math.random() * 0.35,
        r: 0.8 + Math.random() * 1.4,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(167,139,250,${p.alpha})`;
        ctx.fill();
      });
      animRef.current = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener("resize", setSize);
      cancelAnimationFrame(animRef.current);
    };
  }, []);

  return <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none z-0" />;
}

// Animated count-up hook
function useCountUp(target: number, duration = 2000, start = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime: number | null = null;
    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = Math.min(elapsed / duration, 1);
      setCount(Math.floor(progress * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration, start]);
  return count;
}

function StatsCounter({ value, label, suffix = "" }: { value: number; label: string; suffix?: string }) {
  const [inView, setInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const count = useCountUp(value, 1800, inView);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setInView(true); },
      { threshold: 0.5 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className="text-center">
      <div className="text-4xl font-extrabold text-white tabular-nums">
        {count}{suffix}
      </div>
      <div className="mt-1 text-sm text-violet-300/70">{label}</div>
    </div>
  );
}

const features = [
  {
    icon: Mic,
    color: "rose",
    title: "Multimodal Input",
    desc: "Voice, video, text & file uploads — ChronOS extracts acoustic, visual and semantic features from any modality instantly.",
    gradient: "from-rose-500/20 via-rose-500/5 to-transparent",
    border: "border-rose-500/20",
    spotlight: "rgba(244,63,94,0.12)",
  },
  {
    icon: Brain,
    color: "violet",
    title: "Model-Agnostic LLM",
    desc: "Switch seamlessly between GPT-4o, Claude 3.5, Gemini Pro and Ollama Local — the reasoning layer stays intact.",
    gradient: "from-violet-500/20 via-violet-500/5 to-transparent",
    border: "border-violet-500/20",
    spotlight: "rgba(139,92,246,0.15)",
  },
  {
    icon: Layers,
    color: "cyan",
    title: "Identity Evolution",
    desc: "Reflect on your past self vs. current self with full explainability traces, confidence scores & belief-shift analytics.",
    gradient: "from-cyan-500/20 via-cyan-500/5 to-transparent",
    border: "border-cyan-500/20",
    spotlight: "rgba(6,182,212,0.12)",
  },
  {
    icon: Shield,
    color: "emerald",
    title: "Private by Design",
    desc: "Your memories stay yours. Local-first processing with optional encrypted cloud sync — zero retention, zero telemetry.",
    gradient: "from-emerald-500/20 via-emerald-500/5 to-transparent",
    border: "border-emerald-500/20",
    spotlight: "rgba(16,185,129,0.12)",
  },
  {
    icon: Zap,
    color: "amber",
    title: "Real-time Context",
    desc: "The ChronOS context engine synthesizes episodic memory, semantic patterns and behavioral signals in milliseconds.",
    gradient: "from-amber-500/20 via-amber-500/5 to-transparent",
    border: "border-amber-500/20",
    spotlight: "rgba(245,158,11,0.12)",
  },
  {
    icon: Sparkles,
    color: "indigo",
    title: "Pattern Intelligence",
    desc: "Automatic detection of recurring behavioral patterns, mood cycles, and cognitive shifts across your lifetime of memories.",
    gradient: "from-indigo-500/20 via-indigo-500/5 to-transparent",
    border: "border-indigo-500/20",
    spotlight: "rgba(99,102,241,0.12)",
  },
];

export default function HomePage() {
  const [heroLoaded, setHeroLoaded] = useState(false);
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // Redirect authenticated users away from the landing page
  useEffect(() => {
    if (!authLoading && user) {
      router.replace("/dashboard");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    const t = setTimeout(() => setHeroLoaded(true), 100);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="relative flex min-h-screen flex-col bg-[#060614] text-white overflow-x-hidden selection:bg-violet-500 selection:text-white">
      {/* Particle field */}
      <ParticleField />

      {/* === HEADER === */}
      <header
        className="relative z-30 flex items-center justify-between px-8 py-5 border-b border-white/5"
        style={{ backdropFilter: "blur(16px)", background: "rgba(6,6,20,0.7)" }}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-500 shadow-lg shadow-violet-600/40">
            <Cpu className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-white via-violet-200 to-indigo-300 bg-clip-text text-transparent">
            OpenTime
          </span>
          <span className="hidden sm:inline-flex items-center gap-1 rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-0.5 text-[10px] font-semibold text-violet-300">
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulse" />
            ChronOS Powered
          </span>
        </div>
        <nav className="flex items-center gap-2">
          <Link href="/login">
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-white/70 hover:text-white hover:bg-white/10 transition-all"
            >
              Sign in
            </Button>
          </Link>
          <Link href="/register">
            <Button
              size="sm"
              className="text-xs px-4 rounded-xl font-semibold bg-gradient-to-r from-violet-600 to-indigo-500 hover:from-violet-500 hover:to-indigo-400 text-white shadow-lg shadow-violet-600/30 transition-all hover:shadow-violet-500/50 hover:scale-105 active:scale-95"
            >
              Launch ChronOS
            </Button>
          </Link>
        </nav>
      </header>

      {/* === HERO === */}
      <section className="relative z-10 flex flex-1 flex-col items-center justify-center min-h-[calc(100vh-76px)] px-6 py-20 overflow-hidden">
        {/* Aurora background */}
        <div className="absolute inset-0 overflow-hidden">
          <AuroraBackground
            colorStops={["#7C3AED", "#4F46E5", "#06B6D4"]}
            blend={0.45}
            amplitude={1.1}
            speed={0.4}
          />
        </div>

        {/* Grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(139,92,246,1) 1px, transparent 1px), linear-gradient(90deg, rgba(139,92,246,1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        {/* Hero content */}
        <div className="relative z-10 flex flex-col lg:flex-row items-center justify-center gap-12 max-w-7xl w-full">
          {/* Left: Text */}
          <div
            className="flex flex-col items-center lg:items-start text-center lg:text-left max-w-xl"
            style={{
              transform: heroLoaded ? "translateY(0)" : "translateY(24px)",
              opacity: heroLoaded ? 1 : 0,
              transition: "all 0.9s cubic-bezier(0.16,1,0.3,1)",
            }}
          >
            {/* Badge */}
            <div className="inline-flex items-center gap-2 mb-8 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-1.5 text-xs font-semibold text-violet-300 shadow-inner">
              <Sparkles className="h-3.5 w-3.5 text-violet-400 animate-pulse" />
              <span>Introducing ChronOS Core Intelligence Layer</span>
            </div>

            {/* Main headline */}
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.05]">
              <span className="text-white">The Personal</span>
              <br />
              <span className="bg-gradient-to-r from-violet-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">
                <DecryptedText
                  text="Evolution Engine"
                  animateOn="view"
                  speed={40}
                  maxIterations={15}
                  characters="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%&"
                  className="bg-gradient-to-r from-violet-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent"
                  encryptedClassName="text-violet-400/50"
                />
              </span>
            </h1>

            <p
              className="mt-6 text-lg sm:text-xl text-white/60 leading-relaxed max-w-lg"
              style={{ transitionDelay: "200ms" }}
            >
              ChronOS is the reasoning, memory, and context layer that sits between your voice, video & text — and any language model. It knows who you were, and who you're becoming.
            </p>

            {/* CTA buttons */}
            <div
              className="mt-10 flex flex-wrap items-center gap-4"
              style={{ transitionDelay: "350ms" }}
            >
              <Link href="/register">
                <button
                  id="cta-launch"
                  className="group relative flex items-center gap-2 px-8 py-3.5 rounded-2xl text-sm font-bold text-white overflow-hidden transition-all hover:scale-105 active:scale-95"
                  style={{
                    background: "linear-gradient(135deg, #7C3AED 0%, #4F46E5 60%, #06B6D4 100%)",
                    boxShadow: "0 0 40px rgba(139,92,246,0.5), 0 4px 24px rgba(0,0,0,0.4)",
                  }}
                >
                  <span className="relative z-10">Launch ChronOS Engine</span>
                  <ArrowRight className="relative z-10 h-4 w-4 transition-transform group-hover:translate-x-1" />
                  {/* Shimmer overlay */}
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-r from-transparent via-white/15 to-transparent -translate-x-full group-hover:translate-x-full duration-700" />
                </button>
              </Link>
              <Link href="/login">
                <button
                  id="cta-signin"
                  className="flex items-center gap-2 px-6 py-3.5 rounded-2xl text-sm font-semibold text-white/80 border border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20 backdrop-blur-sm transition-all hover:scale-105 active:scale-95"
                >
                  Sign in to Dashboard
                </button>
              </Link>
            </div>

            {/* Stats */}
            <div className="mt-12 flex items-center gap-8 pt-8 border-t border-white/10">
              <StatsCounter value={100} suffix="%" label="Private" />
              <div className="w-px h-8 bg-white/10" />
              <StatsCounter value={5} suffix="x" label="LLM providers" />
              <div className="w-px h-8 bg-white/10" />
              <StatsCounter value={360} label="Memory contexts" />
            </div>
          </div>

          {/* Right: Neural Brain */}
          <div
            className="relative w-[320px] h-[320px] sm:w-[420px] sm:h-[420px] lg:w-[480px] lg:h-[480px] flex-shrink-0"
            style={{
              transform: heroLoaded ? "translateY(0) scale(1)" : "translateY(30px) scale(0.96)",
              opacity: heroLoaded ? 1 : 0,
              transition: "all 1.1s cubic-bezier(0.16,1,0.3,1) 0.2s",
            }}
          >
            {/* Outer glow ring */}
            <div className="absolute inset-0 rounded-full"
              style={{ background: "radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 70%)" }} />

            {/* Pulsing rings */}
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="absolute inset-0 rounded-full border border-violet-500/20"
                style={{
                  animation: `ping ${3 + i * 1.2}s cubic-bezier(0,0,0.2,1) infinite`,
                  animationDelay: `${i * 0.8}s`,
                }}
              />
            ))}

            {/* Brain container */}
            <div className="absolute inset-8 rounded-full overflow-hidden border border-violet-500/20 bg-black/20 backdrop-blur-sm">
              <NeuralBrainCanvas />
            </div>

            {/* Center icon */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div
                className="flex h-16 w-16 items-center justify-center rounded-2xl"
                style={{
                  background: "linear-gradient(135deg, rgba(124,58,237,0.8), rgba(79,70,229,0.8))",
                  boxShadow: "0 0 30px rgba(139,92,246,0.6), 0 0 60px rgba(139,92,246,0.2)",
                  backdropFilter: "blur(8px)",
                }}
              >
                <Brain className="h-8 w-8 text-white" />
              </div>
            </div>

            {/* Floating labels */}
            {[
              { label: "Memory Graph", x: "-20%", y: "25%", delay: "0s" },
              { label: "Identity Core", x: "85%", y: "20%", delay: "0.5s" },
              { label: "ChronOS Engine", x: "10%", y: "80%", delay: "1s" },
            ].map(({ label, x, y, delay }) => (
              <div
                key={label}
                className="absolute text-[10px] font-semibold text-violet-300/70 border border-violet-500/20 bg-black/40 backdrop-blur-sm px-2 py-1 rounded-full whitespace-nowrap"
                style={{
                  left: x,
                  top: y,
                  animation: `float 4s ease-in-out infinite`,
                  animationDelay: delay,
                }}
              >
                {label}
              </div>
            ))}
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 animate-bounce opacity-50">
          <div className="w-px h-8 bg-gradient-to-b from-transparent to-violet-400" />
          <span className="text-[10px] text-violet-400 font-medium tracking-widest uppercase">Scroll</span>
        </div>
      </section>

      {/* === FEATURES === */}
      <section className="relative z-10 px-6 py-24">
        <div className="max-w-7xl mx-auto">
          {/* Section header */}
          <div className="text-center mb-16">
            <p className="text-xs font-bold tracking-widest text-violet-400 uppercase mb-4">Capabilities</p>
            <h2 className="text-4xl sm:text-5xl font-extrabold text-white leading-tight">
              Intelligence at every layer
            </h2>
            <p className="mt-4 text-white/50 text-lg max-w-xl mx-auto">
              ChronOS orchestrates your entire cognitive stack — from raw input to refined insight.
            </p>
          </div>

          {/* Feature grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(({ icon: Icon, color, title, desc, border, spotlight }) => (
              <SpotlightCard
                key={title}
                spotlightColor={spotlight}
                className={`group border ${border} bg-white/[0.02] p-6 hover:bg-white/[0.04] transition-all hover:-translate-y-1`}
              >
                <div
                  className={`flex h-11 w-11 items-center justify-center rounded-xl bg-${color}-500/10 border border-${color}-500/20 text-${color}-400 mb-4 transition-all group-hover:scale-110`}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">{title}</h3>
                <p className="text-sm text-white/50 leading-relaxed">{desc}</p>
              </SpotlightCard>
            ))}
          </div>
        </div>
      </section>

      {/* === HOW IT WORKS === */}
      <section className="relative z-10 px-6 py-24 overflow-hidden">
        {/* BG glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full pointer-events-none"
          style={{ background: "radial-gradient(circle, rgba(79,70,229,0.08) 0%, transparent 70%)" }} />

        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs font-bold tracking-widest text-indigo-400 uppercase mb-4">How it works</p>
            <h2 className="text-4xl sm:text-5xl font-extrabold text-white">
              Your memory,{" "}
              <span className="bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
                intelligently organized
              </span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
            {/* Connecting line (desktop only) */}
            <div className="hidden md:block absolute top-10 left-[calc(16%+2rem)] right-[calc(16%+2rem)] h-px bg-gradient-to-r from-violet-500/30 via-indigo-500/50 to-cyan-500/30" />

            {[
              {
                step: "01",
                icon: Mic,
                title: "Capture Input",
                desc: "Record voice, video, or text. Upload documents, journals, or media.",
                color: "violet",
              },
              {
                step: "02",
                icon: Cpu,
                title: "ChronOS Processes",
                desc: "The engine extracts patterns, emotions, and entities. Builds your semantic memory graph.",
                color: "indigo",
              },
              {
                step: "03",
                icon: Sparkles,
                title: "Evolving Insight",
                desc: "Ask who you were. Discover how you've changed. Receive AI-powered reflections.",
                color: "cyan",
              },
            ].map(({ step, icon: Icon, title, desc, color }) => (
              <div key={step} className="flex flex-col items-center text-center gap-4 group">
                <div
                  className={`relative flex h-20 w-20 items-center justify-center rounded-2xl border border-${color}-500/30 bg-${color}-500/10 text-${color}-400 transition-all group-hover:scale-110 group-hover:shadow-lg group-hover:shadow-${color}-500/20`}
                >
                  <Icon className="h-8 w-8" />
                  <span className={`absolute -top-2 -right-2 flex h-6 w-6 items-center justify-center rounded-full bg-${color}-500 text-[10px] font-black text-white`}>
                    {step}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white">{title}</h3>
                <p className="text-sm text-white/50 leading-relaxed max-w-[220px]">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* === CTA SECTION === */}
      <section className="relative z-10 px-6 py-24">
        <div className="max-w-4xl mx-auto">
          <div
            className="relative overflow-hidden rounded-3xl border border-violet-500/20 p-12 text-center"
            style={{
              background:
                "linear-gradient(135deg, rgba(124,58,237,0.12) 0%, rgba(79,70,229,0.08) 50%, rgba(6,182,212,0.08) 100%)",
              backdropFilter: "blur(24px)",
            }}
          >
            {/* BG glow */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background:
                  "radial-gradient(ellipse at 50% -20%, rgba(139,92,246,0.25) 0%, transparent 60%)",
              }}
            />

            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 mb-6 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-1.5 text-xs font-semibold text-violet-300">
                <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
                Early access — free to start
              </div>

              <h2 className="text-4xl sm:text-5xl font-extrabold text-white leading-tight mb-4">
                Start understanding{" "}
                <span className="bg-gradient-to-r from-violet-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">
                  how you evolve
                </span>
              </h2>
              <p className="text-white/50 text-lg mb-10 max-w-2xl mx-auto">
                Join the waitlist and get early access to ChronOS — the AI engine that builds a living map of your mind.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-4">
                <Link href="/register">
                  <button
                    id="cta-register-bottom"
                    className="group relative flex items-center gap-2 px-10 py-4 rounded-2xl text-sm font-bold text-white overflow-hidden transition-all hover:scale-105 active:scale-95"
                    style={{
                      background: "linear-gradient(135deg, #7C3AED 0%, #4F46E5 60%, #06B6D4 100%)",
                      boxShadow: "0 0 40px rgba(139,92,246,0.5)",
                    }}
                  >
                    <span>Get Early Access</span>
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </button>
                </Link>
                <Link href="/login">
                  <button
                    id="cta-login-bottom"
                    className="px-8 py-4 rounded-2xl text-sm font-semibold text-white/70 border border-white/10 bg-white/5 hover:bg-white/10 transition-all hover:scale-105"
                  >
                    Sign in →
                  </button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* === FOOTER === */}
      <footer className="relative z-10 px-8 py-6 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-violet-400" />
          <span className="text-xs text-white/30 font-medium">OpenTime · ChronOS Core Engine Architecture</span>
        </div>
        <span className="text-xs text-white/20">Built with reactbits.dev animations</span>
      </footer>

      {/* Global animation styles */}
      <style jsx global>{`
        @keyframes shining {
          0% { background-position: 200% center; }
          100% { background-position: -200% center; }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
        @keyframes ping {
          75%, 100% { transform: scale(1.4); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
