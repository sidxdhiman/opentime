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
    BaseTemporalEventDetector,
    BaseTemporalStore,
    BaseTemporalThreadMatcher,
    BaseTemporalThreadLifecycleManager,
    BaseTemporalComparisonEngine,
    BasePastSelfQuestionPlanner,
    BasePastSelfConversationComposer,
    BaseTemporalRelevanceEngine,
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
from chronos_engine.storage.repository import InMemoryStorageAdapter, InMemoryTemporalStore
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
from chronos_engine.temporal.detector import TemporalEventDetector
from chronos_engine.temporal.comparison import TemporalComparisonEngine
from chronos_engine.temporal.lifecycle import TemporalThreadLifecycleManager
from chronos_engine.temporal.matcher import TemporalThreadMatcher
from chronos_engine.temporal.questions import PastSelfQuestionPlanner
from chronos_engine.temporal.relevance import TemporalRelevanceEngine
from chronos_engine.temporal.conversation import (
    PastSelfConversationComposer,
    render_past_self_section,
)
from chronos_engine.temporal.models import (
    PastSelfConversationMoment,
    PastSelfQuestionResult,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalLifecycleResult,
    TemporalRelevanceDecision,
    TemporalRelevanceResult,
    TemporalThreadMatchResult,
)


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
        temporal_event_detector: Optional[BaseTemporalEventDetector] = None,
        temporal_store: Optional[BaseTemporalStore] = None,
        temporal_thread_matcher: Optional[BaseTemporalThreadMatcher] = None,
        temporal_lifecycle: Optional[BaseTemporalThreadLifecycleManager] = None,
        temporal_comparison: Optional[BaseTemporalComparisonEngine] = None,
        past_self_question_planner: Optional[BasePastSelfQuestionPlanner] = None,
        temporal_relevance_engine: BaseTemporalRelevanceEngine | None = None,
        past_self_conversation_composer: BasePastSelfConversationComposer | None = None,
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
        self.temporal_event_detector = temporal_event_detector or TemporalEventDetector()
        self.temporal_store = temporal_store or InMemoryTemporalStore()
        self.temporal_thread_matcher = temporal_thread_matcher or TemporalThreadMatcher()
        # Phase 3D: the lifecycle manager owns thread creation, event
        # attachment, status transitions and persistence. It is the only
        # component that writes to the temporal store during processing.
        self.temporal_lifecycle = temporal_lifecycle or TemporalThreadLifecycleManager(
            self.temporal_store
        )
        # Phase 3E: the comparison engine is strictly read-only — it observes
        # the thread the lifecycle just touched and never mutates or persists
        # anything itself.
        self.temporal_comparison = temporal_comparison or TemporalComparisonEngine()
        # Phase 3F: the past-self question planner is strictly read-only pure
        # computation over the already-computed temporal evidence. It never
        # invokes AI, never persists and never schedules anything.
        self.past_self_question_planner = (
            past_self_question_planner or PastSelfQuestionPlanner()
        )
        # Phase 3G: the relevance & timing engine is strictly read-only pure
        # computation over already-computed evidence. It decides whether the
        # planned past-self question should surface now — it never mutates,
        # persists, schedules or renders anything.
        self.temporal_relevance_engine = (
            temporal_relevance_engine or TemporalRelevanceEngine()
        )
        # Phase 3H: the conversation composer is strictly read-only pure
        # computation over already-computed evidence. It turns a valid
        # SURFACE_NOW permission into deterministic user-facing content —
        # it never mutates, persists, schedules or invents anything.
        self.past_self_conversation_composer = (
            past_self_conversation_composer or PastSelfConversationComposer()
        )

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

        # Step 4d2: Temporal event detection. Deterministic and offline: it
        # classifies whether this input is a meaningful moment worth
        # remembering as a TemporalEvent, reusing intent / user-state / goal
        # evidence already computed above. Detection only — nothing is
        # persisted and no threads are created or searched.
        temporal_detection = await self.temporal_event_detector.detect_temporal_event(
            user_input,
            intent=intent_result,
            user_state=user_state_result,
            goal_analysis=goal_analysis_result,
            memory_id=memory_item.id,
        )

        # Step 4d3: Temporal thread matching (Phase 3C). Only runs when a
        # meaningful event was detected: compares it against the user's
        # existing live threads (bounded read from the temporal store) and
        # decides whether this moment belongs to an ongoing story.
        # Deterministic and conservative — a false connection is worse than
        # no connection. Matching only answers the question; linking and
        # persistence belong to Step 4d4.
        if temporal_detection.detected and temporal_detection.event is not None:
            candidate_threads = await self.temporal_store.get_candidate_threads(
                user_input.user_id
            )
            temporal_thread_match = await self.temporal_thread_matcher.match_threads(
                temporal_detection.event,
                candidate_threads,
                goal_analysis=goal_analysis_result,
                consistency_result=consistency_result,
            )
        else:
            temporal_thread_match = TemporalThreadMatchResult(
                attempted=False,
                matched=False,
                reason="No temporal event detected; thread matching skipped.",
            )

        # Step 4d4: Temporal lifecycle handling (Phase 3D). Deterministic
        # and offline: turns a confidently unmatched event into a new
        # persistent thread, attaches a confidently matched event to its
        # thread (with evidence-based status transitions), or — on ambiguity
        # or absence of an event — performs no mutation at all. The honest
        # result is carried additively in ChronosState.temporal_lifecycle.
        temporal_lifecycle_result: TemporalLifecycleResult = (
            await self.temporal_lifecycle.handle(
                user_id=user_input.user_id,
                detection=temporal_detection,
                match_result=temporal_thread_match,
                input_content=user_input.content,
                goal_analysis=goal_analysis_result,
                consistency_result=consistency_result,
            )
        )

        # Step 4d5: Past-vs-Present comparison (Phase 3E). Strictly
        # read-only: for the temporal thread this interaction touched (if
        # any), the newest persisted moment is compared against where the
        # story began. The comparison never mutates threads or events and
        # never persists anything; when no thread is available it says so
        # honestly.
        comparison_thread = None
        if temporal_lifecycle_result.thread_id:
            comparison_thread = await self.temporal_store.get_thread(
                temporal_lifecycle_result.thread_id, user_input.user_id
            )
        comparison_events: List[TemporalEvent] = []
        if comparison_thread is not None:
            comparison_events = await self.temporal_store.get_events_by_thread(
                comparison_thread.id, user_input.user_id
            )
        temporal_comparison_result: TemporalComparisonResult = (
            await self.temporal_comparison.compare(
                user_id=user_input.user_id,
                thread=comparison_thread,
                events=comparison_events,
                lifecycle_result=temporal_lifecycle_result,
                consistency_result=consistency_result,
                goal_analysis=goal_analysis_result,
            )
        )

        # Step 4d6: Past-self question planning (Phase 3F). Deterministic
        # and offline pure computation over the temporal evidence above:
        # decides whether a past-self interaction is appropriate, what kind,
        # what it should be about (grounded focus + canonical template) and
        # which stored evidence supports it. Read-only: no mutation, no
        # persistence, no scheduling; AI wording is deferred to a later
        # phase.
        past_self_question_result: PastSelfQuestionResult = (
            self.past_self_question_planner.plan(
                user_id=user_input.user_id,
                thread=comparison_thread,
                comparison=temporal_comparison_result,
                lifecycle_result=temporal_lifecycle_result,
                events=comparison_events,
            )
        )

        # Step 4d7: Temporal relevance & timing (Phase 3G). Deterministic
        # and offline pure computation over the evidence above: decides
        # whether the planned past-self question is relevant to this
        # conversation and appropriate to surface NOW — or should be
        # deferred ("not now") or skipped. Read-only: no mutation, no
        # persistence, no scheduling; DEFER is a decision label only.
        # Rendering the surfaced question belongs to a later phase.
        temporal_relevance_result: TemporalRelevanceResult = (
            self.temporal_relevance_engine.evaluate(
                user_id=user_input.user_id,
                user_input=user_input,
                past_self_question=past_self_question_result,
                thread=comparison_thread,
                events=comparison_events,
                thread_match=temporal_thread_match,
                lifecycle_result=temporal_lifecycle_result,
                comparison=temporal_comparison_result,
                intent=intent_result,
                user_state=user_state_result,
                goal_analysis=goal_analysis_result,
                consistency_result=consistency_result,
            )
        )

        # Step 4d8: Past-self conversation composition (Phase 3H).
        # Deterministic and offline pure computation over the evidence
        # above: turns a valid SURFACE_NOW permission into ONE subtle,
        # evidence-grounded user-facing moment (opening, grounded reminder,
        # optional bridge, question). Read-only: no mutation, no
        # persistence, no scheduling; hard-gated so Phase 3F/3G refusals
        # are echoed, never overridden.
        past_self_conversation: PastSelfConversationMoment = (
            self.past_self_conversation_composer.compose(
                user_id=user_input.user_id,
                past_self_question=past_self_question_result,
                relevance_result=temporal_relevance_result,
                thread=comparison_thread,
                comparison=temporal_comparison_result,
                lifecycle_result=temporal_lifecycle_result,
                events=comparison_events,
            )
        )

        # Step 4e: Build structured ChronOS state from the retrieved context.
        # The intent, user-state, goal, consistency detectors, the temporal
        # event detector, the temporal thread matcher, the temporal
        # lifecycle manager, the temporal comparison engine, the past-self
        # question planner, the relevance & timing engine and the
        # conversation composer populate their sections.
        chronos_state: ChronosState = await self.state_builder.build(
            user_input,
            retrieved_context,
            intent=intent_result,
            user_state=user_state_result,
            goal_analysis=goal_analysis_result,
            consistency_result=consistency_result,
            temporal_event_detection=temporal_detection,
            temporal_thread_match=temporal_thread_match,
            temporal_lifecycle=temporal_lifecycle_result,
            temporal_comparison=temporal_comparison_result,
            past_self_question=past_self_question_result,
            temporal_relevance=temporal_relevance_result,
            past_self_conversation=past_self_conversation,
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

        # Step 4i: Past-self conversation surfacing (Phase 3H). Additive and
        # deterministic: when (and only when) a valid moment was composed,
        # its section is appended AFTER the existing final answer on every
        # path (FAST deterministic, LIGHT/DEEP AI, AI failure fallback).
        # The underlying answer text is never rewritten; nothing is appended
        # when should_surface=False.
        if past_self_conversation.should_surface:
            final_response = "\n\n".join(
                [final_response, render_past_self_section(past_self_conversation)]
            )

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
        if temporal_detection.detected and temporal_detection.event is not None:
            temporal_step = (
                f"Temporal event detection -> {temporal_detection.event.temporal_type.value} "
                f"(confidence {temporal_detection.confidence})."
            )
        else:
            temporal_step = (
                "Temporal event detection -> NONE "
                f"({temporal_detection.reason or 'no significant temporal event'})."
            )
        if temporal_thread_match.matched and temporal_thread_match.thread_id:
            thread_step = (
                f"Temporal event matched existing thread "
                f"'{temporal_thread_match.thread_id}' "
                f"(confidence {temporal_thread_match.confidence})."
            )
        elif temporal_thread_match.ambiguous:
            thread_step = (
                "Multiple temporal threads similarly plausible; "
                "no reliable match chosen."
            )
        elif not temporal_thread_match.attempted:
            thread_step = "No temporal event detected; thread matching skipped."
        else:
            thread_step = "No sufficiently reliable temporal thread match found."

        # Phase 3D: honest lifecycle trace entry. Thread subjects are used
        # instead of internal ids so the trace stays human-readable.
        lifecycle_label = (
            temporal_lifecycle_result.thread_subject
            or temporal_lifecycle_result.thread_id
            or "thread"
        )
        if not temporal_lifecycle_result.attempted:
            lifecycle_step = "No temporal event detected; lifecycle handling skipped."
        elif temporal_lifecycle_result.ambiguous:
            lifecycle_step = (
                "Temporal thread relationship was ambiguous; no thread was modified."
            )
        elif temporal_lifecycle_result.created and temporal_lifecycle_result.persisted:
            lifecycle_step = (
                f"Created new temporal thread '{lifecycle_label}' from detected "
                f"{temporal_detection.event.temporal_type.value} event."
                if temporal_detection.event is not None
                and temporal_detection.event.temporal_type is not None
                else f"Created new temporal thread '{lifecycle_label}'."
            )
        elif temporal_lifecycle_result.updated:
            if temporal_lifecycle_result.transitioned:
                lifecycle_step = (
                    f"Attached temporal event to existing thread '{lifecycle_label}'; "
                    f"status {temporal_lifecycle_result.previous_status.value} -> "
                    f"{temporal_lifecycle_result.current_status.value}."
                )
            else:
                status_value = (
                    temporal_lifecycle_result.current_status.value
                    if temporal_lifecycle_result.current_status is not None
                    else "UNCHANGED"
                )
                lifecycle_step = (
                    f"Attached temporal event to existing thread '{lifecycle_label}'; "
                    f"status remains {status_value}."
                )
        else:
            lifecycle_step = (
                f"Temporal lifecycle performed no mutation "
                f"({temporal_lifecycle_result.reason or 'no action required'})."
            )

        # Phase 3E: honest comparison trace entry.
        if not temporal_comparison_result.attempted:
            comparison_step = (
                "Temporal comparison skipped: no temporal thread available."
            )
        else:
            comparison_step = (
                f"Temporal comparison -> {temporal_comparison_result.relation.value} "
                f"(confidence {temporal_comparison_result.confidence})."
            )

        # Phase 3F: honest past-self question trace entry.
        if not past_self_question_result.attempted:
            question_step = (
                "Past-self question skipped: no temporal thread available."
            )
        elif not past_self_question_result.should_ask:
            question_step = f"Past-self question skipped: {past_self_question_result.reason}"
        else:
            question_step = (
                f"Past-self question planned -> "
                f"{past_self_question_result.question_type.value} "
                f"(confidence {past_self_question_result.confidence})."
            )

        # Phase 3G: honest relevance & timing trace entry.
        if not temporal_relevance_result.attempted:
            relevance_step = (
                "Past-self relevance skipped: no valid past-self question."
            )
        elif (
            temporal_relevance_result.decision is TemporalRelevanceDecision.SURFACE_NOW
        ):
            relevance_step = (
                f"Past-self relevance -> SURFACE_NOW "
                f"(relevance {temporal_relevance_result.relevance_score}, "
                f"timing {temporal_relevance_result.timing_score}, "
                f"confidence {temporal_relevance_result.confidence})."
            )
        elif temporal_relevance_result.decision is TemporalRelevanceDecision.DEFER:
            relevance_step = (
                f"Past-self relevance -> DEFER "
                f"({temporal_relevance_result.reason})"
            )
        else:
            relevance_step = f"Past-self relevance -> SKIP ({temporal_relevance_result.reason})"

        # Phase 3H: honest conversation-composition trace entry.
        if past_self_conversation.should_surface:
            conversation_step = (
                f"Past-self conversation -> surfaced: "
                f"{past_self_conversation.question_type.value} "
                f"(confidence {past_self_conversation.confidence})."
            )
        else:
            conversation_step = (
                "Past-self conversation skipped: "
                f"{past_self_conversation.reason}"
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
                temporal_step,
                thread_step,
                lifecycle_step,
                comparison_step,
                question_step,
                relevance_step,
                conversation_step,
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
                "Temporal Event Detector",
                "Temporal Lifecycle Manager",
                "Temporal Comparison Engine",
                "Past-Self Question Planner",
                "Past-Self Relevance Engine",
                "Past-Self Conversation Composer",
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
