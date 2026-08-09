"""MongoDB implementations of the onboarding repositories."""

from __future__ import annotations

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from opentime.domain.onboarding.entities import (
    OnboardingResponse,
    OnboardingSession,
    OnboardingStatus,
    OnboardingStep,
)
from opentime.domain.onboarding.repositories import (
    OnboardingResponseRepository,
    OnboardingSessionRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MongoOnboardingSessionRepository(OnboardingSessionRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["onboarding_sessions"]

    async def create(self, session: OnboardingSession) -> OnboardingSession:
        doc = session.model_dump(mode="json")
        await self._col.insert_one(doc)
        return session

    async def get_by_id(self, session_id: str) -> OnboardingSession | None:
        doc = await self._col.find_one({"id": session_id})
        return OnboardingSession(**doc) if doc else None

    async def get_active_for_user(self, user_id: str) -> OnboardingSession | None:
        doc = await self._col.find_one(
            {"user_id": user_id, "status": OnboardingStatus.IN_PROGRESS},
            sort=[("started_at", -1)],
        )
        return OnboardingSession(**doc) if doc else None

    async def get_completed_for_user(self, user_id: str) -> OnboardingSession | None:
        doc = await self._col.find_one(
            {"user_id": user_id, "status": OnboardingStatus.COMPLETED},
            sort=[("completed_at", -1)],
        )
        return OnboardingSession(**doc) if doc else None

    async def update(self, session: OnboardingSession) -> OnboardingSession:
        doc = session.model_dump(mode="json")
        await self._col.replace_one({"id": session.id}, doc, upsert=False)
        return session

    async def update_step(
        self,
        session_id: str,
        current_step: OnboardingStep,
        completed_steps: list[OnboardingStep],
        draft_data: dict | None = None,
    ) -> OnboardingSession:
        update: dict = {
            "$set": {
                "current_step": current_step,
                "completed_steps": completed_steps,
            }
        }
        if draft_data is not None:
            update["$set"]["draft_data"] = draft_data
        await self._col.update_one({"id": session_id}, update)
        doc = await self._col.find_one({"id": session_id})
        return OnboardingSession(**doc)

    async def mark_complete(self, session_id: str) -> OnboardingSession:
        now = _now()
        await self._col.update_one(
            {"id": session_id},
            {
                "$set": {
                    "status": OnboardingStatus.COMPLETED,
                    "completed_at": now.isoformat(),
                }
            },
        )
        doc = await self._col.find_one({"id": session_id})
        return OnboardingSession(**doc)

    async def mark_failed(self, session_id: str, reason: str) -> None:
        await self._col.update_one(
            {"id": session_id},
            {"$set": {"status": OnboardingStatus.FAILED, "failure_reason": reason}},
        )


class MongoOnboardingResponseRepository(OnboardingResponseRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["onboarding_responses"]

    async def create(self, response: OnboardingResponse) -> OnboardingResponse:
        doc = response.model_dump(mode="json")
        await self._col.insert_one(doc)
        return response

    async def get_by_id(self, response_id: str) -> OnboardingResponse | None:
        doc = await self._col.find_one({"id": response_id})
        return OnboardingResponse(**doc) if doc else None

    async def get_for_session(self, session_id: str) -> list[OnboardingResponse]:
        cursor = self._col.find({"session_id": session_id}).sort("created_at", 1)
        return [OnboardingResponse(**d) async for d in cursor]

    async def get_for_step(
        self, user_id: str, session_id: str, step: OnboardingStep
    ) -> OnboardingResponse | None:
        doc = await self._col.find_one(
            {"user_id": user_id, "session_id": session_id, "step": step},
            sort=[("created_at", -1)],
        )
        return OnboardingResponse(**doc) if doc else None

    async def get_all_for_user(self, user_id: str) -> list[OnboardingResponse]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", 1)
        return [OnboardingResponse(**d) async for d in cursor]
