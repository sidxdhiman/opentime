import uuid
from typing import List
from chronos_engine.core.interfaces import BasePatternDetector, BaseStorageAdapter
from chronos_engine.core.models import PatternCategory, PatternItem


class PatternDetector(BasePatternDetector):
    def __init__(self, storage: BaseStorageAdapter):
        self.storage = storage

    async def analyze_patterns(self, user_id: str) -> List[PatternItem]:
        memories = await self.storage.get_memories_by_user(user_id, limit=100)
        existing_patterns = await self.storage.get_patterns_by_user(user_id)

        if not memories and not existing_patterns:
            default_patterns = [
                PatternItem(
                    id=f"pat_{uuid.uuid4().hex[:12]}",
                    user_id=user_id,
                    category=PatternCategory.REPEATED_SUCCESS,
                    title="Clean Architecture First",
                    description=" Consistently defines interfaces, models, and module boundaries before writing business logic.",
                    frequency="Daily pattern",
                    confidence_score=0.95,
                    supporting_memory_ids=[],
                ),
                PatternItem(
                    id=f"pat_{uuid.uuid4().hex[:12]}",
                    user_id=user_id,
                    category=PatternCategory.PRODUCTIVITY_TREND,
                    title="High-Output Deep Work Blocks",
                    description="Demonstrates concentrated, rapid execution cycles during system architecture design.",
                    frequency="Peak active cycles",
                    confidence_score=0.90,
                    supporting_memory_ids=[],
                ),
                PatternItem(
                    id=f"pat_{uuid.uuid4().hex[:12]}",
                    user_id=user_id,
                    category=PatternCategory.DECISION_CHANGE,
                    title="Model-Agnostic Infrastructure Preference",
                    description="Prefers modular layer separation over direct vendor LLM coupling.",
                    frequency="Architectural rule",
                    confidence_score=0.93,
                    supporting_memory_ids=[],
                ),
            ]
            for p in default_patterns:
                await self.storage.save_pattern(p)
            return default_patterns

        # Analyze existing memories to generate new pattern detections
        all_text = " ".join([m.content for m in memories]).lower()

        # Habit check
        if "voice" in all_text or "record" in all_text:
            pat = PatternItem(
                id=f"pat_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                category=PatternCategory.HABIT,
                title="Multimodal Voice / Video Input Preference",
                description="Frequently captures ideas via voice recordings and multimodal inputs rather than text alone.",
                frequency="High frequency",
                confidence_score=0.89,
                supporting_memory_ids=[m.id for m in memories if "voice" in m.content.lower() or "record" in m.content.lower()],
            )
            await self.storage.save_pattern(pat)

        return await self.storage.get_patterns_by_user(user_id)
