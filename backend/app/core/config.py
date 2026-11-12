"""Environment-based configuration.

All settings come from environment variables (or a `.env` file at the
repository root). Nothing secret is hardcoded: `SECRET_KEY` has *no default*,
so the app refuses to start if it is missing.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "development"  # development | test | production
    database_url: str = Field(
        description="SQLAlchemy URL, e.g. postgresql+psycopg://user:pass@host:5432/db"
    )
    secret_key: str = Field(min_length=32, description="Signs auth tokens")
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:5173"]
    # Set true behind HTTPS (production) so the session cookie is never sent over plain HTTP.
    cookie_secure: bool = False
    # Optional: without it the app runs, but search/playback report "provider not configured".
    jamendo_client_id: str | None = None
    # Development only: serve an invented catalogue (labelled 'mock_dev') with generated
    # tones when no real provider is configured. Ignored outside ENVIRONMENT=development.
    dev_mock_provider: bool = False

    @property
    def mock_provider_enabled(self) -> bool:
        return self.dev_mock_provider and self.environment == "development" and not self.jamendo_client_id


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
