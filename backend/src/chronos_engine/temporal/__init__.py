"""Temporal Intelligence foundation for the ChronOS Engine.

Phase 3A: domain models and a dormant storage abstraction.
Phase 3B: deterministic TemporalEvent detection (``temporal.detector``).
Phase 3C: deterministic TemporalThread matching (``temporal.matcher``).
Phase 3D: deterministic thread lifecycle + persistence
(``temporal.lifecycle``).
Phase 3E: deterministic Past-vs-Present comparison
(``temporal.comparison``).
Phase 3F: deterministic past-self question planning
(``temporal.questions``).
Phase 3G: deterministic temporal relevance & timing
(``temporal.relevance``).

This package ``__init__`` intentionally exposes only the leaf ``models``
module: importing implementations here would create an import cycle
(state.models -> temporal.__init__ -> matcher -> core.interfaces ->
state.models). Import implementations explicitly::

    from chronos_engine.temporal.detector import TemporalEventDetector
    from chronos_engine.temporal.matcher import TemporalThreadMatcher
    from chronos_engine.temporal.lifecycle import TemporalThreadLifecycleManager
    from chronos_engine.temporal.relevance import TemporalRelevanceEngine
    """

from chronos_engine.temporal.models import (
    PastSelfPerspective,
    PastSelfQuestionIntent,
    PastSelfQuestionResult,
    PastSelfQuestionType,
    TemporalComparisonRelation,
    TemporalComparisonResult,
    TemporalEvent,
    TemporalEventDetectionResult,
    TemporalLifecycleResult,
    TemporalRelevanceDecision,
    TemporalRelevanceResult,
    TemporalSnapshot,
    TemporalThread,
    TemporalThreadMatchResult,
    TemporalThreadStatus,
    TemporalType,
)

__all__ = [
    "PastSelfPerspective",
    "PastSelfQuestionIntent",
    "PastSelfQuestionResult",
    "PastSelfQuestionType",
    "TemporalComparisonRelation",
    "TemporalComparisonResult",
    "TemporalEvent",
    "TemporalEventDetectionResult",
    "TemporalLifecycleResult",
    "TemporalRelevanceDecision",
    "TemporalRelevanceResult",
    "TemporalSnapshot",
    "TemporalThread",
    "TemporalThreadMatchResult",
    "TemporalThreadStatus",
    "TemporalType",
]
