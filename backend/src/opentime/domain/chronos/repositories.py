"""Repository interfaces for the Chronos domain."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from opentime.domain.chronos.entities import (
    AnalysisPreferenceRecord,
    ChronosState,
    Goal,
    GoalStatus,
    IdentityState,
    Memory,
    Pattern,
    TimelineEvent,
)


class MemoryRepository(ABC):
    @abstractmethod
    async def create(self, memory: Memory) -> Memory: ...

    @abstractmethod
    async def get_by_id(self, memory_id: str, user_id: str) -> Memory | None: ...

    @abstractmethod
    async def get_for_user(
        self, user_id: str, limit: int = 50, skip: int = 0
    ) -> list[Memory]: ...

    @abstractmethod
    async def get_genesis(self, user_id: str) -> Memory | None: ...

    @abstractmethod
    async def exists_genesis(self, user_id: str) -> bool: ...

    @abstractmethod
    async def search_by_topics(self, user_id: str, topics: list[str]) -> list[Memory]: ...

    @abstractmethod
    async def update(self, memory: Memory) -> Memory | None: ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> int: ...


class IdentityStateRepository(ABC):
    @abstractmethod
    async def create(self, state: IdentityState) -> IdentityState: ...

    @abstractmethod
    async def get_latest(self, user_id: str) -> IdentityState | None: ...

    @abstractmethod
    async def get_all_versions(self, user_id: str) -> list[IdentityState]: ...

    @abstractmethod
    async def get_by_id(self, state_id: str, user_id: str) -> IdentityState | None: ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> int: ...


class GoalRepository(ABC):
    @abstractmethod
    async def create(self, goal: Goal) -> Goal: ...

    @abstractmethod
    async def get_by_id(self, goal_id: str, user_id: str) -> Goal | None: ...

    @abstractmethod
    async def get_active_for_user(self, user_id: str) -> list[Goal]: ...

    @abstractmethod
    async def get_all_for_user(self, user_id: str) -> list[Goal]: ...

    @abstractmethod
    async def update_status(
        self, goal_id: str, user_id: str, status: GoalStatus
    ) -> Goal | None: ...

    @abstractmethod
    async def update(self, goal: Goal) -> Goal | None: ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> int: ...


class TimelineRepository(ABC):
    @abstractmethod
    async def create(self, event: TimelineEvent) -> TimelineEvent: ...

    @abstractmethod
    async def get_for_user(
        self, user_id: str, limit: int = 100, skip: int = 0
    ) -> list[TimelineEvent]: ...

    @abstractmethod
    async def get_range(
        self, user_id: str, from_date: datetime, to_date: datetime
    ) -> list[TimelineEvent]: ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> int: ...


class PatternRepository(ABC):
    @abstractmethod
    async def create(self, pattern: Pattern) -> Pattern: ...

    @abstractmethod
    async def get_for_user(self, user_id: str) -> list[Pattern]: ...

    @abstractmethod
    async def increment_evidence(
        self, pattern_id: str, user_id: str
    ) -> Pattern | None: ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> int: ...


class AnalysisPreferenceRepository(ABC):
    @abstractmethod
    async def create_many(
        self, records: list[AnalysisPreferenceRecord]
    ) -> list[AnalysisPreferenceRecord]: ...

    @abstractmethod
    async def get_for_user(self, user_id: str) -> list[AnalysisPreferenceRecord]: ...

    @abstractmethod
    async def replace_all_for_user(
        self, user_id: str, records: list[AnalysisPreferenceRecord]
    ) -> list[AnalysisPreferenceRecord]:
        """Delete existing prefs and insert new set atomically."""
        ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> int: ...


class ChronosStateRepository(ABC):
    @abstractmethod
    async def create(self, state: ChronosState) -> ChronosState: ...

    @abstractmethod
    async def get_for_user(self, user_id: str) -> ChronosState | None: ...

    @abstractmethod
    async def update(self, state: ChronosState) -> ChronosState: ...

    @abstractmethod
    async def exists_for_user(self, user_id: str) -> bool: ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> int: ...
