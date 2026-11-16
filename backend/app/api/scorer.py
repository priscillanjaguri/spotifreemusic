"""Secret-gated engagement scorer retrain + status (Render cron / manual trigger)."""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.ml.scorer import MIN_LABELED_SAMPLES
from app.schemas.scorer import ScorerRetrainIn, ScorerRetrainOut, ScorerStatusOut
from app.services import scorer_job

router = APIRouter(tags=["scorer"])


def _check_run_secret(provided: str | None, header: str | None) -> None:
    settings = get_settings()
    expected = (settings.eval_run_secret or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "eval_secret_not_configured",
                "message": "EVAL_RUN_SECRET is not set on this server.",
            },
        )
    candidate = (header or provided or "").strip()
    if not candidate or not hmac.compare_digest(candidate, expected):
        raise HTTPException(status_code=401, detail="Invalid eval run secret")


def _status(db: Session) -> ScorerStatusOut:
    counts = scorer_job.labeled_counts(db)
    model = scorer_job.get_active_model(db)
    return ScorerStatusOut(
        active_model_id=int(model.id) if model else None,
        algorithm=model.algorithm if model else None,
        n_samples=int(model.n_samples) if model else None,
        n_positives=int(model.n_positives) if model else None,
        metrics=dict(model.metrics or {}) if model else {},
        labeled_impressions=counts["labeled"],
        positive_labels=counts["positives"],
        negative_labels=counts["negatives"],
        min_labeled_required=MIN_LABELED_SAMPLES,
        ready=scorer_job.scorer_ready(db),
        created_at=model.created_at if model else None,
    )


@router.get("/scorer/status", response_model=ScorerStatusOut, summary="Engagement scorer readiness")
def get_scorer_status(db: Session = Depends(get_db)) -> ScorerStatusOut:
    return _status(db)


@router.post(
    "/scorer/retrain",
    response_model=ScorerRetrainOut,
    summary="Train / retrain engagement scorer from labeled impressions",
)
def post_scorer_retrain(
    body: ScorerRetrainIn | None = None,
    db: Session = Depends(get_db),
    x_eval_secret: str | None = Header(default=None, alias="X-Eval-Secret"),
) -> ScorerRetrainOut:
    body = body or ScorerRetrainIn()
    _check_run_secret(body.secret, x_eval_secret)
    result = scorer_job.retrain(db, activate=body.activate)
    db.commit()
    return ScorerRetrainOut(
        model_id=result.model_id,
        n_samples=result.n_samples,
        n_positives=result.n_positives,
        metrics=result.metrics,
        activated=result.activated,
        message=result.message,
        status=_status(db),
    )
