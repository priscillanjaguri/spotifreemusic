"""Eval dashboard API: public reads + secret-gated run + online impression metrics."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import get_settings
from app.models import Artist, EvalSnapshot, RecommendationImpression, Song, SongArtist, User
from app.services import eval_job, online_eval
from app.services.eval_job import SOURCE_LABELS
from tests.conftest import register


@pytest.fixture()
def eval_secret(monkeypatch):
    secret = "test-eval-run-secret-value"
    monkeypatch.setenv("EVAL_RUN_SECRET", secret)
    get_settings.cache_clear()
    yield secret
    monkeypatch.delenv("EVAL_RUN_SECRET", raising=False)
    get_settings.cache_clear()


def _make_song(db, title: str = "Eval Track") -> Song:
    artist = Artist(name="Eval Artist", data_source="mock_dev")
    song = Song(title=title, duration_ms=180_000, data_source="mock_dev")
    song.artist_links.append(SongArtist(artist=artist, position=0))
    db.add(song)
    db.flush()
    return song


def _seed_impressions(db, user_id, *, n_pos: int = 4, n_neg: int = 2) -> None:
    now = datetime.now(timezone.utc)
    request_id = uuid.uuid4()
    songs = [_make_song(db, title=f"Imp {i}") for i in range(n_pos + n_neg)]
    for i, song in enumerate(songs):
        label = 1 if i < n_pos else 0
        source = "like" if label == 1 and i % 2 == 0 else ("play" if label == 1 else "skip")
        db.add(
            RecommendationImpression(
                user_id=user_id,
                song_id=song.id,
                request_id=request_id,
                position=i,
                shown_at=now - timedelta(hours=i + 1),
                cosine_score=0.5,
                features={"cosine_score": 0.5},
                label=label,
                labeled_at=now - timedelta(minutes=i + 1),
                label_source=source,
            )
        )
    db.flush()


def test_summary_empty(client):
    res = client.get("/api/v1/eval/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["latest"] is None
    assert "precision_at_k" in body["metric_blurbs"]
    assert "engage_rate" in body["metric_blurbs"]
    assert "cosine" in body["ranking_blurb"].lower() or "taste" in body["ranking_blurb"].lower()
    assert body["schedule"]["due"] is True
    assert body["online"] is not None
    assert body["online"]["ready"] is False
    assert body["holdout"]["preferred_source"] in ("holdout", "synthetic")
    assert body["source_labels"]["synthetic"] == SOURCE_LABELS["synthetic"]


def test_status_endpoint(client, eval_secret):
    res = client.get("/api/v1/eval/status")
    assert res.status_code == 200
    body = res.json()
    assert body["latest_id"] is None
    assert body["run_secret_configured"] is True
    assert "metrics" in body["online"]
    assert body["holdout"]["min_positives"] >= 1


def test_snapshots_empty(client):
    res = client.get("/api/v1/eval/snapshots")
    assert res.status_code == 200
    assert res.json() == {"items": [], "total": 0}


def test_run_requires_secret(client, monkeypatch):
    monkeypatch.delenv("EVAL_RUN_SECRET", raising=False)
    get_settings.cache_clear()
    res = client.post("/api/v1/eval/run", json={})
    assert res.status_code == 503
    get_settings.cache_clear()


def test_run_rejects_bad_secret(client, eval_secret):
    res = client.post("/api/v1/eval/run", json={"secret": "wrong", "force_synthetic": True})
    assert res.status_code == 401


def test_run_and_read_snapshot(client, eval_secret, db):
    res = client.post(
        "/api/v1/eval/run",
        headers={"X-Eval-Secret": eval_secret},
        json={"force_synthetic": True, "k": 10},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    snap = payload["snapshot"]
    assert snap["source"] == "synthetic"
    assert snap["source_label"] == SOURCE_LABELS["synthetic"]
    assert "precision_at_k" in snap["metrics"]
    assert "engage_rate" in snap["metrics"]
    assert "listening_events" in snap["data_volume"]
    assert "impressions_shown" in snap["data_volume"]
    assert "interested" in snap["feedback_counts"]
    assert "synthetic" in payload["message"].lower() or "fallback" in payload["message"].lower()

    summary = client.get("/api/v1/eval/summary").json()
    assert summary["latest"]["id"] == snap["id"]
    assert summary["latest"]["metrics"]["precision_at_k"] == snap["metrics"]["precision_at_k"]
    assert summary["latest"]["source_label"]

    listed = client.get("/api/v1/eval/snapshots").json()
    assert listed["total"] >= 1
    assert listed["items"][0]["id"] == snap["id"]


def test_online_metrics_from_impressions(client, eval_secret, db):
    register(client, email="eval-online@example.com")
    from sqlalchemy import select

    user = db.scalar(select(User).where(User.email == "eval-online@example.com"))
    assert user is not None
    _seed_impressions(db, user.id, n_pos=4, n_neg=2)
    db.flush()

    live = online_eval.collect_online_metrics(db)
    assert live["impressions_labeled"] == 6.0
    assert live["engage_rate"] == pytest.approx(4 / 6)
    assert live["skip_rate"] > 0

    summary = client.get("/api/v1/eval/summary").json()
    assert summary["online"]["ready"] is True
    assert summary["online"]["metrics"]["engage_rate"] == pytest.approx(4 / 6)
    assert summary["online"]["label_sources"]["skip"] >= 1
    assert len(summary["online"]["series"]) >= 1

    res = client.post(
        "/api/v1/eval/run",
        headers={"X-Eval-Secret": eval_secret},
        json={"force_synthetic": True},
    )
    assert res.status_code == 200
    snap = res.json()["snapshot"]
    # Offline fold may be synthetic, but online rates come from real impressions.
    assert snap["source"] == "synthetic"
    assert snap["metrics"]["engage_rate"] == pytest.approx(4 / 6)
    assert snap["data_volume"]["impressions_labeled"] == 6


def test_eval_job_persists_volume(db):
    snap = eval_job.run_eval(db, force_synthetic=True)
    db.flush()
    assert isinstance(snap, EvalSnapshot)
    assert snap.source == "synthetic"
    assert snap.data_volume["users"] >= 0
    assert "engage_rate" in snap.metrics
    assert eval_job.latest_snapshot(db).id == snap.id


def test_build_status_includes_secret_flag(db, eval_secret):
    status = eval_job.build_status(db)
    assert status["run_secret_configured"] is True
    assert status["holdout"]["preferred_source"] in ("holdout", "synthetic")
    assert "engage_rate" in status["online"]["metrics"]
