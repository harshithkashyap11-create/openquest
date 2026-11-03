from functools import lru_cache
from pathlib import Path

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str
    app_env: str = "development"
    auth_mode: Literal["demo", "required"] = "demo"
    session_hours: int = Field(default=8, ge=1, le=24)
    ai_provider: str = "mock"
    openrouter_api_key: str | None = Field(default=None, repr=False)
    openrouter_model: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 20
    ai_batch_timeout_seconds: float = 45
    gemini_api_key: str | None = Field(default=None, repr=False)
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_timeout_seconds: float = 45

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def forbid_public_demo(self):
        if self.app_env not in {"development", "test"} and self.auth_mode != "required":
            raise ValueError("AUTH_MODE=required is mandatory outside development/test")
        return self

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            raise ValueError(
                "Use postgresql+psycopg:// for the configured Psycopg 3 driver"
            )
        if not value.startswith(("postgresql+psycopg://", "sqlite")):
            raise ValueError(
                "DATABASE_URL must use postgresql+psycopg:// or a SQLite URL for tests"
            )
        return value

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"mock", "openrouter", "gemini"}:
            raise ValueError("AI_PROVIDER must be 'mock', 'openrouter', or 'gemini'")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
