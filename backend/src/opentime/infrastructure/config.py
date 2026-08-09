from functools import lru_cache

from pydantic import Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "OpenTime"
    app_version: str = "0.1.0"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database (SQLAlchemy – auth)
    # Local dev without Docker: sqlite+aiosqlite:///./opentime-dev.db
    database_url: str = Field(
        default="postgresql+asyncpg://opentime:opentime@localhost:5432/opentime"
    )

    # MongoDB (Chronos state, onboarding, memories)
    mongodb_url: str = Field(default="mongodb://localhost:27017")
    mongodb_db_name: str = Field(default="opentime")

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    # JWT
    jwt_secret_key: str = Field(default="change-me-in-production-use-a-long-random-string")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # S3-compatible storage (MinIO in dev)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "opentime-memories"
    s3_region: str = "us-east-1"

    # LLM / Embeddings (optional – system falls back to mocks when absent)
    openai_api_key: str | None = Field(default=None)
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"


@lru_cache
def get_settings() -> Settings:
    return Settings()
