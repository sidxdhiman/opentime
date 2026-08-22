import asyncio
from typing import Dict, List, Optional
from chronos_engine.core.interfaces import BaseStorageAdapter, BaseTemporalStore
from chronos_engine.core.models import (
    IdentityProfile,
    MemoryItem,
    PatternItem,
    ReflectionInsight,
    TimelineEvent,
)
from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalSnapshot,
    TemporalThread,
    TemporalThreadStatus,
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


class InMemoryTemporalStore(BaseTemporalStore):
    """In-memory temporal store for the temporal domain.

    Follows the same shape as ``InMemoryStorageAdapter`` so a MongoDB
    implementation (preferred collection: ``engine_temporal_threads``) can
    be dropped in later without changing callers. Wired into the engine in
    Phase 3C for read-only candidate retrieval during thread matching —
    no automatic writes happen yet (thread lifecycle belongs to later
    temporal phases).
    """

    def __init__(self):
        self._threads: Dict[str, List[TemporalThread]] = {}
        self._events: Dict[str, List[TemporalEvent]] = {}
        self._snapshots: Dict[str, List[TemporalSnapshot]] = {}
        self._lock = asyncio.Lock()

    async def save_thread(self, thread: TemporalThread) -> TemporalThread:
        async with self._lock:
            user_list = self._threads.setdefault(thread.user_id, [])
            for idx, item in enumerate(user_list):
                if item.id == thread.id:
                    user_list[idx] = thread
                    return thread
            user_list.append(thread)
            return thread

    async def get_thread(self, thread_id: str, user_id: str) -> Optional[TemporalThread]:
        async with self._lock:
            for thread in self._threads.get(user_id, []):
                if thread.id == thread_id:
                    return thread
            return None

    async def get_threads_by_user(self, user_id: str) -> List[TemporalThread]:
        async with self._lock:
            threads = self._threads.get(user_id, [])
            return sorted(threads, key=lambda t: t.created_at, reverse=True)

    async def get_candidate_threads(self, user_id: str, limit: int = 25) -> List[TemporalThread]:
        """Bounded candidate retrieval for thread matching (Phase 3C).

        Live threads only: OPEN / ACTIVE / CHANGED. Resolved, abandoned and
        archived stories are excluded so they cannot absorb new events.
        Most recent first, capped at ``limit``.
        """
        live = {
            TemporalThreadStatus.OPEN,
            TemporalThreadStatus.ACTIVE,
            TemporalThreadStatus.CHANGED,
        }
        async with self._lock:
            threads = [t for t in self._threads.get(user_id, []) if t.status in live]
            return sorted(threads, key=lambda t: t.created_at, reverse=True)[:limit]

    async def save_event(self, event: TemporalEvent) -> TemporalEvent:
        async with self._lock:
            user_list = self._events.setdefault(event.thread_id, [])
            for idx, item in enumerate(user_list):
                if item.id == event.id:
                    user_list[idx] = event
                    return event
            user_list.append(event)
            return event

    async def get_events_by_thread(self, thread_id: str, user_id: str) -> List[TemporalEvent]:
        async with self._lock:
            events = self._events.get(thread_id, [])
            return sorted(events, key=lambda e: e.occurred_at)

    async def save_snapshot(self, snapshot: TemporalSnapshot) -> TemporalSnapshot:
        async with self._lock:
            user_list = self._snapshots.setdefault(snapshot.user_id, [])
            for idx, item in enumerate(user_list):
                if item.id == snapshot.id:
                    user_list[idx] = snapshot
                    return snapshot
            user_list.append(snapshot)
            return snapshot

    async def get_snapshots_by_user(self, user_id: str) -> List[TemporalSnapshot]:
        async with self._lock:
            snapshots = self._snapshots.get(user_id, [])
            return sorted(snapshots, key=lambda s: s.timestamp)
