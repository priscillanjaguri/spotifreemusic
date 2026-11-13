"""Orchestrates recommendations: load signals + catalogue features, call ml/, shape results.

Dependency direction: services -> ml (never the reverse).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ml.features import FeatureMatrix, build_feature_matrix
from app.ml.rank import (
    RankedItem,
    explain_recommendations,
    inject_exploration,
    mmr_select,
    rank_by_cosine,
    similar_to_seed,
)
from app.ml.taste import Signal, blend_profiles, build_taste_profile, cold_start_from_genres
from app.models import (
    ListeningEvent,
    Song,
    SongFeatures,
    User,
    UserCollection,
    UserInteraction,
    UserPreferences,
)
from app.providers.base import MusicProviderAdapter, ProviderError
from app.services.catalog import import_tracks
from app.services.collection import SONG_LOAD
from app.services.feedback import latest_not_interested_ids

log = logging.getLogger(__name__)

Mode = Literal["taste", "similar", "popular", "genre_seed"]


@dataclass
class RecommendationResult:
    items: list[tuple[Song, RankedItem]]
    cold_start: bool
    mode: Mode
    short_term_days: int
    long_term_days: int


def _song_row(song: Song) -> dict:
    feats = song.features
    return {
        "id": song.id,
        "genres": [g.name for g in song.genres],
        "tempo": feats.tempo if feats else None,
        "energy": feats.energy if feats else None,
        "loudness_db": feats.loudness_db if feats else None,
        "spectral_centroid_hz": feats.spectral_centroid_hz if feats else None,
        "spectral_rolloff_hz": feats.spectral_rolloff_hz if feats else None,
        "zero_crossing_rate": feats.zero_crossing_rate if feats else None,
        "danceability": feats.danceability if feats else None,
        "acousticness": feats.acousticness if feats else None,
        "valence": feats.valence if feats else None,
        "instrumentalness": feats.instrumentalness if feats else None,
        "key": feats.key if feats else None,
        "mode": feats.mode if feats else None,
        "from_library": song.owner_user_id is not None,
    }


def _load_candidate_songs(
    db: Session,
    user: User,
    *,
    extra_ids: set[int] | None = None,
) -> list[Song]:
    """Cached catalogue songs the user may see, plus their private library tracks."""
    ban_private = (Song.owner_user_id.is_(None)) | (Song.owner_user_id == user.id)
    q = (
        select(Song)
        .where(ban_private)
        .options(*SONG_LOAD, selectinload(Song.features))
        .order_by(Song.id.desc())
        .limit(800)
    )
    songs = list(db.scalars(q).unique().all())
    if extra_ids:
        missing = extra_ids - {s.id for s in songs}
        if missing:
            more = list(
                db.scalars(
                    select(Song)
                    .where(Song.id.in_(missing), ban_private)
                    .options(*SONG_LOAD, selectinload(Song.features))
                ).unique().all()
            )
            songs.extend(more)
    return songs


def _seed_provider_candidates(
    db: Session,
    provider: MusicProviderAdapter | None,
    genres: list[str],
    *,
    limit_per_tag: int = 12,
) -> list[Song]:
    """Fresh tag-seeded searches to widen the candidate pool beyond the local cache."""
    if provider is None or not genres:
        return []
    imported: list[Song] = []
    for tag in genres[:6]:
        try:
            tracks = provider.search_tracks(tag, limit=limit_per_tag)
        except ProviderError as exc:
            log.info("Provider seed search failed for %r: %s", tag, exc)
            continue
        if tracks:
            imported.extend(import_tracks(db, provider, tracks))
    db.flush()
    return imported


def _collect_signals(db: Session, user: User, prefs: UserPreferences, now: datetime) -> list[Signal]:
    signals: list[Signal] = []

    # Explicit likes (interested). Skips / dismissed / not_interested are ignored here.
    interactions = db.scalars(
        select(UserInteraction)
        .where(
            UserInteraction.user_id == user.id,
            UserInteraction.song_id.is_not(None),
            UserInteraction.interaction_type.in_(("interested", "saved")),
        )
        .order_by(UserInteraction.created_at.desc())
        .limit(2000)
    ).all()
    for row in interactions:
        signals.append(Signal(song_id=int(row.song_id), kind=row.interaction_type, at=row.created_at))

    # Saves from the collection (source doesn't matter; weight is "saved").
    saves = db.scalars(
        select(UserCollection)
        .where(UserCollection.user_id == user.id)
        .order_by(UserCollection.added_at.desc())
        .limit(1000)
    ).all()
    for row in saves:
        signals.append(Signal(song_id=row.song_id, kind="saved", at=row.added_at))

    # Listening: play / completed / replay. Neutrals (tiny blips) already filtered at insert.
    events = db.scalars(
        select(ListeningEvent)
        .where(ListeningEvent.user_id == user.id)
        .order_by(ListeningEvent.started_at.desc())
        .limit(3000)
    ).all()
    plays_per_song: dict[int, int] = {}
    for ev in events:
        sid = ev.song_id
        plays_per_song[sid] = plays_per_song.get(sid, 0) + 1
        if ev.completed:
            kind = "replay" if plays_per_song[sid] > 1 else "completed"
        else:
            kind = "replay" if plays_per_song[sid] > 1 else "play"
        signals.append(Signal(song_id=sid, kind=kind, at=ev.started_at))

    return signals


def _popular_fallback(features: FeatureMatrix, exclude: set[int], limit: int) -> list[RankedItem]:
    """When we have no taste, prefer songs with richer tags (proxy for 'popular' in cache)."""
    if features.matrix.size == 0:
        return []
    gdim = len(features.genre_vocab)
    richness = features.matrix[:, :gdim].sum(axis=1) if gdim else np.zeros(len(features.song_ids))
    # Slight noise so ties don't always return the same order.
    rng = np.random.default_rng(42)
    scores = richness + rng.normal(0, 0.01, size=len(richness))
    order = np.argsort(-scores)
    out: list[RankedItem] = []
    for idx in order:
        sid = int(features.song_ids[idx])
        if sid in exclude:
            continue
        out.append(RankedItem(song_id=sid, score=float(scores[idx])))
        if len(out) >= limit:
            break
    return out


def recommend_for_user(
    db: Session,
    user: User,
    *,
    limit: int = 20,
    provider: MusicProviderAdapter | None = None,
    now: datetime | None = None,
) -> RecommendationResult:
    now = now or datetime.now(timezone.utc)
    prefs = user.preferences
    exclude = latest_not_interested_ids(db, user.id)

    # Seed genres: preferred (onboarding) else top genres from the user's collection.
    seed_genres = list(prefs.preferred_genres or [])
    if not seed_genres:
        from app.services.collection import collection_facets

        facets = collection_facets(db, user.id)
        seed_genres = [name for _id, name, _count in facets["genres"][:8]]

    _seed_provider_candidates(db, provider, seed_genres or ["lofi", "pop", "electronic", "jazz"])

    songs = _load_candidate_songs(db, user)
    rows = [_song_row(s) for s in songs]
    features = build_feature_matrix(rows)
    by_id = {s.id: s for s in songs}

    signals = _collect_signals(db, user, prefs, now)
    short = build_taste_profile(features, signals, now=now, window_days=prefs.short_term_days)
    long = build_taste_profile(features, signals, now=now, window_days=prefs.long_term_days)
    profile = blend_profiles(short, long, short_weight=0.6)

    cold = profile.is_empty
    mode: Mode = "taste"
    if cold and seed_genres:
        profile = cold_start_from_genres(features, seed_genres)
        mode = "genre_seed"
        cold = profile.is_empty
    if cold:
        ranked = _popular_fallback(features, exclude, limit=limit * 4)
        mode = "popular"
    else:
        ranked = rank_by_cosine(features, profile, exclude=exclude, limit=limit * 5)

    diverse = mmr_select(features, ranked, k=limit, lambda_relevance=0.72)
    final = inject_exploration(features, diverse, ranked, k=limit, explore_frac=0.15)
    meta = {s.id: _song_row(s) for s in songs}
    explained = explain_recommendations(features, profile, final, song_meta=meta)

    items = [(by_id[r.song_id], r) for r in explained if r.song_id in by_id]
    return RecommendationResult(
        items=items,
        cold_start=mode != "taste",
        mode=mode,
        short_term_days=prefs.short_term_days,
        long_term_days=prefs.long_term_days,
    )


def similar_songs(
    db: Session,
    user: User,
    song_id: int,
    *,
    limit: int = 12,
    provider: MusicProviderAdapter | None = None,
) -> RecommendationResult:
    song = db.get(Song, song_id, options=[*SONG_LOAD, selectinload(Song.features)])
    if song is None or (song.owner_user_id is not None and song.owner_user_id != user.id):
        raise LookupError("song")

    seed_genres = [g.name for g in song.genres]
    _seed_provider_candidates(db, provider, seed_genres or ["pop"], limit_per_tag=10)

    exclude = latest_not_interested_ids(db, user.id)
    songs = _load_candidate_songs(db, user, extra_ids={song_id})
    features = build_feature_matrix([_song_row(s) for s in songs])
    by_id = {s.id: s for s in songs}

    ranked = similar_to_seed(features, song_id, exclude=exclude, limit=limit * 3)
    diverse = mmr_select(features, ranked, k=limit, lambda_relevance=0.65)
    profile = build_taste_profile(
        features,
        [Signal(song_id=song_id, kind="interested", at=datetime.now(timezone.utc))],
        window_days=365,
    )
    meta = {s.id: _song_row(s) for s in songs}
    # Nudge explanations toward the seed song.
    for i, item in enumerate(diverse):
        from app.ml.rank import Explanation

        diverse[i] = RankedItem(
            song_id=item.song_id,
            score=item.score,
            explanations=(Explanation("more_like", f"More like {song.title}"),),
        )
    explained = explain_recommendations(features, profile, diverse, song_meta=meta)
    items = [(by_id[r.song_id], r) for r in explained if r.song_id in by_id]
    prefs = user.preferences
    return RecommendationResult(
        items=items,
        cold_start=False,
        mode="similar",
        short_term_days=prefs.short_term_days,
        long_term_days=prefs.long_term_days,
    )
