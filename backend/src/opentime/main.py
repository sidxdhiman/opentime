import structlog
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from opentime.api.v1.router import router as v1_router
from opentime.infrastructure.config import get_settings
from opentime.infrastructure.mongodb.client import close_mongo_client, ensure_indexes

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await ensure_indexes()
        logger.info("mongodb_ready")
    except Exception as exc:
        # Don't crash the app if MongoDB is unavailable at startup (e.g. dev without Docker)
        logger.warning("mongodb_startup_warning", error=str(exc))
    yield
    # Shutdown
    await close_mongo_client()
    logger.info("mongodb_closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
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

    # Serve uploaded audio/video memory recordings.
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")

    return app


app = create_app()
