from datetime import datetime, timedelta, timezone

from tests.conftest import register


def search(client, q="night"):
    return client.get(f"/api/v1/songs/search?q={q}")


def test_recommendations_cold_start_and_feedback_exclusion(client):
    register(client)
    songs = search(client).json()["results"]
    assert len(songs) >= 2
    a, b = songs[0], songs[1]

    # Seed preferred genres so cold start has something to latch onto.
    prefs = client.patch("/api/v1/profile/preferences", json={"preferred_genres": ["electronic", "chillout"]})
    assert prefs.status_code == 200
    assert prefs.json()["preferred_genres"] == ["chillout", "electronic"]

    reco = client.get("/api/v1/recommendations?limit=10")
    assert reco.status_code == 200
    body = reco.json()
    assert body["cold_start"] is True
    assert body["mode"] in {"genre_seed", "popular"}
    assert len(body["items"]) >= 1
    assert "explanations" in body["items"][0]

    # Like one, hide the other.
    like = client.post("/api/v1/feedback", json={"song_id": a["id"], "action": "like"})
    assert like.status_code == 200 and like.json()["interaction_type"] == "interested"
    hide = client.post("/api/v1/feedback", json={"song_id": b["id"], "action": "not_interested"})
    assert hide.status_code == 200 and hide.json()["interaction_type"] == "not_interested"

    again = client.get("/api/v1/recommendations?limit=10").json()
    ids = [i["song"]["id"] for i in again["items"]]
    assert b["id"] not in ids


def test_similar_songs_and_listening_events(client):
    register(client)
    song = search(client).json()["results"][0]
    similar = client.get(f"/api/v1/songs/{song['id']}/similar?limit=5")
    assert similar.status_code == 200
    body = similar.json()
    assert body["mode"] == "similar"
    assert all(i["song"]["id"] != song["id"] for i in body["items"])

    start = datetime.now(timezone.utc) - timedelta(seconds=40)
    end = datetime.now(timezone.utc)
    event = client.post(
        "/api/v1/listening/events",
        json={
            "song_id": song["id"],
            "started_at": start.isoformat(),
            "ended_at": end.isoformat(),
            "listened_ms": 35_000,
            "song_duration_ms": song["duration_ms"],
            "completed": False,
            "client_session_id": "test-session-1",
        },
    )
    assert event.status_code == 201
    assert event.json()["song_id"] == song["id"]
    assert event.json()["listened_ms"] == 35_000

    # Overlapping event must be rejected by the exclusion constraint / service.
    overlap = client.post(
        "/api/v1/listening/events",
        json={
            "song_id": song["id"],
            "started_at": (start + timedelta(seconds=5)).isoformat(),
            "ended_at": (end + timedelta(seconds=5)).isoformat(),
            "listened_ms": 10_000,
            "song_duration_ms": song["duration_ms"],
            "client_session_id": "test-session-1",
        },
    )
    assert overlap.status_code == 422


def test_recommendations_require_auth(client):
    assert client.get("/api/v1/recommendations").status_code == 401
    assert client.post("/api/v1/feedback", json={"song_id": 1, "action": "like"}).status_code == 401
