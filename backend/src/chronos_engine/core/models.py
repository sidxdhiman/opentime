from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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


class ReasoningTrace(BaseModel):
    confidence_score: float = 0.9
    supporting_memory_ids: List[str] = Field(default_factory=list)
    reasoning_steps: List[str] = Field(default_factory=list)
    affected_time_range: str = "Recent interactions"
    context_sources: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    is_valid: bool = True
    validated_response: str
    corrections_made: List[str] = Field(default_factory=list)
    contradictions_detected: List[str] = Field(default_factory=list)
    personalization_score: float = 0.95


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
    processing_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Imported at the end to avoid a circular import: ChronosState lives in the
# chronos_engine.state package but itself references core models defined above.
from chronos_engine.state.models import ChronosState  # noqa: E402

# Force schema resolution for the deferred forward reference on EngineResponse.
EngineResponse.model_rebuild()
