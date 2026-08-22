"""Temporal Intelligence foundation for the ChronOS Engine.

Phase 3A: domain models and a dormant storage abstraction.
Phase 3B: deterministic TemporalEvent detection (``temporal.detector``).
Phase 3C: deterministic TemporalThread matching (``temporal.matcher``).

This package ``__init__`` intentionally exposes only the leaf ``models``
module: importing the detector or matcher here would create an import cycle
(state.models -> temporal.__init__ -> matcher -> core.interfaces ->
state.models). Import implementations explicitly::

    from chronos_engine.temporal.detector import TemporalEventDetector
    from chronos_engine.temporal.matcher import TemporalThreadMatcher
"""

from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalEventDetectionResult,
    TemporalSnapshot,
    TemporalThread,
    TemporalThreadMatchResult,
    TemporalThreadStatus,
    TemporalType,
)

__all__ = [
    "TemporalEvent",
    "TemporalEventDetectionResult",
    "TemporalSnapshot",
    "TemporalThread",
    "TemporalThreadMatchResult",
    "TemporalThreadStatus",
    "TemporalType",
]
