"""LRCLIB client — plain lyrics (no API key).

Docs: https://lrclib.net — prefer ``GET /api/get`` (exact) then ``GET /api/search``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from app.providers.base import ProviderError

log = logging.getLogger(__name__)

API_BASE = "https://lrclib.net/api"
# LRCLIB asks clients to send an identifying User-Agent.
USER_AGENT = "SpotifreeLyrics/1.0 (https://github.com/priscillanjaguri/spotifreemusic)"


@dataclass(frozen=True)
class LrcLibTrack:
    id: int
    title: str
    artist: str
    album: str | None
    duration_s: float | None
    plain_lyrics: str
    synced_lyrics: str | None = None
    instrumental: bool = False


@dataclass
class LrcLibClient:
    http: httpx.Client = field(
        default_factory=lambda: httpx.Client(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
    )

    def close(self) -> None:
        self.http.close()

    def get_lyrics(
        self,
        title: str,
        artist: str,
        *,
        duration_ms: int | None = None,
        album: str | None = None,
    ) -> LrcLibTrack | None:
        """Resolve plain lyrics: exact ``/get`` first, then ``/search``."""
        title = (title or "").strip()
        artist = (artist or "").strip()
        if not title or not artist:
            return None

        duration_s = (duration_ms / 1000.0) if duration_ms and duration_ms > 0 else None
        album_s = (album or "").strip() or None

        hit = self._get_exact(title, artist, duration_s=duration_s, album=album_s)
        if hit and hit.plain_lyrics:
            return hit

        return self._search_best(title, artist, duration_s=duration_s, album=album_s)

    def _get_exact(
        self,
        title: str,
        artist: str,
        *,
        duration_s: float | None,
        album: str | None,
    ) -> LrcLibTrack | None:
        params: dict[str, str | float] = {
            "track_name": title,
            "artist_name": artist,
        }
        if duration_s is not None:
            params["duration"] = round(duration_s, 2)
        if album:
            params["album_name"] = album
        try:
            resp = self.http.get(f"{API_BASE}/get", params=params)
            if resp.status_code == 404:
                # Retry without album if album-qualified get missed.
                if album:
                    return self._get_exact(title, artist, duration_s=duration_s, album=None)
                return None
            resp.raise_for_status()
            return _parse_row(resp.json())
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError(f"LRCLIB get failed: {exc.__class__.__name__}") from exc

    def _search_best(
        self,
        title: str,
        artist: str,
        *,
        duration_s: float | None,
        album: str | None,
    ) -> LrcLibTrack | None:
        params: dict[str, str] = {
            "track_name": title,
            "artist_name": artist,
        }
        if album:
            params["album_name"] = album
        try:
            resp = self.http.get(f"{API_BASE}/search", params=params)
            resp.raise_for_status()
            rows = resp.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError(f"LRCLIB search failed: {exc.__class__.__name__}") from exc

        if not isinstance(rows, list) or not rows:
            return None

        title_l = title.lower()
        artist_l = artist.lower()
        scored: list[tuple[float, LrcLibTrack]] = []
        for row in rows:
            track = _parse_row(row)
            if track is None or not track.plain_lyrics:
                continue
            score = 0.0
            if title_l and title_l in track.title.lower():
                score += 3.0
            if artist_l and artist_l in track.artist.lower():
                score += 3.0
            if album and track.album and album.lower() in track.album.lower():
                score += 1.0
            if duration_s is not None and track.duration_s is not None:
                delta = abs(track.duration_s - duration_s)
                if delta <= 2:
                    score += 2.0
                elif delta <= 5:
                    score += 1.0
                else:
                    score -= min(2.0, delta / 30.0)
            scored.append((score, track))

        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]
        if best_score < 3.0:
            # Require at least a title or artist hit to avoid random garbage.
            log.debug("LRCLIB search best score too low (%.2f) for %r / %r", best_score, title, artist)
            return None
        return best


def _parse_row(row: object) -> LrcLibTrack | None:
    if not isinstance(row, dict):
        return None
    try:
        track_id = int(row["id"])
    except (KeyError, TypeError, ValueError):
        return None
    title = str(row.get("trackName") or row.get("name") or "").strip()
    artist = str(row.get("artistName") or "").strip()
    if not title or not artist:
        return None
    plain = row.get("plainLyrics")
    if not isinstance(plain, str) or not plain.strip():
        if row.get("instrumental"):
            return None
        return None
    duration = row.get("duration")
    duration_s = float(duration) if isinstance(duration, (int, float)) else None
    synced = row.get("syncedLyrics")
    album = row.get("albumName")
    return LrcLibTrack(
        id=track_id,
        title=title,
        artist=artist,
        album=str(album).strip() if isinstance(album, str) and album.strip() else None,
        duration_s=duration_s,
        plain_lyrics=plain.strip(),
        synced_lyrics=synced.strip() if isinstance(synced, str) and synced.strip() else None,
        instrumental=bool(row.get("instrumental")),
    )
