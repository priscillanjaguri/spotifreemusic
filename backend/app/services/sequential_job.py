"""Train / load / apply the sequential next-track candidate generator."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.ml.rank import Explanation, RankedItem
from app.ml.sequential import (
    DEFAULT_SESSION_GAP,
    MIN_SESSIONS,
    MIN_TRANSITIONS,
    PlayEvent,
    SequentialModel,
    build_sessions,
    dumps_model,
    loads_model,
    predict_next,
    train_markov,
)
from app.models.listening import ListeningEvent
from app.models.sequential import SequentialModelRow

log = logging.getLogger(__name__)

_active_cache_key: int | None = None
_active_model: SequentialModel | None = None

# How many recent seeds to condition on at serve time.
SERVE_SEED_COUNT = 3
# Max sequential candidates merged into the cosine pool.
SERVE_CANDIDATE_LIMIT = 40


@dataclass
class RetrainResult:
    model_id: int
    n_transitions: int
    n_sessions: int
    n_unique_songs: int
    metrics: dict[str, float]
    activated: bool
    message: str


def history_counts(db: Session, *, user_id=None) -> dict[str, int]:
    """Cheap readiness stats from listening events (optionally one user)."""
    q = select(ListeningEvent).order_by(ListeningEvent.started_at.asc()).limit(8000)
    if user_id is not None:
        q = q.where(ListeningEvent.user_id == user_id)
    events = list(db.scalars(q).all())
    plays = [
        PlayEvent(
            song_id=int(e.song_id),
            started_at=e.started_at,
            session_id=int(e.session_id) if e.session_id is not None else None,
            listened_ms=int(e.listened_ms),
            completed=e.completed,
        )
        for e in events
    ]
    sessions = build_sessions(plays, gap=DEFAULT_SESSION_GAP)
    n_trans = sum(max(0, len(s) - 1) for s in sessions)
    unique = {sid for s in sessions for sid in s}
    return {
        "events": len(plays),
        "sessions": len(sessions),
        "transitions": n_trans,
        "unique_songs": len(unique),
    }


def _load_play_events(db: Session) -> list[PlayEvent]:
    # Single-user app: train on all listening history.
    rows = db.scalars(
        select(ListeningEvent)
        .order_by(ListeningEvent.started_at.asc())
        .limit(10_000)
    ).all()
    return [
        PlayEvent(
            song_id=int(e.song_id),
            started_at=e.started_at,
            session_id=int(e.session_id) if e.session_id is not None else None,
            listened_ms=int(e.listened_ms),
            completed=e.completed,
        )
        for e in rows
    ]


def get_active_model_row(db: Session) -> SequentialModelRow | None:
    return db.scalar(
        select(SequentialModelRow)
        .where(SequentialModelRow.is_active.is_(True))
        .order_by(SequentialModelRow.created_at.desc(), SequentialModelRow.id.desc())
        .limit(1)
    )


def _refresh_cache(row: SequentialModelRow | None) -> None:
    global _active_cache_key, _active_model
    if row is None:
        _active_cache_key = None
        _active_model = None
        return
    if _active_cache_key == row.id and _active_model is not None:
        return
    _active_model = loads_model(bytes(row.artifact))
    _active_cache_key = row.id


def clear_sequential_cache() -> None:
    global _active_cache_key, _active_model
    _active_cache_key = None
    _active_model = None


def sequential_ready(db: Session) -> bool:
    row = get_active_model_row(db)
    if row is None:
        return False
    _refresh_cache(row)
    return _active_model is not None


def recent_seed_song_ids(
    db: Session,
    user_id,
    *,
    limit: int = SERVE_SEED_COUNT,
    now: datetime | None = None,
) -> list[int]:
    """Most recent distinct songs the user listened to (oldest → newest)."""
    now = now or datetime.now(timezone.utc)
    # Prefer recent history (last 14 days) so next-track stays local to current taste.
    cutoff = now - timedelta(days=14)
    rows = db.scalars(
        select(ListeningEvent)
        .where(
            ListeningEvent.user_id == user_id,
            ListeningEvent.started_at >= cutoff,
        )
        .order_by(ListeningEvent.started_at.desc())
        .limit(80)
    ).all()
    seeds: list[int] = []
    seen: set[int] = set()
    for ev in rows:
        sid = int(ev.song_id)
        if sid in seen:
            continue
        seen.add(sid)
        seeds.append(sid)
        if len(seeds) >= limit:
            break
    seeds.reverse()
    return seeds


def sequential_candidates(
    db: Session,
    *,
    seed_song_ids: list[int],
    exclude: set[int],
    limit: int = SERVE_CANDIDATE_LIMIT,
) -> list[RankedItem] | None:
    """Return next-track RankedItems, or None when the model is unavailable."""
    row = get_active_model_row(db)
    if row is None:
        return None
    _refresh_cache(row)
    if _active_model is None:
        return None
    scored = predict_next(
        _active_model,
        seed_song_ids,
        exclude=exclude,
        limit=limit,
    )
    explain = (
        Explanation("next_track", "Often follows what you just played"),
    )
    return [
        RankedItem(song_id=sid, score=float(score), explanations=explain)
        for sid, score in scored
    ]


def merge_candidates(
    cosine_ranked: list[RankedItem],
    sequential_ranked: list[RankedItem] | None,
    *,
    cosine_weight: float = 1.0,
    sequential_weight: float = 0.85,
) -> tuple[list[RankedItem], set[int]]:
    """Union cosine ∪ sequential candidates. Returns (merged, sequential_song_ids).

    Cosine scores stay primary for songs seen by taste; sequential-only songs keep
    their transition score (scaled). Overlap keeps the better of the two weighted scores
    and attaches a next_track explanation when sequential contributed.
    """
    if not sequential_ranked:
        return list(cosine_ranked), set()

    seq_ids = {r.song_id for r in sequential_ranked}
    seq_by_id = {r.song_id: r for r in sequential_ranked}
    cos_by_id = {r.song_id: r for r in cosine_ranked}
    all_ids = list(dict.fromkeys([*cos_by_id.keys(), *seq_by_id.keys()]))

    merged: list[RankedItem] = []
    for sid in all_ids:
        cos = cos_by_id.get(sid)
        seq = seq_by_id.get(sid)
        if cos and seq:
            score = max(cosine_weight * cos.score, sequential_weight * seq.score)
            expl = tuple(dict.fromkeys([*cos.explanations, *seq.explanations]))
            merged.append(RankedItem(song_id=sid, score=float(score), explanations=expl))
        elif cos:
            merged.append(cos)
        elif seq:
            merged.append(
                RankedItem(
                    song_id=sid,
                    score=float(sequential_weight * seq.score),
                    explanations=seq.explanations,
                )
            )
    merged.sort(key=lambda r: (-r.score, r.song_id))
    return merged, seq_ids


def retrain(db: Session, *, activate: bool = True) -> RetrainResult:
    """Fit Markov transitions from listening sessions and optionally activate."""
    counts = history_counts(db)
    if counts["transitions"] < MIN_TRANSITIONS or counts["sessions"] < MIN_SESSIONS:
        return RetrainResult(
            model_id=0,
            n_transitions=counts["transitions"],
            n_sessions=counts["sessions"],
            n_unique_songs=counts["unique_songs"],
            metrics={},
            activated=False,
            message=(
                f"Not enough listening history "
                f"({counts['transitions']} transitions / {MIN_TRANSITIONS}, "
                f"{counts['sessions']} sessions / {MIN_SESSIONS}). "
                "Keep serving cosine candidates until more ordered plays land."
            ),
        )

    plays = _load_play_events(db)
    sessions = build_sessions(plays, gap=DEFAULT_SESSION_GAP)
    try:
        result = train_markov(
            sessions,
            session_gap_minutes=DEFAULT_SESSION_GAP.total_seconds() / 60.0,
        )
    except ValueError as exc:
        return RetrainResult(
            model_id=0,
            n_transitions=counts["transitions"],
            n_sessions=counts["sessions"],
            n_unique_songs=counts["unique_songs"],
            metrics={},
            activated=False,
            message=str(exc),
        )

    blob = dumps_model(result.model)
    row = SequentialModelRow(
        algorithm=result.model.algorithm,
        n_transitions=result.n_transitions,
        n_sessions=result.n_sessions,
        n_unique_songs=result.n_unique_songs,
        metrics=result.metrics,
        artifact=blob,
        is_active=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()

    activated = False
    if activate:
        db.execute(update(SequentialModelRow).values(is_active=False))
        row.is_active = True
        db.flush()
        activated = True
        clear_sequential_cache()
        _refresh_cache(row)

    log.info(
        "Trained sequential model id=%s transitions=%s sessions=%s activated=%s",
        row.id,
        result.n_transitions,
        result.n_sessions,
        activated,
    )
    return RetrainResult(
        model_id=int(row.id),
        n_transitions=result.n_transitions,
        n_sessions=result.n_sessions,
        n_unique_songs=result.n_unique_songs,
        metrics=result.metrics,
        activated=activated,
        message=(
            f"Trained Markov next-track model #{row.id} on {result.n_transitions} transitions "
            f"across {result.n_sessions} sessions ({result.n_unique_songs} songs)."
            + (" Activated for For You candidate merge." if activated else " Saved inactive.")
        ),
    )
