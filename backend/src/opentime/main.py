import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from opentime.api.v1.router import router as v1_router
from opentime.infrastructure.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    app.include_router(v1_router, prefix=settings.api_prefix)

    return app


app = create_app()
