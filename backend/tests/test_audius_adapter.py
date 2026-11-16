import httpx
import pytest

from app.providers.audius import AudiusAdapter, OML_LICENSE_URL
from app.providers.base import ProviderError

SAMPLE = {
    "data": [
        {
            "id": "abc123",
            "title": "Night Drive",
            "duration": 200,
            "is_streamable": True,
            "is_stream_gated": False,
            "is_available": True,
            "genre": "Electronic",
            "tags": "lofi, chill",
            "release_date": "2024-01-05T12:00:00Z",
            "permalink": "/neoncat/night-drive",
            "artwork": {
                "150x150": "https://img/150.jpg",
                "480x480": "https://img/480.jpg",
                "1000x1000": "https://img/1000.jpg",
            },
            "user": {"id": "u1", "name": "Neon Cat", "handle": "neoncat"},
        },
        {
            "id": "gated",
            "title": "VIP Only",
            "duration": 180,
            "is_streamable": True,
            "is_stream_gated": True,
            "user": {"name": "X"},
        },
        {
            "id": "nostream",
            "title": "Preview Clip",
            "duration": 180,
            "is_streamable": False,
            "user": {"name": "X"},
        },
        {
            "id": "nodur",
            "title": "Broken",
            "duration": 0,
            "is_streamable": True,
            "user": {"name": "X"},
        },
        {
            "id": "plain",
            "title": "Soft Keys",
            "duration": 90,
            "is_streamable": True,
            "is_stream_gated": False,
            "user": {"handle": "piano_pal"},
        },
    ]
}


def adapter(handler, **kwargs):
    return AudiusAdapter(
        api_host="https://api.audius.co",
        app_name="spotifree",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        **kwargs,
    )


def test_parses_streamable_tracks_and_skips_unusable_rows():
    seen = {}

    def handler(request: httpx.Request):
        seen.update(request.url.params)
        return httpx.Response(200, json=SAMPLE)

    tracks = adapter(handler).search_tracks("night", limit=5)
    assert seen["query"] == "night" and seen["app_name"] == "spotifree"
    assert [t.title for t in tracks] == ["Night Drive", "Soft Keys"]
    t = tracks[0]
    assert t.provider_track_id == "abc123"
    assert t.duration_ms == 200_000
    assert t.artists[0].name == "Neon Cat"
    assert t.genres == ["Electronic", "lofi", "chill"]
    assert t.cover_url == "https://img/480.jpg"
    assert t.stream_url == "https://api.audius.co/v1/tracks/abc123/stream?app_name=spotifree"
    assert t.license_url == "https://audius.co/neoncat/night-drive"
    assert t.download_allowed is False
    assert tracks[1].artists[0].name == "piano_pal"
    assert tracks[1].license_url == OML_LICENSE_URL


def test_optional_api_key_is_forwarded():
    seen = {}

    def handler(request: httpx.Request):
        seen.update(request.url.params)
        return httpx.Response(200, json={"data": []})

    adapter(handler, api_key="free-key").search_tracks("x")
    assert seen["api_key"] == "free-key"


def test_http_failure_raises_provider_error():
    with pytest.raises(ProviderError):
        adapter(lambda r: httpx.Response(500)).search_tracks("x")


def test_bad_payload_raises_provider_error():
    with pytest.raises(ProviderError, match="unexpected"):
        adapter(lambda r: httpx.Response(200, json={"data": "nope"})).search_tracks("x")


def test_network_failure_raises_provider_error():
    def boom(request):
        raise httpx.ConnectError("no network")

    with pytest.raises(ProviderError):
        adapter(boom).search_tracks("x")


def test_respects_limit_after_filtering():
    rows = []
    for i in range(10):
        rows.append(
            {
                "id": f"t{i}",
                "title": f"Track {i}",
                "duration": 60,
                "is_streamable": True,
                "user": {"name": "A"},
            }
        )
    tracks = adapter(lambda r: httpx.Response(200, json={"data": rows})).search_tracks("q", limit=3)
    assert len(tracks) == 3
