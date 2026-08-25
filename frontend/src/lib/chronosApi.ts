const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const ENGINE_BASE = `${API_URL}/chronos/engine`;
const BACKEND_ORIGIN = API_URL.replace(/\/api\/v1\/?$/, "");

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
  embedding?: number[];
  created_at: string;
  timestamp: string;
  importance_score: number;
  linked_memory_ids: string[];
  tags: string[];
  metadata: Record<string, any>;
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
  thread_id?: string;
  temporal_type?: string;
  description: string;
  memory_id?: string;
  occurred_at: string;
  recorded_at: string;
  importance: number;
  confidence: number;
}

export interface TemporalThread {
  id: string;
  temporal_type?: string;
  subject: string;
  description?: string;
  status: string;
  origin_memory_id?: string;
  related_memory_ids: string[];
  importance: number;
  confidence: number;
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

export interface ChronosState {
  past_self_conversation?: PastSelfMoment;
  temporal_reflection?: TemporalReflection;
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

export interface InteractionRecord {
  id: string;
  user_content: string;
  input_type: string;
  final_response: string;
  provider_name: string;
  model_name: string;
  processing_time_ms: number;
  created_at: string;
  past_self_opening?: string;
  past_self_context?: string;
  past_self_bridge?: string;
  past_self_question?: string;
  past_self_reflection?: string;
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
  /** Resolve a relative media path (e.g. /uploads/...) against the backend origin. */
  mediaUrl(relativePath?: string | null): string | undefined {
    if (!relativePath) return undefined;
    if (/^https?:\/\//.test(relativePath)) return relativePath;
    return `${BACKEND_ORIGIN}${relativePath.startsWith("/") ? "" : "/"}${relativePath}`;
  },

  async processInput(formData: FormData): Promise<EngineResponse> {
    const res = await fetch(`${ENGINE_BASE}/process`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Engine execution failed" }));
      throw new Error(err.detail || "ChronOS Engine execution failed");
    }
    return res.json();
  },

  async processInputJson(data: {
    user_id?: string;
    content?: string;
    input_type?: string;
    base64_data?: string;
    file_name?: string;
    provider_key?: string;
    model_name?: string;
    active_thread_id?: string;
  }): Promise<EngineResponse> {
    const res = await fetch(`${ENGINE_BASE}/process-json`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "user_default", ...data }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Engine execution failed" }));
      throw new Error(err.detail || "ChronOS Engine execution failed");
    }
    return res.json();
  },

  async getMemories(userId = "user_default"): Promise<MemoryItem[]> {
    const res = await fetch(`${ENGINE_BASE}/memories?user_id=${userId}`);
    if (!res.ok) return [];
    return res.json();
  },

  async getTimeline(userId = "user_default"): Promise<TimelineEvent[]> {
    const res = await fetch(`${ENGINE_BASE}/timeline?user_id=${userId}`);
    if (!res.ok) return [];
    return res.json();
  },

  async getIdentity(userId = "user_default"): Promise<IdentityProfile> {
    const res = await fetch(`${ENGINE_BASE}/identity?user_id=${userId}`);
    if (!res.ok) throw new Error("Failed to load identity");
    return res.json();
  },

  async getReflections(userId = "user_default"): Promise<ReflectionInsight[]> {
    const res = await fetch(`${ENGINE_BASE}/reflections?user_id=${userId}`);
    if (!res.ok) return [];
    return res.json();
  },

  async getPatterns(userId = "user_default"): Promise<PatternItem[]> {
    const res = await fetch(`${ENGINE_BASE}/patterns?user_id=${userId}`);
    if (!res.ok) return [];
    return res.json();
  },

  async getInteractions(userId = "user_default", limit = 20): Promise<InteractionRecord[]> {
    const res = await fetch(`${ENGINE_BASE}/interactions?user_id=${userId}&limit=${limit}`);
    if (!res.ok) return [];
    return res.json();
  },

  async getThreads(userId = "user_default"): Promise<TemporalThread[]> {
    const res = await fetch(`${ENGINE_BASE}/threads?user_id=${userId}`);
    if (!res.ok) return [];
    return res.json();
  },

  async getThread(threadId: string, userId = "user_default"): Promise<TemporalThread> {
    const res = await fetch(`${ENGINE_BASE}/threads/${threadId}?user_id=${userId}`);
    if (!res.ok) throw new Error("Thread not found");
    return res.json();
  },

  async getProviders(): Promise<{ active: string; available: Record<string, string> }> {
    const res = await fetch(`${ENGINE_BASE}/providers`);
    if (!res.ok) return { active: "chronos", available: { chronos: "ChronOS Native" } };
    return res.json();
  },

  async seedState(userId = "user_default"): Promise<void> {
    await fetch(`${ENGINE_BASE}/seed?user_id=${userId}`, { method: "POST" });
  },
};
