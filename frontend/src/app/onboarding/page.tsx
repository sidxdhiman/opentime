"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, CheckCircle2, Cpu, Loader2, SkipForward } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import {
  onboardingApi,
  type OnboardingSession,
  type OnboardingStep,
} from "@/lib/onboardingApi";
import { OnboardingProgress } from "@/components/onboarding/OnboardingProgress";
import { StepAboutYou, type AboutYouData } from "@/components/onboarding/steps/StepAboutYou";
import { StepFreeText } from "@/components/onboarding/steps/StepFreeText";
import { StepGoals, type GoalInput } from "@/components/onboarding/steps/StepGoals";
import { StepFirstMemory } from "@/components/onboarding/steps/StepFirstMemory";
import { StepAnalysisPrefs } from "@/components/onboarding/steps/StepAnalysisPrefs";

// ─────────────────────────────────────────────────────────────────────────────
// Step metadata
// ─────────────────────────────────────────────────────────────────────────────

interface StepConfig {
  key: OnboardingStep;
  label: string;
  title: string;
  subtitle: string;
  question: string;
  optional?: boolean;
}

const STEPS: StepConfig[] = [
  {
    key: "about_you",
    label: "About you",
    title: "Let's get to know you",
    subtitle: "Chronos needs a few basics to understand your context.",
    question: "Tell Chronos a bit about yourself.",
  },
  {
    key: "life_right_now",
    label: "Life now",
    title: "What does your life look like right now?",
    subtitle: "This is one of the most important questions. Write freely.",
    question: "What does your life look like right now?",
  },
  {
    key: "whats_on_mind",
    label: "On your mind",
    title: "What's taking up most of your mind right now?",
    subtitle: "Worries, excitement, decisions, open questions — anything.",
    question: "What's taking up most of your mind right now?",
    optional: true,
  },
  {
    key: "where_going",
    label: "Goals",
    title: "What are you trying to change or achieve?",
    subtitle: "Add your goals — big or small, short-term or long-term.",
    question: "What are you trying to change or achieve?",
  },
  {
    key: "how_changed",
    label: "Changes",
    title: "How have you changed recently?",
    subtitle: "This helps Chronos build historical context about who you were.",
    question: "How have you changed recently?",
    optional: true,
  },
  {
    key: "first_memory",
    label: "First memory",
    title: "Give Chronos something to remember.",
    subtitle: "This becomes your Genesis Memory — the first entry in your timeline.",
    question: "Give Chronos something to remember about who you are today.",
  },
  {
    key: "analysis_prefs",
    label: "Preferences",
    title: "What do you want OpenTime to help you understand?",
    subtitle: "Select what matters most to you. You can always change this later.",
    question: "What do you want OpenTime to help you understand about yourself?",
  },
];

const STEP_KEYS = STEPS.map((s) => s.key);

// ─────────────────────────────────────────────────────────────────────────────
// State shape
// ─────────────────────────────────────────────────────────────────────────────

interface FormState {
  about_you: Partial<AboutYouData>;
  life_right_now: string;
  whats_on_mind: string;
  where_going: GoalInput[];
  how_changed: string;
  first_memory: string;
  analysis_prefs: string[];
}

const INITIAL_STATE: FormState = {
  about_you: {},
  life_right_now: "",
  whats_on_mind: "",
  where_going: [],
  how_changed: "",
  first_memory: "",
  analysis_prefs: [],
};

// ─────────────────────────────────────────────────────────────────────────────
// Validation: is a step "ready to submit"?
// ─────────────────────────────────────────────────────────────────────────────

function isStepReady(key: OnboardingStep, form: FormState): boolean {
  switch (key) {
    case "about_you": return true; // all optional fields
    case "life_right_now": return form.life_right_now.trim().length > 20;
    case "whats_on_mind": return true; // optional step
    case "where_going": return form.where_going.length > 0 && form.where_going[0].title.trim().length > 0;
    case "how_changed": return true; // optional step
    case "first_memory": return form.first_memory.trim().length > 20;
    case "analysis_prefs": return form.analysis_prefs.length > 0;
    default: return true;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Build the response payload for each step
// ─────────────────────────────────────────────────────────────────────────────

function buildResponse(key: OnboardingStep, form: FormState): unknown {
  switch (key) {
    case "about_you": return form.about_you;
    case "life_right_now": return form.life_right_now;
    case "whats_on_mind": return form.whats_on_mind;
    case "where_going": return { goals: form.where_going };
    case "how_changed": return form.how_changed;
    case "first_memory": return form.first_memory;
    case "analysis_prefs": return form.analysis_prefs;
    default: return {};
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page component
// ─────────────────────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [session, setSession] = useState<OnboardingSession | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [isBooting, setIsBooting] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completedKeys, setCompletedKeys] = useState<OnboardingStep[]>([]);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [done, setDone] = useState(false);

  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const currentStep = STEPS[stepIndex];

  // ── Boot: check status / create session ──────────────────────────────────

  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.replace("/login"); return; }

    onboardingApi.status().then((s) => {
      if (s.has_completed_session) {
        router.replace("/dashboard");
        return;
      }
      if (s.has_active_session && s.session) {
        setSession(s.session);
        const idx = STEP_KEYS.indexOf(s.session.current_step);
        setStepIndex(idx >= 0 ? idx : 0);
        setCompletedKeys(s.session.completed_steps);
        setIsBooting(false);
      } else {
        onboardingApi.start().then((sess) => {
          setSession(sess);
          setIsBooting(false);
        }).catch((e) => { setError(e.message); setIsBooting(false); });
      }
    }).catch(() => {
      // No session yet — create one
      onboardingApi.start().then((sess) => {
        setSession(sess);
        setIsBooting(false);
      }).catch((e) => { setError(e.message); setIsBooting(false); });
    });
  }, [user, authLoading, router]);

  // ── Autosave draft ────────────────────────────────────────────────────────

  const triggerAutosave = useCallback(() => {
    if (!session) return;
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = setTimeout(async () => {
      try {
        await onboardingApi.saveDraft(session.session_id, form as unknown as Record<string, unknown>);
      } catch { /* silent */ }
    }, 1500);
  }, [session, form]);

  useEffect(() => { triggerAutosave(); }, [form, triggerAutosave]);

  // ── Navigation ────────────────────────────────────────────────────────────

  const goTo = (idx: number, dir: 1 | -1) => {
    setDirection(dir);
    setStepIndex(idx);
    setError(null);
  };

  const handleNext = async () => {
    if (!session) return;
    setError(null);
    setIsSaving(true);
    const key = currentStep.key;

    try {
      await onboardingApi.saveResponse(
        session.session_id,
        key,
        currentStep.question,
        buildResponse(key, form)
      );
      const newCompleted = completedKeys.includes(key)
        ? completedKeys
        : [...completedKeys, key];
      setCompletedKeys(newCompleted);

      if (stepIndex < STEPS.length - 1) {
        goTo(stepIndex + 1, 1);
      } else {
        await handleComplete();
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSkip = async () => {
    if (!session || !currentStep.optional) return;
    setDirection(1);
    setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
    setError(null);
  };

  const handleBack = () => {
    if (stepIndex > 0) goTo(stepIndex - 1, -1);
  };

  const handleComplete = async () => {
    if (!session) return;
    setIsCompleting(true);
    try {
      await onboardingApi.complete(session.session_id);
      setDone(true);
      setTimeout(() => router.push("/dashboard"), 2500);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
      setIsCompleting(false);
    }
  };

  // ── Render helpers ────────────────────────────────────────────────────────

  const isLastStep = stepIndex === STEPS.length - 1;
  const canProceed = isStepReady(currentStep.key, form);

  if (authLoading || isBooting) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
          <span className="text-sm text-muted">Preparing your onboarding...</span>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-4 text-center"
        >
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-violet-500/10 border border-violet-500/30">
            <CheckCircle2 className="h-10 w-10 text-violet-400" />
          </div>
          <h2 className="text-2xl font-bold text-foreground">Chronos is ready.</h2>
          <p className="text-muted max-w-sm">
            Your baseline has been established. Taking you to your dashboard...
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-500 text-white">
              <Cpu className="h-4 w-4" />
            </div>
            <span className="font-bold text-sm tracking-tight">OpenTime</span>
            <span className="hidden sm:inline text-xs text-muted border border-border rounded-full px-2 py-0.5">
              Getting to know you
            </span>
          </div>
          <span className="text-xs text-muted">
            {completedKeys.length} / {STEPS.length} complete
          </span>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 mx-auto w-full max-w-3xl px-6 py-10">
        {/* Progress */}
        <div className="mb-10">
          <OnboardingProgress
            steps={STEPS.map((s) => ({ key: s.key, label: s.label, optional: s.optional }))}
            currentIndex={stepIndex}
            completedKeys={completedKeys}
          />
        </div>

        {/* Step card */}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={currentStep.key}
            initial={{ opacity: 0, x: direction * 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: direction * -40 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
          >
            <div className="rounded-2xl border border-border bg-card p-8 shadow-sm space-y-6">
              {/* Step heading */}
              <div>
                <p className="text-xs font-bold text-violet-400 uppercase tracking-widest mb-1">
                  Step {stepIndex + 1} of {STEPS.length}
                  {currentStep.optional && (
                    <span className="ml-2 text-muted/60 normal-case font-normal tracking-normal">optional</span>
                  )}
                </p>
                <h1 className="text-2xl font-bold text-foreground">{currentStep.title}</h1>
                <p className="text-sm text-muted mt-1">{currentStep.subtitle}</p>
              </div>

              {/* Step content */}
              <div>
                {currentStep.key === "about_you" && (
                  <StepAboutYou
                    data={form.about_you}
                    onChange={(d) => setForm((f) => ({ ...f, about_you: d }))}
                  />
                )}
                {currentStep.key === "life_right_now" && (
                  <StepFreeText
                    value={form.life_right_now}
                    onChange={(v) => setForm((f) => ({ ...f, life_right_now: v }))}
                    placeholder={"What are you working on? What's occupying your time? What are you excited or worried about?\n\nWrite as much or as little as you want — Chronos will understand."}
                  />
                )}
                {currentStep.key === "whats_on_mind" && (
                  <StepFreeText
                    value={form.whats_on_mind}
                    onChange={(v) => setForm((f) => ({ ...f, whats_on_mind: v }))}
                    placeholder={"Worries, uncertainty, open decisions, things weighing on you...\n\nChronos will never judge."}
                  />
                )}
                {currentStep.key === "where_going" && (
                  <StepGoals
                    goals={form.where_going}
                    onChange={(g) => setForm((f) => ({ ...f, where_going: g }))}
                  />
                )}
                {currentStep.key === "how_changed" && (
                  <StepFreeText
                    value={form.how_changed}
                    onChange={(v) => setForm((f) => ({ ...f, how_changed: v }))}
                    placeholder={"Have your priorities shifted? Did something change recently?\n\nPersonality, interests, relationships, beliefs, habits — anything you feel has evolved."}
                  />
                )}
                {currentStep.key === "first_memory" && (
                  <StepFirstMemory
                    value={form.first_memory}
                    onChange={(v) => setForm((f) => ({ ...f, first_memory: v }))}
                  />
                )}
                {currentStep.key === "analysis_prefs" && (
                  <StepAnalysisPrefs
                    selected={form.analysis_prefs}
                    onChange={(p) => setForm((f) => ({ ...f, analysis_prefs: p }))}
                  />
                )}
              </div>

              {/* Error */}
              {error && (
                <p className="text-sm text-destructive rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2">
                  {error}
                </p>
              )}

              {/* Navigation */}
              <div className="flex items-center justify-between pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleBack}
                  disabled={stepIndex === 0 || isSaving}
                  className="gap-1.5 text-muted hover:text-foreground"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>

                <div className="flex items-center gap-3">
                  {currentStep.optional && (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={handleSkip}
                      disabled={isSaving}
                      className="gap-1.5 text-muted hover:text-foreground text-sm"
                    >
                      <SkipForward className="h-4 w-4" />
                      Skip
                    </Button>
                  )}

                  <Button
                    type="button"
                    onClick={handleNext}
                    disabled={!canProceed || isSaving || isCompleting}
                    className="gap-2 bg-gradient-to-r from-violet-600 to-indigo-500 hover:from-violet-500 hover:to-indigo-400 text-white shadow-lg shadow-violet-600/20 disabled:opacity-40"
                  >
                    {isSaving || isCompleting ? (
                      <><Loader2 className="h-4 w-4 animate-spin" />{isCompleting ? "Initialising Chronos..." : "Saving..."}</>
                    ) : isLastStep ? (
                      <><CheckCircle2 className="h-4 w-4" />Finish & launch Chronos</>
                    ) : (
                      <>Continue<ArrowRight className="h-4 w-4" /></>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Reassurance footer */}
        <p className="mt-6 text-center text-xs text-muted/60">
          Your answers are private and belong only to you.
          Autosaved as you type.
        </p>
      </main>
    </div>
  );
}
