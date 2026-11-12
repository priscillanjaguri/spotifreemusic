"""Stage 5: listening analytics, taste timeline, memory lane, privacy."""
from datetime import datetime, timedelta, timezone

from tests.conftest import register


def _search(client, q="night"):
    return client.get(f"/api/v1/songs/search?q={q}").json()["results"]


def _listen(client, song, *, start, listened_ms=30_000, completed=True, session="s1"):
    end = start + timedelta(milliseconds=listened_ms + 500)
    return client.post(
        "/api/v1/listening/events",
        json={
            "song_id": song["id"],
            "started_at": start.isoformat(),
            "ended_at": end.isoformat(),
            "listened_ms": listened_ms,
            "song_duration_ms": song["duration_ms"],
            "completed": completed,
            "client_session_id": session,
        },
    )


def test_weekly_analytics_and_privacy_off(client):
    register(client)
    songs = _search(client)
    a, b = songs[0], songs[1]
    now = datetime.now(timezone.utc)

    assert _listen(client, a, start=now - timedelta(minutes=10), session="a1").status_code == 201
    assert _listen(client, a, start=now - timedelta(minutes=5), session="a1", completed=False).status_code == 201
    assert _listen(client, b, start=now - timedelta(minutes=2), session="a1").status_code == 201

    week = client.get("/api/v1/analytics?period=week")
    assert week.status_code == 200
    body = week.json()
    assert body["period"] == "week"
    assert body["play_count"] == 3
    assert body["unique_songs"] == 2
    assert body["total_listened_ms"] == 90_000
    assert body["completion_rate"] is not None
    assert body["top_songs"][0]["song"]["id"] == a["id"]
    assert len(body["daily"]) == 7
    assert body["top_artists"]
    assert body["top_genres"]

    month = client.get("/api/v1/analytics?period=month&offset=0")
    assert month.status_code == 200
    assert month.json()["play_count"] >= 3

    # Privacy off → no new events stored (201 with null body).
    prefs = client.patch("/api/v1/profile/preferences", json={"record_listening_history": False})
    assert prefs.status_code == 200 and prefs.json()["record_listening_history"] is False
    quiet = _listen(client, b, start=now + timedelta(minutes=1), session="a1")
    assert quiet.status_code == 201
    assert quiet.json() is None
    assert client.get("/api/v1/analytics?period=week").json()["play_count"] == 3


def test_delete_listening_history(client):
    register(client, email="history@example.com")
    song = _search(client)[0]
    now = datetime.now(timezone.utc)
    assert _listen(client, song, start=now - timedelta(minutes=3), session="h1").status_code == 201
    assert client.get("/api/v1/analytics?period=week").json()["play_count"] == 1

    deleted = client.delete("/api/v1/listening/history")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_events"] == 1
    assert deleted.json()["deleted_sessions"] >= 1
    assert client.get("/api/v1/analytics?period=week").json()["play_count"] == 0


def test_taste_timeline_and_memory_lane(client):
    register(client, email="timeline@example.com")
    songs = _search(client)
    a, b = songs[0], songs[1]
    now = datetime.now(timezone.utc)

    assert _listen(client, a, start=now - timedelta(days=21), session="t1").status_code == 201
    assert _listen(client, a, start=now - timedelta(days=2), session="t1").status_code == 201
    assert _listen(client, b, start=now - timedelta(hours=1), session="t1").status_code == 201
    client.post("/api/v1/feedback", json={"song_id": a["id"], "action": "like"})
    client.post("/api/v1/collection", json={"song_id": b["id"], "source": "manual"})

    timeline = client.get("/api/v1/analytics/taste-timeline?weeks=8")
    assert timeline.status_code == 200
    tl = timeline.json()
    assert len(tl["weeks"]) == 8
    assert any(w["play_count"] > 0 for w in tl["weeks"])
    kinds = {m["kind"] for m in tl["milestones"]}
    assert "first_listen" in kinds
    assert "first_like" in kinds or "first_save" in kinds

    lane = client.get("/api/v1/analytics/memory-lane")
    assert lane.status_code == 200
    items = lane.json()["items"]
    assert items
    assert any(i["kind"] in {"rediscovered", "most_replayed", "first_save", "first_like", "flashback", "on_this_day"} for i in items)


def test_analytics_requires_auth(client):
    assert client.get("/api/v1/analytics").status_code == 401
    assert client.delete("/api/v1/listening/history").status_code == 401
