"""
Motor (async MongoDB) client factory and index bootstrap.

Usage:
    from opentime.infrastructure.mongodb.client import get_mongo_db

    db = await get_mongo_db()
    collection = db["memories"]

The client is created once per process and reused.
"""

from __future__ import annotations

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from opentime.infrastructure.config import get_settings

logger = structlog.get_logger()

_client: AsyncIOMotorClient | None = None


def _get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongodb_url)
    return _client


async def get_mongo_db() -> AsyncIOMotorDatabase:
    settings = get_settings()
    return _get_client()[settings.mongodb_db_name]


async def close_mongo_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


# ---------------------------------------------------------------------------
# Index bootstrapping — called once on application startup
# ---------------------------------------------------------------------------

async def ensure_indexes() -> None:
    """Create all required MongoDB indexes for the onboarding + Chronos
    collections.  This is idempotent."""
    db = await get_mongo_db()
    log = structlog.get_logger()

    await db["onboarding_sessions"].create_index("user_id")
    await db["onboarding_sessions"].create_index([("user_id", 1), ("status", 1)])

    await db["onboarding_responses"].create_index("user_id")
    await db["onboarding_responses"].create_index(
        [("user_id", 1), ("session_id", 1), ("step", 1)]
    )

    await db["memories"].create_index("user_id")
    await db["memories"].create_index([("user_id", 1), ("is_genesis", 1)])
    await db["memories"].create_index([("user_id", 1), ("topics", 1)])
    await db["memories"].create_index([("user_id", 1), ("created_at", -1)])
    # Vector search index must be created via Atlas UI / Atlas API.
    # The field `embedding` is a list[float] ready for that.

    await db["identity_states"].create_index("user_id")
    await db["identity_states"].create_index([("user_id", 1), ("version", -1)])

    await db["goals"].create_index("user_id")
    await db["goals"].create_index([("user_id", 1), ("status", 1)])

    await db["timeline_events"].create_index("user_id")
    await db["timeline_events"].create_index([("user_id", 1), ("event_time", -1)])

    await db["patterns"].create_index("user_id")

    await db["analysis_preferences"].create_index("user_id")

    await db["chronos_states"].create_index("user_id", unique=True)

    # ChronOS Engine collections (runtime memory store)
    await db["engine_memories"].create_index("user_id")
    await db["engine_memories"].create_index([("user_id", 1), ("timestamp", -1)])
    await db["engine_timeline"].create_index("user_id")
    await db["engine_identity"].create_index("user_id", unique=True)
    await db["engine_reflections"].create_index("user_id")
    await db["engine_patterns"].create_index("user_id")

    log.info("mongodb_indexes_ensured")
