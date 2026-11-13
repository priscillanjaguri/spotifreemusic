"""Enrich catalogue / library songs with Spotify metadata (no streaming).

When SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET are set, we match a song by
title + primary artist, store a non-playback SongProviderLink (key=spotify),
merge artist genres, and fill missing song_features from Spotify audio-features.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.models import Genre, MusicProvider, Song, SongArtist, SongFeatures, SongProviderLink
from app.providers.base import ProviderError
from app.providers.spotify_metadata import (
    SpotifyMetadataClient,
    SpotifyTrackMatch,
    build_spotify_client,
)

log = logging.getLogger(__name__)

SPOTIFY_PROVIDER_KEY = "spotify"
SPOTIFY_DISPLAY_NAME = "Spotify (metadata)"
ANALYZER_LABEL = "spotify-audio-features"


def _norm(text: str) -> str:
    t = text.casefold().strip()
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def _score_match(song: Song, primary_artist: str | None, candidate: SpotifyTrackMatch) -> float:
    title_score = 1.0 if _norm(song.title) == _norm(candidate.name) else (
        0.6 if _norm(song.title) in _norm(candidate.name) or _norm(candidate.name) in _norm(song.title) else 0.0
    )
    artist_score = 0.0
    if primary_artist and candidate.artists:
        cand_names = [_norm(a.name) for a in candidate.artists]
        pa = _norm(primary_artist)
        if pa in cand_names:
            artist_score = 1.0
        elif any(pa in n or n in pa for n in cand_names if n):
            artist_score = 0.7
    duration_score = 0.0
    if song.duration_ms and candidate.duration_ms:
        delta = abs(int(song.duration_ms) - int(candidate.duration_ms))
        if delta <= 2_000:
            duration_score = 1.0
        elif delta <= 8_000:
            duration_score = 0.5
    return title_score * 0.5 + artist_score * 0.35 + duration_score * 0.15


def ensure_spotify_provider_row(db: Session) -> MusicProvider:
    row = db.scalar(select(MusicProvider).where(MusicProvider.key == SPOTIFY_PROVIDER_KEY))
    if row is None:
        db.execute(
            insert(MusicProvider)
            .values(
                key=SPOTIFY_PROVIDER_KEY,
                display_name=SPOTIFY_DISPLAY_NAME,
                is_configured=True,
                supports_playback=False,
                is_mock=False,
            )
            .on_conflict_do_nothing(index_elements=["key"])
        )
        row = db.scalar(select(MusicProvider).where(MusicProvider.key == SPOTIFY_PROVIDER_KEY))
    assert row is not None
    row.is_configured = True
    row.supports_playback = False  # never enable Spotify playback in Spotifree
    row.is_mock = False
    row.display_name = SPOTIFY_DISPLAY_NAME
    db.flush()
    return row


def _genre(db: Session, name: str) -> Genre:
    genre = db.scalars(select(Genre).where(Genre.name == name)).first()
    if genre is None:
        genre = Genre(name=name)
        db.add(genre)
        db.flush()
    return genre


def _primary_artist_name(song: Song) -> str | None:
    links = sorted(song.artist_links or [], key=lambda l: l.position)
    if not links:
        return None
    return links[0].artist.name if links[0].artist else None


def _pick_best(
    song: Song,
    primary_artist: str | None,
    candidates: list[SpotifyTrackMatch],
) -> SpotifyTrackMatch | None:
    if not candidates:
        return None
    ranked = sorted(
        (( _score_match(song, primary_artist, c), c) for c in candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    best_score, best = ranked[0]
    return best if best_score >= 0.55 else None


def _merge_features(row: SongFeatures, *, from_spotify: dict, feature_source: str) -> None:
    """Fill empty numeric fields from Spotify; do not overwrite Librosa measurements."""
    for key, value in from_spotify.items():
        if value is None:
            continue
        current = getattr(row, key, None)
        if current is None:
            setattr(row, key, value)
    # Mark analyzer when we contributed Spotify audio-features.
    if row.analyzer and "spotify" not in row.analyzer:
        row.analyzer = f"{row.analyzer}+{ANALYZER_LABEL}"[:50]
    elif not row.analyzer:
        row.analyzer = ANALYZER_LABEL
    row.analyzed_at = row.analyzed_at or datetime.now(timezone.utc)
    # Keep existing feature_source if already set; otherwise use caller hint.
    if not row.feature_source:
        row.feature_source = feature_source


def enrich_song_with_spotify(
    db: Session,
    song: Song,
    *,
    client: SpotifyMetadataClient | None = None,
    settings: Settings | None = None,
) -> bool:
    """Best-effort Spotify metadata enrich. Returns True when a match was applied."""
    settings = settings or get_settings()
    owns_client = client is None
    client = client or build_spotify_client(settings.spotify_client_id, settings.spotify_client_secret)
    if client is None:
        return False

    try:
        # Reload with relationships if needed.
        if song.artist_links is None or song.genres is None:
            song = db.scalars(
                select(Song)
                .where(Song.id == song.id)
                .options(
                    selectinload(Song.artist_links).selectinload(SongArtist.artist),
                    selectinload(Song.genres),
                    selectinload(Song.features),
                    selectinload(Song.provider_links).selectinload(SongProviderLink.provider),
                )
            ).one()

        provider = ensure_spotify_provider_row(db)
        existing = next(
            (l for l in (song.provider_links or []) if l.provider and l.provider.key == SPOTIFY_PROVIDER_KEY),
            None,
        )
        primary = _primary_artist_name(song)
        if existing is None:
            query = f"track:{song.title}"
            if primary:
                query += f" artist:{primary}"
            try:
                candidates = client.search_tracks(query, limit=5)
            except ProviderError as exc:
                log.info("Spotify search failed for song %s: %s", song.id, exc)
                return False
            match = _pick_best(song, primary, candidates)
            if match is None:
                return False
            link = SongProviderLink(
                song_id=song.id,
                provider_id=provider.id,
                provider_track_id=match.id,
                playback_uri=None,  # metadata only — never a stream URL
                license_url=None,
                download_allowed=False,
            )
            db.add(link)
            db.flush()
            if match.isrc and not song.isrc:
                # Avoid unique conflicts: only set when free.
                clash = db.scalar(select(Song).where(Song.isrc == match.isrc, Song.id != song.id))
                if clash is None:
                    song.isrc = match.isrc
            track_id = match.id
            artist_ids = [a.id for a in match.artists if a.id]
        else:
            track_id = existing.provider_track_id
            try:
                matched = client.get_track(track_id)
            except ProviderError:
                matched = None
            artist_ids = [a.id for a in matched.artists if a.id] if matched else []

        # Genres from Spotify artists.
        try:
            genres = client.artist_genres(artist_ids) if artist_ids else []
        except ProviderError as exc:
            log.info("Spotify artist genres failed for song %s: %s", song.id, exc)
            genres = []
        if genres:
            existing_names = {g.name for g in (song.genres or [])}
            for name in genres:
                if name not in existing_names:
                    song.genres.append(_genre(db, name))
                    existing_names.add(name)

        # Audio features (may be restricted by Spotify for some apps — skip quietly).
        try:
            feats = client.audio_features(track_id)
        except ProviderError as exc:
            log.info("Spotify audio-features failed for song %s: %s", song.id, exc)
            feats = None

        if feats is not None:
            row = db.get(SongFeatures, song.id) or SongFeatures(song_id=song.id)
            source = song.data_source if song.data_source in ("provider", "mock_dev", "user_provided") else "provider"
            _merge_features(
                row,
                from_spotify={
                    "tempo": feats.tempo,
                    "energy": feats.energy,
                    "danceability": feats.danceability,
                    "acousticness": feats.acousticness,
                    "valence": feats.valence,
                    "instrumentalness": feats.instrumentalness,
                    "loudness_db": feats.loudness_db,
                    "key": feats.key,
                    "mode": feats.mode,
                },
                feature_source=source,
            )
            if not row.feature_source:
                row.feature_source = source
            db.add(row)

        db.flush()
        return True
    except ProviderError as exc:
        log.info("Spotify enrichment skipped for song %s: %s", getattr(song, "id", None), exc)
        return False
    finally:
        if owns_client and client is not None:
            client.close()


def enrich_songs_best_effort(db: Session, songs: list[Song], *, settings: Settings | None = None) -> int:
    """Enrich a batch; returns how many songs received a Spotify match."""
    settings = settings or get_settings()
    client = build_spotify_client(settings.spotify_client_id, settings.spotify_client_secret)
    if client is None or not songs:
        return 0
    applied = 0
    try:
        for song in songs:
            if enrich_song_with_spotify(db, song, client=client, settings=settings):
                applied += 1
    finally:
        client.close()
    return applied
