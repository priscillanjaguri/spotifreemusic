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
    source_label: str | None = None
    k: int


class EvalScheduleOut(BaseModel):
    due: bool
    reason: str | None = None
    new_events_since_last: int = 0
    hours_since_last: float | None = None
    threshold_events: int | None = None
    daily_hours: float | None = None


class OnlineSeriesPointOut(BaseModel):
    date: str
    labeled: int = 0
    engage_rate: float = 0.0
    skip_rate: float = 0.0
    like_rate: float = 0.0
    play_rate: float = 0.0


class OnlineMetricsOut(BaseModel):
    ready: bool
    min_labeled_required: int
    metrics: dict[str, float]
    label_sources: dict[str, int] = Field(default_factory=dict)
    series: list[OnlineSeriesPointOut] = Field(default_factory=list)
    metric_blurbs: dict[str, str] = Field(default_factory=dict)


class HoldoutReadyOut(BaseModel):
    ready: bool
    min_positives: int
    catalogue_songs: int
    qualifying_users: int
    preferred_source: Literal["holdout", "synthetic"]


class EvalSummaryOut(BaseModel):
    latest: EvalSnapshotOut | None
    metric_blurbs: dict[str, str]
    ranking_blurb: str
    schedule: EvalScheduleOut
    online: OnlineMetricsOut | None = None
    holdout: HoldoutReadyOut | None = None
    source_labels: dict[str, str] = Field(default_factory=dict)


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


class EvalOnlineStatusOut(BaseModel):
    ready: bool
    min_labeled_required: int
    metrics: dict[str, float]
    label_sources: dict[str, int] = Field(default_factory=dict)


class EvalStatusOut(BaseModel):
    """Public readiness alongside scorer/sequential; POST /eval/run still needs EVAL_RUN_SECRET."""

    latest_id: int | None
    latest_source: Literal["holdout", "synthetic"] | None = None
    latest_source_label: str | None = None
    holdout: HoldoutReadyOut
    online: EvalOnlineStatusOut
    schedule: EvalScheduleOut
    run_secret_configured: bool
