"""Builds a ``ChronosState`` from the information ChronOS already has."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from chronos_engine.core.models import RetrievedContext, UserInput
from chronos_engine.state.models import (
    ChronosState,
    ConsistencyResult,
    GoalAnalysisResult,
    IntentResult,
    UserStateResult,
)
from chronos_engine.temporal.models import TemporalEventDetectionResult


class StateBuilder:
    """Assembles existing engine data into a single structured ``ChronosState``.

    No detection logic is performed here — this only groups the results the
    pipeline already produced (current input, retrieved context, intent, user
    state, goal analysis, temporal event detection) into one object. The
    dedicated detectors and the ``ConsistencyEngine`` run before ``build``;
    the builder just wires their results in. Engine-state sections stay empty
    until their detectors exist.
    """

    async def build(
        self,
        user_input: UserInput,
        retrieved_context: RetrievedContext,
        intent: Optional[IntentResult] = None,
        user_state: Optional[UserStateResult] = None,
        goal_analysis: Optional[GoalAnalysisResult] = None,
        consistency_result: Optional[ConsistencyResult] = None,
        temporal_event_detection: Optional[TemporalEventDetectionResult] = None,
    ) -> ChronosState:
        contradictions = []
        if consistency_result is not None:
            contradictions = (
                list(consistency_result.contradictions)
                + list(consistency_result.changes)
            )
        return ChronosState(
            id=f"state_{uuid.uuid4().hex[:12]}",
            user_id=user_input.user_id,
            created_at=datetime.now(timezone.utc),
            current_input=user_input,
            intent=intent,
            user_state=user_state,
            goal_analysis=goal_analysis,
            context=retrieved_context,
            goals=list(retrieved_context.goals) if retrieved_context else [],
            patterns=list(retrieved_context.patterns) if retrieved_context else [],
            contradictions=contradictions,
            temporal_event_detection=temporal_event_detection,
            engine_state=None,
            confidence=None,
        )
