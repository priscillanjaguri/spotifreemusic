"""Eval dashboard API: public reads + secret-gated run."""
from __future__ import annotations

import os

import pytest

from app.core.config import get_settings
from app.models import EvalSnapshot
from app.services import eval_job


@pytest.fixture()
def eval_secret(monkeypatch):
    secret = "test-eval-run-secret-value"
    monkeypatch.setenv("EVAL_RUN_SECRET", secret)
    get_settings.cache_clear()
    yield secret
    monkeypatch.delenv("EVAL_RUN_SECRET", raising=False)
    get_settings.cache_clear()


def test_summary_empty(client):
    res = client.get("/api/v1/eval/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["latest"] is None
    assert "precision_at_k" in body["metric_blurbs"]
    assert "cosine" in body["ranking_blurb"].lower()
    assert body["schedule"]["due"] is True


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
    assert "precision_at_k" in snap["metrics"]
    assert "listening_events" in snap["data_volume"]
    assert "interested" in snap["feedback_counts"]

    summary = client.get("/api/v1/eval/summary").json()
    assert summary["latest"]["id"] == snap["id"]
    assert summary["latest"]["metrics"]["precision_at_k"] == snap["metrics"]["precision_at_k"]

    listed = client.get("/api/v1/eval/snapshots").json()
    assert listed["total"] >= 1
    assert listed["items"][0]["id"] == snap["id"]


def test_eval_job_persists_volume(db):
    snap = eval_job.run_eval(db, force_synthetic=True)
    db.flush()
    assert isinstance(snap, EvalSnapshot)
    assert snap.source == "synthetic"
    assert snap.data_volume["users"] >= 0
    assert eval_job.latest_snapshot(db).id == snap.id
