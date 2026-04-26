from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    service_name: str = Field(default="service", alias="SERVICE_NAME")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    queue_name: str = Field(default="runs:queue", alias="QUEUE_NAME")

    api_port: int = Field(default=8000, alias="API_PORT")
    worker_concurrency: int = Field(default=1, alias="WORKER_CONCURRENCY")
    worker_poll_timeout_seconds: int = Field(
        default=5, alias="WORKER_POLL_TIMEOUT_SECONDS"
    )
    worker_max_retries: int = Field(default=2, alias="WORKER_MAX_RETRIES")

    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

