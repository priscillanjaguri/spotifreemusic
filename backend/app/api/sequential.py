"""Secret-gated sequential next-track retrain + status (Render cron / manual trigger)."""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.ml.sequential import MIN_SESSIONS, MIN_TRANSITIONS
from app.schemas.sequential import (
    SequentialRetrainIn,
    SequentialRetrainOut,
    SequentialStatusOut,
)
from app.services import sequential_job

router = APIRouter(tags=["sequential"])


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


def _status(db: Session) -> SequentialStatusOut:
    counts = sequential_job.history_counts(db)
    row = sequential_job.get_active_model_row(db)
    return SequentialStatusOut(
        active_model_id=int(row.id) if row else None,
        algorithm=row.algorithm if row else None,
        n_transitions=int(row.n_transitions) if row else None,
        n_sessions=int(row.n_sessions) if row else None,
        n_unique_songs=int(row.n_unique_songs) if row else None,
        metrics=dict(row.metrics or {}) if row else {},
        history_events=counts["events"],
        history_sessions=counts["sessions"],
        history_transitions=counts["transitions"],
        history_unique_songs=counts["unique_songs"],
        min_transitions_required=MIN_TRANSITIONS,
        min_sessions_required=MIN_SESSIONS,
        ready=sequential_job.sequential_ready(db),
        created_at=row.created_at if row else None,
    )


@router.get(
    "/sequential/status",
    response_model=SequentialStatusOut,
    summary="Sequential next-track model readiness",
)
def get_sequential_status(db: Session = Depends(get_db)) -> SequentialStatusOut:
    return _status(db)


@router.post(
    "/sequential/retrain",
    response_model=SequentialRetrainOut,
    summary="Train / retrain sequential next-track model from listening sessions",
)
def post_sequential_retrain(
    body: SequentialRetrainIn | None = None,
    db: Session = Depends(get_db),
    x_eval_secret: str | None = Header(default=None, alias="X-Eval-Secret"),
) -> SequentialRetrainOut:
    body = body or SequentialRetrainIn()
    _check_run_secret(body.secret, x_eval_secret)
    result = sequential_job.retrain(db, activate=body.activate)
    db.commit()
    return SequentialRetrainOut(
        model_id=result.model_id,
        n_transitions=result.n_transitions,
        n_sessions=result.n_sessions,
        n_unique_songs=result.n_unique_songs,
        metrics=result.metrics,
        activated=result.activated,
        message=result.message,
        status=_status(db),
    )
