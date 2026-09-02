import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(
            "request_validation_error",
            path=request.url.path,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": "Request validation failed"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_api_exception",
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred."},
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
