from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.music import SongOut


class ExplanationOut(BaseModel):
    code: str
    label: str


class RecommendationItemOut(BaseModel):
    song: SongOut
    score: float
    explanations: list[ExplanationOut]


class RecommendationsOut(BaseModel):
    items: list[RecommendationItemOut]
    cold_start: bool
    mode: Literal["taste", "similar", "popular", "genre_seed"]
    short_term_days: int
    long_term_days: int


class FeedbackIn(BaseModel):
    song_id: int
    action: Literal["like", "not_interested"]
    context: str | None = Field(default="recommendations", max_length=30)


class FeedbackOut(BaseModel):
    song_id: int
    interaction_type: Literal["interested", "not_interested"]
    created_at: datetime


class ListeningEventIn(BaseModel):
    song_id: int
    started_at: datetime
    ended_at: datetime
    listened_ms: int = Field(ge=0)
    song_duration_ms: int = Field(gt=0)
    completed: bool | None = None
    client_session_id: str | None = Field(default=None, max_length=64)


class ListeningEventOut(BaseModel):
    id: int
    song_id: int
    listened_ms: int
    completed: bool | None
    play_date: str
