"""
ChronosInitializationService

Processes all onboarding responses and bootstraps the full Chronos state
for a newly-onboarded user.

Pipeline:
  RAW ONBOARDING RESPONSES
    ↓ Validation / ownership
    ↓ Memory Extraction   (one Memory per meaningful response)
    ↓ Genesis Memory      (Step 6 first-memory becomes the genesis)
    ↓ Identity Extraction (LLM extracts traits/interests from Step 1,2,5)
    ↓ Goal Extraction     (Step 4 structured goals → Goal entities)
    ↓ Timeline Creation   (Step 5 changes → TimelineEvents)
    ↓ Analysis Preferences (Step 7)
    ↓ Pattern Baseline    (low-confidence from Step 2,3)
    ↓ Chronos State       (master snapshot)
    ↓ MongoDB

Idempotency:
  - If a ChronosState already exists for the user, the function is a no-op.
  - Genesis memory creation is guarded by exists_genesis().
"""

from __future__ import annotations

import structlog
from datetime import datetime, timezone

from opentime.domain.chronos.entities import (
    AnalysisPreferenceRecord,
    ChronosState,
    ClaimType,
    CurrentLifeState,
    Goal,
    GoalStatus,
    IdentityState,
    IdentityTrait,
    Memory,
    Pattern,
    PatternType,
    PersonalChange,
    TimelineEvent,
    TypedClaim,
    ContentType,
)
from opentime.domain.chronos.repositories import (
    AnalysisPreferenceRepository,
    ChronosStateRepository,
    GoalRepository,
    IdentityStateRepository,
    MemoryRepository,
    PatternRepository,
    TimelineRepository,
)
from opentime.domain.onboarding.entities import (
    AnalysisPreference,
    OnboardingResponse,
    OnboardingStep,
)
from opentime.infrastructure.services.embedding_service import EmbeddingService
from opentime.infrastructure.services.llm_service import LLMService

logger = structlog.get_logger()


class ChronosAlreadyInitialized(Exception):
    pass


class ChronosInitializationService:
    def __init__(
        self,
        memory_repo: MemoryRepository,
        identity_repo: IdentityStateRepository,
        goal_repo: GoalRepository,
        timeline_repo: TimelineRepository,
        pattern_repo: PatternRepository,
        pref_repo: AnalysisPreferenceRepository,
        chronos_repo: ChronosStateRepository,
        llm: LLMService,
        embedding: EmbeddingService,
    ) -> None:
        self._memories = memory_repo
        self._identity = identity_repo
        self._goals = goal_repo
        self._timeline = timeline_repo
        self._patterns = pattern_repo
        self._prefs = pref_repo
        self._chronos = chronos_repo
        self._llm = llm
        self._embedding = embedding

    async def initialize(
        self,
        user_id: str,
        responses: list[OnboardingResponse],
    ) -> ChronosState:
        """
        Main entry point.  Idempotent – safe to call twice.
        Returns the ChronosState (existing or newly created).
        """
        existing = await self._chronos.get_for_user(user_id)
        if existing and existing.is_initialised:
            logger.info("chronos_already_initialised", user_id=user_id)
            raise ChronosAlreadyInitialized(
                f"Chronos already initialized for user {user_id}."
            )

        log = logger.bind(user_id=user_id)
        log.info("chronos_init_start", response_count=len(responses))

        resp_by_step: dict[OnboardingStep, OnboardingResponse] = {}
        for r in responses:
            # Keep latest per step
            if r.step not in resp_by_step or r.created_at > resp_by_step[r.step].created_at:
                resp_by_step[r.step] = r

        # ---- 1. Extract memories from every response ----
        memory_map: dict[str, Memory] = {}  # step → memory_id
        for step, resp in resp_by_step.items():
            if step == OnboardingStep.FIRST_MEMORY:
                continue  # handled separately as genesis
            memory = await self._create_memory_from_response(user_id, resp)
            memory_map[step] = memory
            log.info("memory_created", step=step, memory_id=memory.id)

        # ---- 2. Genesis memory (Step 6) ----
        genesis_memory: Memory | None = None
        if OnboardingStep.FIRST_MEMORY in resp_by_step:
            genesis_exists = await self._memories.exists_genesis(user_id)
            if not genesis_exists:
                genesis_memory = await self._create_genesis_memory(
                    user_id, resp_by_step[OnboardingStep.FIRST_MEMORY]
                )
                log.info("genesis_memory_created", memory_id=genesis_memory.id)
            else:
                genesis_memory = await self._memories.get_genesis(user_id)
                log.info("genesis_memory_exists", memory_id=genesis_memory.id if genesis_memory else None)

        # ---- 3. Identity extraction (Steps 1 + 2 + 5) ----
        identity_source_texts: list[str] = []
        for step in [
            OnboardingStep.ABOUT_YOU,
            OnboardingStep.LIFE_RIGHT_NOW,
            OnboardingStep.HOW_CHANGED,
        ]:
            if step in resp_by_step:
                raw = resp_by_step[step].response
                if isinstance(raw, str):
                    identity_source_texts.append(raw)
                elif isinstance(raw, dict):
                    identity_source_texts.append(str(raw))

        identity_state = await self._extract_identity(
            user_id, identity_source_texts, memory_map
        )
        log.info("identity_state_created", version=identity_state.version)

        # ---- 4. Goal extraction (Step 4) ----
        goals: list[Goal] = []
        if OnboardingStep.WHERE_GOING in resp_by_step:
            goals = await self._extract_goals(
                user_id,
                resp_by_step[OnboardingStep.WHERE_GOING],
                memory_map.get(OnboardingStep.WHERE_GOING),
            )
            log.info("goals_created", count=len(goals))

        # ---- 5. Timeline events (Step 5 – changes) ----
        timeline_events: list[TimelineEvent] = []
        if OnboardingStep.HOW_CHANGED in resp_by_step:
            timeline_events = await self._extract_timeline(
                user_id,
                resp_by_step[OnboardingStep.HOW_CHANGED],
                memory_map.get(OnboardingStep.HOW_CHANGED),
            )
            log.info("timeline_events_created", count=len(timeline_events))

        # Always add a "Joined OpenTime" genesis timeline event
        genesis_event = TimelineEvent(
            user_id=user_id,
            event_time=datetime.now(timezone.utc),
            title="Joined OpenTime",
            description="User completed onboarding and established their Chronos baseline.",
            category="milestone",
            source_memory_id=genesis_memory.id if genesis_memory else None,
            confidence=1.0,
        )
        await self._timeline.create(genesis_event)
        timeline_events.append(genesis_event)

        # ---- 6. Analysis preferences (Step 7) ----
        pref_records: list[AnalysisPreferenceRecord] = []
        if OnboardingStep.ANALYSIS_PREFS in resp_by_step:
            pref_records = await self._extract_prefs(
                user_id, resp_by_step[OnboardingStep.ANALYSIS_PREFS]
            )
            log.info("pref_records_created", count=len(pref_records))

        # ---- 7. Pattern baseline (Steps 2 + 3) ----
        patterns: list[Pattern] = []
        for step in [OnboardingStep.LIFE_RIGHT_NOW, OnboardingStep.WHATS_ON_MIND]:
            if step in resp_by_step:
                raw = resp_by_step[step].response
                if isinstance(raw, str) and len(raw) > 30:
                    p = await self._create_baseline_pattern(
                        user_id, step, raw,
                        memory_map.get(step)
                    )
                    if p:
                        patterns.append(p)

        # ---- 8. Current life state (Step 2) ----
        current_life_state = await self._extract_current_life_state(
            user_id,
            resp_by_step.get(OnboardingStep.LIFE_RIGHT_NOW),
            resp_by_step.get(OnboardingStep.WHATS_ON_MIND),
            memory_map,
        )

        # ---- 9. Personal changes (Step 5) ----
        personal_changes: list[PersonalChange] = []
        if OnboardingStep.HOW_CHANGED in resp_by_step:
            personal_changes = await self._extract_changes(
                user_id,
                resp_by_step[OnboardingStep.HOW_CHANGED],
                memory_map.get(OnboardingStep.HOW_CHANGED),
            )

        # ---- 10. Assemble ChronosState ----
        chronos_state = ChronosState(
            user_id=user_id,
            version=1,
            identity_state_id=identity_state.id,
            current_life_state=current_life_state,
            goal_ids=[g.id for g in goals],
            concerns=current_life_state.concerns,
            changes=personal_changes,
            analysis_preference_ids=[p.id for p in pref_records],
            genesis_memory_id=genesis_memory.id if genesis_memory else None,
            is_initialised=True,
        )

        if existing:
            chronos_state.id = existing.id
            chronos_state.version = existing.version + 1
            await self._chronos.update(chronos_state)
        else:
            await self._chronos.create(chronos_state)

        log.info("chronos_state_created", chronos_id=chronos_state.id)
        return chronos_state

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _create_memory_from_response(
        self, user_id: str, response: OnboardingResponse
    ) -> Memory:
        text = (
            response.response if isinstance(response.response, str)
            else str(response.response)
        )
        summary = await self._llm.summarise(text, max_words=60)
        topics = await self._llm.extract_topics(text)
        embedding = await self._embedding.generate_embedding(text)

        memory = Memory(
            user_id=user_id,
            content=text,
            content_type=ContentType.TEXT,
            source="onboarding",
            source_reference=response.id,
            summary=summary,
            topics=topics,
            embedding=embedding,
            importance=0.7,
            confidence=1.0,
        )
        return await self._memories.create(memory)

    async def _create_genesis_memory(
        self, user_id: str, response: OnboardingResponse
    ) -> Memory:
        text = (
            response.response if isinstance(response.response, str)
            else str(response.response)
        )
        summary = await self._llm.summarise(text, max_words=80)
        topics = await self._llm.extract_topics(text)
        emotions = await self._llm.extract_emotions(text)
        embedding = await self._embedding.generate_embedding(text)

        emotion_claims: list[TypedClaim] = [
            TypedClaim(
                value=e.get("emotion"),
                claim_type=ClaimType.INFERENCE,
                confidence=float(e.get("confidence", 0.5)),
            )
            for e in emotions
            if e.get("emotion")
        ]

        memory = Memory(
            user_id=user_id,
            content=text,
            content_type=ContentType.TEXT,
            source="genesis",
            source_reference=response.id,
            summary=summary,
            topics=topics,
            emotions=emotion_claims,
            embedding=embedding,
            importance=1.0,
            confidence=1.0,
            is_genesis=True,
            media_url=response.media_url,
        )
        return await self._memories.create(memory)

    async def _extract_identity(
        self,
        user_id: str,
        texts: list[str],
        memory_map: dict,
    ) -> IdentityState:
        combined = "\n\n".join(texts)
        extraction_prompt = (
            "Extract identity information from the following onboarding text.\n"
            "Return a JSON object with keys: traits (list of strings), "
            "interests (list of strings), values (list of strings), "
            "self_perception (list of strings), current_phase (string or null).\n"
            "Be conservative – only include things the user explicitly stated or "
            "strongly implied. Mark everything as user_statement."
        )
        extracted = await self._llm.extract_structured(combined, extraction_prompt)

        def to_claims(items: list, mem_id: str | None = None) -> list[TypedClaim]:
            return [
                TypedClaim(
                    value=item,
                    claim_type=ClaimType.USER_STATEMENT,
                    confidence=0.85,
                    source_memory_id=mem_id,
                )
                for item in items
                if isinstance(item, str) and item.strip()
            ]

        source_mem_id = (
            memory_map.get(OnboardingStep.LIFE_RIGHT_NOW, None)
        )
        source_mem_id = source_mem_id.id if source_mem_id else None

        traits = [
            IdentityTrait(
                trait=t,
                claim_type=ClaimType.USER_STATEMENT,
                confidence=0.8,
                source_memory_id=source_mem_id,
            )
            for t in extracted.get("traits", [])
            if isinstance(t, str) and t.strip()
        ]

        phase_raw = extracted.get("current_phase")
        phase_claim = (
            TypedClaim(
                value=phase_raw,
                claim_type=ClaimType.INFERENCE,
                confidence=0.75,
                source_memory_id=source_mem_id,
            )
            if phase_raw
            else None
        )

        state = IdentityState(
            user_id=user_id,
            version=1,
            traits=traits,
            interests=to_claims(extracted.get("interests", []), source_mem_id),
            values=to_claims(extracted.get("values", []), source_mem_id),
            self_perception=to_claims(extracted.get("self_perception", []), source_mem_id),
            current_phase=phase_claim,
        )
        return await self._identity.create(state)

    async def _extract_goals(
        self,
        user_id: str,
        response: OnboardingResponse,
        memory: Memory | None,
    ) -> list[Goal]:
        raw = response.response

        goal_inputs: list[dict] = []
        if isinstance(raw, list):
            goal_inputs = raw
        elif isinstance(raw, dict):
            goal_inputs = raw.get("goals", [raw])
        elif isinstance(raw, str):
            # Ask LLM to parse free-form text into goals
            extraction_prompt = (
                "Parse the following text into a list of personal goals.\n"
                "Return a JSON array with objects: "
                "{title, description, category, importance (0-1)}.\n"
                "category must be one of: career, education, health, relationships, "
                "finance, creativity, personal_growth, lifestyle, other."
            )
            result = await self._llm.extract_structured(raw, extraction_prompt)
            goal_inputs = result if isinstance(result, list) else result.get("goals", [])

        goals: list[Goal] = []
        for gi in goal_inputs:
            if not isinstance(gi, dict):
                continue
            title = gi.get("title", "").strip()
            if not title:
                continue
            goal = Goal(
                user_id=user_id,
                title=title,
                description=gi.get("description"),
                category=gi.get("category", "other"),
                importance=float(gi.get("importance", 0.7)),
                status=GoalStatus.ACTIVE,
                source="onboarding",
                confidence=1.0,
                source_memory_id=memory.id if memory else None,
            )
            goal = await self._goals.create(goal)
            goals.append(goal)

        return goals

    async def _extract_timeline(
        self,
        user_id: str,
        response: OnboardingResponse,
        memory: Memory | None,
    ) -> list[TimelineEvent]:
        text = (
            response.response if isinstance(response.response, str)
            else str(response.response)
        )
        extraction_prompt = (
            "Extract personal changes or life events from the following text.\n"
            "Return a JSON array with objects: "
            "{title, description, category (career/education/health/"
            "relationships/personal_growth/other), approximate_period (year or period)}.\n"
            "Only include changes the user explicitly mentioned."
        )
        result = await self._llm.extract_structured(text, extraction_prompt)
        events_raw = result if isinstance(result, list) else result.get("events", [])

        events: list[TimelineEvent] = []
        now = datetime.now(timezone.utc)
        for ev in events_raw:
            if not isinstance(ev, dict):
                continue
            title = ev.get("title", "").strip()
            if not title:
                continue
            event = TimelineEvent(
                user_id=user_id,
                event_time=now,  # approximate; LLM parsing could refine
                title=title,
                description=ev.get("description", ""),
                category=ev.get("category", "other"),
                source_memory_id=memory.id if memory else None,
                confidence=0.8,
            )
            event = await self._timeline.create(event)
            events.append(event)

        return events

    async def _extract_prefs(
        self, user_id: str, response: OnboardingResponse
    ) -> list[AnalysisPreferenceRecord]:
        raw = response.response
        prefs: list[str] = []
        if isinstance(raw, list):
            prefs = [str(p) for p in raw]
        elif isinstance(raw, dict):
            prefs = raw.get("preferences", [])
        elif isinstance(raw, str):
            prefs = [p.strip() for p in raw.split(",") if p.strip()]

        records = [
            AnalysisPreferenceRecord(
                user_id=user_id,
                preference=p,
            )
            for p in prefs
        ]
        return await self._prefs.create_many(records)

    async def _create_baseline_pattern(
        self,
        user_id: str,
        step: OnboardingStep,
        text: str,
        memory: Memory | None,
    ) -> Pattern | None:
        topics = await self._llm.extract_topics(text)
        if not topics:
            return None

        pattern_text = f"User is currently focused on: {', '.join(topics[:3])}"
        p = Pattern(
            user_id=user_id,
            type=PatternType.BASELINE,
            pattern=pattern_text,
            confidence=0.35,  # low initial confidence – single evidence point
            evidence_count=1,
            source_memory_ids=[memory.id] if memory else [],
        )
        return await self._patterns.create(p)

    async def _extract_current_life_state(
        self,
        user_id: str,
        life_response: OnboardingResponse | None,
        mind_response: OnboardingResponse | None,
        memory_map: dict,
    ) -> CurrentLifeState:
        texts: list[str] = []
        for resp in [life_response, mind_response]:
            if resp:
                raw = resp.response
                texts.append(raw if isinstance(raw, str) else str(raw))

        if not texts:
            return CurrentLifeState()

        combined = "\n\n".join(texts)
        extraction_prompt = (
            "Extract the user's current life context from this text.\n"
            "Return a JSON object with keys: phase (string or null), "
            "priorities (list[str]), interests (list[str]), "
            "concerns (list[str]), responsibilities (list[str]), projects (list[str]).\n"
            "Only include what is explicitly stated."
        )
        extracted = await self._llm.extract_structured(combined, extraction_prompt)

        def claims(items: list) -> list[TypedClaim]:
            return [
                TypedClaim(
                    value=item,
                    claim_type=ClaimType.USER_STATEMENT,
                    confidence=0.85,
                )
                for item in items
                if isinstance(item, str) and item.strip()
            ]

        phase_raw = extracted.get("phase")
        return CurrentLifeState(
            phase=TypedClaim(
                value=phase_raw,
                claim_type=ClaimType.INFERENCE,
                confidence=0.7,
            ) if phase_raw else None,
            priorities=claims(extracted.get("priorities", [])),
            interests=claims(extracted.get("interests", [])),
            concerns=claims(extracted.get("concerns", [])),
            responsibilities=claims(extracted.get("responsibilities", [])),
            projects=claims(extracted.get("projects", [])),
        )

    async def _extract_changes(
        self,
        user_id: str,
        response: OnboardingResponse,
        memory: Memory | None,
    ) -> list[PersonalChange]:
        text = (
            response.response if isinstance(response.response, str)
            else str(response.response)
        )
        extraction_prompt = (
            "Extract personal changes from the following text.\n"
            "Return a JSON array with objects: "
            "{change_type (career/education/health/relationships/interests/"
            "personality/habits/other), previous_state (string), "
            "current_state (string), approximate_period (string or null), "
            "confidence (0-1)}.\n"
            "Be conservative – only include changes the user explicitly mentioned."
        )
        result = await self._llm.extract_structured(text, extraction_prompt)
        changes_raw = result if isinstance(result, list) else result.get("changes", [])

        changes: list[PersonalChange] = []
        for c in changes_raw:
            if not isinstance(c, dict):
                continue
            prev = c.get("previous_state", "")
            curr = c.get("current_state", "")
            if not prev or not curr:
                continue
            change = PersonalChange(
                change_type=c.get("change_type", "other"),
                previous_state=TypedClaim(
                    value=prev,
                    claim_type=ClaimType.USER_STATEMENT,
                    confidence=float(c.get("confidence", 0.8)),
                    source_memory_id=memory.id if memory else None,
                ),
                current_state=TypedClaim(
                    value=curr,
                    claim_type=ClaimType.USER_STATEMENT,
                    confidence=float(c.get("confidence", 0.8)),
                    source_memory_id=memory.id if memory else None,
                ),
                approximate_period=c.get("approximate_period"),
                confidence=float(c.get("confidence", 0.8)),
                source_memory_id=memory.id if memory else None,
            )
            changes.append(change)

        return changes
