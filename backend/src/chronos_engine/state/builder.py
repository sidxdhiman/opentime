"""Builds a ``ChronosState`` from the information ChronOS already has."""

import uuid
from datetime import datetime, timezone

from chronos_engine.core.models import RetrievedContext, UserInput
from chronos_engine.state.models import ChronosState


class StateBuilder:
    """Assembles existing engine data into a single structured ``ChronosState``.

    No new detection logic is performed here yet — this only groups the
    information the pipeline already produces (current input + retrieved
    context, which carries life phase, goals, patterns and memories) into one
    object. Intent / user-state / engine-state sections stay empty until their
    dedicated detectors exist.
    """

    async def build(
        self,
        user_input: UserInput,
        retrieved_context: RetrievedContext,
    ) -> ChronosState:
        return ChronosState(
            id=f"state_{uuid.uuid4().hex[:12]}",
            user_id=user_input.user_id,
            created_at=datetime.now(timezone.utc),
            current_input=user_input,
            intent=None,
            user_state=None,
            context=retrieved_context,
            goals=list(retrieved_context.goals) if retrieved_context else [],
            patterns=list(retrieved_context.patterns) if retrieved_context else [],
            contradictions=[],
            engine_state=None,
            confidence=None,
        )
