/**
 * Onboarding API client.
 * Mirrors the backend onboarding routes.
 */

import { http, type HttpOptions } from "@/lib/http";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("opentime_tokens");
  if (!raw) return null;
  try {
    return JSON.parse(raw)?.access_token ?? null;
  } catch {
    return null;
  }
}

async function authRequest<T>(
  path: string,
  options: HttpOptions = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  return http<T>(`${API_URL}${path}`, { ...options, headers });
}

// ---- Types ----

export type OnboardingStep =
  | "about_you"
  | "life_right_now"
  | "whats_on_mind"
  | "where_going"
  | "how_changed"
  | "first_memory"
  | "analysis_prefs";

export type OnboardingStatus =
  | "not_started"
  | "in_progress"
  | "completed"
  | "failed";

export interface OnboardingSession {
  session_id: string;
  user_id: string;
  status: OnboardingStatus;
  current_step: OnboardingStep;
  completed_steps: OnboardingStep[];
  started_at: string;
  completed_at: string | null;
}

export interface OnboardingStatusResponse {
  has_active_session: boolean;
  has_completed_session: boolean;
  session: OnboardingSession | null;
}

export interface CompleteOnboardingResponse {
  session_id: string;
  status: OnboardingStatus;
  chronos_initialised: boolean;
  message: string;
}

// ---- API ----

export const onboardingApi = {
  /** Start a new session or resume an in-progress one. */
  start(): Promise<OnboardingSession> {
    return authRequest("/onboarding/start", { method: "POST" });
  },

  /** Check current onboarding status. */
  status(): Promise<OnboardingStatusResponse> {
    return authRequest("/onboarding/status");
  },

  /** Save a completed step response. */
  saveResponse(
    sessionId: string,
    step: OnboardingStep,
    question: string,
    response: unknown
  ): Promise<{ session_id: string; step: OnboardingStep; saved: boolean }> {
    return authRequest(`/onboarding/${sessionId}/response`, {
      method: "POST",
      body: JSON.stringify({ step, question, response, is_draft: false }),
    });
  },

  /** Autosave draft data for the current step. */
  saveDraft(sessionId: string, data: Record<string, unknown>): Promise<void> {
    return authRequest(`/onboarding/${sessionId}/draft`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /** Complete onboarding and trigger Chronos initialisation. */
  complete(sessionId: string): Promise<CompleteOnboardingResponse> {
    return authRequest(`/onboarding/${sessionId}/complete`, {
      method: "POST",
    });
  },
};
