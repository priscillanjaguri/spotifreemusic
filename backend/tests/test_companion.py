"""Stage 6: daily companion."""
from datetime import datetime, timedelta, timezone

from tests.conftest import register


def test_daily_companion_with_and_without_mood(client):
    register(client, email="companion@example.com")
    songs = client.get("/api/v1/songs/search?q=night").json()["results"]
    song = songs[0]
    start = datetime.now(timezone.utc) - timedelta(minutes=8)
    client.post(
        "/api/v1/listening/events",
        json={
            "song_id": song["id"],
            "started_at": start.isoformat(),
            "ended_at": (start + timedelta(seconds=40)).isoformat(),
            "listened_ms": 35_000,
            "song_duration_ms": song["duration_ms"],
            "completed": True,
            "client_session_id": "c1",
        },
    )
    client.patch("/api/v1/profile/preferences", json={"preferred_genres": ["electronic", "chillout"]})

    daily = client.get("/api/v1/companion/daily?limit=8")
    assert daily.status_code == 200
    body = daily.json()
    assert body["greeting"]
    assert body["briefing"]
    assert body["available_moods"]
    assert body["insights"]
    assert len(body["playlist"]) >= 1
    assert body["date"]

    soft = client.post("/api/v1/companion/daily?limit=6", json={"mood": "soft"})
    assert soft.status_code == 200
    assert soft.json()["mood"] == "soft"
    assert len(soft.json()["playlist"]) >= 1

    bad = client.get("/api/v1/companion/daily?mood=angry")
    assert bad.status_code == 422


def test_companion_requires_auth(client):
    assert client.get("/api/v1/companion/daily").status_code == 401
