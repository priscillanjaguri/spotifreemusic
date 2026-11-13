"""LRCLIB lyrics client (mocked HTTP; no network)."""
from __future__ import annotations

import httpx
import pytest

from app.providers.lrclib import LrcLibClient
from app.services.lyrics import clear_lyrics_cache


SAMPLE = {
    "id": 19080,
    "name": "Bohemian Rhapsody",
    "trackName": "Bohemian Rhapsody",
    "artistName": "Queen",
    "albumName": "A Night at the Opera",
    "duration": 355.0,
    "instrumental": False,
    "plainLyrics": "Is this the real life?\nIs this just fantasy?",
    "syncedLyrics": "[00:00.15] Is this the real life?\n[00:07.13] Is this just fantasy?",
}


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/get"):
        params = dict(request.url.params)
        if params.get("track_name") == "Missing":
            return httpx.Response(404, json={"code": 404, "name": "TrackNotFoundError"})
        return httpx.Response(200, json=SAMPLE)
    if path.endswith("/search"):
        params = dict(request.url.params)
        if params.get("track_name") == "Missing":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[SAMPLE])
    return httpx.Response(404, json={"error": "not found"})


@pytest.fixture
def lrclib_client():
    transport = httpx.MockTransport(_handler)
    client = LrcLibClient(http=httpx.Client(transport=transport, follow_redirects=True))
    yield client
    client.close()
    clear_lyrics_cache()


def test_get_exact(lrclib_client: LrcLibClient):
    hit = lrclib_client.get_lyrics("Bohemian Rhapsody", "Queen", duration_ms=355_000, album="A Night at the Opera")
    assert hit is not None
    assert hit.id == 19080
    assert "real life" in hit.plain_lyrics
    assert hit.synced_lyrics


def test_search_fallback_when_get_404(lrclib_client: LrcLibClient):
    # Force get 404 via title "Missing", then search empty → None
    assert lrclib_client.get_lyrics("Missing", "Nobody") is None


def test_search_finds_lyrics(lrclib_client: LrcLibClient):
    # get succeeds for normal titles in this mock; exercise search path by calling _search_best
    hit = lrclib_client._search_best("Bohemian Rhapsody", "Queen", duration_s=355.0, album=None)
    assert hit is not None
    assert hit.artist == "Queen"
