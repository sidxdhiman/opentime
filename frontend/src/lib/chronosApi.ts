import { http, type HttpOptions } from "@/lib/http";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const ENGINE_BASE = `${API_URL}/chronos/engine`;
const BACKEND_ORIGIN = API_URL.replace(/\/api\/v1\/?$/, "");

/** Window event broadcast after the user's ChronOS data is wiped. */
export const CHRONOS_DATA_CLEARED_EVENT = "opentime:chronos-data-cleared";

/**
 * Broadcast that the authenticated user's ChronOS data has been wiped (e.g.
 * after "Delete all my ChronOS data"). Consuming pages listen so they never
 * keep showing stale/phantom data that no longer exists server-side.
 */
export function notifyChronosDataCleared(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(CHRONOS_DATA_CLEARED_EVENT));
}

/** Subscribe to the data-cleared event. Returns a cleanup function. */
export function onChronosDataCleared(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(CHRONOS_DATA_CLEARED_EVENT, listener);
  return () => window.removeEventListener(CHRONOS_DATA_CLEARED_EVENT, listener);
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return JSON.parse(localStorage.getItem("opentime_tokens") ?? "null")?.access_token ?? null;
  } catch { return null; }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) return { Authorization: `Bearer ${token}` };
  return {};
}

async function req<T>(path: string, options: HttpOptions = {}): Promise<T> {
  return http<T>(`${ENGINE_BASE}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers as Record<string, string>) },
  });
}

async function reqNoThrow<T>(path: string, options: HttpOptions = {}): Promise<T> {
  try {
    return await req<T>(path, options);
  } catch {
    return [] as unknown as T;
  }
}

export interface UserInputPayload {
  id: string;
  user_id: string;
  input_type: "text" | "audio" | "video" | "image";
  content: string;
  media_url?: string;
  file_name?: string;
  media_metadata?: Record<string, any>;
  timestamp: string;
}

export interface MemoryItem {
  id: string;
  user_id: string;
  content: string;
  memory_type: string;
  created_at: string;
  timestamp: string;
  importance_score: number;
  linked_memory_ids: string[];
  tags: string[];
  metadata: Record<string, any>;
  is_genesis?: boolean;
}

export interface TimelineEvent {
  id: string;
  user_id: string;
  title: string;
  description: string;
  timestamp: string;
  life_phase: string;
  is_recurring: boolean;
  frequency?: string;
  memory_ids: string[];
  sentiment: number;
  belief_evolution_notes?: string;
}

export interface IdentityProfile {
  user_id: string;
  interests: string[];
  goals: string[];
  values: string[];
  emotional_tendencies: Record<string, number>;
  skills: string[];
  relationships: Record<string, string>;
  preferences: Record<string, any>;
  decision_patterns: string[];
  communication_style: string;
  version: number;
  last_updated: string;
}

export interface ReflectionInsight {
  id: string;
  user_id: string;
  insight_type: string;
  summary: string;
  past_state_summary: string;
  current_state_summary: string;
  confidence_score: number;
  supporting_memory_ids: string[];
  reasoning_trace: string[];
  affected_time_range: string;
  timestamp: string;
}

export interface PatternItem {
  id: string;
  user_id: string;
  category: string;
  title: string;
  description: string;
  frequency: string;
  confidence_score: number;
  first_detected: string;
  last_detected: string;
  supporting_memory_ids: string[];
}

export interface TemporalEvent {
  id: string;
  temporal_type?: string;
  description: string;
  occurred_at: string;
  recorded_at: string;
}

export interface TemporalThread {
  id: string;
  temporal_type?: string;
  subject: string;
  description?: string;
  status: string;
  user_archived?: boolean;
  created_at: string;
  updated_at: string;
  event_count: number;
  events?: TemporalEvent[];
}

export interface ReasoningTrace {
  confidence_score: number;
  supporting_memory_ids: string[];
  reasoning_steps: string[];
  affected_time_range: string;
  context_sources: string[];
}

export interface ValidationResult {
  is_valid: boolean;
  validated_response: string;
  corrections_made: string[];
  contradictions_detected: string[];
  personalization_score: number;
}

export interface PastSelfMoment {
  should_surface: boolean;
  opening: string;
  context: string;
  bridge: string;
  question: string;
  question_type?: string;
  relation?: string;
  confidence: number;
}

export interface TemporalReflection {
  used: boolean;
  success: boolean;
  reflection: string;
}

export interface TemporalLifecycleResult {
  attempted: boolean;
  created: boolean;
  updated: boolean;
  persisted: boolean;
  thread_id?: string;
  event_id?: string;
  thread_subject?: string;
  previous_status?: string;
  current_status?: string;
  transitioned: boolean;
}

/** Minimal, safely-typed view of a retrieved memory: only the human-readable
 *  content is ever needed on the client. Raw ids / embeddings never surface. */
export interface RetrievedMemoryPayload {
  content: string;
  memory_type?: string;
}

/** Minimal client view of the deterministic retrieval context. Mirrors the
 *  shape already emitted by the backend; strictly human-readable subsets. */
export interface RetrievedContextPayload {
  relevant_memories?: RetrievedMemoryPayload[];
}

export interface IntentResultPayload {
  intent?: string | null;
  signals?: string[];
}

export interface UserStateResultPayload {
  emotional_state?: string | null;
  cognitive_state?: string | null;
}

export interface ChronosState {
  intent?: IntentResultPayload;
  user_state?: UserStateResultPayload;
  context?: RetrievedContextPayload;
  temporal_reflection?: TemporalReflection;
  temporal_lifecycle?: TemporalLifecycleResult;
  past_self_conversation?: PastSelfMoment;
}

export interface ActiveTemporalEvent {
  description: string;
  temporal_type?: string;
  occurred_at?: string;
}

export interface ActiveTemporalContext {
  thread_id: string;
  subject: string;
  description?: string;
  temporal_type?: string;
  status: string;
  origin_description?: string;
  origin_occurred_at?: string;
  recent_events: ActiveTemporalEvent[];
}

export type ReturnUserKind = "FIRST_EVER" | "RETURNING" | "MEANINGFULLY_RETURNING";
export type ReturnChangeType =
  | "STORY_PROGRESSED"
  | "STORY_RESOLVED"
  | "STORY_CHANGED"
  | "NEW_STORY";

export interface ReturnChange {
  change_type: ReturnChangeType;
  headline: string;
  detail: string;
  thread_id?: string;
  subject: string;
}

export interface ReturnContext {
  has_return_context: boolean;
  user_kind: ReturnUserKind;
  since_timestamp?: string;
  welcome: string;
  summary_section?: string;
  changes: ReturnChange[];
  suggested_story_subject?: string;
  suggested_thread_id?: string;
  suggested_story_because: string;
}

export interface InteractionRecord {
  id: string;
  user_content: string;
  input_type: string;
  final_response: string;
  provider_name: string;
  model_name: string;
  processing_time_ms: number;
  created_at: string;
  past_self_opening: string;
  past_self_context: string;
  past_self_bridge: string;
  past_self_question: string;
  past_self_reflection: string;
}

export interface EngineResponse {
  id: string;
  user_id: string;
  original_input: UserInputPayload;
  raw_llm_response: string;
  final_response: string;
  provider_name: string;
  model_name: string;
  prompt_context: {
    system_prompt: string;
    user_prompt: string;
    retrieved_context: any;
  };
  reasoning_trace: ReasoningTrace;
  validation_result: ValidationResult;
  chronos_state?: ChronosState;
  active_thread_context?: ActiveTemporalContext;
  processing_time_ms: number;
  timestamp: string;
}

export const chronosApi = {
  /** Resolve a relative media path (e.g. /uploads/...) to an authenticated URL. */
  mediaUrl(relativePath?: string | null, token?: string | null): string | undefined {
    if (!relativePath) return undefined;
    if (/^https?:\/\//.test(relativePath)) return relativePath;
    // Convert /uploads/{user_id}/{file} → /api/v1/chronos/engine/media/{user_id}/{file}
    const match = relativePath.match(/^\/uploads\/([^/]+)\/(.+)$/);
    if (match) {
      return `${ENGINE_BASE}/media/${match[1]}/${match[2]}`;
    }
    return `${BACKEND_ORIGIN}${relativePath.startsWith("/") ? "" : "/"}${relativePath}`;
  },

  /** Fetch a media file with the auth header and return an object URL.
   *  Honours an optional AbortSignal so callers can revoke in-flight work. */
  async fetchMediaObjectUrl(
    relativePath?: string | null,
    signal?: AbortSignal,
  ): Promise<string | null> {
    const url = this.mediaUrl(relativePath);
    if (!url) return null;
    const token = getToken();
    if (!token) return null;
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    });
    if (!res.ok) return null;
    const blob = await res.blob();
    if (signal?.aborted) return null;
    return URL.createObjectURL(blob);
  },

  async processInput(formData: FormData, signal?: AbortSignal): Promise<EngineResponse> {
    return http<EngineResponse>(`${ENGINE_BASE}/process`, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
      signal,
    });
  },

  async getMemories(signal?: AbortSignal): Promise<MemoryItem[]> {
    return reqNoThrow<MemoryItem[]>("/memories", { signal });
  },

  async getTimeline(signal?: AbortSignal): Promise<TimelineEvent[]> {
    return reqNoThrow<TimelineEvent[]>("/timeline", { signal });
  },

  async getIdentity(signal?: AbortSignal): Promise<IdentityProfile> {
    return req<IdentityProfile>("/identity", { signal });
  },

  async getReflections(signal?: AbortSignal): Promise<ReflectionInsight[]> {
    return reqNoThrow<ReflectionInsight[]>("/reflections", { signal });
  },

  async getPatterns(signal?: AbortSignal): Promise<PatternItem[]> {
    return reqNoThrow<PatternItem[]>("/patterns", { signal });
  },

  async getInteractions(limit = 20, signal?: AbortSignal): Promise<InteractionRecord[]> {
    return reqNoThrow<InteractionRecord[]>(`/interactions?limit=${limit}`, { signal });
  },

  async getThreads(signal?: AbortSignal): Promise<TemporalThread[]> {
    return reqNoThrow<TemporalThread[]>("/threads", { signal });
  },

  async getThread(threadId: string): Promise<TemporalThread> {
    return req<TemporalThread>(`/threads/${threadId}`);
  },

  /** Permanently delete one memory belonging to the authenticated user. */
  async deleteMemory(memoryId: string): Promise<void> {
    await req<void>(`/memories/${memoryId}`, { method: "DELETE" });
  },

  /** User-controlled archive of a Story (presentation-level; history kept). */
  async archiveStory(threadId: string): Promise<TemporalThread> {
    return req<TemporalThread>(`/threads/${threadId}/archive`, { method: "POST" });
  },

  /** Restore a previously archived Story. */
  async restoreStory(threadId: string): Promise<TemporalThread> {
    return req<TemporalThread>(`/threads/${threadId}/restore`, { method: "POST" });
  },

  /** Deterministic, grounded return context for the authenticated user. */
  async getReturnContext(signal?: AbortSignal): Promise<ReturnContext> {
    return req<ReturnContext>("/return-context", { signal });
  },

  /** Toggle the in-app return-hook preference for the authenticated user. */
  async setReturnContextPreference(enabled: boolean): Promise<{ enabled: boolean }> {
    return req<{ enabled: boolean }>("/return-context", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
  },

  /** Export the authenticated user's full ChronOS engine data. */
  async exportData(): Promise<any> {
    return req<any>("/export");
  },

  /** Permanently delete the authenticated user's ChronOS engine data. */
  async deleteAllData(): Promise<void> {
    return req<void>("/", { method: "DELETE" });
  },
};
