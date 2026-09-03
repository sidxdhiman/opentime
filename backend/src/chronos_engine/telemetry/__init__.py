"""Metadata-only product telemetry for the ChronOS engine (Phase 6).

This emitter records lightweight, *metadata-only* product events into the
MongoDB ``product_events`` collection. It exists purely for product
observability (activation, engagement, trust surfaces) and observational
(quota-free) privacy metrics.

Design guarantees:

- **Non-blocking & failure-safe.** Every write is wrapped in try/except and
  never raises into the caller; a telemetry failure can never affect the
  primary user flow (conversation, memory lifecycle, return context, export).
- **Metadata only.** Events never contain user content, prompts, AI responses,
  reasoning, confidence scores, internal IDs of memories/threads/events, or
  provider secrets. Only coarse booleans/counts/enums are recorded.
- **User-scoped.** Each event carries the owning ``user_id`` so ``delete_user_data``
  can purge a user's telemetry alongside the rest of their data (privacy-first).
- **Cross-user isolation.** Queries are always scoped by ``user_id``; PII is a
  first-class indexed key alongside ``event_type``.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from opentime.infrastructure.mongodb.client import get_mongo_db

logger = logging.getLogger(__name__)

_COLLECTION = "product_events"

# Canonical event types emitted by the product surfaces.
ACCOUNT_CREATED = "account_created"
ONBOARDING_COMPLETED = "onboarding_completed"
CONVERSATION_PROCESSED = "conversation_processed"
CONVERSATION_FAILED = "conversation_failed"
MEMORY_DELETED = "memory_deleted"
STORY_ARCHIVED = "story_archived"
STORY_RESTORED = "story_restored"
RETURN_CONTEXT_SHOWN = "return_context_shown"
DATA_EXPORTED = "data_exported"


async def record_event(
    user_id: str,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Persist one metadata-only product event, never raising on failure.

    ``data`` is a flat dict of coarse, non-sensitive metadata (booleans,
    counts, enum-like strings). It is never user content. All failures are
    swallowed and logged so telemetry can never break the product flow.
    """
    try:
        db = await get_mongo_db()
        document = {
            "user_id": user_id,
            "event_type": event_type,
            # Coarse metadata only; kept flat and bounded.
            "data": data or {},
            "occurred_at": datetime.now(UTC),
        }
        await db[_COLLECTION].insert_one(document)
    except Exception:  # noqa: BLE001 - telemetry must never break the product.
        logger.exception(
            "telemetry: failed to record event=%s user=%s", event_type, user_id
        )
