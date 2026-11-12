"""Analyse provider tracks when the stored licence / download flag permits it.

Temporary audio is fetched, measured with Librosa, then discarded. Features are
stored on song_features with feature_source matching the catalogue data_source.
"""
from __future__ import annotations

import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analysis import AnalysisUnavailable, analyze_file, librosa_available
from app.models import Song, SongFeatures, SongProviderLink
from app.providers.base import MusicProviderAdapter, ProviderError
from app.providers.jamendo import JamendoAdapter

log = logging.getLogger(__name__)


def songs_needing_provider_analysis(db: Session, *, limit: int = 20, user_id: uuid.UUID | None = None) -> list[Song]:
    """Catalogue songs with download_allowed links and no song_features yet."""
    q = (
        select(Song)
        .join(SongProviderLink, SongProviderLink.song_id == Song.id)
        .outerjoin(SongFeatures, SongFeatures.song_id == Song.id)
        .where(
            SongProviderLink.download_allowed.is_(True),
            SongFeatures.song_id.is_(None),
            Song.owner_user_id.is_(None),  # never re-analyse private uploads here
        )
        .options(selectinload(Song.provider_links).selectinload(SongProviderLink.provider))
        .limit(limit)
    )
    return list(db.scalars(q).unique().all())


def analyse_provider_song(db: Session, adapter: MusicProviderAdapter, song: Song) -> SongFeatures | None:
    """Download (temporarily) and analyse one song. Returns None if not permitted or unavailable."""
    if not librosa_available():
        return None
    link = next((l for l in song.provider_links if l.download_allowed and l.provider_track_id), None)
    if link is None or not link.license_url:
        return None
    if not isinstance(adapter, JamendoAdapter) and not hasattr(adapter, "download_track_bytes"):
        return None

    try:
        raw = adapter.download_track_bytes(link.provider_track_id)  # type: ignore[attr-defined]
    except (ProviderError, AttributeError) as exc:
        log.info("Skipping analysis for song %s: %s", song.id, exc)
        return None

    suffix = ".mp3"
    with tempfile.TemporaryDirectory(prefix="tunewise-provider-") as tmp:
        path = Path(tmp) / f"track{suffix}"
        path.write_bytes(raw)
        try:
            features = analyze_file(path)
        except (AnalysisUnavailable, ValueError) as exc:
            log.info("Analysis failed for song %s: %s", song.id, exc)
            return None

    row = db.get(SongFeatures, song.id) or SongFeatures(song_id=song.id)
    for name, value in features.as_dict().items():
        setattr(row, name, value)
    row.analyzed_at = datetime.now(timezone.utc)
    row.feature_source = song.data_source if song.data_source in ("provider", "mock_dev", "user_provided") else "provider"
    db.add(row)
    db.flush()
    return row
