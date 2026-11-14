from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvalSnapshotOut(BaseModel):
    id: int
    created_at: datetime | None
    metrics: dict[str, float]
    data_volume: dict[str, int]
    feedback_counts: dict[str, int]
    source: Literal["holdout", "synthetic"]
    k: int


class EvalScheduleOut(BaseModel):
    due: bool
    reason: str | None = None
    new_events_since_last: int = 0
    hours_since_last: float | None = None
    threshold_events: int | None = None
    daily_hours: float | None = None


class EvalSummaryOut(BaseModel):
    latest: EvalSnapshotOut | None
    metric_blurbs: dict[str, str]
    ranking_blurb: str
    schedule: EvalScheduleOut


class EvalSnapshotsOut(BaseModel):
    items: list[EvalSnapshotOut]
    total: int


class EvalRunIn(BaseModel):
    secret: str | None = Field(default=None, description="Shared EVAL_RUN_SECRET (or use X-Eval-Secret header)")
    k: int = Field(default=10, ge=1, le=50)
    force_synthetic: bool = False


class EvalRunOut(BaseModel):
    snapshot: EvalSnapshotOut
    message: str
