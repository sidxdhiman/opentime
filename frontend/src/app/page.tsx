import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Cpu, Mic, Video, Brain, Layers, ArrowRight, ShieldCheck, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground selection:bg-violet-500 selection:text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-5 border-b border-border/60 bg-background/80 backdrop-blur-md sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white font-extrabold shadow-lg shadow-violet-600/30">
            <Cpu className="h-5 w-5" />
          </div>
          <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-white via-violet-200 to-indigo-300 bg-clip-text text-transparent">
            OpenTime
          </span>
          <span className="rounded-full bg-violet-500/10 border border-violet-500/20 px-2.5 py-0.5 text-xs font-semibold text-violet-300">
            ChronOS Powered
          </span>
        </div>

        <nav className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm" className="text-xs">
              Sign in
            </Button>
          </Link>
          <Link href="/register">
            <Button size="sm" className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 text-xs px-4 rounded-xl shadow-md shadow-violet-600/25">
              Launch ChronOS
            </Button>
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <main className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
        <div className="max-w-4xl flex flex-col items-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-1.5 text-xs font-semibold text-violet-300 mb-8 shadow-inner">
            <Sparkles className="h-3.5 w-3.5 text-violet-400" />
            Introducing the ChronOS Core Intelligence Layer
          </div>

          <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight leading-tight text-foreground">
            The Personal Evolution Engine <br />
            <span className="bg-gradient-to-r from-violet-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">
              Driven by ChronOS
            </span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl leading-relaxed text-muted max-w-2xl">
            ChronOS is the reasoning, memory, context, and orchestration system that sits between your text, voice, and video inputs and any language model.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link href="/register">
              <Button size="lg" className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 text-sm px-7 py-3 h-auto rounded-xl shadow-lg shadow-violet-600/30 gap-2 font-semibold">
                Launch ChronOS Engine <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" size="lg" className="border-border text-sm px-6 py-3 h-auto rounded-xl">
                Sign in to Dashboard
              </Button>
            </Link>
          </div>

          {/* Engine Capability Feature Cards */}
          <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-6 text-left w-full max-w-4xl">
            <div className="rounded-2xl border border-border/80 bg-card/80 p-6 shadow-xl space-y-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
                <Mic className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-foreground">Multimodal Voice & Video</h3>
              <p className="text-xs text-muted leading-relaxed">
                Record voice notes or video logs directly in the browser or upload media files. ChronOS extracts acoustic & visual features instantly.
              </p>
            </div>

            <div className="rounded-2xl border border-border/80 bg-card/80 p-6 shadow-xl space-y-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20">
                <Brain className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-foreground">Model-Agnostic LLM Swap</h3>
              <p className="text-xs text-muted leading-relaxed">
                Switch seamlessly between OpenAI GPT-4o, Claude 3.5, Gemini 1.5 Pro, and Ollama Local without modifying engine reasoning logic.
              </p>
            </div>

            <div className="rounded-2xl border border-border/80 bg-card/80 p-6 shadow-xl space-y-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Layers className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-foreground">Past Self vs Current Self</h3>
              <p className="text-xs text-muted leading-relaxed">
                Reflect on your evolving identity, belief shifts, and behavioral patterns with complete explainability traces & confidence scores.
              </p>
            </div>
          </div>
        </div>
      </main>

      <footer className="px-8 py-6 text-center text-xs text-muted border-t border-border/60">
        OpenTime • ChronOS Core Engine Architecture
      </footer>
    </div>
  );
}

function Sparkles(props: any) {
  return <Zap {...props} />;
}
