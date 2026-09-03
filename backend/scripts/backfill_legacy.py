#!/usr/bin/env python3
"""Operator-run legacy backfill: application store -> engine stores.

Safe, idempotent, user-scoped. Migrates pre-5G-C application-store data
(memories / identity_states / timeline_events / patterns) into the ChronOS
engine stores so that legacy users appear in My Data / Dashboard without any
runtime fallback.

Usage (from backend/):
    python -m scripts.backfill_legacy                      # all legacy users
    python -m scripts.backfill_legacy --user <uuid>        # one user
    python -m scripts.backfill_legacy --dry-run            # report only, no writes

Requirements: MONGODB_URL / MONGODB_DB_NAME configured (or defaults), as with
the application. This script is additive and never deletes data.
"""

from __future__ import annotations

import argparse
import asyncio

import structlog

from opentime.application.migration.legacy_backfill import LegacyBackfillService
from opentime.infrastructure.mongodb.client import close_mongo_client, get_mongo_db

logger = structlog.get_logger()


async def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", dest="user_id", default=None, help="Backfill one user id")
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Report what would be migrated without writing anything.",
    )
    args = parser.parse_args()

    db = await get_mongo_db()
    service = LegacyBackfillService(db)
    dry_run = args.dry_run

    if args.user_id:
        result = await service.backfill_user(args.user_id, dry_run=dry_run)
        print(result.model_dump())
    else:
        summary = await service.backfill_all(dry_run=dry_run)
        print(summary.model_dump())
    await close_mongo_client()


if __name__ == "__main__":
    asyncio.run(run())
