import asyncio
from typing import Dict, List, Optional
from chronos_engine.core.interfaces import BaseStorageAdapter, BaseTemporalStore
from chronos_engine.core.models import (
    IdentityProfile,
    InteractionRecord,
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
    ReturnLedger,
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
        self._interactions: Dict[str, List[InteractionRecord]] = {}
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
            effective_limit = max(1, limit)
            return sorted_memories[:effective_limit]

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

    async def save_interaction(self, record: InteractionRecord) -> InteractionRecord:
        async with self._lock:
            user_list = self._interactions.setdefault(record.user_id, [])
            for idx, item in enumerate(user_list):
                if item.id == record.id:
                    user_list[idx] = record
                    return record
            user_list.append(record)
            return record

    async def get_interactions_by_user(
        self, user_id: str, limit: int = 50
    ) -> List[InteractionRecord]:
        async with self._lock:
            items = self._interactions.get(user_id, [])
            sorted_items = sorted(items, key=lambda r: r.created_at, reverse=True)
            effective_limit = max(1, limit)
            return sorted_items[:effective_limit]

    async def delete_all_for_user(self, user_id: str) -> None:
        async with self._lock:
            self._memories.pop(user_id, None)
            self._timeline.pop(user_id, None)
            self._identity.pop(user_id, None)
            self._reflections.pop(user_id, None)
            self._patterns.pop(user_id, None)
            self._interactions.pop(user_id, None)


class InMemoryTemporalStore(BaseTemporalStore):
    """In-memory temporal store for the temporal domain.

    Follows the same shape as ``InMemoryStorageAdapter`` so a MongoDB
    implementation (collections: ``engine_temporal_threads`` /
    ``engine_temporal_events``) can be dropped in without changing callers.
    Wired into the engine in Phase 3C for read-only candidate retrieval
    during thread matching; since Phase 3D it also persists lifecycle
    writes (thread creation, event attachment, status updates).

    Like the rest of this repository, stored objects are returned as-is —
    callers must not rely on defensive copies. Event reads are user-scoped:
    each event records its owner at save time and is only returned to that
    user.
    """

    def __init__(self):
        self._threads: Dict[str, List[TemporalThread]] = {}
        self._events: Dict[str, List[TemporalEvent]] = {}
        self._event_owner: Dict[str, str] = {}
        self._snapshots: Dict[str, List[TemporalSnapshot]] = {}
        self._return_ledgers: Dict[str, ReturnLedger] = {}
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

    async def find_thread_by_origin_memory(
        self, user_id: str, memory_id: str
    ) -> Optional[TemporalThread]:
        """Targeted duplicate guard for lifecycle idempotency (Phase 3D).

        Bounded by the requesting user's own thread list — never a global
        scan.
        """
        async with self._lock:
            for thread in self._threads.get(user_id, []):
                if thread.origin_memory_id == memory_id:
                    return thread
            return None

    async def save_event(self, event: TemporalEvent) -> TemporalEvent:
        async with self._lock:
            # Always record ownership — unconditionally
            if event.user_id is not None:
                self._event_owner[event.id] = event.user_id
            user_list = self._events.setdefault(event.thread_id, [])
            for idx, item in enumerate(user_list):
                if item.id == event.id:
                    user_list[idx] = event
                    return event
            user_list.append(event)
            return event

    async def get_events_by_thread(self, thread_id: str, user_id: str) -> List[TemporalEvent]:
        async with self._lock:
            events = [
                e
                for e in self._events.get(thread_id, [])
                # User isolation: an event recorded by another user is
                # invisible here even if its thread id were somehow known.
                # Events with no owner record are visible to no one (safe default).
                if self._event_owner.get(e.id) == user_id
            ]
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

    async def get_return_ledger(self, user_id: str) -> Optional[ReturnLedger]:
        async with self._lock:
            return self._return_ledgers.get(user_id)

    async def save_return_ledger(self, ledger: ReturnLedger) -> ReturnLedger:
        async with self._lock:
            self._return_ledgers[ledger.user_id] = ledger
            return ledger

    async def delete_all_for_user(self, user_id: str) -> None:
        async with self._lock:
            owned_thread_ids = {t.id for t in self._threads.get(user_id, [])}
            # Clean up events that belong to any of this user's threads
            for thread_id in owned_thread_ids:
                for ev in self._events.pop(thread_id, []):
                    self._event_owner.pop(ev.id, None)
            # Also purge any events attributed to the user that may live under
            # an unknown thread bucket, plus their ownership records.
            orphan_ids = [
                eid for eid, owner in self._event_owner.items() if owner == user_id
            ]
            for eid in orphan_ids:
                self._event_owner.pop(eid, None)
            self._threads.pop(user_id, None)
            self._snapshots.pop(user_id, None)
            self._return_ledgers.pop(user_id, None)
