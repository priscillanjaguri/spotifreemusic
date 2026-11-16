"""Log recommendation impressions and attach engage / skip labels from feedback & listening."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scorer import RecommendationImpression

# Match an outcome to the most recent unlabeled impression of that song.
OUTCOME_LOOKBACK = timedelta(days=14)


def log_impressions(
    db: Session,
    user_id: uuid.UUID,
    *,
    request_id: uuid.UUID,
    items: Sequence[tuple[int, float, dict[str, Any]]],
    shown_at: datetime | None = None,
) -> list[RecommendationImpression]:
    """Persist one row per served recommendation.

    `items` is (song_id, cosine_score, features_dict) in served order.
    """
    shown_at = shown_at or datetime.now(timezone.utc)
    rows: list[RecommendationImpression] = []
    for pos, (song_id, cosine_score, features) in enumerate(items):
        row = RecommendationImpression(
            user_id=user_id,
            song_id=int(song_id),
            request_id=request_id,
            position=pos,
            shown_at=shown_at,
            cosine_score=float(cosine_score),
            features=dict(features),
        )
        db.add(row)
        rows.append(row)
    if rows:
        db.flush()
    return rows


def label_impression(
    db: Session,
    user_id: uuid.UUID,
    song_id: int,
    *,
    label: int,
    source: str,
    at: datetime | None = None,
) -> RecommendationImpression | None:
    """Label the newest unlabeled impression for (user, song) within the lookback window.

    Does not overwrite an existing label (first outcome wins).
    """
    if label not in (0, 1):
        raise ValueError("label must be 0 or 1")
    at = at or datetime.now(timezone.utc)
    cutoff = at - OUTCOME_LOOKBACK
    row = db.scalar(
        select(RecommendationImpression)
        .where(
            RecommendationImpression.user_id == user_id,
            RecommendationImpression.song_id == song_id,
            RecommendationImpression.label.is_(None),
            RecommendationImpression.shown_at >= cutoff,
            RecommendationImpression.shown_at <= at,
        )
        .order_by(RecommendationImpression.shown_at.desc(), RecommendationImpression.id.desc())
        .limit(1)
    )
    if row is None:
        return None
    row.label = label
    row.labeled_at = at
    row.label_source = source[:20]
    db.flush()
    return row

