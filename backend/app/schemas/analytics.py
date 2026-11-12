"""Schemas for listening analytics, taste timeline, memory lane and companion."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.music import SongOut
from app.schemas.recommend import ExplanationOut, RecommendationItemOut


class NamedCount(BaseModel):
    id: int | None = None
    name: str
    play_count: int
    listened_ms: int


class TopSongOut(BaseModel):
    song: SongOut
    play_count: int
    listened_ms: int
    completed_count: int


class DailyTotalOut(BaseModel):
    date: date
    play_count: int
    listened_ms: int


class AnalyticsPeriodOut(BaseModel):
    period: Literal["week", "month"]
    offset: int
    start: date
    end: date  # inclusive
    timezone: str
    total_listened_ms: int
    play_count: int
    unique_songs: int
    unique_artists: int
    completion_rate: float | None  # None when no completed-known events
    top_artists: list[NamedCount]
    top_genres: list[NamedCount]
    top_songs: list[TopSongOut]
    daily: list[DailyTotalOut]


class TimelineWeekOut(BaseModel):
    week_start: date
    week_end: date
    listened_ms: int
    play_count: int
    unique_songs: int
    top_genres: list[NamedCount]


class TimelineMilestoneOut(BaseModel):
    at: datetime
    kind: str
    label: str
    song: SongOut | None = None


class TasteTimelineOut(BaseModel):
    weeks: list[TimelineWeekOut]
    milestones: list[TimelineMilestoneOut]


class MemoryLaneItemOut(BaseModel):
    kind: Literal["on_this_day", "rediscovered", "first_save", "first_like", "most_replayed", "flashback"]
    label: str
    at: datetime | None = None
    song: SongOut
    listened_ms: int | None = None
    play_count: int | None = None


class MemoryLaneOut(BaseModel):
    items: list[MemoryLaneItemOut]


class HistoryDeletedOut(BaseModel):
    deleted_events: int
    deleted_sessions: int


class CompanionInsightOut(BaseModel):
    code: str
    label: str


class DailyCompanionOut(BaseModel):
    date: date
    timezone: str
    greeting: str
    briefing: str
    mood: str | None
    available_moods: list[str]
    insights: list[CompanionInsightOut]
    playlist: list[RecommendationItemOut]
    spotlight: MemoryLaneItemOut | None
    cold_start: bool
    mode: str


class CompanionMoodIn(BaseModel):
    mood: Literal["soft", "dreamy", "focus", "energy", "chill", "glow"] = Field(
        description="Explicit mood for today's companion mix"
    )
