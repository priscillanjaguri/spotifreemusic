"""API + DB integration for impressions, labels, retrain, and scorer re-ranking."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.ml.scorer import MIN_LABELED_SAMPLES, build_song_features
from app.models import RecommendationImpression, ScorerModel, User
from app.services import scorer_job
from tests.conftest import register


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


def _seed_labeled_impressions(db, user_id, songs, n: int = MIN_LABELED_SAMPLES) -> None:
    request_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    for i in range(n):
        sid = songs[i % len(songs)]["id"]
        feat = build_song_features(
            cosine_score=0.15 + (i % 10) * 0.08,
            song_genres=["electronic"] if i % 2 == 0 else ["rock"],
            profile_genres=["electronic", "chillout"],
            from_library=False,
            energy=0.4 + 0.05 * (i % 5),
            tempo=90 + i,
            user_plays=i % 3,
            days_since_play=float(i % 40),
        )
        db.add(
            RecommendationImpression(
                user_id=user_id,
                song_id=sid,
                request_id=request_id,
                position=i,
                shown_at=now - timedelta(minutes=i + 1),
                cosine_score=feat["cosine_score"],
                features=feat,
                label=1 if i % 2 == 0 else 0,
                labeled_at=now,
                label_source="like" if i % 2 == 0 else "hide",
            )
        )
    db.flush()


def test_recommendations_log_impressions_and_feedback_labels(client, db):
    register(client)
    client.patch("/api/v1/profile/preferences", json={"preferred_genres": ["electronic", "chillout"]})
    songs = _songs(client)
    assert len(songs) >= 2

    reco = client.get("/api/v1/recommendations?limit=5")
    assert reco.status_code == 200
    body = reco.json()
    assert body["scorer_applied"] is False
    assert len(body["items"]) >= 1

    impressions = list(db.scalars(select(RecommendationImpression)).all())
    assert len(impressions) == len(body["items"])
    assert all(row.label is None for row in impressions)
    assert all("cosine_score" in (row.features or {}) for row in impressions)

    liked = body["items"][0]["song"]["id"]
    impressed_ids = [row.song_id for row in impressions]
    hide_id = next((sid for sid in impressed_ids if sid != liked), None)

    assert client.post("/api/v1/feedback", json={"song_id": liked, "action": "like"}).status_code == 200
    if hide_id is not None:
        assert (
            client.post("/api/v1/feedback", json={"song_id": hide_id, "action": "not_interested"}).status_code
            == 200
        )

    db.expire_all()
    labeled = list(
        db.scalars(select(RecommendationImpression).where(RecommendationImpression.label.is_not(None))).all()
    )
    assert any(row.label == 1 and row.label_source == "like" for row in labeled)
    if hide_id is not None:
        assert any(row.label == 0 and row.label_source == "hide" for row in labeled)


def test_listening_labels_impressions(client, db):
    register(client)
    client.patch("/api/v1/profile/preferences", json={"preferred_genres": ["electronic"]})
    reco = client.get("/api/v1/recommendations?limit=3").json()
    song_id = reco["items"][0]["song"]["id"]
    duration = reco["items"][0]["song"]["duration_ms"]

    listened_ms = int(duration * 0.8)
    start = datetime.now(timezone.utc) - timedelta(milliseconds=listened_ms + 5_000)
    end = datetime.now(timezone.utc)
    event = client.post(
        "/api/v1/listening/events",
        json={
            "song_id": song_id,
            "started_at": start.isoformat(),
            "ended_at": end.isoformat(),
            "listened_ms": listened_ms,
            "song_duration_ms": duration,
            "completed": True,
            "client_session_id": "scorer-listen-1",
        },
    )
    assert event.status_code == 201
    db.expire_all()
    row = db.scalar(
        select(RecommendationImpression)
        .where(
            RecommendationImpression.song_id == song_id,
            RecommendationImpression.label == 1,
        )
        .limit(1)
    )
    assert row is not None
    assert row.label_source in {"play", "complete"}


def test_retrain_endpoint_and_scorer_applied(client, db, eval_secret):
    reg = register(client)
    assert reg.status_code == 201
    client.patch("/api/v1/profile/preferences", json={"preferred_genres": ["electronic", "chillout"]})
    songs = _songs(client)
    user = db.scalar(select(User).limit(1))
    assert user is not None
    _seed_labeled_impressions(db, user.id, songs)

    status = client.get("/api/v1/scorer/status")
    assert status.status_code == 200
    assert status.json()["labeled_impressions"] >= MIN_LABELED_SAMPLES
    assert status.json()["ready"] is False

    denied = client.post("/api/v1/scorer/retrain", json={"activate": True})
    assert denied.status_code == 401

    trained = client.post(
        "/api/v1/scorer/retrain",
        json={"activate": True},
        headers={"X-Eval-Secret": eval_secret},
    )
    assert trained.status_code == 200, trained.text
    payload = trained.json()
    assert payload["activated"] is True
    assert payload["model_id"] > 0
    assert payload["status"]["ready"] is True

    scorer_job.clear_scorer_cache()
    again = client.get("/api/v1/recommendations?limit=5").json()
    assert again["scorer_applied"] is True

    active = db.scalar(select(ScorerModel).where(ScorerModel.is_active.is_(True)))
    assert active is not None
    assert active.n_samples >= MIN_LABELED_SAMPLES


def test_fallback_when_model_missing(client):
    register(client, email="fallback@example.com")
    client.patch("/api/v1/profile/preferences", json={"preferred_genres": ["electronic"]})
    scorer_job.clear_scorer_cache()
    body = client.get("/api/v1/recommendations?limit=4").json()
    assert body["scorer_applied"] is False
    assert len(body["items"]) >= 1


def test_retrain_cold_start_message(client, db, eval_secret):
    register(client, email="cold@example.com")
    res = client.post(
        "/api/v1/scorer/retrain",
        headers={"X-Eval-Secret": eval_secret},
        json={"activate": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["activated"] is False
    assert body["model_id"] == 0
    assert "Not enough" in body["message"] or "Need" in body["message"]
