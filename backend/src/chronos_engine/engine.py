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
    BaseConsistencyEngine,
    BaseResponseGenerator,
    BaseAIRouter,
    BaseAIExecutor,
)
from chronos_engine.core.models import (
    EngineResponse,
    IdentityProfile,
    InputType,
    MemoryItem,
    PatternItem,
    PromptContext,
    ReasoningTrace,
    ReflectionInsight,
    TimelineEvent,
    UserInput,
    ValidationResult,
)
from chronos_engine.embeddings.provider import DefaultEmbeddingProvider
from chronos_engine.config import OllamaConfig
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
from chronos_engine.state.models import (
    ChronosState,
    ConsistencyResult,
    GoalAnalysisResult,
    UserStateResult,
)
from chronos_engine.user_state.service import UserStateDetector
from chronos_engine.goals.service import GoalDetector
from chronos_engine.consistency.service import ConsistencyEngine
from chronos_engine.response.service import ResponseGenerator
from chronos_engine.routing.service import AIRouter
from chronos_engine.ai.service import AIExecutor
from chronos_engine.ai.models import AIExecutionResult
from chronos_engine.ai.policy import InferencePolicy, capabilities_from_config
from chronos_engine.ai.reasoning.planner import ReasoningPlanner


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
        consistency_engine: Optional[BaseConsistencyEngine] = None,
        response_generator: Optional[BaseResponseGenerator] = None,
        ai_router: Optional[BaseAIRouter] = None,
        ai_executor: Optional[BaseAIExecutor] = None,
        inference_policy: Optional[InferencePolicy] = None,
        reasoning_planner: Optional[ReasoningPlanner] = None,
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
        self.consistency_engine = consistency_engine or ConsistencyEngine()
        self.response_generator = response_generator or ResponseGenerator()
        self.ai_router = ai_router or AIRouter()
        self.ai_executor = ai_executor or AIExecutor()
        # The default inference policy reads the SAME configuration the
        # executor executes with, so the recorded decision and the executed
        # tier/model always agree. The catalog is built from the configured
        # DEEP + LIGHT models with honest (unknown) metadata.
        executor_config = getattr(self.ai_executor, "config", None) or OllamaConfig()
        self.inference_policy = inference_policy or InferencePolicy(
            config=executor_config,
            available_models=capabilities_from_config(executor_config),
        )
        self.reasoning_planner = reasoning_planner or ReasoningPlanner()

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

        # Step 4d: Check the input against stored user context. This is the
        # continuity layer: it flags goal changes / conflicts and statement
        # contradictions from already-retrieved context — no full-database scan.
        identity = await self.identity_model.get_or_create_profile(user_id)
        consistency_result: ConsistencyResult = await self.consistency_engine.check_consistency(
            user_input,
            retrieved_context,
            goal_analysis=goal_analysis_result,
            identity=identity,
            current_memory_id=memory_item.id,
        )

        # Step 4e: Build structured ChronOS state from the retrieved context.
        # The intent, user-state, goal and consistency detectors populate their
        # sections.
        chronos_state: ChronosState = await self.state_builder.build(
            user_input,
            retrieved_context,
            intent=intent_result,
            user_state=user_state_result,
            goal_analysis=goal_analysis_result,
            consistency_result=consistency_result,
        )

        # Step 4f: Deterministic response generation. Pure template/rule logic
        # over the structured ChronosState — no LLM, no network. This is the
        # AI-free interpretation that accompanies the LLM response.
        deterministic_response = self.response_generator.generate(chronos_state)

        # Step 4g: AI routing. Decides whether the deterministic state is
        # sufficient (FAST) or whether an AI model would materially help
        # (DEEP). The routing decision is now operational: FAST returns the
        # deterministic response; DEEP invokes the AI executor (Ollama) with a
        # graceful deterministic fallback if AI is disabled or unavailable.
        ai_routing = self.ai_router.route(chronos_state)

        # Step 4g2: Inference policy. Decides which tier/model the AI executor
        # must use for this interaction: NONE (no model), LIGHT (the
        # configured light model) or DEEP (the configured capable model). The
        # decision is passed to the executor, which executes exactly that
        # model — never another one.
        policy_plan = self.reasoning_planner.plan(chronos_state, ai_routing)
        inference_policy_decision = self.inference_policy.decide(
            routing_result=ai_routing,
            plan=policy_plan,
            chronos_state=chronos_state,
        )

        # Step 4h: AI execution. The AI executor is ONLY invoked on the DEEP
        # path — a FAST routing must never touch Ollama. The executor never
        # mutates ChronosState and never writes memory. The model it calls is
        # dictated by the inference-policy decision (LIGHT vs DEEP); a LIGHT
        # failure falls back deterministically instead of escalating to DEEP.
        if ai_routing.use_ai:
            ai_execution: AIExecutionResult = await self.ai_executor.execute(
                ai_routing,
                chronos_state,
                deterministic_response,
                inference_policy_decision=inference_policy_decision,
            )
            if ai_execution.used:
                final_response = ai_execution.response
            else:
                final_response = deterministic_response.rendered
            prompt_context = ai_execution.prompt_context or PromptContext(
                current_input=user_input,
                retrieved_context=retrieved_context,
                system_prompt="",
                user_prompt="",
            )
            validation_result = ai_execution.validation_result or ValidationResult(
                is_valid=True, validated_response=final_response
            )
            raw_llm_response = ai_execution.response or final_response
            provider_name = self.llm_registry.get_provider("ollama").provider_name()
            target_model = ai_execution.model
            plan = ai_execution.reasoning_plan
            plan_step = None
            plan_entry = None
            if plan is not None:
                plan_step = (
                    f"Reasoning plan -> {', '.join(m.value for m in plan.modes)} "
                    f"(primary: {plan.primary_mode.value})."
                )
                plan_entry = {
                    "step": "REASONING_PLAN",
                    "modes": [m.value for m in plan.modes],
                    "primary_mode": plan.primary_mode.value,
                    "confidence": plan.confidence,
                }
            latency_entry: dict = {
                "step": "AI_LATENCY",
                **ai_execution.latency_report(),
            }
        else:
            # FAST path: the deterministic response IS the final output. The
            # legacy prompt/LLM pipeline still runs to provide the response
            # metadata fields, but no Ollama interaction happens here.
            ai_execution = AIExecutionResult(
                attempted=False, used=False, success=False, fallback_used=False,
                tier=inference_policy_decision.tier.value,
            )
            final_response = deterministic_response.rendered
            prompt_context = await self.orchestrator.orchestrate_prompt(
                user_input, retrieved_context
            )
            llm_provider = self.llm_registry.get_provider(provider_key)
            target_model = model_name or (
                "chronos-v1-core" if provider_key == "chronos" or not provider_key else "gpt-4o"
            )
            raw_llm_response = await llm_provider.generate_response(
                prompt_context, target_model
            )
            validation_result = await self.validator.validate_response(
                raw_llm_response, prompt_context
            )
            provider_name = llm_provider.provider_name()
            plan_step = None
            plan_entry = None

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

        all_events = list(consistency_result.contradictions) + list(consistency_result.changes)
        if all_events:
            top_event = max(all_events, key=lambda e: e.confidence)
            consistency_step = (
                f"Consistency check -> {top_event.type} "
                f"(confidence {top_event.confidence})."
            )
        else:
            consistency_step = (
                f"Consistency check -> CONSISTENT "
                f"(confidence {consistency_result.confidence})."
            )
        if ai_routing.use_ai:
            latency_text = (
                f"{ai_execution.latency_ms}ms"
                if ai_execution.latency_ms is not None
                else "n/a"
            )
            prompt_step = "Assembled AI prompt from structured ChronOS state."
            execution_step = (
                f"Executed AI provider '{provider_name}' (tier: {ai_execution.tier or 'n/a'}, "
                f"model: {target_model or 'n/a'}, "
                f"latency: {latency_text})."
            )
            if ai_execution.used:
                validation_step = (
                    "Validated AI response consistency "
                    f"(Corrections: {len(validation_result.corrections_made)})."
                )
                ai_execution_step = (
                    "AI execution -> OLLAMA_SUCCESS (ai_used: true, provider: ollama)."
                )
                ai_execution_steps = [
                    {
                        "step": "AI_EXECUTION",
                        "result": "OLLAMA_SUCCESS",
                        "ai_used": True,
                        "provider": "ollama",
                        "tier": ai_execution.tier,
                        "model": ai_execution.model,
                    }
                ]
                if plan_entry is not None:
                    ai_execution_steps.append(plan_entry)
                ai_execution_steps.append(latency_entry)
            else:
                error_type = ai_execution.error_type or "unknown"
                validation_step = (
                    f"AI execution failed ({error_type}); "
                    "deterministic response used (fallback)."
                )
                ai_execution_step = (
                    "AI execution -> OLLAMA_FAILED_DETERMINISTIC_FALLBACK "
                    "(ai_used: false, fallback_used: true)."
                )
                fallback_step: dict = {
                    "step": "AI_EXECUTION",
                    "result": "OLLAMA_FAILED_DETERMINISTIC_FALLBACK",
                    "ai_used": False,
                    "fallback_used": True,
                    "tier": ai_execution.tier,
                    "model": ai_execution.model,
                }
                if ai_execution.error_type:
                    fallback_step["error_type"] = ai_execution.error_type
                ai_execution_steps = [fallback_step]
                if plan_entry is not None:
                    ai_execution_steps.append(plan_entry)
                ai_execution_steps.append(latency_entry)
        else:
            prompt_step = (
                "Orchestrated prompt with evolving identity "
                f"(Interests: {', '.join(retrieved_context.identity_summary.get('interests', [])[:2])})."
            )
            execution_step = (
                f"Executed model-agnostic LLM provider '{provider_name}'."
            )
            validation_step = (
                "Validated response consistency "
                f"(Corrections: {len(validation_result.corrections_made)})."
            )
            ai_execution_step = (
                "AI execution -> SKIPPED_FAST_PATH (ai_used: false)."
            )
            ai_execution_steps = [
                {
                    "step": "AI_EXECUTION",
                    "result": "SKIPPED_FAST_PATH",
                    "ai_used": False,
                }
            ]

        reasoning_trace = ReasoningTrace(
            confidence_score=validation_result.personalization_score,
            supporting_memory_ids=[m.id for m in retrieved_context.relevant_memories],
            reasoning_steps=[
                f"Input Processing Layer converted {user_input.input_type.value} to structured context.",
                f"Retrieved {len(retrieved_context.relevant_memories)} semantic memories and timeline phase '{retrieved_context.life_phase}'.",
                f"Detected user intent '{intent_result.intent.value if intent_result.intent else 'UNKNOWN'}' (confidence {intent_result.confidence}).",
                f"Detected user interaction state '{state_label}' (confidence {user_state_result.confidence}).",
                goal_step,
                consistency_step,
                f"Constructed structured ChronosState (life phase '{chronos_state.context.life_phase if chronos_state.context else 'n/a'}', {len(chronos_state.context.relevant_memories) if chronos_state.context else 0} memories, {len(chronos_state.patterns)} patterns).",
                prompt_step,
                execution_step,
                validation_step,
                "Deterministic response generation -> generated (ai_used: False).",
                f"AI routing -> {ai_routing.path.value} (use_ai: {str(ai_routing.use_ai).lower()}, confidence {ai_routing.confidence}).",
                *([plan_step] if plan_step else []),
                ai_execution_step,
            ],
            ai_execution_steps=ai_execution_steps,
            affected_time_range="Current interaction window",
            context_sources=[
                "Memory System",
                "Timeline Engine",
                "Identity Profile",
                "Pattern Detector",
                "Intent Detector",
                "User State Detector",
                "Goal Detector",
                "Consistency Engine",
                "Response Generator",
                "AI Router",
                "AI Executor",
            ],
        )

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        response_id = f"resp_{uuid.uuid4().hex[:12]}"

        return EngineResponse(
            id=response_id,
            user_id=user_id,
            original_input=user_input,
            raw_llm_response=raw_llm_response,
            final_response=final_response,
            provider_name=provider_name,
            model_name=target_model,
            prompt_context=prompt_context,
            reasoning_trace=reasoning_trace,
            validation_result=validation_result,
            chronos_state=chronos_state,
            deterministic_response=deterministic_response,
            ai_routing=ai_routing,
            ai_execution=ai_execution,
            inference_policy=inference_policy_decision,
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
