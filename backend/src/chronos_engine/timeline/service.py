import uuid
from typing import List
from chronos_engine.core.interfaces import BaseStorageAdapter, BaseTimelineEngine
from chronos_engine.core.models import MemoryItem, TimelineEvent


class TimelineEngine(BaseTimelineEngine):
    def __init__(self, storage: BaseStorageAdapter):
        self.storage = storage

    async def process_memory(self, user_id: str, memory: MemoryItem) -> TimelineEvent:
        timeline_events = await self.storage.get_timeline_by_user(user_id)

        # Detect life phase from memory tags/content
        content_lower = memory.content.lower()
        if "opentime" in content_lower or "chronos" in content_lower or "architect" in content_lower:
            life_phase = "ChronOS Architecture & OpenTime Building"
        elif "learn" in content_lower or "study" in content_lower or "research" in content_lower:
            life_phase = "Exploration & Deep Research"
        elif "build" in content_lower or "ship" in content_lower or "code" in content_lower:
            life_phase = "Active System Execution"
        elif len(timeline_events) > 0:
            life_phase = timeline_events[-1].life_phase
        else:
            life_phase = "Initial Phase"

        # Check if recurring event
        is_recurring = False
        frequency = None
        for ev in timeline_events:
            if ev.title.lower() in content_lower:
                is_recurring = True
                frequency = "Weekly"
                break

        # Basic sentiment heuristic
        positive_words = {"great", "good", "excited", "love", "confident", "success", "amazing", "optimistic"}
        negative_words = {"hard", "stuck", "tired", "anxious", "frustrated", "bug", "issue"}
        words = set(content_lower.split())
        pos_count = len(words.intersection(positive_words))
        neg_count = len(words.intersection(negative_words))
        sentiment = 0.0
        if pos_count or neg_count:
            sentiment = (pos_count - neg_count) / max(1, pos_count + neg_count)

        title = memory.content[:50] + ("..." if len(memory.content) > 50 else "")

        event = TimelineEvent(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            title=title,
            description=memory.content,
            timestamp=memory.timestamp,
            life_phase=life_phase,
            is_recurring=is_recurring,
            frequency=frequency,
            memory_ids=[memory.id],
            sentiment=sentiment,
            belief_evolution_notes=f"Reflects shift towards {life_phase}"
        )

        return await self.storage.save_timeline_event(event)

    async def get_timeline(self, user_id: str) -> List[TimelineEvent]:
        return await self.storage.get_timeline_by_user(user_id)

    async def generate_historical_summary(self, user_id: str) -> str:
        events = await self.get_timeline(user_id)
        if not events:
            return "No historical events recorded yet."

        phases = {}
        for ev in events:
            phases.setdefault(ev.life_phase, []).append(ev)

        summary_parts = []
        for phase, ev_list in phases.items():
            summary_parts.append(f"Phase '{phase}' ({len(ev_list)} events): Key focus around {ev_list[-1].title}")

        return "\n".join(summary_parts)
