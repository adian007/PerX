"""Runtime settings for standalone cv-service."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = Field(default="perx-cv-service", alias="CV_SERVICE_NAME")
    service_version: str = Field(default="0.1.0", alias="CV_SERVICE_VERSION")
    max_payload_bytes: int = Field(default=5_000_000, alias="CV_MAX_PAYLOAD_BYTES")
    internal_key: str | None = Field(default=None, alias="CV_INTERNAL_KEY")


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
