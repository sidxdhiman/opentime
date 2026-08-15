from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from chronos_engine.core.models import (
    EngineResponse,
    IdentityProfile,
    MemoryItem,
    PatternItem,
    PromptContext,
    ReflectionInsight,
    RetrievedContext,
    TimelineEvent,
    UserInput,
    ValidationResult,
)
from chronos_engine.state.models import (
    ChronosState,
    ConsistencyResult,
    GoalAnalysisResult,
    IntentResult,
    UserStateResult,
)
from chronos_engine.response.models import DeterministicResponse


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Generate semantic embedding vector for a string."""
        pass

    @abstractmethod
    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two embedding vectors."""
        pass


class BaseStorageAdapter(ABC):
    @abstractmethod
    async def save_memory(self, memory: MemoryItem) -> MemoryItem:
        pass

    @abstractmethod
    async def get_memories_by_user(self, user_id: str, limit: int = 100) -> List[MemoryItem]:
        pass

    @abstractmethod
    async def save_timeline_event(self, event: TimelineEvent) -> TimelineEvent:
        pass

    @abstractmethod
    async def get_timeline_by_user(self, user_id: str) -> List[TimelineEvent]:
        pass

    @abstractmethod
    async def save_identity(self, profile: IdentityProfile) -> IdentityProfile:
        pass

    @abstractmethod
    async def get_identity(self, user_id: str) -> Optional[IdentityProfile]:
        pass

    @abstractmethod
    async def save_reflection(self, insight: ReflectionInsight) -> ReflectionInsight:
        pass

    @abstractmethod
    async def get_reflections_by_user(self, user_id: str) -> List[ReflectionInsight]:
        pass

    @abstractmethod
    async def save_pattern(self, pattern: PatternItem) -> PatternItem:
        pass

    @abstractmethod
    async def get_patterns_by_user(self, user_id: str) -> List[PatternItem]:
        pass


class BaseMemorySystem(ABC):
    @abstractmethod
    async def add_interaction(self, input_item: UserInput) -> MemoryItem:
        """Store interaction as a memory item and generate semantic embedding."""
        pass

    @abstractmethod
    async def search_semantic_memories(
        self, user_id: str, query: str, top_k: int = 5
    ) -> List[MemoryItem]:
        """Retrieve memories relevant to the query based on embedding similarity."""
        pass

    @abstractmethod
    async def get_short_term_context(self, user_id: str, limit: int = 5) -> List[MemoryItem]:
        """Get recent conversational memories."""
        pass


class BaseTimelineEngine(ABC):
    @abstractmethod
    async def process_memory(self, user_id: str, memory: MemoryItem) -> TimelineEvent:
        """Organize memory chronologically, detect life phase and recurring events."""
        pass

    @abstractmethod
    async def get_timeline(self, user_id: str) -> List[TimelineEvent]:
        """Get ordered chronological timeline for user."""
        pass

    @abstractmethod
    async def generate_historical_summary(self, user_id: str) -> str:
        """Build narrative summary of user timeline."""
        pass


class BaseIdentityModel(ABC):
    @abstractmethod
    async def get_or_create_profile(self, user_id: str) -> IdentityProfile:
        pass

    @abstractmethod
    async def evolve_profile(
        self, user_id: str, memory: MemoryItem, prompt_context: Optional[Dict[str, Any]] = None
    ) -> IdentityProfile:
        """Continuously update profile fields based on new interaction."""
        pass


class BaseReflectionEngine(ABC):
    @abstractmethod
    async def compare_past_and_present(
        self, user_id: str, days_back: int = 30
    ) -> List[ReflectionInsight]:
        """Compare historic self vs current self and generate insights."""
        pass


class BasePatternDetector(ABC):
    @abstractmethod
    async def analyze_patterns(self, user_id: str) -> List[PatternItem]:
        """Identify habits, recurring problems, repeated successes, and mood/behavior shifts."""
        pass


class BaseIntentDetector(ABC):
    @abstractmethod
    async def detect_intent(self, user_input: str) -> "IntentResult":
        """Classify raw input text into one of the intent taxonomy categories."""
        pass


class BaseUserStateDetector(ABC):
    @abstractmethod
    async def detect_state(
        self, user_input: "UserInput", intent: "Optional[IntentResult]" = None
    ) -> UserStateResult:
        """Infer cautious interaction-state signals from the input's language.

        The already-detected intent may be passed as optional context, but it
        must never directly determine the emotional state.
        """
        pass


class BaseGoalDetector(ABC):
    @abstractmethod
    async def detect_goals(
        self, user_input: "UserInput", existing_goals: "List[str]"
    ) -> GoalAnalysisResult:
        """Analyze how the current input relates to the user's goals.

        Determines whether the input introduces a new goal or relates to an
        existing goal (active / progress / completed / abandoned / blocked /
        changed). Deterministic and offline.
        """
        pass


class BaseConsistencyEngine(ABC):
    @abstractmethod
    async def check_consistency(
        self,
        user_input: "UserInput",
        retrieved_context: "RetrievedContext",
        goal_analysis: "Optional[GoalAnalysisResult]" = None,
        identity: "Optional[IdentityProfile]" = None,
        current_memory_id: "Optional[str]" = None,
    ) -> ConsistencyResult:
        """Compare the current input against stored user context.

        Detects goal changes, goal/preference/identity conflicts, decision
        changes and statement contradictions. A *change* is a continuity signal,
        not an accusation that the user is wrong. Deterministic and offline.
        """
        pass


class BaseRetrievalEngine(ABC):
    @abstractmethod
    async def retrieve_context(self, user_input: UserInput) -> RetrievedContext:
        """Retrieve relevant memories, timeline events, identity info, and patterns for input."""
        pass


class BasePromptOrchestrator(ABC):
    @abstractmethod
    async def orchestrate_prompt(
        self, user_input: UserInput, retrieved_context: RetrievedContext
    ) -> PromptContext:
        """Construct rich augmented prompt for LLM."""
        pass


class BaseLLMProvider(ABC):
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def generate_response(self, prompt_context: PromptContext, model_name: str) -> str:
        """Execute LLM call using model-agnostic provider."""
        pass


class BaseResponseValidator(ABC):
    @abstractmethod
    async def validate_response(
        self, raw_response: str, prompt_context: PromptContext
    ) -> ValidationResult:
        """Verify factual consistency, remove contradictions, and inject missing context."""
        pass


class BaseResponseGenerator(ABC):
    @abstractmethod
    def generate(self, state: "ChronosState") -> DeterministicResponse:
        """Build a fully deterministic, human-readable interpretation of a state.

        Pure computation over ``ChronosState``: no LLM, no network, no
        retrieval. Identical states always produce identical responses.
        """
        pass


class BaseAIRouter(ABC):
    @abstractmethod
    def route(self, state: "ChronosState") -> "AIRoutingResult":
        """Decide whether the state requires an AI model.

        Deterministic and offline: the router never calls an LLM. It only
        classifies the interaction as ``FAST`` (deterministic is sufficient)
        or ``DEEP`` (AI would materially improve the result).
        """
        pass


# Imported at the end to avoid a circular import: routing.service imports
# BaseAIRouter above, and importing routing.models mid-module would trigger
# the routing package __init__ -> routing.service -> core.interfaces loop
# while core.interfaces is still partially initialized.
from chronos_engine.routing.models import AIRoutingResult  # noqa: E402
