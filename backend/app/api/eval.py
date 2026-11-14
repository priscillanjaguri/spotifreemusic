"""Public eval dashboard APIs + secret-gated run trigger."""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.schemas.eval import (
    EvalRunIn,
    EvalRunOut,
    EvalScheduleOut,
    EvalSnapshotOut,
    EvalSnapshotsOut,
    EvalSummaryOut,
)
from app.services import eval_job

router = APIRouter(tags=["eval"])


def _pack(snap) -> EvalSnapshotOut:
    return EvalSnapshotOut(
        id=snap.id,
        created_at=snap.created_at,
        metrics={k: float(v) for k, v in (snap.metrics or {}).items()},
        data_volume={k: int(v) for k, v in (snap.data_volume or {}).items()},
        feedback_counts={k: int(v) for k, v in (snap.feedback_counts or {}).items()},
        source=snap.source if snap.source in ("holdout", "synthetic") else "synthetic",
        k=int(snap.k),
    )


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


@router.get("/eval/summary", response_model=EvalSummaryOut, summary="Latest eval snapshot + blurbs")
def get_eval_summary(db: Session = Depends(get_db)) -> EvalSummaryOut:
    raw = eval_job.build_summary(db)
    latest = _pack(eval_job.latest_snapshot(db)) if raw["latest"] else None
    return EvalSummaryOut(
        latest=latest,
        metric_blurbs=raw["metric_blurbs"],
        ranking_blurb=raw["ranking_blurb"],
        schedule=EvalScheduleOut(**raw["schedule"]),
    )


@router.get("/eval/snapshots", response_model=EvalSnapshotsOut, summary="Recent eval snapshots for trends")
def get_eval_snapshots(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> EvalSnapshotsOut:
    items = eval_job.list_snapshots(db, limit=limit)
    return EvalSnapshotsOut(items=[_pack(s) for s in items], total=len(items))


@router.post("/eval/run", response_model=EvalRunOut, summary="Run hold-out eval and store a snapshot")
def post_eval_run(
    body: EvalRunIn | None = None,
    db: Session = Depends(get_db),
    x_eval_secret: str | None = Header(default=None, alias="X-Eval-Secret"),
) -> EvalRunOut:
    body = body or EvalRunIn()
    _check_run_secret(body.secret, x_eval_secret)
    snap = eval_job.run_eval(db, k=body.k, force_synthetic=body.force_synthetic)
    db.commit()
    db.refresh(snap)
    src = "synthetic catalogue" if snap.source == "synthetic" else "live hold-out"
    return EvalRunOut(
        snapshot=_pack(snap),
        message=f"Stored {src} eval snapshot #{snap.id}.",
    )
