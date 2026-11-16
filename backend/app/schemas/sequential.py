from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SequentialRetrainIn(BaseModel):
    secret: str | None = None
    activate: bool = True


class SequentialStatusOut(BaseModel):
    active_model_id: int | None
    algorithm: str | None = None
    n_transitions: int | None = None
    n_sessions: int | None = None
    n_unique_songs: int | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    history_events: int
    history_sessions: int
    history_transitions: int
    history_unique_songs: int
    min_transitions_required: int
    min_sessions_required: int
    ready: bool
    created_at: datetime | None = None


class SequentialRetrainOut(BaseModel):
    model_id: int
    n_transitions: int
    n_sessions: int
    n_unique_songs: int
    metrics: dict[str, Any]
    activated: bool
    message: str
    status: SequentialStatusOut
