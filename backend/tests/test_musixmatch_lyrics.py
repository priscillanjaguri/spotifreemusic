"""Musixmatch client + lyrics service fallback (mocked HTTP; no network)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from app.models import Artist, Song, SongArtist
from app.providers.base import ProviderError
from app.providers.lyrics_mock import LocalLyricsFallback
from app.providers.musixmatch import MusixmatchClient, _clean_lyrics_body
from app.services.lyrics import (
    clear_lyrics_cache,
    get_lyrics_for_song,
    reset_lyrics_clients,
)


def _mxm_payload(status: int, body: str | None) -> dict:
    lyrics = None
    if body is not None:
        lyrics = {
            "lyrics_id": 42,
            "lyrics_body": body,
            "lyrics_copyright": "Lyrics powered by www.musixmatch.com",
        }
    return {
        "message": {
            "header": {"status_code": status},
            "body": {"lyrics": lyrics} if lyrics is not None else {},
        }
    }


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    params = dict(request.url.params)
    if not path.endswith("/matcher.lyrics.get"):
        return httpx.Response(404, json={"error": "not found"})
    if params.get("apikey") == "bad-key":
        return httpx.Response(200, json=_mxm_payload(401, None))
    if params.get("q_track") == "Missing":
        return httpx.Response(200, json=_mxm_payload(404, None))
    body = (
        "Is this the real life?\nIs this just fantasy?\n"
        "...\n\n******* This Lyrics is NOT for Commercial use *******"
    )
    return httpx.Response(200, json=_mxm_payload(200, body))


@pytest.fixture
def mxm_client():
    transport = httpx.MockTransport(_handler)
    client = MusixmatchClient(
        api_key="test-key",
        http=httpx.Client(transport=transport, follow_redirects=True),
    )
    yield client
    client.close()
    clear_lyrics_cache()
    reset_lyrics_clients()


def test_clean_lyrics_strips_commercial_footer():
    raw = "Line one\nLine two\n...\n\n******* This Lyrics is NOT for Commercial use *******"
    assert _clean_lyrics_body(raw) == "Line one\nLine two"


def test_matcher_hit(mxm_client: MusixmatchClient):
    hit = mxm_client.get_lyrics("Bohemian Rhapsody", "Queen")
    assert hit is not None
    assert "real life" in hit.plain_lyrics
    assert "Commercial use" not in hit.plain_lyrics
    assert hit.lyrics_id == 42


def test_matcher_miss(mxm_client: MusixmatchClient):
    assert mxm_client.get_lyrics("Missing", "Nobody") is None


def test_matcher_unauthorized():
    transport = httpx.MockTransport(_handler)
    client = MusixmatchClient(
        api_key="bad-key",
        http=httpx.Client(transport=transport, follow_redirects=True),
    )
    try:
        with pytest.raises(ProviderError, match="unauthorized"):
            client.get_lyrics("Anything", "Anyone")
    finally:
        client.close()


def test_local_mock_allowlist():
    mock = LocalLyricsFallback()
    hit = mock.get_lyrics("Demo Mock Anthem", "Spotifree Mock")
    assert hit is not None
    assert "local mock lyric" in hit.plain_lyrics.lower()
    assert mock.get_lyrics("Unknown", "Nobody") is None


def _make_song(db, title: str, artist_name: str) -> Song:
    artist = Artist(name=artist_name)
    song = Song(title=title, duration_ms=200_000, data_source="mock_dev")
    song.artist_links.append(SongArtist(artist=artist, position=0))
    db.add(song)
    db.flush()
    return song


def test_service_falls_back_to_musixmatch(db, monkeypatch):
    clear_lyrics_cache()
    reset_lyrics_clients()
    song = _make_song(db, "Fallback Hit", "Demo Artist")
    user_id = SimpleNamespace()  # public catalogue song — owner check skipped via None owner

    monkeypatch.setattr(
        "app.services.lyrics._try_lrclib",
        lambda *a, **k: None,
    )

    class _Hit:
        plain_lyrics = "Fallback verse from Musixmatch"
        title = "Fallback Hit"
        artist = "Demo Artist"

    fake_client = MagicMock()
    fake_client.get_lyrics.return_value = _Hit()
    monkeypatch.setattr("app.services.lyrics._get_musixmatch", lambda key: fake_client)

    settings = SimpleNamespace(musixmatch_api_key="live-key", musixmatch_enabled=True)
    result = get_lyrics_for_song(db, settings, song.id, user_id)  # type: ignore[arg-type]
    assert result is not None
    assert result.source == "musixmatch"
    assert "Musixmatch" in result.lyrics or "Fallback" in result.lyrics
    clear_lyrics_cache()
    reset_lyrics_clients()


def test_service_falls_back_to_mock_when_no_key(db, monkeypatch):
    clear_lyrics_cache()
    reset_lyrics_clients()
    song = _make_song(db, "Demo Mock Anthem", "Spotifree Mock")
    user_id = SimpleNamespace()

    monkeypatch.setattr("app.services.lyrics._try_lrclib", lambda *a, **k: None)

    settings = SimpleNamespace(musixmatch_api_key=None, musixmatch_enabled=False)
    result = get_lyrics_for_song(db, settings, song.id, user_id)  # type: ignore[arg-type]
    assert result is not None
    assert result.source == "mock_local"
    assert "local mock" in result.lyrics.lower()
    clear_lyrics_cache()
    reset_lyrics_clients()


def test_service_prefers_lrclib(db, monkeypatch):
    clear_lyrics_cache()
    reset_lyrics_clients()
    song = _make_song(db, "Any Title", "Any Artist")
    user_id = SimpleNamespace()

    from app.services.lyrics import LyricsResult

    monkeypatch.setattr(
        "app.services.lyrics._try_lrclib",
        lambda *a, **k: LyricsResult(
            song_id=0,
            title="Any Title",
            artist="Any Artist",
            lyrics="From LRCLIB",
            source="lrclib",
            genius_url=None,
        ),
    )
    called = {"mxm": False}

    def _mxm(*a, **k):
        called["mxm"] = True
        return None

    monkeypatch.setattr("app.services.lyrics._try_musixmatch", _mxm)
    settings = SimpleNamespace(musixmatch_api_key="live-key", musixmatch_enabled=True)
    result = get_lyrics_for_song(db, settings, song.id, user_id)  # type: ignore[arg-type]
    assert result is not None
    assert result.source == "lrclib"
    assert called["mxm"] is False
    clear_lyrics_cache()
    reset_lyrics_clients()
