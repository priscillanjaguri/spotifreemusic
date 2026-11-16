"""Musixmatch Lyrics API client — plain lyrics (official API, requires API key).

Docs: https://docs.musixmatch.com/lyrics-api/matcher/matcher-lyrics-get
Uses ``matcher.lyrics.get`` (title + artist fuzzy match). No HTML scraping.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from app.providers.base import ProviderError

log = logging.getLogger(__name__)

API_BASE = "https://api.musixmatch.com/ws/1.1"
USER_AGENT = "SpotifreeLyrics/1.0 (https://github.com/priscillanjaguri/spotifreemusic)"


@dataclass(frozen=True)
class MusixmatchTrack:
    lyrics_id: int | None
    title: str
    artist: str
    plain_lyrics: str
    copyright: str | None = None


@dataclass
class MusixmatchClient:
    """Official Musixmatch API. Construct only when ``MUSIXMATCH_API_KEY`` is set."""

    api_key: str
    http: httpx.Client = field(
        default_factory=lambda: httpx.Client(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
    )

    def close(self) -> None:
        self.http.close()

    def get_lyrics(self, title: str, artist: str) -> MusixmatchTrack | None:
        title = (title or "").strip()
        artist = (artist or "").strip()
        if not title or not artist:
            return None
        if not self.api_key.strip():
            raise ProviderError("Musixmatch API key is empty")

        params = {
            "apikey": self.api_key,
            "q_track": title,
            "q_artist": artist,
        }
        try:
            resp = self.http.get(f"{API_BASE}/matcher.lyrics.get", params=params)
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError(f"Musixmatch request failed: {exc.__class__.__name__}") from exc

        return _parse_matcher_response(payload, title=title, artist=artist)


def _parse_matcher_response(payload: object, *, title: str, artist: str) -> MusixmatchTrack | None:
    if not isinstance(payload, dict):
        raise ProviderError("Musixmatch response was not an object")
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ProviderError("Musixmatch response missing message")
    header = message.get("header")
    if not isinstance(header, dict):
        raise ProviderError("Musixmatch response missing header")
    try:
        status = int(header.get("status_code"))
    except (TypeError, ValueError) as exc:
        raise ProviderError("Musixmatch status_code missing") from exc

    # 200 = hit, 404 = no match, 401 = bad key, 402 = limit, etc.
    if status == 404:
        return None
    if status == 401:
        raise ProviderError("Musixmatch unauthorized (check MUSIXMATCH_API_KEY)")
    if status == 402:
        raise ProviderError("Musixmatch daily limit reached")
    if status != 200:
        raise ProviderError(f"Musixmatch API status {status}")

    body = message.get("body")
    if not isinstance(body, dict):
        return None
    lyrics = body.get("lyrics")
    if not isinstance(lyrics, dict):
        return None
    text = lyrics.get("lyrics_body")
    if not isinstance(text, str) or not text.strip():
        return None

    plain = _clean_lyrics_body(text)
    if not plain:
        return None

    lyrics_id_raw = lyrics.get("lyrics_id")
    lyrics_id: int | None
    try:
        lyrics_id = int(lyrics_id_raw) if lyrics_id_raw is not None else None
    except (TypeError, ValueError):
        lyrics_id = None

    copyright_raw = lyrics.get("lyrics_copyright")
    copyright_s = (
        copyright_raw.strip()
        if isinstance(copyright_raw, str) and copyright_raw.strip()
        else None
    )

    return MusixmatchTrack(
        lyrics_id=lyrics_id,
        title=title,
        artist=artist,
        plain_lyrics=plain,
        copyright=copyright_s,
    )


def _clean_lyrics_body(text: str) -> str:
    """Return plain lyrics; drop free-tier commercial footer / ellipsis trailers."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if "this lyrics is not for commercial use" in lower:
            break
        if stripped == "..." and not cleaned:
            continue
        cleaned.append(line.rstrip())
    # Trim trailing blank / lone "..." lines Musixmatch appends on the free plan.
    while cleaned and (not cleaned[-1].strip() or cleaned[-1].strip() == "..."):
        cleaned.pop()
    return "\n".join(cleaned).strip()
