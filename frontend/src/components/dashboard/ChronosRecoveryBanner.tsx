"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, ArrowRight, Database, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { onboardingApi } from "@/lib/onboardingApi";

type RecoveryState = "idle" | "loading" | "error";

interface Props {
  /** Whether an in-progress onboarding session exists (server told us) */
  hasActiveSession: boolean;
  /** Called after user chooses an action, so the parent can re-check state */
  onRetry?: () => void;
}

export function ChronosRecoveryBanner({ hasActiveSession, onRetry }: Props) {
  const router = useRouter();
  const [state, setState] = useState<RecoveryState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleResumeOnboarding = async () => {
    setState("loading");
    setErrorMsg(null);
    try {
      // start_or_resume is idempotent — returns existing session if one exists
      await onboardingApi.start();
      router.push("/onboarding");
    } catch (e: unknown) {
      setState("error");
      setErrorMsg(e instanceof Error ? e.message : "Something went wrong.");
    }
  };

  return (
    <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-5">
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/10">
          <AlertTriangle className="h-5 w-5 text-amber-400" />
        </div>

        <div className="flex-1 space-y-3">
          <div>
            <h3 className="font-semibold text-foreground">
              Your data isn&apos;t configured yet
            </h3>
            <p className="mt-1 text-sm text-muted leading-relaxed">
              Your data hasn&apos;t been configured — kindly configure it in the{" "}
              <Link
                href="/me"
                className="font-medium text-amber-400 underline underline-offset-2 hover:text-amber-300"
              >
                Me
              </Link>
              section.
              {hasActiveSession && (
                <span className="mt-1 block">
                  You also have an onboarding in progress — you can finish it below.
                </span>
              )}
            </p>
          </div>

          {errorMsg && (
            <p role="alert" className="text-xs text-destructive rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2">
              {errorMsg}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Link href="/me">
              <Button
                type="button"
                className="gap-2 bg-violet-600 hover:bg-violet-500 text-white font-semibold shadow-lg shadow-violet-600/20"
              >
                <Database className="h-4 w-4" />
                Go to Me
              </Button>
            </Link>

            {hasActiveSession && (
              <Button
                type="button"
                onClick={handleResumeOnboarding}
                disabled={state === "loading"}
                variant="outline"
                className="gap-2 border-amber-500/30 text-amber-400 hover:text-amber-300"
              >
                {state === "loading" ? (
                  <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
                ) : (
                  <ArrowRight className="h-4 w-4" />
                )}
                {state === "loading" ? "Resuming..." : "Resume onboarding"}
              </Button>
            )}

            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="flex items-center gap-1.5 text-xs text-muted hover:text-foreground transition-colors"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Check again
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}