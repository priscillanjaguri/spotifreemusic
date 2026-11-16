"""Audius adapter (Open Music License catalogue, https://docs.audius.co/api/).

Read-only search + stream URLs via the official REST gateway. Unauthenticated
reads work with an `app_name`; an optional API key raises rate limits.
We only return streamable, non-gated tracks and store the stable
`/v1/tracks/{id}/stream` URL (not the short-lived CDN redirect).
"""
from datetime import date, datetime
from urllib.parse import urlencode

import httpx

from app.providers.base import MusicProviderAdapter, ProviderArtist, ProviderError, ProviderTrack

DEFAULT_HOST = "https://api.audius.co"
DEFAULT_APP_NAME = "spotifree"
OML_LICENSE_URL = "https://audius.co"  # Open Music License; per-track permalink preferred when present


class AudiusAdapter(MusicProviderAdapter):
    key = "audius"
    display_name = "Audius"
    supports_playback = True

    def __init__(
        self,
        *,
        api_host: str = DEFAULT_HOST,
        app_name: str = DEFAULT_APP_NAME,
        api_key: str | None = None,
        http: httpx.Client | None = None,
    ):
        self._host = api_host.rstrip("/")
        self._app_name = app_name.strip() or DEFAULT_APP_NAME
        self._api_key = (api_key or "").strip() or None
        self._http = http or httpx.Client(
            timeout=12.0,
            headers={"User-Agent": f"spotifree/{self._app_name}", "Accept": "application/json"},
        )

    def search_tracks(self, query: str, limit: int = 20) -> list[ProviderTrack]:
        params: dict[str, str | int] = {
            "query": query,
            "app_name": self._app_name,
            # Ask for extras so we can filter down to streamable rows.
            "limit": max(limit * 2, limit),
        }
        if self._api_key:
            params["api_key"] = self._api_key
        rows = self._fetch("/v1/tracks/search", params)
        tracks: list[ProviderTrack] = []
        for row in rows:
            parsed = self._parse(row)
            if parsed is not None:
                tracks.append(parsed)
            if len(tracks) >= limit:
                break
        return tracks

    def _fetch(self, path: str, params: dict) -> list[dict]:
        try:
            response = self._http.get(f"{self._host}{path}", params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Audius request failed: {exc.__class__.__name__}") from exc
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise ProviderError("Audius returned an unexpected payload")
        return [row for row in data if isinstance(row, dict)]

    def _stream_url(self, track_id: str) -> str:
        query = {"app_name": self._app_name}
        if self._api_key:
            query["api_key"] = self._api_key
        return f"{self._host}/v1/tracks/{track_id}/stream?{urlencode(query)}"

    def _parse(self, row: dict) -> ProviderTrack | None:
        """Convert one Audius track; skip gated / non-streamable / unusable rows."""
        try:
            track_id = str(row.get("id") or "").strip()
            title = str(row.get("title") or "").strip()
            duration_s = int(row.get("duration") or 0)
        except (TypeError, ValueError):
            return None
        if not track_id or not title or duration_s <= 0:
            return None
        if row.get("is_streamable") is False:
            return None
        if row.get("is_stream_gated") is True:
            return None
        if row.get("is_available") is False:
            return None

        user = row.get("user") if isinstance(row.get("user"), dict) else {}
        artist_name = str(user.get("name") or user.get("handle") or "").strip()
        if not artist_name:
            return None
        artist_id = str(user.get("id") or "").strip() or None

        genres: list[str] = []
        genre = row.get("genre")
        if isinstance(genre, str) and genre.strip():
            genres.append(genre.strip())
        tags = row.get("tags")
        if isinstance(tags, str) and tags.strip():
            genres.extend(t.strip() for t in tags.split(",") if t.strip())
        # Keep order, drop duplicates (case-insensitive).
        seen: set[str] = set()
        uniq_genres: list[str] = []
        for g in genres:
            key = g.lower()
            if key not in seen:
                seen.add(key)
                uniq_genres.append(g)

        artwork = row.get("artwork") if isinstance(row.get("artwork"), dict) else {}
        cover = (
            artwork.get("480x480")
            or artwork.get("1000x1000")
            or artwork.get("150x150")
            or None
        )

        released = _parse_date(row.get("release_date") or row.get("created_at"))
        permalink = row.get("permalink")
        license_url = OML_LICENSE_URL
        if isinstance(permalink, str) and permalink.startswith("/"):
            license_url = f"https://audius.co{permalink}"

        return ProviderTrack(
            provider_track_id=track_id,
            title=title,
            duration_ms=duration_s * 1000,
            artists=[ProviderArtist(name=artist_name, provider_artist_id=artist_id)],
            album_title=None,
            release_date=released,
            cover_url=cover if isinstance(cover, str) else None,
            genres=uniq_genres,
            stream_url=self._stream_url(track_id),
            license_url=license_url,
            download_allowed=False,  # OML grants stream/perform; we do not download for analysis
        )


def _parse_date(value: object) -> date | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return date.fromisoformat(text[:10])
    except ValueError:
        return None
