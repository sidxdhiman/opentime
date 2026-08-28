from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from chronos_engine.core.models import (
    EngineResponse,
    IdentityProfile,
    InteractionRecord,
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
from chronos_engine.temporal.models import (
    ActiveTemporalContext,
    PastSelfConversationMoment,
    PastSelfQuestionResult,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalEventDetectionResult,
    TemporalLifecycleResult,
    TemporalReflectionResult,
    TemporalRelevanceResult,
    TemporalSnapshot,
    TemporalThread,
    TemporalThreadMatchResult,
)


class BaseTemporalStore(ABC):
    """Persistence contract for the temporal domain.

    Dormant in Phase 3A: nothing in the engine creates or reads temporal
    documents yet. The abstraction exists so later temporal phases can add
    persistence without reshaping existing interfaces. Implementations must
    never fabricate threads, events or snapshots — they only store and
    return what they were given.
    """

    @abstractmethod
    async def save_thread(self, thread: "TemporalThread") -> "TemporalThread":
        pass

    @abstractmethod
    async def get_thread(self, thread_id: str, user_id: str) -> Optional["TemporalThread"]:
        pass

    @abstractmethod
    async def get_threads_by_user(self, user_id: str) -> List["TemporalThread"]:
        pass

    @abstractmethod
    async def get_candidate_threads(self, user_id: str, limit: int = 25) -> List["TemporalThread"]:
        """Return bounded candidate threads for matching.

        Phase 3C contract: candidates for thread matching are live threads
        (not archived/resolved/abandoned), most recent first, capped by
        ``limit``. This is a targeted read over the temporal store only —
        never a scan of user memories and never a vector/embedding query.
        """
        pass

    @abstractmethod
    async def find_thread_by_origin_memory(
        self, user_id: str, memory_id: str
    ) -> Optional["TemporalThread"]:
        """Find a thread whose ``origin_memory_id`` equals ``memory_id``.

        Required for lifecycle idempotency (Phase 3D): before creating a new
        thread from an event, the lifecycle manager checks whether a thread
        was already created from the same memory so accidental reprocessing
        never produces duplicate threads. Targeted indexed lookup — never a
        full collection scan.
        """
        pass

    @abstractmethod
    async def save_event(self, event: "TemporalEvent") -> "TemporalEvent":
        pass

    @abstractmethod
    async def get_events_by_thread(self, thread_id: str, user_id: str) -> List["TemporalEvent"]:
        pass

    @abstractmethod
    async def save_snapshot(self, snapshot: "TemporalSnapshot") -> "TemporalSnapshot":
        pass

    @abstractmethod
    async def get_snapshots_by_user(self, user_id: str) -> List["TemporalSnapshot"]:
        pass

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> None:
        """Remove every temporal thread, event and snapshot owned by the user.

        Must clear the user's threads, their events and their snapshots with
        no orphaned events or ownership mappings left behind.
        """
        pass


class BaseTemporalEventDetector(ABC):
    """Deterministic detection of meaningful temporal moments.

    Answers whether the current input is a moment worth recognizing as a
    ``TemporalEvent``. Purely offline: no LLM, no embeddings, no database.
    The detector may consume already-computed ChronOS evidence (intent,
    user state, goal analysis) but must never fabricate an event — when
    evidence is insufficient it returns ``detected=False`` with
    ``event=None``. It never persists anything and never touches threads;
    thread matching belongs to a later temporal phase.
    """

    @abstractmethod
    async def detect_temporal_event(
        self,
        user_input: "UserInput",
        intent: "Optional[IntentResult]" = None,
        user_state: "Optional[UserStateResult]" = None,
        goal_analysis: "Optional[GoalAnalysisResult]" = None,
        memory_id: Optional[str] = None,
    ) -> TemporalEventDetectionResult:
        pass


class BaseTemporalThreadMatcher(ABC):
    """Deterministic matching of a new TemporalEvent to existing threads.

    Answers one question: does this newly detected event belong to an
    existing ``TemporalThread``? The matcher is purely offline and
    conservative — a false connection is worse than no connection. It
    combines multiple deterministic evidence signals (topic overlap,
    temporal-type compatibility, goal association, consistency/change
    evidence, memory continuity); no single weak signal may produce a match.

    Candidates are supplied by the caller through a ``BaseTemporalStore``
    abstraction; the matcher itself never queries storage, never scans
    memories, never creates threads and never persists anything.
    """

    @abstractmethod
    async def match_threads(
        self,
        event: "TemporalEvent",
        candidate_threads: "List[TemporalThread]",
        goal_analysis: "Optional[GoalAnalysisResult]" = None,
        consistency_result: "Optional[ConsistencyResult]" = None,
        active_temporal_context: "Optional[ActiveTemporalContext]" = None,
    ) -> TemporalThreadMatchResult:
        pass


class BaseTemporalThreadLifecycleManager(ABC):
    """Deterministic lifecycle handling for temporal threads (Phase 3D).

    Turns detected ``TemporalEvent``s into persistent life-thread history:

    - confident NO_MATCH      -> create a new conservative, evidence-grounded
      ``TemporalThread`` and persist event + thread
    - confident MATCH         -> attach the event to the existing thread,
      update its memory links / ``updated_at``, and apply evidence-based
      status transitions through one explicit transition policy
    - AMBIGUOUS match         -> perform NO mutation at all
    - no detected event       -> perform nothing

    All decisions are deterministic and offline: no AI, no embeddings, no
    fabricated subjects. The manager is the only engine component allowed to
    mutate or persist threads/events; persistence goes exclusively through a
    ``BaseTemporalStore``.
    """

    @abstractmethod
    async def handle(
        self,
        user_id: str,
        detection: TemporalEventDetectionResult,
        match_result: Optional["TemporalThreadMatchResult"] = None,
        input_content: Optional[str] = None,
        goal_analysis: "Optional[GoalAnalysisResult]" = None,
        consistency_result: "Optional[ConsistencyResult]" = None,
    ) -> TemporalLifecycleResult:
        pass


class BaseTemporalComparisonEngine(ABC):
    """Deterministic Past-vs-Present comparison for temporal threads (Phase 3E).

    Answers one question per interaction: for the thread this input touched,
    how does the present moment relate to where that story began? Strictly
    read-only — the comparison never mutates threads or events, never
    persists anything, never crosses thread boundaries and never invents a
    new matching algorithm. Threads and their events are handed in by the
    caller (loaded through a ``BaseTemporalStore``); when evidence is
    insufficient the result says so honestly instead of fabricating a
    verdict.
    """

    @abstractmethod
    async def compare(
        self,
        user_id: str,
        thread: Optional["TemporalThread"],
        events: "List[TemporalEvent]",
        lifecycle_result: "Optional[TemporalLifecycleResult]" = None,
        consistency_result: "Optional[ConsistencyResult]" = None,
        goal_analysis: "Optional[GoalAnalysisResult]" = None,
    ) -> TemporalComparisonResult:
        pass


class BasePastSelfQuestionPlanner(ABC):
    """Deterministic past-self question planning for temporal threads
    (Phase 3F).

    Consumes the already-computed thread, comparison and lifecycle evidence
    and produces ONE structured decision: whether ChronOS should ask the
    present user something on behalf of their past self, what KIND of
    interaction is appropriate, WHAT it should be about (grounded focus +
    canonical template), and WHICH stored evidence supports it.

    Pure computation over handed-in objects — no LLM, no persistence, no
    mutation, no scheduling. Conservative by design: a comparison existing
    never automatically justifies a question; insufficient evidence yields
    an honest ``should_ask=False`` instead of a fabricated one. AI wording
    and personalization belong to a later phase.
    """

    @abstractmethod
    def plan(
        self,
        user_id: str,
        thread: Optional["TemporalThread"],
        comparison: Optional["TemporalComparisonResult"],
        lifecycle_result: "Optional[TemporalLifecycleResult]" = None,
        events: "Optional[List[TemporalEvent]]" = None,
    ) -> PastSelfQuestionResult:
        pass


class BaseTemporalRelevanceEngine(ABC):
    """Deterministic temporal relevance & timing evaluation (Phase 3G).

    Consumes the already-computed evidence of the current interaction
    (current input, Phase 3F ``PastSelfQuestionResult``, the touched
    ``TemporalThread``, comparison/lifecycle/match results, intent, user
    state, goal and consistency analysis) and produces ONE structured
    decision: should the planned past-self question be surfaced NOW,
    deferred ("not now" — a decision only, never a scheduled job), or
    skipped?

    Pure computation over handed-in objects — strictly read-only: no LLM,
    no embeddings, no storage access, no mutation, no persistence, no
    scheduling, no notifications. It never invents a past-self question
    and never overrides a Phase 3F ``should_ask=False`` decision.
    """

    @abstractmethod
    def evaluate(
        self,
        user_id: str,
        user_input: "UserInput",
        past_self_question: "PastSelfQuestionResult | None",
        thread: "TemporalThread | None" = None,
        events: "list[TemporalEvent] | None" = None,
        thread_match: "TemporalThreadMatchResult | None" = None,
        lifecycle_result: "TemporalLifecycleResult | None" = None,
        comparison: "TemporalComparisonResult | None" = None,
        intent: "IntentResult | None" = None,
        user_state: "UserStateResult | None" = None,
        goal_analysis: "GoalAnalysisResult | None" = None,
        consistency_result: "ConsistencyResult | None" = None,
    ) -> TemporalRelevanceResult:
        pass


class BasePastSelfConversationComposer(ABC):
    """Deterministic past-self conversation composition (Phase 3H).

    Consumes the already-computed Phase 3F question plan and Phase 3G
    relevance decision plus the grounded temporal evidence, and composes AT
    MOST ONE subtle user-facing conversation moment: a short opening, a
    grounded reminder of the earlier moment, an optional bridge to the
    present and the past-self question.

    Hard gate: a moment is only composed when relevance is ``SURFACE_NOW``,
    Phase 3F says the question should be asked, the thread exists and
    matches, the comparison is meaningful and nothing is ambiguous. A
    ``SURFACE_NOW`` decision is permission to surface — never permission to
    invent content.

    Pure computation over handed-in objects — strictly read-only: no LLM,
    no embeddings, no storage access, no mutation, no persistence, no
    scheduling, no notifications.
    """

    @abstractmethod
    def compose(
        self,
        user_id: str,
        past_self_question: "PastSelfQuestionResult",
        relevance_result: "TemporalRelevanceResult | None",
        thread: "TemporalThread | None" = None,
        comparison: "TemporalComparisonResult | None" = None,
        lifecycle_result: "TemporalLifecycleResult | None" = None,
        events: "list[TemporalEvent] | None" = None,
    ) -> "PastSelfConversationMoment":
        pass


class BaseTemporalReflectionGenerator(ABC):
    """Bounded AI enhancement of an already-valid temporal moment
    (Phase 3I).

    Consumes ONLY the deterministic Phase 3A–3H results (the composed
    ``PastSelfConversationMoment``, the planned question, the relevance
    decision, the comparison and the grounded evidence) and produces at
    most ONE optional, validated reflection that re-expresses what the
    deterministic pipeline already established.

    The AI is a writer/interpreter, never a historian: it may not decide
    temporal truth (detection, thread membership, lifecycle outcomes,
    question planning or surfacing remain deterministic), may not invent
    facts/emotions/durations, and every cited evidence id must come from
    the curated allowed set. Any failure — disabled provider, connection
    error, timeout, malformed output, hallucinated evidence, validation
    failure — yields an honest non-used result; the deterministic moment
    always surfaces unchanged. Never retries.

    Orchestration only: the generator uses the existing inference policy,
    LLM registry and parsing infrastructure rather than creating a second
    AI stack.
    """

    @abstractmethod
    async def generate(
        self,
        user_id: str,
        moment: "PastSelfConversationMoment",
        past_self_question: "PastSelfQuestionResult | None" = None,
        relevance_result: "TemporalRelevanceResult | None" = None,
        comparison: "TemporalComparisonResult | None" = None,
        lifecycle_result: "TemporalLifecycleResult | None" = None,
    ) -> "TemporalReflectionResult":
        pass


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

    @abstractmethod
    async def save_interaction(self, record: "InteractionRecord") -> "InteractionRecord":
        pass

    @abstractmethod
    async def get_interactions_by_user(
        self, user_id: str, limit: int = 50
    ) -> List["InteractionRecord"]:
        pass

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> None:
        """Remove all memories, timeline events, identity, reflections,
        patterns and interactions owned by the user."""
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


class BaseAIExecutor(ABC):
    @abstractmethod
    async def execute(
        self,
        routing_result: "AIRoutingResult",
        chronos_state: "ChronosState",
        deterministic_response: "DeterministicResponse",
        inference_policy_decision: "InferencePolicyDecision | None" = None,
    ) -> "AIExecutionResult":
        """Execute the AI routing decision through the selected provider.

        The executor is the ONLY component allowed to invoke the provider. It
        never decides which model to use (that is the ``InferencePolicy``'s
        job — the decision is consumed here), never mutates ``ChronosState``,
        never writes memory, and never crashes the engine when AI is
        unavailable — it returns an honest fallback result.
        """
        pass


class BaseReasoningPlanner(ABC):
    @abstractmethod
    def plan(
        self,
        state: "ChronosState",
        routing_result: "AIRoutingResult",
    ) -> "ReasoningPlan":
        """Decide the minimum-sufficient reasoning modes for one AI call.

        Deterministic and offline: the planner never calls an LLM. It only
        translates deterministic state into a ``ReasoningPlan`` that always
        ends with ``GENERATE``.
        """
        pass


# Imported at the end to avoid a circular import: routing.service imports
# BaseAIRouter above, and importing routing.models mid-module would trigger
# the routing package __init__ -> routing.service -> core.interfaces loop
# while core.interfaces is still partially initialized.
from chronos_engine.routing.models import AIRoutingResult  # noqa: E402
from chronos_engine.ai.models import AIExecutionResult  # noqa: E402
from chronos_engine.ai.policy.models import InferencePolicyDecision  # noqa: E402
from chronos_engine.ai.reasoning.models import ReasoningPlan  # noqa: E402
