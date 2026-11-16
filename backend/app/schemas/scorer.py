from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ScorerRetrainIn(BaseModel):
    secret: str | None = None
    activate: bool = True


class ScorerStatusOut(BaseModel):
    active_model_id: int | None
    algorithm: str | None = None
    n_samples: int | None = None
    n_positives: int | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    labeled_impressions: int
    positive_labels: int
    negative_labels: int
    min_labeled_required: int
    ready: bool
    created_at: datetime | None = None


class ScorerRetrainOut(BaseModel):
    model_id: int
    n_samples: int
    n_positives: int
    metrics: dict[str, Any]
    activated: bool
    message: str
    status: ScorerStatusOut
