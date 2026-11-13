"""Spotify metadata client + enrichment (mocked HTTP; no real credentials)."""
from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select

from app.models import Artist, Genre, MusicProvider, Song, SongArtist, SongFeatures, SongProviderLink
from app.providers.spotify_metadata import SpotifyMetadataClient
from app.services.spotify_enrichment import enrich_song_with_spotify


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
                            "album": {"name": "Demo"},
                            "external_ids": {"isrc": "USABC1234567"},
                        }
                    ]
                }
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
    if request.url.path.endswith("/artists"):
        return httpx.Response(
            200,
            json={"artists": [{"id": "spart1", "name": "Violet Sheen", "genres": ["lofi", "chillout"]}]},
        )
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
    feats = spotify_client.audio_features("sptrack1")
    assert feats is not None and feats.danceability == 0.7 and feats.tempo == 118.0
    genres = spotify_client.artist_genres(["spart1"])
    assert genres == ["chillout", "lofi"]


def test_enrich_song_writes_link_genres_and_features(db, spotify_client):
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
    names = sorted(g.name for g in song.genres)
    assert "lofi" in names and "chillout" in names

    feats = db.get(SongFeatures, song.id)
    assert feats is not None
    assert feats.danceability == 0.7 and feats.energy == 0.55 and feats.key == 5
    assert feats.analyzer and "spotify" in feats.analyzer


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
