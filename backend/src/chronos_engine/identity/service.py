from datetime import datetime, timezone
from typing import Any, Dict, Optional
from chronos_engine.core.interfaces import BaseIdentityModel, BaseStorageAdapter
from chronos_engine.core.models import IdentityProfile, MemoryItem


class IdentityModel(BaseIdentityModel):
    def __init__(self, storage: BaseStorageAdapter):
        self.storage = storage

    async def get_or_create_profile(self, user_id: str) -> IdentityProfile:
        profile = await self.storage.get_identity(user_id)
        if not profile:
            profile = IdentityProfile(
                user_id=user_id,
                interests=["AI Systems Architecture", "Personal Intelligence Layer", "ChronOS"],
                goals=["Build OpenTime into a world-class platform", "Master model-agnostic orchestration"],
                values=["Autonomy", "Deep Technical Craftsmanship", "Self-Reflection"],
                emotional_tendencies={"optimism": 0.85, "focus": 0.90, "resilience": 0.88, "curiosity": 0.95},
                skills=["Python Architecture", "Next.js", "AI System Design", "Clean Architecture"],
                relationships={"OpenTime Team": "Founder / Architect"},
                preferences={"communication": "Concise, highly technical, action-oriented", "theme": "Dark Mode"},
                decision_patterns=["Prioritizes core architecture & data models before logic"],
                communication_style="Direct, insightful, clear",
                version=1,
            )
            await self.storage.save_identity(profile)
        return profile

    async def evolve_profile(
        self, user_id: str, memory: MemoryItem, prompt_context: Optional[Dict[str, Any]] = None
    ) -> IdentityProfile:
        profile = await self.get_or_create_profile(user_id)
        content_lower = memory.content.lower()

        # Dynamically extract potential new goals, interests, or skill mentions
        new_interests = list(profile.interests)
        new_goals = list(profile.goals)
        new_skills = list(profile.skills)
        emotional_tendencies = dict(profile.emotional_tendencies)

        if "voice" in content_lower or "audio" in content_lower or "video" in content_lower:
            if "Multimodal Interaction" not in new_interests:
                new_interests.append("Multimodal Interaction")

        if "want to" in content_lower or "goal" in content_lower or "plan" in content_lower:
            goal_extract = memory.content[:60]
            if goal_extract not in new_goals:
                new_goals.append(goal_extract)

        if "confident" in content_lower or "optimistic" in content_lower or "excited" in content_lower:
            emotional_tendencies["optimism"] = min(1.0, emotional_tendencies.get("optimism", 0.8) + 0.02)
        elif "anxious" in content_lower or "tired" in content_lower:
            emotional_tendencies["optimism"] = max(0.0, emotional_tendencies.get("optimism", 0.8) - 0.02)

        # Update profile
        profile.interests = new_interests[:10]
        profile.goals = new_goals[:10]
        profile.skills = new_skills[:10]
        profile.emotional_tendencies = emotional_tendencies
        profile.version += 1
        profile.last_updated = datetime.now(timezone.utc)

        return await self.storage.save_identity(profile)
