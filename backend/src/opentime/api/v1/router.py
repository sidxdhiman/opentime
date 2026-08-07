from fastapi import APIRouter

from opentime.api.v1.auth import router as auth_router
from chronos_engine.api.router import router as chronos_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(chronos_router)

