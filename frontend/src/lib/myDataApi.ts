/**
 * Chronos data API — read and edit endpoints.
 * All calls require a valid access token stored in localStorage.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return JSON.parse(localStorage.getItem("opentime_tokens") ?? "null")?.access_token ?? null;
  } catch { return null; }
}

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    const msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface TypedClaim {
  value: string;
  claim_type: "fact" | "user_statement" | "inference" | "hypothesis";
  confidence: number;
  source_memory_id: string | null;
}

export interface Goal {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  category: string;
  importance: number;
  status: "active" | "completed" | "paused" | "abandoned";
  source: string;
  confidence: number;
  created_at: string;
}

export interface AnalysisPref {
  id: string;
  user_id: string;
  preference: string;
  custom_text: string | null;
  created_at: string;
}

export interface GenesisMemory {
  id: string;
  user_id: string;
  content: string;
  summary: string | null;
  topics: string[];
  importance: number;
  is_genesis: boolean;
  created_at: string;
  event_time: string;
}

export interface IdentityTrait {
  trait: string;
  claim_type: string;
  confidence: number;
}

export interface IdentityState {
  id?: string;
  user_id: string;
  version: number;
  traits?: IdentityTrait[];
  skills?: string[];
  interests: TypedClaim[] | string[];
  values: TypedClaim[] | string[];
  self_perception?: TypedClaim[];
  current_phase?: TypedClaim | null;
  created_at?: string;
  emotional_tendencies?: Record<string, number>;
  communication_style?: string;
  decision_patterns?: string[];
}

export interface Pattern {
  id: string;
  pattern: string;
  type: string;
  confidence: number;
  evidence_count: number;
}

// ── Read ──────────────────────────────────────────────────────────────────

export const myDataApi = {
  goals: (activeOnly = false) =>
    req<Goal[]>(`/chronos/goals?active_only=${activeOnly}`),

  preferences: () =>
    req<AnalysisPref[]>("/chronos/preferences"),

  genesis: () =>
    req<GenesisMemory[]>("/chronos/memories?limit=1&skip=0").then(
      (mems) => mems.find((m: any) => m.is_genesis) ?? null
    ),

  memories: (limit = 20, skip = 0) =>
    req<GenesisMemory[]>(`/chronos/memories?limit=${limit}&skip=${skip}`),

  identity: () =>
    req<IdentityState>("/chronos/identity"),

  patterns: () =>
    req<Pattern[]>("/chronos/patterns"),

  // ── Edit ──────────────────────────────────────────────────────────────────

  updateGoal: (goalId: string, data: {
    title: string;
    description?: string | null;
    category: string;
    importance: number;
    status: string;
  }) => req<Goal>(`/chronos/goals/${goalId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  }),

  createGoal: (data: {
    title: string;
    description?: string | null;
    category: string;
    importance: number;
  }) => req<Goal>("/chronos/goals", {
    method: "POST",
    body: JSON.stringify(data),
  }),

  deleteGoal: (goalId: string) =>
    req<void>(`/chronos/goals/${goalId}`, { method: "DELETE" }),

  updatePreferences: (preferences: string[]) =>
    req<AnalysisPref[]>("/chronos/preferences", {
      method: "PATCH",
      body: JSON.stringify({ preferences }),
    }),

  updateGenesis: (content: string) =>
    req<GenesisMemory>("/chronos/genesis", {
      method: "PATCH",
      body: JSON.stringify({ content }),
    }),

  updateTraits: (traits: string[]) =>
    req<IdentityState>("/chronos/identity/traits", {
      method: "PATCH",
      body: JSON.stringify({ traits }),
    }),
};
