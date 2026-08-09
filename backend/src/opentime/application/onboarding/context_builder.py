"""
ChronosContextBuilder

Assembles a rich context snapshot for any LLM call after onboarding.
This is what future Chronos features (chat, reflection, analysis) will
consume instead of raw database queries.

Usage:
    ctx = await builder.build(user_id)
    # ctx is a structured dict ready to inject into an LLM prompt
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from opentime.domain.chronos.repositories import (
    AnalysisPreferenceRepository,
    ChronosStateRepository,
    GoalRepository,
    IdentityStateRepository,
    MemoryRepository,
    PatternRepository,
    TimelineRepository,
)


class ChronosContextBuilder:
    def __init__(
        self,
        chronos_repo: ChronosStateRepository,
        identity_repo: IdentityStateRepository,
        memory_repo: MemoryRepository,
        goal_repo: GoalRepository,
        timeline_repo: TimelineRepository,
        pattern_repo: PatternRepository,
        pref_repo: AnalysisPreferenceRepository,
    ) -> None:
        self._chronos = chronos_repo
        self._identity = identity_repo
        self._memories = memory_repo
        self._goals = goal_repo
        self._timeline = timeline_repo
        self._patterns = pattern_repo
        self._prefs = pref_repo

    async def build(
        self,
        user_id: str,
        memory_limit: int = 10,
        timeline_limit: int = 20,
    ) -> dict[str, Any]:
        """
        Return a structured context dict representing:
          "Who is this user right now?"
        """
        # Fetch all data concurrently where possible
        import asyncio
        (
            chronos_state,
            identity_state,
            goals,
            memories,
            timeline,
            patterns,
            prefs,
        ) = await asyncio.gather(
            self._chronos.get_for_user(user_id),
            self._identity.get_latest(user_id),
            self._goal_repo_active(user_id),
            self._memories.get_for_user(user_id, limit=memory_limit),
            self._timeline.get_for_user(user_id, limit=timeline_limit),
            self._patterns.get_for_user(user_id),
            self._prefs.get_for_user(user_id),
        )

        return {
            "user_id": user_id,
            "assembled_at": datetime.now(timezone.utc).isoformat(),
            "is_initialised": chronos_state.is_initialised if chronos_state else False,

            # Current identity snapshot
            "identity": {
                "version": identity_state.version if identity_state else None,
                "traits": [
                    {
                        "trait": t.trait,
                        "claim_type": t.claim_type,
                        "confidence": t.confidence,
                    }
                    for t in (identity_state.traits if identity_state else [])
                ],
                "interests": [
                    {"value": c.value, "confidence": c.confidence}
                    for c in (identity_state.interests if identity_state else [])
                ],
                "values": [
                    {"value": c.value, "confidence": c.confidence}
                    for c in (identity_state.values if identity_state else [])
                ],
                "self_perception": [
                    c.value
                    for c in (identity_state.self_perception if identity_state else [])
                ],
                "current_phase": (
                    {
                        "value": identity_state.current_phase.value,
                        "confidence": identity_state.current_phase.confidence,
                    }
                    if identity_state and identity_state.current_phase
                    else None
                ),
            },

            # Current life state
            "current_state": (
                _serialize_life_state(chronos_state.current_life_state)
                if chronos_state
                else {}
            ),

            # Goals
            "goals": [
                {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description,
                    "category": g.category,
                    "importance": g.importance,
                    "status": g.status,
                }
                for g in goals
            ],

            # Relevant memories (recent, ordered by importance)
            "relevant_memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "summary": m.summary,
                    "topics": m.topics,
                    "importance": m.importance,
                    "is_genesis": m.is_genesis,
                    "event_time": m.event_time.isoformat() if m.event_time else None,
                }
                for m in memories
            ],

            # Timeline context
            "timeline_context": [
                {
                    "id": e.id,
                    "event_time": e.event_time.isoformat() if e.event_time else None,
                    "title": e.title,
                    "description": e.description,
                    "category": e.category,
                    "confidence": e.confidence,
                }
                for e in timeline
            ],

            # Known patterns (sorted by confidence)
            "known_patterns": [
                {
                    "id": p.id,
                    "type": p.type,
                    "pattern": p.pattern,
                    "confidence": p.confidence,
                    "evidence_count": p.evidence_count,
                }
                for p in patterns
            ],

            # Analysis preferences
            "analysis_preferences": [
                {"preference": p.preference, "custom_text": p.custom_text}
                for p in prefs
            ],

            # Changes (personal evolution)
            "changes": [
                {
                    "change_type": c.change_type,
                    "previous_state": c.previous_state.value,
                    "current_state": c.current_state.value,
                    "approximate_period": c.approximate_period,
                    "confidence": c.confidence,
                }
                for c in (chronos_state.changes if chronos_state else [])
            ],
        }

    async def _goal_repo_active(self, user_id: str):
        return await self._goals.get_active_for_user(user_id)


def _serialize_life_state(life_state) -> dict[str, Any]:
    return {
        "phase": (
            {"value": life_state.phase.value, "confidence": life_state.phase.confidence}
            if life_state.phase
            else None
        ),
        "priorities": [c.value for c in life_state.priorities],
        "interests": [c.value for c in life_state.interests],
        "concerns": [c.value for c in life_state.concerns],
        "responsibilities": [c.value for c in life_state.responsibilities],
        "projects": [c.value for c in life_state.projects],
    }
