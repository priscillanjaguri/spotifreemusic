"""API + DB integration for sequential next-track train/serve/fallback."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.ml.sequential import MIN_SESSIONS, MIN_TRANSITIONS
from app.models import Artist, ListeningEvent, SequentialModelRow, Song, SongArtist, User
from app.services import sequential_job
from tests.conftest import register

T0 = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)


def _extra_songs(db, n: int = 4) -> list[int]:
    """Grow the catalogue so unique-song thresholds are reachable in tests."""
    ids: list[int] = []
    for i in range(n):
        artist = Artist(name=f"Seq Artist {i}", data_source="mock_dev")
        song = Song(title=f"Seq Track {i}", duration_ms=200_000, data_source="mock_dev")
        song.artist_links.append(SongArtist(artist=artist, position=0))
        db.add(song)
        db.flush()
        ids.append(int(song.id))
    return ids


@pytest.fixture()
def eval_secret(monkeypatch):
    secret = "test-eval-run-secret-value"
    monkeypatch.setenv("EVAL_RUN_SECRET", secret)
    get_settings.cache_clear()
    yield secret
    monkeypatch.delenv("EVAL_RUN_SECRET", raising=False)
    get_settings.cache_clear()


def _songs(client):
    return client.get("/api/v1/songs/search?q=night").json()["results"]


def _seed_listening_sessions(db, user_id, song_ids: list[int], *, n_sessions: int = 8) -> None:
    """Insert non-overlapping multi-song sessions with repeating transitions."""
    assert len(song_ids) >= 4
    # Popular path: s0 → s1 → s2 → s3
    path = song_ids[:4]
    cursor = T0
    for s in range(n_sessions):
        sess_songs = path if s % 2 == 0 else [song_ids[i % len(song_ids)] for i in range(s, s + 4)]
        # Dedupe consecutive for variety while keeping length ≥ 2.
        cleaned: list[int] = []
        for sid in sess_songs:
            if not cleaned or cleaned[-1] != sid:
                cleaned.append(sid)
        if len(cleaned) < 2:
            cleaned = path
        for sid in cleaned:
            start = cursor
            end = start + timedelta(seconds=40)
            db.add(
                ListeningEvent(
                    user_id=user_id,
                    song_id=sid,
                    started_at=start,
                    ended_at=end,
                    listened_ms=35_000,
                    song_duration_ms=200_000,
                    completed=True,
                    play_date=start.date(),
                )
            )
            cursor = end + timedelta(seconds=5)
        # Gap between sessions
        cursor += timedelta(minutes=45)
    db.flush()


def test_retrain_endpoint_and_sequential_applied(client, db, eval_secret):
    reg = register(client)
    assert reg.status_code == 201
    client.patch("/api/v1/profile/preferences", json={"preferred_genres": ["electronic", "chillout"]})
    songs = _songs(client)
    song_ids = [s["id"] for s in songs] + _extra_songs(db, 4)
    user = db.scalar(select(User).limit(1))
    assert user is not None
    _seed_listening_sessions(db, user.id, song_ids, n_sessions=10)

    status = client.get("/api/v1/sequential/status")
    assert status.status_code == 200
    body = status.json()
    assert body["history_transitions"] >= MIN_TRANSITIONS
    assert body["history_sessions"] >= MIN_SESSIONS
    assert body["ready"] is False

    denied = client.post("/api/v1/sequential/retrain", json={"activate": True})
    assert denied.status_code == 401

    trained = client.post(
        "/api/v1/sequential/retrain",
        json={"activate": True},
        headers={"X-Eval-Secret": eval_secret},
    )
    assert trained.status_code == 200, trained.text
    payload = trained.json()
    assert payload["activated"] is True
    assert payload["model_id"] > 0
    assert payload["status"]["ready"] is True

    sequential_job.clear_sequential_cache()
    again = client.get("/api/v1/recommendations?limit=5").json()
    assert again["sequential_applied"] is True
    assert "scorer_applied" in again

    active = db.scalar(select(SequentialModelRow).where(SequentialModelRow.is_active.is_(True)))
    assert active is not None
    assert active.n_transitions >= MIN_TRANSITIONS


def test_fallback_when_sequential_model_missing(client):
    register(client, email="seq-fallback@example.com")
    client.patch("/api/v1/profile/preferences", json={"preferred_genres": ["electronic"]})
    sequential_job.clear_sequential_cache()
    body = client.get("/api/v1/recommendations?limit=4").json()
    assert body["sequential_applied"] is False
    assert len(body["items"]) >= 1


def test_retrain_cold_start_message(client, db, eval_secret):
    register(client, email="seq-cold@example.com")
    res = client.post(
        "/api/v1/sequential/retrain",
        headers={"X-Eval-Secret": eval_secret},
        json={"activate": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["activated"] is False
    assert body["model_id"] == 0
    assert "Not enough" in body["message"] or "Need" in body["message"]
