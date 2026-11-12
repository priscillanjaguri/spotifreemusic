from tests.conftest import register


def search(client, q="night"):
    return client.get(f"/api/v1/songs/search?q={q}")


def test_endpoints_require_login(client):
    assert search(client).status_code == 401
    assert client.get("/api/v1/collection").status_code == 401


def test_search_imports_provider_tracks_into_catalogue(client):
    register(client)
    res = search(client)
    assert res.status_code == 200
    first, collab = res.json()["results"]
    assert first["title"] == "Night Drive" and first["genres"] == ["chillout", "electronic"]
    assert first["album"]["title"] == "Glow" and first["data_source"] == "provider"
    assert first["playback"] == {"provider": "fake", "stream_url": "http://stream/1.mp3", "license_url": "http://cc/by"}
    assert [a["name"] for a in collab["artists"]] == ["Neon Cat", "Dusty Fox"]  # collaboration keeps both artists
    # Searching again must not create duplicates, and the shared artist is one row.
    again = search(client).json()["results"]
    assert [s["id"] for s in again] == [first["id"], collab["id"]]
    assert first["artists"][0]["id"] == collab["artists"][0]["id"]


def test_song_detail_and_missing_song(client):
    register(client)
    song_id = search(client).json()["results"][0]["id"]
    assert client.get(f"/api/v1/songs/{song_id}").json()["title"] == "Night Drive"
    assert client.get("/api/v1/songs/999999").status_code == 404


def test_search_validates_input(client):
    register(client)
    assert client.get("/api/v1/songs/search?q=a").status_code == 422
    assert client.get("/api/v1/songs/search?q=ok&limit=500").status_code == 422


def test_unconfigured_provider_is_reported_clearly(client):
    from app.main import app
    from app.providers.registry import get_music_provider
    register(client)
    app.dependency_overrides[get_music_provider] = lambda: None
    res = search(client)
    assert res.status_code == 503 and res.json()["detail"]["code"] == "provider_not_configured"


def test_provider_failure_returns_502_not_a_crash(client, provider):
    register(client)
    provider.fail = True
    res = search(client)
    assert res.status_code == 502 and res.json()["detail"]["code"] == "provider_error"


def test_add_list_filter_remove(client):
    register(client)
    one, collab = search(client).json()["results"]
    assert client.post("/api/v1/collection", json={"song_id": one["id"], "source": "search"}).status_code == 201
    assert client.post("/api/v1/collection", json={"song_id": collab["id"]}).status_code == 201
    assert client.post("/api/v1/collection", json={"song_id": one["id"]}).status_code == 409
    assert client.post("/api/v1/collection", json={"song_id": 999999}).status_code == 404

    page = client.get("/api/v1/collection").json()
    assert page["total"] == 2 and page["items"][0]["song"]["title"] == "Collab Song"  # newest first

    neon = one["artists"][0]["id"]
    fox = collab["artists"][1]["id"]
    assert client.get(f"/api/v1/collection?artist_id={neon}").json()["total"] == 2
    assert client.get(f"/api/v1/collection?artist_id={fox}").json()["total"] == 1
    assert client.get("/api/v1/collection?genre=Rock").json()["total"] == 1       # case-insensitive
    assert client.get(f"/api/v1/collection?album_id={one['album']['id']}").json()["total"] == 1
    assert client.get("/api/v1/collection?genre=jazz").json()["total"] == 0

    facets = client.get("/api/v1/collection/facets").json()
    assert {a["name"]: a["count"] for a in facets["artists"]} == {"Neon Cat": 2, "Dusty Fox": 1}
    assert {g["name"] for g in facets["genres"]} == {"chillout", "electronic", "rock"}

    assert client.delete(f"/api/v1/collection/{one['id']}").status_code == 204
    assert client.delete(f"/api/v1/collection/{one['id']}").status_code == 404
    assert client.get("/api/v1/collection").json()["total"] == 1


def test_collections_are_private_between_users(client):
    register(client, "ada@example.com")
    song_id = search(client).json()["results"][0]["id"]
    client.post("/api/v1/collection", json={"song_id": song_id})
    client.post("/api/v1/auth/logout")
    register(client, "grace@example.com", name="Grace")
    assert client.get("/api/v1/collection").json()["total"] == 0
    assert client.delete(f"/api/v1/collection/{song_id}").status_code == 404  # can't remove Ada's entry
