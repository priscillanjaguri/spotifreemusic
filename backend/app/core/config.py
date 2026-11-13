"""Environment-based configuration.

All settings come from environment variables (or a `.env` file at the
repository root). Nothing secret is hardcoded: `SECRET_KEY` has *no default*,
so the app refuses to start if it is missing.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


def normalize_database_url(url: str) -> str:
    """Railway/Render/Heroku often inject `postgres://` or `postgresql://`.

    SQLAlchemy needs the explicit psycopg (v3) driver name.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


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
    # Capacitor Android/iOS WebViews use https://localhost (and capacitor:// on some builds).
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5791",
        "https://localhost",
        "capacitor://localhost",
        "http://localhost",
    ]
    # Set true behind HTTPS (production) so the session cookie is never sent over plain HTTP.
    cookie_secure: bool = False
    # Optional: without it the app runs, but search/playback report "provider not configured".
    jamendo_client_id: str | None = None
    # Development only: serve an invented catalogue (labelled 'mock_dev') with generated
    # tones when no real provider is configured. Ignored outside ENVIRONMENT=development.
    dev_mock_provider: bool = False

    # My Library: music files the user owns and uploads.
    library_storage_dir: Path = REPO_ROOT / "var" / "library"
    library_max_file_mb: int = 200
    library_max_files_per_request: int = 50
    # Run Librosa feature extraction after each upload (needs requirements-analysis.txt).
    library_analysis_enabled: bool = True
    # Cloudflare R2 (S3-compatible). All four must be set to store uploads in R2 instead of on disk.
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    r2_presign_seconds: int = 600

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    @property
    def r2_enabled(self) -> bool:
        return all((self.r2_account_id, self.r2_access_key_id, self.r2_secret_access_key, self.r2_bucket))

    @property
    def mock_provider_enabled(self) -> bool:
        return self.dev_mock_provider and self.environment == "development" and not self.jamendo_client_id


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
