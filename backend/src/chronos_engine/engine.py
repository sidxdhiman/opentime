import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from chronos_engine.core.interfaces import (
    BaseEmbeddingProvider,
    BaseIdentityModel,
    BaseIntentDetector,
    BaseMemorySystem,
    BasePatternDetector,
    BasePromptOrchestrator,
    BaseReflectionEngine,
    BaseResponseValidator,
    BaseRetrievalEngine,
    BaseStorageAdapter,
    BaseTimelineEngine,
    BaseUserStateDetector,
    BaseGoalDetector,
)
from chronos_engine.core.models import (
    EngineResponse,
    IdentityProfile,
    InputType,
    MemoryItem,
    PatternItem,
    ReasoningTrace,
    ReflectionInsight,
    TimelineEvent,
    UserInput,
)
from chronos_engine.embeddings.provider import DefaultEmbeddingProvider
from chronos_engine.identity.service import IdentityModel
from chronos_engine.intent.service import IntentDetector
from chronos_engine.llm.providers import LLMRegistry
from chronos_engine.memory.service import MemorySystem
from chronos_engine.orchestrator.service import PromptOrchestrator
from chronos_engine.patterns.service import PatternDetector
from chronos_engine.reflection.service import ReflectionEngine
from chronos_engine.retrieval.service import RetrievalEngine
from chronos_engine.storage.repository import InMemoryStorageAdapter
from chronos_engine.timeline.service import TimelineEngine
from chronos_engine.utils.media_processor import MediaProcessor
from chronos_engine.validators.service import ResponseValidator
from chronos_engine.state.builder import StateBuilder
from chronos_engine.state.models import ChronosState, GoalAnalysisResult, UserStateResult
from chronos_engine.user_state.service import UserStateDetector
from chronos_engine.goals.service import GoalDetector


class ChronosEngine:
    """
    ChronOS Engine: Core Intelligence Layer for OpenTime.
    
    Architecture:
    User Input (Text / Audio / Video / Image)
            ↓
    Input Processing Layer
            ↓
    User Memory System & Retrieval Engine
            ↓
    Prompt Orchestrator
            ↓
    Model-Agnostic LLM Provider
            ↓
    Response Validator & Post-Processing Layer
            ↓
    Identity Profile & Timeline Evolution Engine
            ↓
    API Response with Complete Explainability Trace
    """

    def __init__(
        self,
        storage: Optional[BaseStorageAdapter] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        memory_system: Optional[BaseMemorySystem] = None,
        timeline_engine: Optional[BaseTimelineEngine] = None,
        identity_model: Optional[BaseIdentityModel] = None,
        reflection_engine: Optional[BaseReflectionEngine] = None,
        pattern_detector: Optional[BasePatternDetector] = None,
        retrieval_engine: Optional[BaseRetrievalEngine] = None,
        orchestrator: Optional[BasePromptOrchestrator] = None,
        validator: Optional[BaseResponseValidator] = None,
        llm_registry: Optional[LLMRegistry] = None,
        state_builder: Optional[StateBuilder] = None,
        intent_detector: Optional[BaseIntentDetector] = None,
        user_state_detector: Optional[BaseUserStateDetector] = None,
        goal_detector: Optional[BaseGoalDetector] = None,
    ):
        self.storage = storage or InMemoryStorageAdapter()
        self.embedding_provider = embedding_provider or DefaultEmbeddingProvider()
        
        self.memory_system = memory_system or MemorySystem(self.storage, self.embedding_provider)
        self.timeline_engine = timeline_engine or TimelineEngine(self.storage)
        self.identity_model = identity_model or IdentityModel(self.storage)
        self.reflection_engine = reflection_engine or ReflectionEngine(self.storage)
        self.pattern_detector = pattern_detector or PatternDetector(self.storage)
        
        self.retrieval_engine = retrieval_engine or RetrievalEngine(
            self.memory_system, self.timeline_engine, self.identity_model, self.pattern_detector
        )
        self.orchestrator = orchestrator or PromptOrchestrator()
        self.validator = validator or ResponseValidator()
        self.llm_registry = llm_registry or LLMRegistry()
        self.state_builder = state_builder or StateBuilder()
        self.intent_detector = intent_detector or IntentDetector()
        self.user_state_detector = user_state_detector or UserStateDetector()
        self.goal_detector = goal_detector or GoalDetector()

    async def process_user_input(
        self,
        user_id: str,
        content: Optional[str] = None,
        input_type: str = "text",
        media_bytes: Optional[bytes] = None,
        file_name: Optional[str] = None,
        base64_data: Optional[str] = None,
        provider_key: Optional[str] = None,
        model_name: Optional[str] = None,
        media_url: Optional[str] = None,
    ) -> EngineResponse:
        start_time = time.time()

        # Step 1: Input Processing Layer
        user_input: UserInput = await MediaProcessor.process_raw_input(
            user_id=user_id,
            content=content,
            input_type=input_type,
            media_bytes=media_bytes,
            file_name=file_name,
            base64_data=base64_data,
            media_url=media_url,
        )

        # Step 2: Store in Memory System
        memory_item: MemoryItem = await self.memory_system.add_interaction(user_input)

        # Step 3: Update Timeline & Identity
        await self.timeline_engine.process_memory(user_id, memory_item)
        await self.identity_model.evolve_profile(user_id, memory_item)

        # Step 4: Retrieval Engine (Retrieve context before calling LLM)
        retrieved_context = await self.retrieval_engine.retrieve_context(user_input)

        # Step 4a: Detect the user's intent from the raw input. Deterministic
        # and offline; the result feeds the structured state built next.
        intent_result = await self.intent_detector.detect_intent(user_input.content)

        # Step 4b: Infer the user's interaction state from the input's language.
        # Deterministic and offline; the already-detected intent is passed as
        # optional context but never determines the emotion directly.
        user_state_result: UserStateResult = await self.user_state_detector.detect_state(
            user_input, intent=intent_result
        )

        # Step 4c: Analyze how the input relates to the user's goals. Uses the
        # identity goals surfaced through retrieval as the existing-goal source.
        goal_analysis_result: GoalAnalysisResult = await self.goal_detector.detect_goals(
            user_input, retrieved_context.goals
        )

        # Step 4d: Build structured ChronOS state from the retrieved context.
        # The intent, user-state and goal detectors populate their sections.
        chronos_state: ChronosState = await self.state_builder.build(
            user_input,
            retrieved_context,
            intent=intent_result,
            user_state=user_state_result,
            goal_analysis=goal_analysis_result,
        )

        # Step 5: Prompt Orchestrator
        prompt_context = await self.orchestrator.orchestrate_prompt(user_input, retrieved_context)

        # Step 6: Model-Agnostic LLM Provider Call
        llm_provider = self.llm_registry.get_provider(provider_key)
        target_model = model_name or ("chronos-v1-core" if provider_key == "chronos" or not provider_key else "gpt-4o")
        raw_llm_response = await llm_provider.generate_response(prompt_context, target_model)

        # Step 7: Response Validation & Post-Processing
        validation_result = await self.validator.validate_response(raw_llm_response, prompt_context)

        # Step 8: Build Explainability Trace
        state_label = user_state_result.emotional_state.value if user_state_result.emotional_state else "INSUFFICIENT_SIGNALS"
        if state_label == "NEUTRAL":
            state_label = "INSUFFICIENT_SIGNALS"
        goal_status = goal_analysis_result.status.value if goal_analysis_result else "NONE"
        if goal_analysis_result and goal_analysis_result.status is None:
            goal_status = "NONE"
        if goal_analysis_result and goal_analysis_result.goal:
            goal_step = (
                f"Detected goal relationship '{goal_status}' on '{goal_analysis_result.goal}' "
                f"(confidence {goal_analysis_result.confidence})."
            )
        else:
            goal_step = "Detected goal relationship 'NONE' (no relevant goal)."
        reasoning_trace = ReasoningTrace(
            confidence_score=validation_result.personalization_score,
            supporting_memory_ids=[m.id for m in retrieved_context.relevant_memories],
            reasoning_steps=[
                f"Input Processing Layer converted {user_input.input_type.value} to structured context.",
                f"Retrieved {len(retrieved_context.relevant_memories)} semantic memories and timeline phase '{retrieved_context.life_phase}'.",
                f"Detected user intent '{intent_result.intent.value if intent_result.intent else 'UNKNOWN'}' (confidence {intent_result.confidence}).",
                f"Detected user interaction state '{state_label}' (confidence {user_state_result.confidence}).",
                goal_step,
                f"Constructed structured ChronosState (life phase '{chronos_state.context.life_phase if chronos_state.context else 'n/a'}', {len(chronos_state.context.relevant_memories) if chronos_state.context else 0} memories, {len(chronos_state.patterns)} patterns).",
                f"Orchestrated prompt with evolving identity (Interests: {', '.join(retrieved_context.identity_summary.get('interests', [])[:2])}).",
                f"Executed model-agnostic LLM provider '{llm_provider.provider_name()}'.",
                f"Validated response consistency (Corrections: {len(validation_result.corrections_made)}).",
            ],
            affected_time_range="Current interaction window",
            context_sources=[
                "Memory System",
                "Timeline Engine",
                "Identity Profile",
                "Pattern Detector",
                "Intent Detector",
                "User State Detector",
                "Goal Detector",
            ],
        )

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        response_id = f"resp_{uuid.uuid4().hex[:12]}"

        return EngineResponse(
            id=response_id,
            user_id=user_id,
            original_input=user_input,
            raw_llm_response=raw_llm_response,
            final_response=validation_result.validated_response,
            provider_name=llm_provider.provider_name(),
            model_name=target_model,
            prompt_context=prompt_context,
            reasoning_trace=reasoning_trace,
            validation_result=validation_result,
            chronos_state=chronos_state,
            processing_time_ms=elapsed_ms,
        )

    # Direct query methods for ChronOS UI Dashboard
    async def get_memories(self, user_id: str, limit: int = 100) -> List[MemoryItem]:
        return await self.storage.get_memories_by_user(user_id, limit=limit)

    async def get_timeline(self, user_id: str) -> List[TimelineEvent]:
        return await self.timeline_engine.get_timeline(user_id)

    async def get_identity(self, user_id: str) -> IdentityProfile:
        return await self.identity_model.get_or_create_profile(user_id)

    async def get_reflections(self, user_id: str, days_back: int = 30) -> List[ReflectionInsight]:
        return await self.reflection_engine.compare_past_and_present(user_id, days_back)

    async def get_patterns(self, user_id: str) -> List[PatternItem]:
        return await self.pattern_detector.analyze_patterns(user_id)

    async def seed_initial_state(self, user_id: str):
        """Seed rich initial historical memories for instant usability demonstration."""
        sample_memories = [
            ("I want to build OpenTime as a personal evolution engine that tracks beliefs, goals, and identity over time.", InputType.TEXT),
            ("Architecting the ChronOS Engine using modular Python, FastAPI, and Next.js.", InputType.TEXT),
            ("Voice recording detailing our focus shift: moving from generic dashboards to deep personal intelligence layer.", InputType.AUDIO),
            ("Video note: We must ensure model-agnostic LLM swapping works cleanly with OpenAI, Claude, and local Ollama models.", InputType.VIDEO),
        ]
        for text, inp_type in sample_memories:
            inp = await MediaProcessor.process_raw_input(user_id=user_id, content=text, input_type=inp_type.value)
            mem = await self.memory_system.add_interaction(inp)
            await self.timeline_engine.process_memory(user_id, mem)
            await self.identity_model.evolve_profile(user_id, mem)
        await self.reflection_engine.compare_past_and_present(user_id)
        await self.pattern_detector.analyze_patterns(user_id)
