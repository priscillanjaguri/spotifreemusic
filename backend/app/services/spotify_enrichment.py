"""Enrich catalogue / library songs with Spotify metadata (no streaming).

When SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET are set, we match a song by
title + primary artist, store a non-playback SongProviderLink (key=spotify),
merge artist genres, fill missing cover/artist images, and fill missing
song_features from Spotify audio-features.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.models import Artist, Genre, MusicProvider, Song, SongArtist, SongFeatures, SongProviderLink
from app.providers.base import ProviderError
from app.providers.spotify_metadata import (
    SpotifyArtistRef,
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


def _apply_album_cover(song: Song, album_image_url: str | None) -> None:
    """Fill missing song cover from Spotify album art; never overwrite existing art."""
    if album_image_url and not song.cover_url:
        song.cover_url = album_image_url


def _apply_artist_images(
    song: Song,
    *,
    spotify_artists: list[SpotifyArtistRef],
) -> None:
    """Fill missing Artist.image_url from Spotify artist photos (match by name)."""
    by_name = {_norm(a.name): a.image_url for a in spotify_artists if a.name and a.image_url}
    if not by_name:
        return
    for link in song.artist_links or []:
        artist: Artist | None = link.artist
        if artist is None or artist.image_url:
            continue
        url = by_name.get(_norm(artist.name))
        if url:
            artist.image_url = url


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
        matched: SpotifyTrackMatch | None = None
        if existing is None:
            query = f"track:{song.title}"
            if primary:
                query += f" artist:{primary}"
            try:
                candidates = client.search_tracks(query, limit=5)
            except ProviderError as exc:
                log.info("Spotify search failed for song %s: %s", song.id, exc)
                return False
            matched = _pick_best(song, primary, candidates)
            if matched is None:
                return False
            link = SongProviderLink(
                song_id=song.id,
                provider_id=provider.id,
                provider_track_id=matched.id,
                playback_uri=None,  # metadata only — never a stream URL
                license_url=None,
                download_allowed=False,
            )
            db.add(link)
            db.flush()
            if matched.isrc and not song.isrc:
                # Avoid unique conflicts: only set when free.
                clash = db.scalar(select(Song).where(Song.isrc == matched.isrc, Song.id != song.id))
                if clash is None:
                    song.isrc = matched.isrc
            track_id = matched.id
            artist_ids = [a.id for a in matched.artists if a.id]
        else:
            track_id = existing.provider_track_id
            try:
                matched = client.get_track(track_id)
            except ProviderError:
                matched = None
            artist_ids = [a.id for a in matched.artists if a.id] if matched else []

        # Album cover from the matched track (only when song has no cover yet).
        if matched is not None:
            _apply_album_cover(song, matched.album_image_url)

        # Genres + artist photos from one Spotify /artists call.
        spotify_artists: list[SpotifyArtistRef] = []
        try:
            spotify_artists = client.get_artists(artist_ids) if artist_ids else []
        except ProviderError as exc:
            log.info("Spotify artists fetch failed for song %s: %s", song.id, exc)
            spotify_artists = []

        if spotify_artists:
            _apply_artist_images(song, spotify_artists=spotify_artists)
            genre_names = sorted({g for a in spotify_artists for g in a.genres})
            if genre_names:
                existing_names = {g.name for g in (song.genres or [])}
                for name in genre_names:
                    if name not in existing_names:
                        song.genres.append(_genre(db, name))
                        existing_names.add(name)

        # If still no cover, fall back to the primary artist's Spotify photo.
        if not song.cover_url:
            for link in sorted(song.artist_links or [], key=lambda l: l.position):
                if link.artist and link.artist.image_url:
                    song.cover_url = link.artist.image_url
                    break

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


def enrich_library_songs_for_user(
    db: Session,
    user_id,
    *,
    settings: Settings | None = None,
    limit: int = 200,
) -> dict[str, int]:
    """Re-enrich the user's My Library songs (backfill covers / artist images).

    Returns counts: scanned, matched, covers_filled, artist_images_filled.
    """
    from uuid import UUID

    from app.models import LibraryUpload

    settings = settings or get_settings()
    if not settings.spotify_enabled:
        return {"scanned": 0, "matched": 0, "covers_filled": 0, "artist_images_filled": 0, "spotify_enabled": 0}

    uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
    uploads = db.scalars(
        select(LibraryUpload)
        .where(LibraryUpload.user_id == uid, LibraryUpload.song_id.is_not(None))
        .order_by(LibraryUpload.id.desc())
        .limit(max(1, min(limit, 500)))
    ).all()
    song_ids = [u.song_id for u in uploads if u.song_id]
    if not song_ids:
        return {"scanned": 0, "matched": 0, "covers_filled": 0, "artist_images_filled": 0, "spotify_enabled": 1}

    songs = list(
        db.scalars(
            select(Song)
            .where(Song.id.in_(song_ids))
            .options(
                selectinload(Song.artist_links).selectinload(SongArtist.artist),
                selectinload(Song.genres),
                selectinload(Song.features),
                selectinload(Song.provider_links).selectinload(SongProviderLink.provider),
            )
        ).all()
    )

    before_cover = {s.id: s.cover_url for s in songs}
    before_artist = {
        a.id: a.image_url
        for s in songs
        for a in (link.artist for link in (s.artist_links or []) if link.artist)
    }

    matched = enrich_songs_best_effort(db, songs, settings=settings)
    db.flush()

    covers_filled = sum(1 for s in songs if not before_cover.get(s.id) and s.cover_url)
    artist_images_filled = sum(
        1
        for s in songs
        for link in (s.artist_links or [])
        if link.artist
        and not before_artist.get(link.artist.id)
        and link.artist.image_url
    )
    return {
        "scanned": len(songs),
        "matched": matched,
        "covers_filled": covers_filled,
        "artist_images_filled": artist_images_filled,
        "spotify_enabled": 1,
    }
