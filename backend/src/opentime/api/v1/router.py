from fastapi import APIRouter

from opentime.api.v1.auth import router as auth_router
from opentime.api.v1.onboarding import router as onboarding_router
from opentime.api.v1.chronos_state import router as chronos_state_router
from chronos_engine.api.router import router as chronos_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(onboarding_router)
router.include_router(chronos_state_router)
router.include_router(chronos_router)

