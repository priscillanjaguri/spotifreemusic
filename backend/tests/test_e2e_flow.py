"""Stage 7: end-to-end flow covering auth → search → collect → play → feedback →
recommendations → analytics → companion → privacy wipe.
"""
from datetime import datetime, timedelta, timezone

from tests.conftest import register


def test_full_product_flow(client):
    # Auth
    reg = register(client, email="e2e@example.com", password="correct-horse-battery", name="E2E Ada")
    assert reg.status_code == 201
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "e2e@example.com"

    # Search (provider) + save
    search = client.get("/api/v1/songs/search?q=velvet")
    assert search.status_code == 200
    songs = search.json()["results"]
    assert len(songs) >= 2
    a, b = songs[0], songs[1]

    saved = client.post("/api/v1/collection", json={"song_id": a["id"], "source": "search"})
    assert saved.status_code == 201

    # Preferences / seed genres
    prefs = client.patch(
        "/api/v1/profile/preferences",
        json={"preferred_genres": ["electronic", "lofi"], "timezone": "UTC"},
    )
    assert prefs.status_code == 200

    # Listening (player segments)
    now = datetime.now(timezone.utc)
    for i, song in enumerate((a, a, b)):
        start = now - timedelta(minutes=30 - i * 8)
        resp = client.post(
            "/api/v1/listening/events",
            json={
                "song_id": song["id"],
                "started_at": start.isoformat(),
                "ended_at": (start + timedelta(seconds=45)).isoformat(),
                "listened_ms": 40_000,
                "song_duration_ms": song["duration_ms"],
                "completed": i < 2,
                "client_session_id": "e2e-session",
            },
        )
        assert resp.status_code == 201, resp.text

    # Feedback
    like = client.post(
        "/api/v1/feedback",
        json={"song_id": a["id"], "action": "like", "context": "discover"},
    )
    assert like.status_code == 200

    # Recommendations
    reco = client.get("/api/v1/recommendations?limit=10")
    assert reco.status_code == 200
    assert len(reco.json()["items"]) >= 1

    similar = client.get(f"/api/v1/songs/{a['id']}/similar?limit=5")
    assert similar.status_code == 200

    # Analytics surfaces
    week = client.get("/api/v1/analytics?period=week")
    assert week.status_code == 200
    assert week.json()["play_count"] == 3
    assert week.json()["unique_songs"] == 2

    timeline = client.get("/api/v1/analytics/taste-timeline?weeks=4")
    assert timeline.status_code == 200
    assert len(timeline.json()["weeks"]) == 4

    lane = client.get("/api/v1/analytics/memory-lane")
    assert lane.status_code == 200

    # Daily companion
    companion = client.get("/api/v1/companion/daily?mood=chill&limit=8")
    assert companion.status_code == 200
    body = companion.json()
    assert body["mood"] == "chill"
    assert body["playlist"]
    assert body["insights"]

    # Collection from companion context
    pick = body["playlist"][0]["song"]["id"]
    if pick != a["id"]:
        add = client.post(
            "/api/v1/collection",
            json={"song_id": pick, "source": "daily_companion"},
        )
        assert add.status_code in (201, 409)

    # Privacy wipe
    wiped = client.delete("/api/v1/listening/history")
    assert wiped.status_code == 200
    assert wiped.json()["deleted_events"] == 3
    assert client.get("/api/v1/analytics?period=week").json()["play_count"] == 0

    # Explicit feedback / collection survive the wipe
    assert client.get("/api/v1/collection").json()["total"] >= 1
    again = client.get("/api/v1/recommendations?limit=5")
    assert again.status_code == 200
