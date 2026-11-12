from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.analytics import (
    AnalyticsPeriodOut,
    DailyTotalOut,
    MemoryLaneItemOut,
    MemoryLaneOut,
    NamedCount,
    TasteTimelineOut,
    TimelineMilestoneOut,
    TimelineWeekOut,
    TopSongOut,
)
from app.schemas.music import SongOut
from app.services import analytics as analytics_svc

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _named(s: analytics_svc.NamedStat) -> NamedCount:
    return NamedCount(id=s.id, name=s.name, play_count=s.play_count, listened_ms=s.listened_ms)


def _pack_period(p: analytics_svc.AnalyticsPeriod) -> AnalyticsPeriodOut:
    return AnalyticsPeriodOut(
        period=p.period,  # type: ignore[arg-type]
        offset=p.offset,
        start=p.start,
        end=p.end,
        timezone=p.timezone,
        total_listened_ms=p.total_listened_ms,
        play_count=p.play_count,
        unique_songs=p.unique_songs,
        unique_artists=p.unique_artists,
        completion_rate=p.completion_rate,
        top_artists=[_named(s) for s in p.top_artists],
        top_genres=[_named(s) for s in p.top_genres],
        top_songs=[
            TopSongOut(
                song=SongOut.from_song(s.song),
                play_count=s.play_count,
                listened_ms=s.listened_ms,
                completed_count=s.completed_count,
            )
            for s in p.top_songs
        ],
        daily=[
            DailyTotalOut(date=d.day, play_count=d.play_count, listened_ms=d.listened_ms)
            for d in p.daily
        ],
    )


@router.get("", response_model=AnalyticsPeriodOut, summary="Weekly or monthly listening analytics")
def get_analytics(
    period: str = Query("week", pattern="^(week|month)$"),
    offset: int = Query(0, ge=0, le=52),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalyticsPeriodOut:
    return _pack_period(analytics_svc.compute_period(db, user, period, offset))


@router.get("/taste-timeline", response_model=TasteTimelineOut, summary="Taste Timeline")
def get_taste_timeline(
    weeks: int = Query(12, ge=4, le=52),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TasteTimelineOut:
    tl = analytics_svc.taste_timeline(db, user, weeks=weeks)
    return TasteTimelineOut(
        weeks=[
            TimelineWeekOut(
                week_start=w.week_start,
                week_end=w.week_end,
                listened_ms=w.listened_ms,
                play_count=w.play_count,
                unique_songs=w.unique_songs,
                top_genres=[_named(g) for g in w.top_genres],
            )
            for w in tl.weeks
        ],
        milestones=[
            TimelineMilestoneOut(
                at=m.at,
                kind=m.kind,
                label=m.label,
                song=SongOut.from_song(m.song) if m.song else None,
            )
            for m in tl.milestones
        ],
    )


@router.get("/memory-lane", response_model=MemoryLaneOut, summary="Memory Lane")
def get_memory_lane(
    limit: int = Query(24, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemoryLaneOut:
    lane = analytics_svc.memory_lane(db, user, limit=limit)
    return MemoryLaneOut(
        items=[
            MemoryLaneItemOut(
                kind=i.kind,  # type: ignore[arg-type]
                label=i.label,
                at=i.at,
                song=SongOut.from_song(i.song),
                listened_ms=i.listened_ms,
                play_count=i.play_count,
            )
            for i in lane.items
        ]
    )
