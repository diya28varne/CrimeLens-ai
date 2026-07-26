"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: Literal["local", "ci", "staging", "production"] = "local"
    app_name: str = "CrimeLens AI"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    ai_enabled: bool = False
    ml_enabled: bool = False
    network_enabled: bool = False

    postgres_url: str = Field(
        default="postgresql+psycopg://crimelens:crimelens@localhost:5432/crimelens",
        alias="POSTGRES_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7
    cookie_secure: bool = False
    cookie_domain: str = "localhost"
    # Local/datathon: any email+password can sign in (auto-provisions users).
    open_demo_login: bool = Field(default=True, alias="OPEN_DEMO_LOGIN")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def allow_open_demo_login(self) -> bool:
        """Open sign-in for local/datathon demos — never in production."""
        if self.is_production:
            return False
        return self.open_demo_login


@lru_cache
def get_settings() -> Settings:
    return Settings()
