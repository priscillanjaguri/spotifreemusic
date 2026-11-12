"""Jamendo adapter (Creative Commons music, https://developer.jamendo.com).

We only use documented read endpoints and the stream URLs Jamendo returns for
playback. We never use the download URLs.

Verified against the live API (run `python -m scripts.check_jamendo` to re-check).
Cover art comes back as https://usercontent.jamendo.com/... (300px by default) and
stream URLs as https://prod-1.storage.jamendo.com/... MP3s that support range requests.
"""
from datetime import date

import httpx

from app.providers.base import MusicProviderAdapter, ProviderArtist, ProviderError, ProviderTrack

BASE_URL = "https://api.jamendo.com/v3.0"
EMPTY_RESULT_ATTEMPTS = 3


class JamendoAdapter(MusicProviderAdapter):
    key = "jamendo"
    display_name = "Jamendo"
    supports_playback = True

    def __init__(self, client_id: str, http: httpx.Client | None = None):
        self._client_id = client_id
        self._http = http or httpx.Client(timeout=10.0)

    def search_tracks(self, query: str, limit: int = 20) -> list[ProviderTrack]:
        params = {
            "client_id": self._client_id,
            "format": "json",
            "limit": limit,
            "search": query,
            "include": "musicinfo",  # gives genre tags
            "audioformat": "mp31",
        }
        # Jamendo intermittently answers a valid search with status "success" and zero results
        # (about half of identical requests in live testing), so retry empty answers a couple of times.
        rows: list[dict] = []
        for _ in range(EMPTY_RESULT_ATTEMPTS):
            rows = self._fetch(params)
            if rows:
                break
        tracks = (self._parse(row) for row in rows)
        return [t for t in tracks if t is not None]

    def _fetch(self, params: dict) -> list[dict]:
        try:
            response = self._http.get(f"{BASE_URL}/tracks/", params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Jamendo request failed: {exc.__class__.__name__}") from exc

        headers = payload.get("headers", {})
        if headers.get("status") != "success":
            raise ProviderError(f"Jamendo error: {headers.get('error_message') or 'unknown'}")
        return payload.get("results") or []

    @staticmethod
    def _parse(row: dict) -> ProviderTrack | None:
        """Convert one Jamendo row; return None for rows we can't use safely."""
        try:
            track_id, title = str(row["id"]), str(row["name"]).strip()
            duration_s = int(row["duration"])
            artist_name = str(row["artist_name"]).strip()
        except (KeyError, TypeError, ValueError):
            return None
        if not (track_id and title and artist_name) or duration_s <= 0:
            return None

        released = None
        if row.get("releasedate"):
            try:
                released = date.fromisoformat(row["releasedate"])
            except ValueError:
                pass

        genres = ((row.get("musicinfo") or {}).get("tags") or {}).get("genres") or []
        return ProviderTrack(
            provider_track_id=track_id,
            title=title,
            duration_ms=duration_s * 1000,
            artists=[ProviderArtist(name=artist_name, provider_artist_id=str(row.get("artist_id") or "") or None)],
            album_title=(row.get("album_name") or "").strip() or None,
            release_date=released,
            cover_url=row.get("image") or row.get("album_image") or None,
            genres=[g for g in genres if isinstance(g, str)],
            stream_url=row.get("audio") or None,
            license_url=_https(row.get("license_ccurl")),
        )


def _https(url: str | None) -> str | None:
    """Jamendo returns creativecommons.org licence links as http://; the https form is equivalent."""
    if not url:
        return None
    return "https://" + url[len("http://"):] if url.startswith("http://") else url
