"""Application settings for the PerX backend."""

from __future__ import annotations

from typing import Self
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings read from environment variables and optional .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://perx_user:perx_secret@localhost:5432/perx",
        alias="DATABASE_URL",
    )
    postgres_user: str | None = Field(default=None, alias="POSTGRES_USER")
    postgres_password: str | None = Field(default=None, alias="POSTGRES_PASSWORD")
    postgres_db: str | None = Field(default=None, alias="POSTGRES_DB")
    postgres_host: str | None = Field(default=None, alias="POSTGRES_HOST")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_use_memory: bool = Field(default=False, alias="REDIS_USE_MEMORY")
    jwt_secret: str = Field(default="change-me-in-dev-only", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5175",
            "http://127.0.0.1:5176",
        ],
        alias="CORS_ORIGINS",
    )
    recommender_warm_threshold: int = Field(default=10, alias="RECOMMENDER_WARM_THRESHOLD")
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(default="gemma2:2b", alias="OLLAMA_MODEL")
    ollama_timeout_seconds: float = Field(default=5.0, alias="OLLAMA_TIMEOUT_SECONDS")
    ollama_force_fail: bool = Field(default=False, alias="OLLAMA_FORCE_FAIL")
    ollama_max_retries: int = Field(default=0, alias="OLLAMA_MAX_RETRIES")
    allow_demo_mode: bool = Field(
        default=False,
        alias="ALLOW_DEMO_MODE",
        description="Set true only in local/dev. Must be false in production.",
    )
    reconcile_enabled: bool = Field(default=False, alias="RECONCILE_ENABLED")
    reconcile_interval_seconds: int = Field(default=300, alias="RECONCILE_INTERVAL_SECONDS")
    internal_api_key: str | None = Field(default=None, alias="INTERNAL_API_KEY")
    vapid_private_key: str | None = Field(default=None, alias="VAPID_PRIVATE_KEY")
    vapid_public_key: str | None = Field(default=None, alias="VAPID_PUBLIC_KEY")
    vapid_claims_email: str = Field(default="mailto:admin@perx.local", alias="VAPID_CLAIMS_EMAIL")
    cv_enabled: bool = Field(
        default=True,
        alias="CV_ENABLED",
        description="Set false in production if cv-service is unavailable.",
    )
    cv_service_url: str = Field(default="http://localhost:8010", alias="CV_SERVICE_URL")
    cv_internal_key: str | None = Field(default=None, alias="CV_INTERNAL_KEY")
    cv_max_image_bytes: int = Field(default=5_000_000, alias="CV_MAX_IMAGE_BYTES")
    cv_result_ttl_seconds: int = Field(default=3600, alias="CV_RESULT_TTL_SECONDS")
    cv_request_timeout_seconds: float = Field(default=8.0, alias="CV_REQUEST_TIMEOUT_SECONDS")

    @model_validator(mode="after")
    def assemble_database_url_from_postgres_env(self) -> Self:
        """When POSTGRES_* is set, derive DATABASE_URL with proper password URL encoding."""

        if self.postgres_user and self.postgres_password is not None:
            host = self.postgres_host or "localhost"
            db = self.postgres_db or "perx"
            user = quote_plus(self.postgres_user)
            password = quote_plus(self.postgres_password)
            self.database_url = (
                f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db}"
            )
        return self


def get_settings() -> Settings:
    """Return settings read from the current environment."""

    return Settings()


settings = get_settings()
