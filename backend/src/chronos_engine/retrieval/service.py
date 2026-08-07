from chronos_engine.core.interfaces import (
    BaseIdentityModel,
    BaseMemorySystem,
    BasePatternDetector,
    BaseRetrievalEngine,
    BaseTimelineEngine,
)
from chronos_engine.core.models import RetrievedContext, UserInput


class RetrievalEngine(BaseRetrievalEngine):
    def __init__(
        self,
        memory_system: BaseMemorySystem,
        timeline_engine: BaseTimelineEngine,
        identity_model: BaseIdentityModel,
        pattern_detector: BasePatternDetector,
    ):
        self.memory_system = memory_system
        self.timeline_engine = timeline_engine
        self.identity_model = identity_model
        self.pattern_detector = pattern_detector

    async def retrieve_context(self, user_input: UserInput) -> RetrievedContext:
        user_id = user_input.user_id

        # 1. Semantic Memory Retrieval
        relevant_memories = await self.memory_system.search_semantic_memories(
            user_id=user_id, query=user_input.content, top_k=5
        )

        # 2. Short term conversational memory fallback
        if not relevant_memories:
            relevant_memories = await self.memory_system.get_short_term_context(user_id=user_id, limit=5)

        # 3. Timeline Events Retrieval
        timeline_events = await self.timeline_engine.get_timeline(user_id=user_id)

        # Determine current life phase
        life_phase = timeline_events[-1].life_phase if timeline_events else "Initial Phase"

        # 4. Identity Profile Retrieval
        identity = await self.identity_model.get_or_create_profile(user_id=user_id)
        identity_dict = {
            "interests": identity.interests,
            "goals": identity.goals,
            "values": identity.values,
            "emotional_tendencies": identity.emotional_tendencies,
            "communication_style": identity.communication_style,
            "decision_patterns": identity.decision_patterns,
        }

        # 5. Pattern Detection Retrieval
        patterns = await self.pattern_detector.analyze_patterns(user_id=user_id)

        recent_changes = [
            f"Evolving goal: {identity.goals[0]}" if identity.goals else "Establishing core vision",
            f"Emotional posture: Optimism score {(identity.emotional_tendencies.get('optimism', 0.8) * 100):.0f}%",
        ]

        return RetrievedContext(
            relevant_memories=relevant_memories,
            timeline_events=timeline_events[:5],
            life_phase=life_phase,
            identity_summary=identity_dict,
            patterns=patterns[:4],
            goals=identity.goals,
            recent_changes=recent_changes,
        )
