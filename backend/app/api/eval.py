"""Public eval dashboard APIs + secret-gated run trigger."""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.schemas.eval import (
    EvalOnlineStatusOut,
    EvalRunIn,
    EvalRunOut,
    EvalScheduleOut,
    EvalSnapshotOut,
    EvalSnapshotsOut,
    EvalStatusOut,
    EvalSummaryOut,
    HoldoutReadyOut,
    OnlineMetricsOut,
    OnlineSeriesPointOut,
)
from app.services import eval_job
from app.services.eval_job import SOURCE_LABELS

router = APIRouter(tags=["eval"])


def _pack(snap) -> EvalSnapshotOut:
    source = snap.source if snap.source in ("holdout", "synthetic") else "synthetic"
    return EvalSnapshotOut(
        id=snap.id,
        created_at=snap.created_at,
        metrics={k: float(v) for k, v in (snap.metrics or {}).items()},
        data_volume={k: int(v) for k, v in (snap.data_volume or {}).items()},
        feedback_counts={k: int(v) for k, v in (snap.feedback_counts or {}).items()},
        source=source,
        source_label=SOURCE_LABELS.get(source, SOURCE_LABELS["synthetic"]),
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


def _pack_online(raw: dict) -> OnlineMetricsOut:
    return OnlineMetricsOut(
        ready=bool(raw["ready"]),
        min_labeled_required=int(raw["min_labeled_required"]),
        metrics={k: float(v) for k, v in (raw.get("metrics") or {}).items()},
        label_sources={k: int(v) for k, v in (raw.get("label_sources") or {}).items()},
        series=[OnlineSeriesPointOut(**point) for point in (raw.get("series") or [])],
        metric_blurbs=dict(raw.get("metric_blurbs") or {}),
    )


def _pack_holdout(raw: dict) -> HoldoutReadyOut:
    preferred = raw.get("preferred_source")
    if preferred not in ("holdout", "synthetic"):
        preferred = "synthetic"
    return HoldoutReadyOut(
        ready=bool(raw["ready"]),
        min_positives=int(raw["min_positives"]),
        catalogue_songs=int(raw["catalogue_songs"]),
        qualifying_users=int(raw["qualifying_users"]),
        preferred_source=preferred,
    )


@router.get("/eval/summary", response_model=EvalSummaryOut, summary="Latest eval snapshot + online rates")
def get_eval_summary(db: Session = Depends(get_db)) -> EvalSummaryOut:
    raw = eval_job.build_summary(db)
    latest = _pack(eval_job.latest_snapshot(db)) if raw["latest"] else None
    return EvalSummaryOut(
        latest=latest,
        metric_blurbs=raw["metric_blurbs"],
        ranking_blurb=raw["ranking_blurb"],
        schedule=EvalScheduleOut(**raw["schedule"]),
        online=_pack_online(raw["online"]) if raw.get("online") else None,
        holdout=_pack_holdout(raw["holdout"]) if raw.get("holdout") else None,
        source_labels=dict(raw.get("source_labels") or SOURCE_LABELS),
    )


@router.get(
    "/eval/status",
    response_model=EvalStatusOut,
    summary="Eval readiness (hold-out vs synthetic + online impression rates)",
)
def get_eval_status(db: Session = Depends(get_db)) -> EvalStatusOut:
    raw = eval_job.build_status(db)
    online = raw["online"]
    latest_source = raw.get("latest_source")
    if latest_source not in ("holdout", "synthetic", None):
        latest_source = "synthetic"
    return EvalStatusOut(
        latest_id=raw["latest_id"],
        latest_source=latest_source,
        latest_source_label=raw.get("latest_source_label"),
        holdout=_pack_holdout(raw["holdout"]),
        online=EvalOnlineStatusOut(
            ready=bool(online["ready"]),
            min_labeled_required=int(online["min_labeled_required"]),
            metrics={k: float(v) for k, v in (online.get("metrics") or {}).items()},
            label_sources={k: int(v) for k, v in (online.get("label_sources") or {}).items()},
        ),
        schedule=EvalScheduleOut(**raw["schedule"]),
        run_secret_configured=bool(raw["run_secret_configured"]),
    )


@router.get("/eval/snapshots", response_model=EvalSnapshotsOut, summary="Recent eval snapshots for trends")
def get_eval_snapshots(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> EvalSnapshotsOut:
    items = eval_job.list_snapshots(db, limit=limit)
    return EvalSnapshotsOut(items=[_pack(s) for s in items], total=len(items))


@router.post("/eval/run", response_model=EvalRunOut, summary="Run hold-out + online eval and store a snapshot")
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
    src = SOURCE_LABELS.get(snap.source, SOURCE_LABELS["synthetic"])
    return EvalRunOut(
        snapshot=_pack(snap),
        message=f"Stored {src} eval snapshot #{snap.id} (includes live impression rates).",
    )
