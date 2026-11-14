"""Continuous recommender evaluation: hold-out ranking → metrics → snapshot.

Reuses the pure ml/ stack (features → cosine → MMR → exploration) against
listening + feedback already in the database. Falls back to the synthetic
catalogue from scripts.eval_recommender when too few real users qualify.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ml.eval import summarise_run
from app.ml.features import build_feature_matrix
from app.ml.rank import inject_exploration, mmr_select, rank_by_cosine
from app.ml.taste import Signal, blend_profiles, build_taste_profile
from app.models import (
    EvalSnapshot,
    ListeningEvent,
    Song,
    User,
    UserCollection,
    UserInteraction,
)
from app.services.recommender import _song_row

log = logging.getLogger(__name__)

DEFAULT_K = 10
# Minimum positive song signals (likes/saves) before a user enters a hold-out fold.
MIN_POSITIVES = 4
# Auto-schedule: enough new listening+feedback rows since last snapshot, or daily.
NEW_EVENTS_THRESHOLD = 40
DAILY_INTERVAL = timedelta(hours=24)

METRIC_BLURBS = {
    "precision_at_k": "Of the top-k picks, how often they match songs the user later liked (held out).",
    "recall_at_k": "Of the songs the user liked (held out), how many showed up in the top-k list.",
    "diversity": "How different the top picks are from each other (higher = less repetitive).",
    "coverage": "Share of the catalogue that appeared in at least one recommendation list.",
}


def collect_data_volume(db: Session) -> dict[str, int]:
    return {
        "listening_events": int(db.scalar(select(func.count()).select_from(ListeningEvent)) or 0),
        "interactions": int(db.scalar(select(func.count()).select_from(UserInteraction)) or 0),
        "users": int(db.scalar(select(func.count()).select_from(User)) or 0),
        "catalogue_songs": int(
            db.scalar(select(func.count()).select_from(Song).where(Song.owner_user_id.is_(None))) or 0
        ),
        "collection_saves": int(db.scalar(select(func.count()).select_from(UserCollection)) or 0),
    }


def collect_feedback_counts(db: Session) -> dict[str, int]:
    """Aggregated interaction counts only — never song ids or titles."""
    rows = db.execute(
        select(UserInteraction.interaction_type, func.count())
        .group_by(UserInteraction.interaction_type)
    ).all()
    counts = {str(kind): int(n) for kind, n in rows}
    # Always expose the known keys so the dashboard stays stable.
    for kind in ("interested", "not_interested", "saved", "skipped", "dismissed"):
        counts.setdefault(kind, 0)
    counts["collection_saves"] = int(db.scalar(select(func.count()).select_from(UserCollection)) or 0)
    return counts


def _user_positive_ids(db: Session, user_id) -> list[tuple[int, datetime]]:
    """Liked / saved song ids with timestamps (newest first)."""
    out: list[tuple[int, datetime]] = []
    seen: set[int] = set()
    interactions = db.scalars(
        select(UserInteraction)
        .where(
            UserInteraction.user_id == user_id,
            UserInteraction.song_id.is_not(None),
            UserInteraction.interaction_type.in_(("interested", "saved")),
        )
        .order_by(UserInteraction.created_at.desc())
        .limit(500)
    ).all()
    for row in interactions:
        sid = int(row.song_id)
        if sid in seen:
            continue
        seen.add(sid)
        out.append((sid, row.created_at))
    saves = db.scalars(
        select(UserCollection)
        .where(UserCollection.user_id == user_id)
        .order_by(UserCollection.added_at.desc())
        .limit(500)
    ).all()
    for row in saves:
        if row.song_id in seen:
            continue
        seen.add(row.song_id)
        out.append((row.song_id, row.added_at))
    return out


def _user_play_signals(db: Session, user_id, *, exclude: set[int]) -> list[Signal]:
    events = db.scalars(
        select(ListeningEvent)
        .where(ListeningEvent.user_id == user_id)
        .order_by(ListeningEvent.started_at.desc())
        .limit(2000)
    ).all()
    plays_per_song: dict[int, int] = {}
    signals: list[Signal] = []
    for ev in events:
        if ev.song_id in exclude:
            continue
        plays_per_song[ev.song_id] = plays_per_song.get(ev.song_id, 0) + 1
        if ev.completed:
            kind = "replay" if plays_per_song[ev.song_id] > 1 else "completed"
        else:
            kind = "replay" if plays_per_song[ev.song_id] > 1 else "play"
        signals.append(Signal(song_id=ev.song_id, kind=kind, at=ev.started_at))
    return signals


def _load_public_catalogue(db: Session) -> list[Song]:
    return list(
        db.scalars(
            select(Song)
            .where(Song.owner_user_id.is_(None))
            .options(selectinload(Song.genres), selectinload(Song.features))
            .order_by(Song.id.desc())
            .limit(800)
        ).unique().all()
    )


def _holdout_eval_from_db(db: Session, *, k: int = DEFAULT_K) -> tuple[dict[str, float], str] | None:
    """Per-user hold-out ranking on real likes. Returns None if too little data."""
    songs = _load_public_catalogue(db)
    if len(songs) < 20:
        return None
    features = build_feature_matrix([_song_row(s) for s in songs])
    catalogue_ids = set(features.song_ids)

    users = list(db.scalars(select(User)).all())
    lists: list[list[int]] = []
    relevant_sets: list[set[int]] = []
    now = datetime.now(timezone.utc)

    for user in users:
        positives = [(sid, at) for sid, at in _user_positive_ids(db, user.id) if sid in catalogue_ids]
        if len(positives) < MIN_POSITIVES:
            continue
        # Hold out the newest ~30% (at least 2) as relevant; train on the rest.
        hold_n = max(2, len(positives) // 3)
        holdout = {sid for sid, _ in positives[:hold_n]}
        train = positives[hold_n:]
        if len(train) < 2:
            continue

        train_signals = [
            Signal(song_id=sid, kind="interested", at=at) for sid, at in train
        ]
        train_signals.extend(_user_play_signals(db, user.id, exclude=holdout))
        short = build_taste_profile(features, train_signals, now=now, window_days=28)
        long = build_taste_profile(features, train_signals, now=now, window_days=365)
        profile = blend_profiles(short, long)
        if profile.is_empty:
            continue

        train_ids = {sid for sid, _ in train}
        ranked = rank_by_cosine(features, profile, exclude=set(), limit=k * 5)
        ranked = [r for r in ranked if r.song_id not in train_ids]
        diverse = mmr_select(features, ranked, k=k, lambda_relevance=0.72)
        final = inject_exploration(
            features, diverse, ranked, k=k, explore_frac=0.1, rng=np.random.default_rng(11),
        )
        lists.append([r.song_id for r in final])
        relevant_sets.append(holdout)

    if len(lists) < 1:
        return None

    metrics = summarise_run(features, lists, relevant_sets, k=k)
    metrics["users_evaluated"] = float(len(lists))
    metrics["catalogue_size"] = float(len(features.song_ids))
    return metrics, "holdout"


def _synthetic_eval(*, k: int = DEFAULT_K) -> dict[str, float]:
    """Same fold as scripts.eval_recommender — used when the live DB is too sparse."""
    from scripts.eval_recommender import run_synthetic_eval

    metrics = run_synthetic_eval(k=k)
    metrics["k"] = float(k)
    return metrics


def latest_snapshot(db: Session) -> EvalSnapshot | None:
    return db.scalar(select(EvalSnapshot).order_by(EvalSnapshot.created_at.desc()).limit(1))


def list_snapshots(db: Session, *, limit: int = 30) -> list[EvalSnapshot]:
    return list(
        db.scalars(
            select(EvalSnapshot).order_by(EvalSnapshot.created_at.desc()).limit(limit)
        ).all()
    )


def events_since(db: Session, since: datetime | None) -> int:
    if since is None:
        volume = collect_data_volume(db)
        return volume["listening_events"] + volume["interactions"]
    listens = int(
        db.scalar(
            select(func.count()).select_from(ListeningEvent).where(ListeningEvent.started_at > since)
        )
        or 0
    )
    interactions = int(
        db.scalar(
            select(func.count()).select_from(UserInteraction).where(UserInteraction.created_at > since)
        )
        or 0
    )
    return listens + interactions


def is_due(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    """Whether a new run should fire (daily and/or enough new events)."""
    now = now or datetime.now(timezone.utc)
    snap = latest_snapshot(db)
    if snap is None:
        return {
            "due": True,
            "reason": "never_run",
            "new_events_since_last": events_since(db, None),
            "hours_since_last": None,
        }
    age = now - snap.created_at
    new_events = events_since(db, snap.created_at)
    daily = age >= DAILY_INTERVAL
    volume = new_events >= NEW_EVENTS_THRESHOLD
    reason = None
    if daily and volume:
        reason = "daily_and_volume"
    elif daily:
        reason = "daily"
    elif volume:
        reason = "volume"
    return {
        "due": bool(daily or volume),
        "reason": reason,
        "new_events_since_last": new_events,
        "hours_since_last": round(age.total_seconds() / 3600, 2),
        "threshold_events": NEW_EVENTS_THRESHOLD,
        "daily_hours": DAILY_INTERVAL.total_seconds() / 3600,
    }


def run_eval(db: Session, *, k: int = DEFAULT_K, force_synthetic: bool = False) -> EvalSnapshot:
    """Compute metrics, persist a snapshot, return it (caller commits)."""
    volume = collect_data_volume(db)
    feedback = collect_feedback_counts(db)

    source = "synthetic"
    if force_synthetic:
        metrics = _synthetic_eval(k=k)
    else:
        result = _holdout_eval_from_db(db, k=k)
        if result is None:
            log.info("Not enough real signals for hold-out; using synthetic eval")
            metrics = _synthetic_eval(k=k)
            source = "synthetic"
        else:
            metrics, source = result

    snap = EvalSnapshot(
        metrics={key: float(val) for key, val in metrics.items()},
        data_volume=volume,
        feedback_counts=feedback,
        source=source,
        k=k,
    )
    db.add(snap)
    db.flush()
    return snap


def snapshot_to_dict(snap: EvalSnapshot) -> dict[str, Any]:
    return {
        "id": snap.id,
        "created_at": snap.created_at.isoformat() if snap.created_at else None,
        "metrics": snap.metrics,
        "data_volume": snap.data_volume,
        "feedback_counts": snap.feedback_counts,
        "source": snap.source,
        "k": snap.k,
    }


def build_summary(db: Session) -> dict[str, Any]:
    snap = latest_snapshot(db)
    due = is_due(db)
    if snap is None:
        return {
            "latest": None,
            "metric_blurbs": METRIC_BLURBS,
            "ranking_blurb": (
                "Spotifree builds a taste vector from your likes, saves, and listens, "
                "ranks the catalogue by cosine similarity, then reorders with MMR "
                "(diversity) and a light exploration nudge."
            ),
            "schedule": due,
        }
    return {
        "latest": snapshot_to_dict(snap),
        "metric_blurbs": METRIC_BLURBS,
        "ranking_blurb": (
            "Spotifree builds a taste vector from your likes, saves, and listens, "
            "ranks the catalogue by cosine similarity, then reorders with MMR "
            "(diversity) and a light exploration nudge."
        ),
        "schedule": due,
    }
