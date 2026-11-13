"""Genius lyrics client + HTML extract (mocked HTTP; no real credentials)."""
from __future__ import annotations

import httpx
import pytest

from app.providers.genius import GeniusClient, extract_lyrics_from_html
from app.services.lyrics import clear_lyrics_cache


SAMPLE_HTML = """
<html><body>
<div data-lyrics-container="true" class="Lyrics__Container-sc-1ynbvzv-5">
[Verse 1]<br/>Is this the real life?<br/>Is this just fantasy?<br/>
</div>
<div data-lyrics-container="true">
Caught in a landslide<br/>No escape from reality
</div>
<script>not lyrics</script>
</body></html>
"""


def test_extract_lyrics_from_html():
    text = extract_lyrics_from_html(SAMPLE_HTML)
    assert "Is this the real life?" in text
    assert "Caught in a landslide" in text
    assert "not lyrics" not in text


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/oauth/token"):
        return httpx.Response(200, json={"access_token": "genius-tok", "token_type": "bearer", "expires_in": 3600})
    if path.endswith("/search"):
        return httpx.Response(
            200,
            json={
                "meta": {"status": 200},
                "response": {
                    "hits": [
                        {
                            "type": "song",
                            "result": {
                                "id": 1063,
                                "title": "Bohemian Rhapsody",
                                "url": "https://genius.com/Queen-bohemian-rhapsody-lyrics",
                                "primary_artist": {"name": "Queen"},
                            },
                        }
                    ]
                },
            },
        )
    if "genius.com" in request.url.host and "lyrics" in path:
        return httpx.Response(200, text=SAMPLE_HTML)
    return httpx.Response(404, json={"error": "not found"})


@pytest.fixture
def genius_client():
    transport = httpx.MockTransport(_handler)
    client = GeniusClient(
        access_token="client-id-as-token",
        client_secret="client-secret",
        http=httpx.Client(transport=transport, follow_redirects=True),
    )
    yield client
    client.close()
    clear_lyrics_cache()


def test_search_and_fetch_lyrics(genius_client: GeniusClient):
    hit = genius_client.search_song("Bohemian Rhapsody", "Queen")
    assert hit is not None
    assert hit.id == 1063
    assert hit.artist == "Queen"
    lyrics = genius_client.fetch_lyrics(hit.url)
    assert lyrics is not None
    assert "Is this the real life?" in lyrics


def test_refuses_non_genius_url(genius_client: GeniusClient):
    from app.providers.base import ProviderError

    with pytest.raises(ProviderError):
        genius_client.fetch_lyrics("https://example.com/lyrics")
