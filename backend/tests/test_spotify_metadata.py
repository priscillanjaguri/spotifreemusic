"""Spotify metadata client + enrichment (mocked HTTP; no real credentials)."""
from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select

from app.models import Artist, MusicProvider, Song, SongArtist, SongFeatures, SongProviderLink
from app.providers.spotify_metadata import SpotifyMetadataClient
from app.services.spotify_enrichment import enrich_song_with_spotify

ALBUM_IMG = "https://i.scdn.co/image/ab67616d0000b273albumcoverdemo01"
ARTIST_IMG = "https://i.scdn.co/image/ab6761610000e5ebartistphotodemo"


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/api/token"):
        return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
    if request.url.path.endswith("/search"):
        return httpx.Response(
            200,
            json={
                "tracks": {
                    "items": [
                        {
                            "id": "sptrack1",
                            "name": "Lilac Hour",
                            "duration_ms": 180_000,
                            "popularity": 42,
                            "artists": [{"id": "spart1", "name": "Violet Sheen"}],
                            "album": {
                                "name": "Demo",
                                "images": [
                                    {"url": ALBUM_IMG, "height": 640, "width": 640},
                                    {"url": "https://i.scdn.co/image/small", "height": 64, "width": 64},
                                ],
                            },
                            "external_ids": {"isrc": "USABC1234567"},
                        }
                    ]
                }
            },
        )
    if request.url.path.endswith("/tracks/sptrack1"):
        return httpx.Response(
            200,
            json={
                "id": "sptrack1",
                "name": "Lilac Hour",
                "duration_ms": 180_000,
                "popularity": 42,
                "artists": [{"id": "spart1", "name": "Violet Sheen"}],
                "album": {
                    "name": "Demo",
                    "images": [{"url": ALBUM_IMG, "height": 640, "width": 640}],
                },
                "external_ids": {"isrc": "USABC1234567"},
            },
        )
    if request.url.path.endswith("/audio-features/sptrack1"):
        return httpx.Response(
            200,
            json={
                "id": "sptrack1",
                "tempo": 118.0,
                "energy": 0.55,
                "danceability": 0.7,
                "acousticness": 0.2,
                "valence": 0.4,
                "instrumentalness": 0.1,
                "loudness": -9.5,
                "key": 5,
                "mode": 1,
            },
        )
    if "/artists/" in request.url.path:
        # Per-id endpoint (batch ?ids= is 403 for some Client Credentials apps).
        return httpx.Response(
            200,
            json={
                "id": "spart1",
                "name": "Violet Sheen",
                "genres": ["lofi", "chillout"],
                "images": [
                    {"url": ARTIST_IMG, "height": 640, "width": 640},
                    {"url": "https://i.scdn.co/image/tiny", "height": 160, "width": 160},
                ],
            },
        )
    if request.url.path.endswith("/artists"):
        return httpx.Response(403, json={"error": {"status": 403, "message": "Forbidden"}})
    return httpx.Response(404, json={"error": "not found"})


@pytest.fixture
def spotify_client():
    client = SpotifyMetadataClient(
        "cid",
        "secret",
        http=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    yield client
    client.close()


def test_spotify_client_search_and_features(spotify_client):
    tracks = spotify_client.search_tracks("Lilac Hour")
    assert len(tracks) == 1 and tracks[0].id == "sptrack1"
    assert tracks[0].album_image_url == ALBUM_IMG
    feats = spotify_client.audio_features("sptrack1")
    assert feats is not None and feats.danceability == 0.7 and feats.tempo == 118.0
    artists = spotify_client.get_artists(["spart1"])
    assert len(artists) == 1 and artists[0].image_url == ARTIST_IMG
    assert artists[0].genres == ("chillout", "lofi")
    genres = spotify_client.artist_genres(["spart1"])
    assert genres == ["chillout", "lofi"]


def test_enrich_song_writes_link_genres_features_and_images(db, spotify_client):
    artist = Artist(name="Violet Sheen", data_source="user_provided")
    song = Song(title="Lilac Hour", duration_ms=180_500, data_source="user_provided")
    song.artist_links.append(SongArtist(artist=artist, position=0))
    db.add(song)
    db.flush()

    assert enrich_song_with_spotify(db, song, client=spotify_client) is True
    db.flush()

    provider = db.scalar(select(MusicProvider).where(MusicProvider.key == "spotify"))
    assert provider is not None and provider.supports_playback is False
    link = db.scalar(select(SongProviderLink).where(SongProviderLink.song_id == song.id))
    assert link is not None and link.provider_track_id == "sptrack1" and link.playback_uri is None

    db.refresh(song)
    db.refresh(artist)
    names = sorted(g.name for g in song.genres)
    assert "lofi" in names and "chillout" in names
    assert song.cover_url == ALBUM_IMG
    assert artist.image_url == ARTIST_IMG

    feats = db.get(SongFeatures, song.id)
    assert feats is not None
    assert feats.danceability == 0.7 and feats.energy == 0.55 and feats.key == 5
    assert feats.analyzer and "spotify" in feats.analyzer


def test_enrich_keeps_existing_cover_and_fills_artist_image(db, spotify_client):
    artist = Artist(name="Violet Sheen", data_source="user_provided")
    song = Song(
        title="Lilac Hour",
        duration_ms=180_500,
        data_source="user_provided",
        cover_url="/api/v1/library/1/cover",
    )
    song.artist_links.append(SongArtist(artist=artist, position=0))
    db.add(song)
    db.flush()

    assert enrich_song_with_spotify(db, song, client=spotify_client) is True
    db.refresh(song)
    db.refresh(artist)
    assert song.cover_url == "/api/v1/library/1/cover"
    assert artist.image_url == ARTIST_IMG


def test_enrich_falls_back_to_artist_image_when_no_album_art(db):
    def no_album_art(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if request.url.path.endswith("/search"):
            return httpx.Response(
                200,
                json={
                    "tracks": {
                        "items": [
                            {
                                "id": "sptrack1",
                                "name": "Lilac Hour",
                                "duration_ms": 180_000,
                                "artists": [{"id": "spart1", "name": "Violet Sheen"}],
                                "album": {"name": "Demo", "images": []},
                                "external_ids": {},
                            }
                        ]
                    }
                },
            )
        if "/artists/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "id": "spart1",
                    "name": "Violet Sheen",
                    "genres": [],
                    "images": [{"url": ARTIST_IMG, "height": 640, "width": 640}],
                },
            )
        if "/audio-features/" in request.url.path:
            return httpx.Response(403, json={"error": "forbidden"})
        return httpx.Response(404)

    client = SpotifyMetadataClient(
        "cid", "secret", http=httpx.Client(transport=httpx.MockTransport(no_album_art))
    )
    artist = Artist(name="Violet Sheen", data_source="user_provided")
    song = Song(title="Lilac Hour", duration_ms=180_000, data_source="user_provided")
    song.artist_links.append(SongArtist(artist=artist, position=0))
    db.add(song)
    db.flush()
    assert enrich_song_with_spotify(db, song, client=client) is True
    db.refresh(song)
    db.refresh(artist)
    assert artist.image_url == ARTIST_IMG
    assert song.cover_url == ARTIST_IMG
    client.close()


def test_enrich_skips_when_no_good_match(db):
    def empty_search(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"tracks": {"items": []}})
        return httpx.Response(404)

    client = SpotifyMetadataClient(
        "cid", "secret", http=httpx.Client(transport=httpx.MockTransport(empty_search))
    )
    song = Song(title="Totally Unknown XYZ", duration_ms=120_000, data_source="user_provided")
    db.add(song)
    db.flush()
    assert enrich_song_with_spotify(db, song, client=client) is False
    client.close()


def test_library_spotify_enrich_endpoint_requires_spotify(client, db):
    from app.core.config import get_settings
    from app.main import app
    from tests.conftest import register

    register(client)
    settings = get_settings().model_copy(update={"spotify_client_id": None, "spotify_client_secret": None})
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        res = client.post("/api/v1/library/spotify-enrich")
        assert res.status_code == 503
        assert res.json()["detail"]["code"] == "spotify_not_configured"
    finally:
        app.dependency_overrides.pop(get_settings, None)
