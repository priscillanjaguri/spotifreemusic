import httpx
import pytest

from app.providers.base import ProviderError
from app.providers.jamendo import JamendoAdapter

# Shaped like Jamendo's documented /tracks response (note: ids and durations are strings).
SAMPLE = {
    "headers": {"status": "success", "code": 0, "error_message": "", "results_count": 4},
    "results": [
        {"id": "887202", "name": "Press Record", "duration": "192", "artist_id": "376782",
         "artist_name": "WE ARE FM", "album_name": "Season One", "releasedate": "2011-12-29",
         "image": "https://img/x.jpg", "audio": "https://stream/887202.mp3",
         "license_ccurl": "http://creativecommons.org/licenses/by-nc-sa/3.0/",
         "musicinfo": {"tags": {"genres": ["pop", "rock"]}}},
        {"id": "2", "name": "No Duration", "duration": "0", "artist_name": "X"},       # unusable
        {"id": "3", "name": "", "duration": "100", "artist_name": "X"},                  # unusable
        {"id": "4", "name": "Single", "duration": "60", "artist_name": "Solo", "releasedate": "garbage"},
    ],
}


def adapter(handler):
    return JamendoAdapter("test-client-id", httpx.Client(transport=httpx.MockTransport(handler)))


def test_parses_tracks_and_skips_unusable_rows():
    seen = {}

    def handler(request: httpx.Request):
        seen.update(request.url.params)
        return httpx.Response(200, json=SAMPLE)

    tracks = adapter(handler).search_tracks("press", limit=5)
    assert seen["client_id"] == "test-client-id" and seen["search"] == "press" and seen["limit"] == "5"
    assert [t.title for t in tracks] == ["Press Record", "Single"]
    t = tracks[0]
    assert t.duration_ms == 192_000 and t.genres == ["pop", "rock"] and t.album_title == "Season One"
    assert t.stream_url == "https://stream/887202.mp3"
    assert t.license_url == "https://creativecommons.org/licenses/by-nc-sa/3.0/"
    assert tracks[1].release_date is None and tracks[1].album_title is None  # bad date tolerated


def test_api_level_error_raises_provider_error():
    bad = {"headers": {"status": "failed", "code": 5, "error_message": "invalid client_id"}, "results": []}
    with pytest.raises(ProviderError, match="invalid client_id"):
        adapter(lambda r: httpx.Response(200, json=bad)).search_tracks("x")


@pytest.mark.parametrize("response", [httpx.Response(500), httpx.Response(200, content=b"<html>nope")])
def test_http_failure_or_bad_json_raises_provider_error(response):
    with pytest.raises(ProviderError):
        adapter(lambda r: response).search_tracks("x")


def test_network_failure_raises_provider_error():
    def boom(request):
        raise httpx.ConnectError("no network")

    with pytest.raises(ProviderError):
        adapter(boom).search_tracks("x")


def test_retries_spurious_empty_results():
    calls = []
    empty = {"headers": {"status": "success", "code": 0, "results_count": 0}, "results": []}

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json=empty if len(calls) == 1 else SAMPLE)

    assert len(adapter(handler).search_tracks("press")) == 2
    assert len(calls) == 2


def test_gives_up_after_repeated_empty_results():
    calls = []
    empty = {"headers": {"status": "success", "code": 0, "results_count": 0}, "results": []}

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json=empty)

    assert adapter(handler).search_tracks("zzzz") == []
    assert len(calls) == 3
