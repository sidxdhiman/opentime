import asyncio
from typing import Dict, List, Optional
from chronos_engine.core.interfaces import BaseStorageAdapter
from chronos_engine.core.models import (
    IdentityProfile,
    MemoryItem,
    PatternItem,
    ReflectionInsight,
    TimelineEvent,
)


class InMemoryStorageAdapter(BaseStorageAdapter):
    """
    In-memory document repository for fast, non-blocking execution.
    Can easily be swapped with MongoDB or PGVector repository.
    """

    def __init__(self):
        self._memories: Dict[str, List[MemoryItem]] = {}
        self._timeline: Dict[str, List[TimelineEvent]] = {}
        self._identity: Dict[str, IdentityProfile] = {}
        self._reflections: Dict[str, List[ReflectionInsight]] = {}
        self._patterns: Dict[str, List[PatternItem]] = {}
        self._lock = asyncio.Lock()

    async def save_memory(self, memory: MemoryItem) -> MemoryItem:
        async with self._lock:
            user_list = self._memories.setdefault(memory.user_id, [])
            # Replace if existing or append
            for idx, item in enumerate(user_list):
                if item.id == memory.id:
                    user_list[idx] = memory
                    return memory
            user_list.append(memory)
            return memory

    async def get_memories_by_user(self, user_id: str, limit: int = 100) -> List[MemoryItem]:
        async with self._lock:
            memories = self._memories.get(user_id, [])
            # Return sorted by timestamp descending
            sorted_memories = sorted(memories, key=lambda m: m.timestamp, reverse=True)
            return sorted_memories[:limit]

    async def save_timeline_event(self, event: TimelineEvent) -> TimelineEvent:
        async with self._lock:
            user_list = self._timeline.setdefault(event.user_id, [])
            for idx, item in enumerate(user_list):
                if item.id == event.id:
                    user_list[idx] = event
                    return event
            user_list.append(event)
            return event

    async def get_timeline_by_user(self, user_id: str) -> List[TimelineEvent]:
        async with self._lock:
            events = self._timeline.get(user_id, [])
            return sorted(events, key=lambda e: e.timestamp)

    async def save_identity(self, profile: IdentityProfile) -> IdentityProfile:
        async with self._lock:
            self._identity[profile.user_id] = profile
            return profile

    async def get_identity(self, user_id: str) -> Optional[IdentityProfile]:
        async with self._lock:
            return self._identity.get(user_id)

    async def save_reflection(self, insight: ReflectionInsight) -> ReflectionInsight:
        async with self._lock:
            user_list = self._reflections.setdefault(insight.user_id, [])
            for idx, item in enumerate(user_list):
                if item.id == insight.id:
                    user_list[idx] = insight
                    return insight
            user_list.append(insight)
            return insight

    async def get_reflections_by_user(self, user_id: str) -> List[ReflectionInsight]:
        async with self._lock:
            insights = self._reflections.get(user_id, [])
            return sorted(insights, key=lambda r: r.timestamp, reverse=True)

    async def save_pattern(self, pattern: PatternItem) -> PatternItem:
        async with self._lock:
            user_list = self._patterns.setdefault(pattern.user_id, [])
            for idx, item in enumerate(user_list):
                if item.id == pattern.id:
                    user_list[idx] = pattern
                    return pattern
            user_list.append(pattern)
            return pattern

    async def get_patterns_by_user(self, user_id: str) -> List[PatternItem]:
        async with self._lock:
            patterns = self._patterns.get(user_id, [])
            return sorted(patterns, key=lambda p: p.confidence_score, reverse=True)
