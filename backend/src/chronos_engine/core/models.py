from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from chronos_engine.temporal.models import ActiveTemporalContext


class InputType(str, Enum):
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class PatternCategory(str, Enum):
    HABIT = "habit"
    RECURRING_PROBLEM = "recurring_problem"
    REPEATED_SUCCESS = "repeated_success"
    BEHAVIOR_LOOP = "behavior_loop"
    PRODUCTIVITY_TREND = "productivity_trend"
    MOOD_SHIFT = "mood_shift"
    DECISION_CHANGE = "decision_change"


class ReflectionInsightType(str, Enum):
    BELIEF_SHIFT = "belief_shift"
    FOCUS_SHIFT = "focus_shift"
    EMOTIONAL_SHIFT = "emotional_shift"
    HABIT_CHANGE = "habit_change"


class IntentType(str, Enum):
    """User communication intents understood by the ChronOS engine.

    Values are UPPERCASE so the taxonomy reads clearly in API payloads and
    reasoning traces (e.g. ``DECISION``). ``UNKNOWN`` is the fallback for
    inputs that do not clearly signal any communicative need.
    """

    QUESTION = "QUESTION"
    REQUEST = "REQUEST"
    DECISION = "DECISION"
    PLANNING = "PLANNING"
    REFLECTION = "REFLECTION"
    EMOTIONAL_SUPPORT = "EMOTIONAL_SUPPORT"
    INFORMATION = "INFORMATION"
    CREATION = "CREATION"
    PROBLEM_SOLVING = "PROBLEM_SOLVING"
    STATUS_UPDATE = "STATUS_UPDATE"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    COMMAND = "COMMAND"
    UNKNOWN = "UNKNOWN"


class UserInput(BaseModel):
    id: str
    user_id: str
    input_type: InputType = InputType.TEXT
    content: str
    media_url: Optional[str] = None
    file_name: Optional[str] = None
    media_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryItem(BaseModel):
    id: str
    user_id: str
    content: str
    memory_type: MemoryType = MemoryType.LONG_TERM
    embedding: List[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    importance_score: float = 0.5
    linked_memory_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    life_phase: str = "General"
    is_recurring: bool = False
    frequency: Optional[str] = None
    memory_ids: List[str] = Field(default_factory=list)
    sentiment: float = 0.0  # -1.0 to 1.0
    belief_evolution_notes: Optional[str] = None


class IdentityProfile(BaseModel):
    user_id: str
    interests: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    values: List[str] = Field(default_factory=list)
    emotional_tendencies: Dict[str, float] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    relationships: Dict[str, str] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    decision_patterns: List[str] = Field(default_factory=list)
    communication_style: str = "Direct & Thoughtful"
    version: int = 1
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReflectionInsight(BaseModel):
    id: str
    user_id: str
    insight_type: ReflectionInsightType
    summary: str
    past_state_summary: str
    current_state_summary: str
    confidence_score: float = 0.85
    supporting_memory_ids: List[str] = Field(default_factory=list)
    reasoning_trace: List[str] = Field(default_factory=list)
    affected_time_range: str = "Past 30 days"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PatternItem(BaseModel):
    id: str
    user_id: str
    category: PatternCategory
    title: str
    description: str
    frequency: str = "Ongoing"
    confidence_score: float = 0.8
    first_detected: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_detected: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    supporting_memory_ids: List[str] = Field(default_factory=list)


class RetrievedContext(BaseModel):
    relevant_memories: List[MemoryItem] = Field(default_factory=list)
    timeline_events: List[TimelineEvent] = Field(default_factory=list)
    life_phase: str = "Current Phase"
    identity_summary: Dict[str, Any] = Field(default_factory=dict)
    patterns: List[PatternItem] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    recent_changes: List[str] = Field(default_factory=list)


class PromptContext(BaseModel):
    current_input: UserInput
    retrieved_context: RetrievedContext
    system_prompt: str
    user_prompt: str
    assembled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def full_prompt(self) -> str:
        """The complete prompt sent to a provider: system rules + user prompt.

        Providers that have no separate system slot (e.g. Ollama's
        ``/api/generate``) send this single string, so the safety
        instructions always reach the model and prompt-size measurement
        reflects exactly what is transmitted.
        """
        if not self.system_prompt.strip():
            return self.user_prompt
        return f"{self.system_prompt}\n\n{self.user_prompt}"


class ReasoningTrace(BaseModel):
    confidence_score: float = 0.9
    supporting_memory_ids: List[str] = Field(default_factory=list)
    reasoning_steps: List[str] = Field(default_factory=list)
    ai_execution_steps: List[Dict[str, Any]] = Field(default_factory=list)
    affected_time_range: str = "Recent interactions"
    context_sources: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    is_valid: bool = True
    validated_response: str
    corrections_made: List[str] = Field(default_factory=list)
    contradictions_detected: List[str] = Field(default_factory=list)
    personalization_score: float = 0.95


class InteractionRecord(BaseModel):
    """Lightweight persistence of one user→ChronOS interaction.

    Stores only what is needed to reconstruct the conversation display on
    reload. Internal reasoning, prompts, provider metadata, and full
    ChronosState are intentionally excluded. Safe display fields from the
    Past-Self moment are included so structured moments survive page refresh.
    """

    id: str
    user_id: str
    user_content: str = ""
    input_type: str = "text"
    final_response: str = ""
    provider_name: str = ""
    model_name: str = ""
    processing_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Safe display fields from Past-Self moment (empty when no moment surfaced)
    past_self_opening: str = ""
    past_self_context: str = ""
    past_self_bridge: str = ""
    past_self_question: str = ""
    past_self_reflection: str = ""


class EngineResponse(BaseModel):
    id: str
    user_id: str
    original_input: UserInput
    raw_llm_response: str
    final_response: str
    provider_name: str
    model_name: str
    prompt_context: PromptContext
    reasoning_trace: ReasoningTrace
    validation_result: ValidationResult
    chronos_state: Optional["ChronosState"] = None
    deterministic_response: Optional["DeterministicResponse"] = None
    ai_routing: Optional["AIRoutingResult"] = None
    ai_execution: Optional["AIExecutionResult"] = None
    inference_policy: Optional["InferencePolicyDecision"] = None
    processing_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Phase 4F: resolved active thread context (set by API boundary, not engine)
    active_thread_context: Optional[ActiveTemporalContext] = None


# Imported at the end to avoid a circular import: ChronosState lives in the
# chronos_engine.state package but itself references core models defined above,
# DeterministicResponse lives in the chronos_engine.response package,
# AIRoutingResult lives in the chronos_engine.routing package, and
# AIExecutionResult lives in the chronos_engine.ai package.
from chronos_engine.state.models import ChronosState  # noqa: E402
from chronos_engine.response.models import DeterministicResponse  # noqa: E402
from chronos_engine.routing.models import AIRoutingResult  # noqa: E402
from chronos_engine.ai.models import AIExecutionResult  # noqa: E402
from chronos_engine.ai.policy.models import InferencePolicyDecision  # noqa: E402

# Force schema resolution for the deferred forward reference on EngineResponse.
EngineResponse.model_rebuild()
