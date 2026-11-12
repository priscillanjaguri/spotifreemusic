"""Jamendo adapter (Creative Commons music, https://developer.jamendo.com).

We only use documented read endpoints and the stream URLs Jamendo returns for
playback. We never use the download URLs.

NOTE: written from Jamendo's public API docs and tested against sample payloads.
Run `python -m scripts.check_jamendo` on a machine with internet access to verify
it against the live API.
"""
from datetime import date

import httpx

from app.providers.base import MusicProviderAdapter, ProviderArtist, ProviderError, ProviderTrack

BASE_URL = "https://api.jamendo.com/v3.0"


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
            "imagesize": 300,
        }
        try:
            response = self._http.get(f"{BASE_URL}/tracks/", params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Jamendo request failed: {exc.__class__.__name__}") from exc

        headers = payload.get("headers", {})
        if headers.get("status") != "success":
            raise ProviderError(f"Jamendo error: {headers.get('error_message') or 'unknown'}")

        tracks = (self._parse(row) for row in payload.get("results", []))
        return [t for t in tracks if t is not None]

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
            license_url=row.get("license_ccurl") or None,
        )
