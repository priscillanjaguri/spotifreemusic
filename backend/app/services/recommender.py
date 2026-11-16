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
from app.ml.scorer import build_song_features
from app.ml.taste import Signal, TasteProfile, blend_profiles, build_taste_profile, cold_start_from_genres
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
from app.services import impressions as impressions_svc
from app.services import scorer_job
from app.services import sequential_job

log = logging.getLogger(__name__)

Mode = Literal["taste", "similar", "popular", "genre_seed"]


@dataclass
class RecommendationResult:
    items: list[tuple[Song, RankedItem]]
    cold_start: bool
    mode: Mode
    short_term_days: int
    long_term_days: int
    scorer_applied: bool = False
    sequential_applied: bool = False
    request_id: uuid.UUID | None = None


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


def _normalize_providers(
    provider: MusicProviderAdapter | None = None,
    providers: list[MusicProviderAdapter] | None = None,
) -> list[MusicProviderAdapter]:
    if providers:
        return list(providers)
    if provider is not None:
        return [provider]
    return []


def _seed_provider_candidates(
    db: Session,
    providers: list[MusicProviderAdapter],
    genres: list[str],
    *,
    limit_per_tag: int = 12,
) -> list[Song]:
    """Fresh tag-seeded searches to widen the candidate pool beyond the local cache."""
    if not providers or not genres:
        return []
    imported: list[Song] = []
    for adapter in providers:
        for tag in genres[:6]:
            try:
                tracks = adapter.search_tracks(tag, limit=limit_per_tag)
            except ProviderError as exc:
                log.info("Provider seed search failed for %s/%r: %s", adapter.key, tag, exc)
                continue
            if tracks:
                imported.extend(import_tracks(db, adapter, tracks))
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


def _top_profile_genre_names(features: FeatureMatrix, profile: TasteProfile, n: int = 8) -> list[str]:
    if profile.is_empty or not features.genre_vocab:
        return []
    gdim = len(features.genre_vocab)
    weights = profile.vector[:gdim]
    order = np.argsort(-weights)[:n]
    return [features.genre_vocab[i] for i in order if weights[i] > 0]


def _user_listen_stats(
    db: Session, user_id, now: datetime
) -> tuple[dict[int, int], dict[int, float]]:
    """Return (play_counts, days_since_last_play) for the user."""
    events = db.scalars(
        select(ListeningEvent)
        .where(ListeningEvent.user_id == user_id)
        .order_by(ListeningEvent.started_at.desc())
        .limit(5000)
    ).all()
    counts: dict[int, int] = {}
    last_at: dict[int, datetime] = {}
    for ev in events:
        sid = int(ev.song_id)
        counts[sid] = counts.get(sid, 0) + 1
        if sid not in last_at:
            last_at[sid] = ev.started_at
    days: dict[int, float] = {}
    for sid, at in last_at.items():
        started = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
        days[sid] = max(0.0, (now - started).total_seconds() / 86400.0)
    return counts, days


def _apply_engagement_scorer(
    db: Session,
    ranked: list[RankedItem],
    *,
    by_id: dict[int, Song],
    profile_genres: list[str],
    play_counts: dict[int, int],
    days_since: dict[int, float],
) -> tuple[list[RankedItem], dict[int, dict], bool]:
    """Re-rank cosine candidates by P(engage). Returns (ranked, feat_by_song, applied)."""
    feat_by_song: dict[int, dict] = {}
    feature_rows: list[dict] = []
    song_ids: list[int] = []
    for item in ranked:
        song = by_id.get(item.song_id)
        if song is None:
            continue
        feats = song.features
        feat = build_song_features(
            cosine_score=item.score,
            song_genres=[g.name for g in song.genres],
            profile_genres=profile_genres,
            from_library=song.owner_user_id is not None,
            energy=feats.energy if feats else None,
            tempo=feats.tempo if feats else None,
            user_plays=play_counts.get(item.song_id, 0),
            days_since_play=days_since.get(item.song_id),
        )
        feat_by_song[item.song_id] = feat
        feature_rows.append(feat)
        song_ids.append(item.song_id)

    if not feature_rows or not scorer_job.scorer_ready(db):
        return ranked, feat_by_song, False

    scores = scorer_job.score_candidates(db, feature_rows)
    if scores is None:
        return ranked, feat_by_song, False
    engage = {sid: p for sid, p in zip(song_ids, scores)}
    return scorer_job.rerank_by_engagement(ranked, engage), feat_by_song, True


def _log_served_impressions(
    db: Session,
    user: User,
    explained: list[RankedItem],
    *,
    cosine_by_id: dict[int, float],
    feat_by_song: dict[int, dict],
    by_id: dict[int, Song],
    profile_genres: list[str],
    play_counts: dict[int, int],
    days_since: dict[int, float],
) -> uuid.UUID:
    request_id = uuid.uuid4()
    items: list[tuple[int, float, dict]] = []
    for item in explained:
        song = by_id.get(item.song_id)
        if song is None:
            continue
        cosine = float(cosine_by_id.get(item.song_id, item.score))
        feat = feat_by_song.get(item.song_id)
        if feat is None:
            feats = song.features
            feat = build_song_features(
                cosine_score=cosine,
                song_genres=[g.name for g in song.genres],
                profile_genres=profile_genres,
                from_library=song.owner_user_id is not None,
                energy=feats.energy if feats else None,
                tempo=feats.tempo if feats else None,
                user_plays=play_counts.get(item.song_id, 0),
                days_since_play=days_since.get(item.song_id),
            )
        items.append((item.song_id, cosine, feat))
    impressions_svc.log_impressions(db, user.id, request_id=request_id, items=items)
    return request_id


def recommend_for_user(
    db: Session,
    user: User,
    *,
    limit: int = 20,
    provider: MusicProviderAdapter | None = None,
    providers: list[MusicProviderAdapter] | None = None,
    now: datetime | None = None,
) -> RecommendationResult:
    now = now or datetime.now(timezone.utc)
    prefs = user.preferences
    exclude = latest_not_interested_ids(db, user.id)
    catalogue = _normalize_providers(provider, providers)

    # Seed genres: preferred (onboarding) else top genres from the user's collection.
    seed_genres = list(prefs.preferred_genres or [])
    if not seed_genres:
        from app.services.collection import collection_facets

        facets = collection_facets(db, user.id)
        seed_genres = [name for _id, name, _count in facets["genres"][:8]]

    _seed_provider_candidates(db, catalogue, seed_genres or ["lofi", "pop", "electronic", "jazz"])

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

    cosine_by_id = {r.song_id: r.score for r in ranked}
    profile_genres = _top_profile_genre_names(features, profile) or [g.lower() for g in seed_genres]
    play_counts, days_since = _user_listen_stats(db, user.id, now)

    # Sequential next-track candidates ∪ cosine → (optional) P(engage) → MMR.
    sequential_applied = False
    if sequential_job.sequential_ready(db):
        seeds = sequential_job.recent_seed_song_ids(db, user.id, now=now)
        seq_ranked = sequential_job.sequential_candidates(
            db,
            seed_song_ids=seeds,
            exclude=exclude | set(seeds),
        )
        if seq_ranked:
            # Ensure sequential-only songs are in the feature matrix / by_id map.
            missing_ids = {r.song_id for r in seq_ranked if r.song_id not in by_id}
            if missing_ids:
                more = _load_candidate_songs(db, user, extra_ids=missing_ids)
                for s in more:
                    if s.id not in by_id:
                        songs.append(s)
                        by_id[s.id] = s
                features = build_feature_matrix([_song_row(s) for s in songs])
            ranked, seq_ids = sequential_job.merge_candidates(ranked, seq_ranked)
            sequential_applied = bool(seq_ids)
            # Preserve original cosine scores for impression logging; seq-only → their score.
            for r in ranked:
                cosine_by_id.setdefault(r.song_id, r.score)

    # Merged candidates → learned P(engage) re-rank → MMR + exploration.
    ranked, feat_by_song, scorer_applied = _apply_engagement_scorer(
        db,
        ranked,
        by_id=by_id,
        profile_genres=profile_genres,
        play_counts=play_counts,
        days_since=days_since,
    )

    diverse = mmr_select(features, ranked, k=limit, lambda_relevance=0.72)
    final = inject_exploration(features, diverse, ranked, k=limit, explore_frac=0.15)
    meta = {s.id: _song_row(s) for s in songs}
    explained = explain_recommendations(features, profile, final, song_meta=meta)

    request_id = _log_served_impressions(
        db,
        user,
        explained,
        cosine_by_id=cosine_by_id,
        feat_by_song=feat_by_song,
        by_id=by_id,
        profile_genres=profile_genres,
        play_counts=play_counts,
        days_since=days_since,
    )

    items = [(by_id[r.song_id], r) for r in explained if r.song_id in by_id]
    return RecommendationResult(
        items=items,
        cold_start=mode != "taste",
        mode=mode,
        short_term_days=prefs.short_term_days,
        long_term_days=prefs.long_term_days,
        scorer_applied=scorer_applied,
        sequential_applied=sequential_applied,
        request_id=request_id,
    )


def similar_songs(
    db: Session,
    user: User,
    song_id: int,
    *,
    limit: int = 12,
    provider: MusicProviderAdapter | None = None,
    providers: list[MusicProviderAdapter] | None = None,
) -> RecommendationResult:
    song = db.get(Song, song_id, options=[*SONG_LOAD, selectinload(Song.features)])
    if song is None or (song.owner_user_id is not None and song.owner_user_id != user.id):
        raise LookupError("song")

    seed_genres = [g.name for g in song.genres]
    catalogue = _normalize_providers(provider, providers)
    _seed_provider_candidates(db, catalogue, seed_genres or ["pop"], limit_per_tag=10)

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
