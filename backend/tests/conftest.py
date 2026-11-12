"""Test setup.

Tests run against a REAL PostgreSQL database (TEST_DATABASE_URL), built by
running the actual Alembic migrations. That means the tests also prove that
the migrations work, and they can check Postgres-only features such as the
no-overlap exclusion constraint (SQLite could not do that).
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
from dotenv import dotenv_values

# TEST_DATABASE_URL may come from the real environment (CI) or the root .env file.
TEST_URL = os.environ.get("TEST_DATABASE_URL") or dotenv_values(BACKEND_DIR.parent / ".env").get("TEST_DATABASE_URL")
if not TEST_URL:
    pytest.exit("TEST_DATABASE_URL is not set (see .env.example)", returncode=2)
assert "test" in TEST_URL.rsplit("/", 1)[-1], "Refusing to run: TEST_DATABASE_URL must point to a *test* database"

# Point the app at the test DB *before* app modules are imported.
os.environ["DATABASE_URL"] = TEST_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-0123456789")


def _alembic(*args: str) -> None:
    env = {**os.environ, "ALEMBIC_DATABASE_URL": TEST_URL}
    subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND_DIR, env=env, check=True)


@pytest.fixture(scope="session")
def engine():
    # Start from a blank schema, then apply migrations exactly as production would.
    eng = create_engine(TEST_URL)
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    _alembic("upgrade", "head")
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    """A session wrapped in a transaction that is rolled back after each test."""
    conn = engine.connect()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    trans.rollback()
    conn.close()


# ---- API test helpers -------------------------------------------------------
from datetime import date  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.providers.base import (  # noqa: E402
    MusicProviderAdapter, ProviderArtist, ProviderError, ProviderTrack,
)


class FakeProvider(MusicProviderAdapter):
    """Stands in for a real provider in tests. Not used anywhere in the running app."""

    key = "fake"
    display_name = "Fake Provider (tests)"
    supports_playback = True
    fail = False

    def search_tracks(self, query, limit=20):
        if self.fail:
            raise ProviderError("boom")
        return [
            ProviderTrack("t1", "Night Drive", 200_000, [ProviderArtist("Neon Cat")], "Glow", date(2024, 1, 5),
                          "http://img/1.jpg", ["electronic", "chillout"], "http://stream/1.mp3", "http://cc/by",
                          True),
            ProviderTrack("t2", "Collab Song", 180_000, [ProviderArtist("Neon Cat"), ProviderArtist("Dusty Fox")],
                          None, None, None, ["rock"], "http://stream/2.mp3", None, False),
            ProviderTrack("t3", "Velvet Static", 210_000, [ProviderArtist("Dusty Fox")], "Glow", date(2023, 6, 1),
                          "http://img/3.jpg", ["electronic", "lofi"], "http://stream/3.mp3", "http://cc/by", True),
            ProviderTrack("t4", "Amber Wire", 195_000, [ProviderArtist("Neon Cat")], None, None,
                          "http://img/4.jpg", ["chillout", "ambient"], "http://stream/4.mp3", "http://cc/by", True),
        ]


@pytest.fixture()
def provider():
    return FakeProvider()


@pytest.fixture()
def client(db, provider):
    from app.core.db import get_db
    from app.main import app
    from app.providers.registry import get_music_provider

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_music_provider] = lambda: provider
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(client, email="ada@example.com", password="correct-horse-battery", name="Ada"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": name})
