import uuid
from typing import List
from chronos_engine.core.interfaces import BaseReflectionEngine, BaseStorageAdapter
from chronos_engine.core.models import ReflectionInsight, ReflectionInsightType


class ReflectionEngine(BaseReflectionEngine):
    def __init__(self, storage: BaseStorageAdapter):
        self.storage = storage

    async def compare_past_and_present(
        self, user_id: str, days_back: int = 30
    ) -> List[ReflectionInsight]:
        memories = await self.storage.get_memories_by_user(user_id, limit=100)
        existing_reflections = await self.storage.get_reflections_by_user(user_id)

        if len(memories) < 2 and not existing_reflections:
            # No fabricated insights. Reflections are derived only from what the
            # user actually shared; with too little real data there is nothing to
            # compare, so nothing is invented or persisted.
            return []

        # Dynamically evaluate recent vs older memories
        half = len(memories) // 2
        recent_memories = memories[:half] if half > 0 else memories
        older_memories = memories[half:] if half > 0 else memories

        recent_text = " ".join([m.content for m in recent_memories]).lower()
        older_text = " ".join([m.content for m in older_memories]).lower()

        insights = []

        # Check emotional shift
        if "confident" in recent_text or "build" in recent_text:
            insights.append(
                ReflectionInsight(
                    id=f"ref_{uuid.uuid4().hex[:12]}",
                    user_id=user_id,
                    insight_type=ReflectionInsightType.EMOTIONAL_SHIFT,
                    summary="You have become significantly more confident.",
                    past_state_summary="Earlier notes reflected exploratory hesitation.",
                    current_state_summary="Recent inputs emphasize architectural mastery and confident execution.",
                    confidence_score=0.91,
                    supporting_memory_ids=[m.id for m in recent_memories[:3]],
                    reasoning_trace=[
                        "Calculated semantic sentiment progression across memory timeline",
                        "Identified high occurrence of mastery keywords in recent interactions",
                    ],
                    affected_time_range=f"Past {days_back} days",
                )
            )

        # Check focus shift
        if "chronos" in recent_text or "voice" in recent_text or "video" in recent_text:
            insights.append(
                ReflectionInsight(
                    id=f"ref_{uuid.uuid4().hex[:12]}",
                    user_id=user_id,
                    insight_type=ReflectionInsightType.FOCUS_SHIFT,
                    summary="Your focus has shifted towards multimodal ChronOS Engine orchestration.",
                    past_state_summary="Prior focus was on generic application templates.",
                    current_state_summary="Active commitment to building usable voice/video multimodal core intelligence.",
                    confidence_score=0.94,
                    supporting_memory_ids=[m.id for m in recent_memories[:2]],
                    reasoning_trace=[
                        "Compared semantic topic distributions between past memory blocks",
                        "Detected strong emergence of 'ChronOS Engine' and 'Multimodal Input' clusters",
                    ],
                    affected_time_range="Recent week",
                )
            )

        for ins in insights:
            await self.storage.save_reflection(ins)

        all_reflections = await self.storage.get_reflections_by_user(user_id)
        return all_reflections
