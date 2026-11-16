"""Resolve plain lyrics for a catalogue song (LRCLIB first, then Musixmatch / mock)."""
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
from app.providers.lyrics_mock import LocalLyricsFallback
from app.providers.musixmatch import MusixmatchClient
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
_lrclib: LrcLibClient | None = None
_lrclib_lock = threading.Lock()
_musixmatch: MusixmatchClient | None = None
_musixmatch_key: str | None = None
_musixmatch_lock = threading.Lock()
_mock = LocalLyricsFallback()


def _get_lrclib() -> LrcLibClient:
    global _lrclib
    with _lrclib_lock:
        if _lrclib is None:
            _lrclib = LrcLibClient()
        return _lrclib


def _get_musixmatch(api_key: str) -> MusixmatchClient:
    global _musixmatch, _musixmatch_key
    with _musixmatch_lock:
        if _musixmatch is None or _musixmatch_key != api_key:
            if _musixmatch is not None:
                _musixmatch.close()
            _musixmatch = MusixmatchClient(api_key=api_key)
            _musixmatch_key = api_key
        return _musixmatch


def clear_lyrics_cache() -> None:
    with _cache_lock:
        _cache.clear()


def reset_lyrics_clients() -> None:
    """Test helper: drop cached HTTP clients after mock transport swaps."""
    global _lrclib, _musixmatch, _musixmatch_key
    with _lrclib_lock:
        if _lrclib is not None:
            _lrclib.close()
        _lrclib = None
    with _musixmatch_lock:
        if _musixmatch is not None:
            _musixmatch.close()
        _musixmatch = None
        _musixmatch_key = None


def _artist_label(song: Song) -> str:
    names = [link.artist.name for link in song.artist_links if link.artist and link.artist.name]
    return ", ".join(names)


def _try_lrclib(title: str, artist: str, *, duration_ms: int | None, album: str | None) -> LyricsResult | None:
    client = _get_lrclib()
    try:
        hit = client.get_lyrics(title, artist, duration_ms=duration_ms, album=album)
    except ProviderError as exc:
        log.info("LRCLIB lyrics lookup failed: %s", exc)
        return None
    if not hit or not hit.plain_lyrics:
        return None
    return LyricsResult(
        song_id=0,  # filled by caller
        title=hit.title or title,
        artist=hit.artist or artist,
        lyrics=hit.plain_lyrics,
        source="lrclib",
        genius_url=None,
    )


def _try_musixmatch(settings: Settings, title: str, artist: str) -> LyricsResult | None:
    key = (settings.musixmatch_api_key or "").strip()
    if not key:
        return None
    client = _get_musixmatch(key)
    try:
        hit = client.get_lyrics(title, artist)
    except ProviderError as exc:
        log.info("Musixmatch lyrics lookup failed: %s", exc)
        return None
    if not hit or not hit.plain_lyrics:
        return None
    return LyricsResult(
        song_id=0,
        title=hit.title or title,
        artist=hit.artist or artist,
        lyrics=hit.plain_lyrics,
        source="musixmatch",
        genius_url=None,
    )


def _try_mock_local(title: str, artist: str) -> LyricsResult | None:
    hit = _mock.get_lyrics(title, artist)
    if not hit:
        return None
    return LyricsResult(
        song_id=0,
        title=hit.title,
        artist=hit.artist,
        lyrics=hit.plain_lyrics,
        source=LocalLyricsFallback.source,
        genius_url=None,
    )


def get_lyrics_for_song(db: Session, settings: Settings, song_id: int, user_id) -> LyricsResult | None:
    """Return lyrics for an accessible song, or None when missing / unavailable.

    Order: LRCLIB (keyless) → Musixmatch (if ``MUSIXMATCH_API_KEY``) → local mock allowlist
    when Musixmatch is not configured. Genius is not used for lyric bodies.
    """
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

    result = _try_lrclib(title, artist, duration_ms=song.duration_ms, album=album)
    if result is None:
        result = _try_musixmatch(settings, title, artist)
    if result is None and not settings.musixmatch_enabled:
        # Second source without a Render key: tiny local allowlist (tests / demo).
        result = _try_mock_local(title, artist)

    if result is not None:
        result = LyricsResult(
            song_id=song_id,
            title=result.title,
            artist=result.artist,
            lyrics=result.lyrics,
            source=result.source,
            genius_url=None,
        )

    ttl = CACHE_TTL_HIT_S if result else CACHE_TTL_MISS_S
    with _cache_lock:
        _cache[song_id] = _CacheEntry(result=result, expires_at=now + ttl)
    return result


__all__ = [
    "LyricsResult",
    "get_lyrics_for_song",
    "clear_lyrics_cache",
    "reset_lyrics_clients",
]
