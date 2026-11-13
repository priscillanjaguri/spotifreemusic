"""Resolve plain lyrics for a catalogue song via LRCLIB (cached by song_id)."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Song
from app.providers.base import ProviderError
from app.providers.lrclib import LrcLibClient
from app.services.collection import SONG_LOAD

log = logging.getLogger(__name__)

CACHE_TTL_HIT_S = 60 * 60 * 24  # 24h
CACHE_TTL_MISS_S = 60 * 15  # 15m


@dataclass(frozen=True)
class LyricsResult:
    song_id: int
    title: str
    artist: str
    lyrics: str
    source: str
    # Kept for API compatibility with the earlier Genius response shape.
    genius_url: str | None


@dataclass
class _CacheEntry:
    result: LyricsResult | None  # None = known miss
    expires_at: float


_cache: dict[int, _CacheEntry] = {}
_cache_lock = threading.Lock()
_client: LrcLibClient | None = None
_client_lock = threading.Lock()


def _get_client() -> LrcLibClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = LrcLibClient()
        return _client


def clear_lyrics_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _artist_label(song: Song) -> str:
    names = [link.artist.name for link in song.artist_links if link.artist and link.artist.name]
    return ", ".join(names)


def get_lyrics_for_song(db: Session, settings: Settings, song_id: int, user_id) -> LyricsResult | None:
    """Return lyrics for an accessible song, or None when missing / unavailable."""
    del settings  # LRCLIB needs no secrets; signature kept for callers.
    now = time.time()
    with _cache_lock:
        entry = _cache.get(song_id)
        if entry and entry.expires_at > now:
            return entry.result

    song = db.get(Song, song_id, options=list(SONG_LOAD))
    if song is None or (song.owner_user_id is not None and song.owner_user_id != user_id):
        raise LookupError("song_not_found")

    title = song.title
    artist = _artist_label(song)
    album = song.album.title if song.album and song.album.title else None
    client = _get_client()

    result: LyricsResult | None = None
    try:
        hit = client.get_lyrics(
            title,
            artist,
            duration_ms=song.duration_ms,
            album=album,
        )
        if hit and hit.plain_lyrics:
            result = LyricsResult(
                song_id=song_id,
                title=hit.title or title,
                artist=hit.artist or artist,
                lyrics=hit.plain_lyrics,
                source="lrclib",
                genius_url=None,
            )
    except ProviderError as exc:
        log.info("LRCLIB lyrics lookup failed for song_id=%s: %s", song_id, exc)
        result = None

    ttl = CACHE_TTL_HIT_S if result else CACHE_TTL_MISS_S
    with _cache_lock:
        _cache[song_id] = _CacheEntry(result=result, expires_at=now + ttl)
    return result


__all__ = ["LyricsResult", "get_lyrics_for_song", "clear_lyrics_cache"]
