"""Spotify Web API — metadata only (Client Credentials).

Used to match catalogue / library songs and pull genres + audio features for the
recommender. Never returns playback/stream URLs for Spotifree's player.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

from app.providers.base import ProviderError

log = logging.getLogger(__name__)

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"


@dataclass(frozen=True)
class SpotifyArtistRef:
    id: str
    name: str


@dataclass(frozen=True)
class SpotifyTrackMatch:
    id: str
    name: str
    duration_ms: int
    artists: list[SpotifyArtistRef]
    album_name: str | None = None
    popularity: int | None = None
    isrc: str | None = None


@dataclass(frozen=True)
class SpotifyAudioFeatures:
    """Subset of Spotify audio-features we map onto song_features."""

    tempo: float | None = None
    energy: float | None = None
    danceability: float | None = None
    acousticness: float | None = None
    valence: float | None = None
    instrumentalness: float | None = None
    loudness_db: float | None = None
    key: int | None = None
    mode: int | None = None


@dataclass
class SpotifyMetadataClient:
    """Client-credentials Spotify client. Safe to construct when credentials exist."""

    client_id: str
    client_secret: str
    http: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=20.0))
    _token: str | None = field(default=None, init=False, repr=False)
    _token_expires_at: float = field(default=0.0, init=False, repr=False)

    def close(self) -> None:
        self.http.close()

    def _ensure_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires_at - 30:
            return self._token
        try:
            resp = self.http.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Spotify token request failed: {exc}") from exc
        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise ProviderError("Spotify token response missing access_token")
        self._token = token
        self._token_expires_at = now + float(payload.get("expires_in") or 3600)
        return token

    def _get(self, path: str, *, params: dict | None = None) -> dict | list:
        token = self._ensure_token()
        try:
            resp = self.http.get(
                f"{API_BASE}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 404:
                return {}
            if resp.status_code in (401, 403):
                # Token revoked or endpoint restricted — surface as ProviderError for callers to skip.
                raise ProviderError(f"Spotify API {resp.status_code} for {path}")
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Spotify GET {path} failed: {exc}") from exc
        return resp.json()

    def search_tracks(self, query: str, *, limit: int = 5) -> list[SpotifyTrackMatch]:
        q = (query or "").strip()
        if not q:
            return []
        data = self._get("/search", params={"q": q, "type": "track", "limit": max(1, min(limit, 10))})
        items = ((data or {}).get("tracks") or {}).get("items") or []
        out: list[SpotifyTrackMatch] = []
        for item in items:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            artists = [
                SpotifyArtistRef(id=str(a.get("id") or ""), name=str(a.get("name") or "").strip())
                for a in (item.get("artists") or [])
                if isinstance(a, dict) and a.get("name")
            ]
            ext = item.get("external_ids") or {}
            album = item.get("album") or {}
            out.append(
                SpotifyTrackMatch(
                    id=str(item["id"]),
                    name=str(item.get("name") or ""),
                    duration_ms=int(item.get("duration_ms") or 0),
                    artists=artists,
                    album_name=(album.get("name") if isinstance(album, dict) else None),
                    popularity=int(item["popularity"]) if item.get("popularity") is not None else None,
                    isrc=str(ext["isrc"]) if isinstance(ext, dict) and ext.get("isrc") else None,
                )
            )
        return out

    def get_track(self, track_id: str) -> SpotifyTrackMatch | None:
        data = self._get(f"/tracks/{track_id}")
        if not isinstance(data, dict) or not data.get("id"):
            return None
        artists = [
            SpotifyArtistRef(id=str(a.get("id") or ""), name=str(a.get("name") or "").strip())
            for a in (data.get("artists") or [])
            if isinstance(a, dict) and a.get("name")
        ]
        ext = data.get("external_ids") or {}
        album = data.get("album") or {}
        return SpotifyTrackMatch(
            id=str(data["id"]),
            name=str(data.get("name") or ""),
            duration_ms=int(data.get("duration_ms") or 0),
            artists=artists,
            album_name=(album.get("name") if isinstance(album, dict) else None),
            popularity=int(data["popularity"]) if data.get("popularity") is not None else None,
            isrc=str(ext["isrc"]) if isinstance(ext, dict) and ext.get("isrc") else None,
        )

    def audio_features(self, track_id: str) -> SpotifyAudioFeatures | None:
        """Fetch audio features. Returns None if Spotify withholds the endpoint."""
        try:
            data = self._get(f"/audio-features/{track_id}")
        except ProviderError as exc:
            log.info("Spotify audio-features unavailable for %s: %s", track_id, exc)
            return None
        if not isinstance(data, dict) or not data.get("id"):
            return None

        def _f(name: str) -> float | None:
            v = data.get(name)
            return float(v) if v is not None else None

        def _i(name: str) -> int | None:
            v = data.get(name)
            return int(v) if v is not None else None

        tempo = _f("tempo")
        # Clamp to our DB check constraints.
        if tempo is not None and not (30 <= tempo <= 300):
            tempo = None

        def _unit(v: float | None) -> float | None:
            if v is None:
                return None
            return max(0.0, min(1.0, float(v)))

        key = _i("key")
        if key is not None and not (0 <= key <= 11):
            key = None
        mode = _i("mode")
        if mode is not None and mode not in (0, 1):
            mode = None

        return SpotifyAudioFeatures(
            tempo=tempo,
            energy=_unit(_f("energy")),
            danceability=_unit(_f("danceability")),
            acousticness=_unit(_f("acousticness")),
            valence=_unit(_f("valence")),
            instrumentalness=_unit(_f("instrumentalness")),
            loudness_db=_f("loudness"),
            key=key,
            mode=mode,
        )

    def artist_genres(self, artist_ids: list[str]) -> list[str]:
        ids = [i for i in artist_ids if i][:20]
        if not ids:
            return []
        data = self._get("/artists", params={"ids": ",".join(ids)})
        genres: set[str] = set()
        for artist in (data or {}).get("artists") or []:
            if not isinstance(artist, dict):
                continue
            for g in artist.get("genres") or []:
                cleaned = str(g).strip().lower()
                if cleaned:
                    genres.add(cleaned)
        return sorted(genres)


def build_spotify_client(client_id: str | None, client_secret: str | None) -> SpotifyMetadataClient | None:
    if not client_id or not client_secret:
        return None
    return SpotifyMetadataClient(client_id=client_id, client_secret=client_secret)
