"""Temporal Intelligence foundation for the ChronOS Engine.

Phase 3A: domain models and a dormant storage abstraction.
Phase 3B: deterministic TemporalEvent detection (``temporal.detector``).

This package ``__init__`` intentionally exposes only the leaf ``models``
module: importing the detector here would create an import cycle
(state.models -> temporal.__init__ -> detector -> core.interfaces ->
state.models). Import the detector explicitly::

    from chronos_engine.temporal.detector import TemporalEventDetector
"""

from chronos_engine.temporal.models import (
    TemporalEvent,
    TemporalEventDetectionResult,
    TemporalSnapshot,
    TemporalThread,
    TemporalThreadStatus,
    TemporalType,
)

__all__ = [
    "TemporalEvent",
    "TemporalEventDetectionResult",
    "TemporalSnapshot",
    "TemporalThread",
    "TemporalThreadStatus",
    "TemporalType",
]
