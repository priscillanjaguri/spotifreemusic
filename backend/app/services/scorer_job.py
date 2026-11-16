"""Train / load / apply the engagement scorer from labeled impressions."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.ml.rank import RankedItem
from app.ml.scorer import (
    FEATURE_NAMES,
    MIN_LABELED_SAMPLES,
    dumps_pipeline,
    loads_pipeline,
    predict_engage_proba,
    train_logistic,
)
from app.models.scorer import RecommendationImpression, ScorerModel

log = logging.getLogger(__name__)

# Invalidate in-process cache when a new model is activated.
_active_cache_key: int | None = None
_active_pipeline = None
_active_feature_names: tuple[str, ...] = FEATURE_NAMES


@dataclass
class RetrainResult:
    model_id: int
    n_samples: int
    n_positives: int
    metrics: dict[str, float]
    activated: bool
    message: str


def labeled_counts(db: Session) -> dict[str, int]:
    total = int(
        db.scalar(
            select(func.count()).select_from(RecommendationImpression).where(
                RecommendationImpression.label.is_not(None)
            )
        )
        or 0
    )
    positives = int(
        db.scalar(
            select(func.count()).select_from(RecommendationImpression).where(
                RecommendationImpression.label == 1
            )
        )
        or 0
    )
    return {"labeled": total, "positives": positives, "negatives": total - positives}


def _load_training_rows(db: Session) -> tuple[list[dict[str, Any]], list[int]]:
    rows = db.scalars(
        select(RecommendationImpression)
        .where(RecommendationImpression.label.is_not(None))
        .order_by(RecommendationImpression.labeled_at.asc(), RecommendationImpression.id.asc())
    ).all()
    features = [dict(r.features or {}) for r in rows]
    # Prefer stored features; fall back to cosine_score alone if an old row is sparse.
    for feat, row in zip(features, rows):
        feat.setdefault("cosine_score", float(row.cosine_score))
    labels = [int(r.label) for r in rows]
    return features, labels


def get_active_model(db: Session) -> ScorerModel | None:
    return db.scalar(
        select(ScorerModel)
        .where(ScorerModel.is_active.is_(True))
        .order_by(ScorerModel.created_at.desc(), ScorerModel.id.desc())
        .limit(1)
    )


def _refresh_cache(model: ScorerModel | None) -> None:
    global _active_cache_key, _active_pipeline, _active_feature_names
    if model is None:
        _active_cache_key = None
        _active_pipeline = None
        _active_feature_names = FEATURE_NAMES
        return
    if _active_cache_key == model.id and _active_pipeline is not None:
        return
    _active_pipeline = loads_pipeline(bytes(model.artifact))
    names = model.feature_names or list(FEATURE_NAMES)
    _active_feature_names = tuple(str(n) for n in names)
    _active_cache_key = model.id


def clear_scorer_cache() -> None:
    global _active_cache_key, _active_pipeline, _active_feature_names
    _active_cache_key = None
    _active_pipeline = None
    _active_feature_names = FEATURE_NAMES


def scorer_ready(db: Session) -> bool:
    """True when an active model exists (cold-start fallback otherwise)."""
    model = get_active_model(db)
    if model is None:
        return False
    _refresh_cache(model)
    return _active_pipeline is not None


def score_candidates(
    db: Session,
    feature_rows: list[dict[str, Any]],
) -> list[float] | None:
    """Return P(engage) per row, or None when the scorer is unavailable."""
    model = get_active_model(db)
    if model is None:
        return None
    _refresh_cache(model)
    if _active_pipeline is None:
        return None
    proba = predict_engage_proba(
        _active_pipeline, feature_rows, feature_names=_active_feature_names
    )
    return [float(p) for p in proba]


def rerank_by_engagement(
    ranked: list[RankedItem],
    engage_scores: dict[int, float],
) -> list[RankedItem]:
    """Replace cosine scores with P(engage) and sort descending (stable for ties)."""
    rescored = [
        RankedItem(
            song_id=item.song_id,
            score=float(engage_scores.get(item.song_id, item.score)),
            explanations=item.explanations,
        )
        for item in ranked
    ]
    return sorted(rescored, key=lambda r: (-r.score, r.song_id))


def retrain(db: Session, *, activate: bool = True) -> RetrainResult:
    """Fit logistic regression from labeled impressions and optionally activate it."""
    counts = labeled_counts(db)
    if counts["labeled"] < MIN_LABELED_SAMPLES:
        return RetrainResult(
            model_id=0,
            n_samples=counts["labeled"],
            n_positives=counts["positives"],
            metrics={},
            activated=False,
            message=(
                f"Not enough labeled impressions ({counts['labeled']}/{MIN_LABELED_SAMPLES}). "
                "Keep serving cosine order until more play/like/hide outcomes land."
            ),
        )

    feature_rows, labels = _load_training_rows(db)
    try:
        result = train_logistic(feature_rows, labels)
    except ValueError as exc:
        return RetrainResult(
            model_id=0,
            n_samples=len(labels),
            n_positives=sum(labels),
            metrics={},
            activated=False,
            message=str(exc),
        )

    blob = dumps_pipeline(result.pipeline)
    row = ScorerModel(
        algorithm="logistic_regression",
        feature_names=list(result.feature_names),
        n_samples=result.n_samples,
        n_positives=result.n_positives,
        metrics=result.metrics,
        artifact=blob,
        is_active=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()

    activated = False
    if activate:
        db.execute(update(ScorerModel).values(is_active=False))
        row.is_active = True
        db.flush()
        activated = True
        clear_scorer_cache()
        _refresh_cache(row)

    log.info(
        "Trained engagement scorer id=%s n=%s pos=%s activated=%s metrics=%s",
        row.id,
        result.n_samples,
        result.n_positives,
        activated,
        result.metrics,
    )
    return RetrainResult(
        model_id=int(row.id),
        n_samples=result.n_samples,
        n_positives=result.n_positives,
        metrics=result.metrics,
        activated=activated,
        message=(
            f"Trained logistic engagement scorer #{row.id} on {result.n_samples} labels "
            f"({result.n_positives} positive)."
            + (" Activated for For You ranking." if activated else " Saved inactive.")
        ),
    )
