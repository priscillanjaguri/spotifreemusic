from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.providers.base import MusicProviderAdapter
from app.providers.registry import get_music_provider
from app.schemas.analytics import (
    CompanionInsightOut,
    CompanionMoodIn,
    DailyCompanionOut,
    MemoryLaneItemOut,
)
from app.schemas.music import SongOut
from app.schemas.recommend import ExplanationOut, RecommendationItemOut
from app.services import companion as companion_svc
from app.services.companion import AVAILABLE_MOODS

router = APIRouter(prefix="/companion", tags=["companion"])


def _pack(result: companion_svc.DailyCompanion) -> DailyCompanionOut:
    playlist = [
        RecommendationItemOut(
            song=SongOut.from_song(song),
            score=round(item.score, 4),
            explanations=[ExplanationOut(code=e.code, label=e.label) for e in item.explanations],
        )
        for song, item in result.playlist.items
    ]
    spotlight = None
    if result.spotlight is not None:
        s = result.spotlight
        spotlight = MemoryLaneItemOut(
            kind=s.kind,  # type: ignore[arg-type]
            label=s.label,
            at=s.at,
            song=SongOut.from_song(s.song),
            listened_ms=s.listened_ms,
            play_count=s.play_count,
        )
    return DailyCompanionOut(
        date=result.date,
        timezone=result.timezone,
        greeting=result.greeting,
        briefing=result.briefing,
        mood=result.mood,
        available_moods=list(AVAILABLE_MOODS),
        insights=[CompanionInsightOut(code=i.code, label=i.label) for i in result.insights],
        playlist=playlist,
        spotlight=spotlight,
        cold_start=result.playlist.cold_start,
        mode=result.playlist.mode,
    )


@router.get("/daily", response_model=DailyCompanionOut, summary="Daily companion briefing + playlist")
def get_daily_companion(
    mood: str | None = Query(None, max_length=20),
    limit: int = Query(12, ge=1, le=30),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MusicProviderAdapter | None = Depends(get_music_provider),
) -> DailyCompanionOut:
    try:
        result = companion_svc.build_daily_companion(
            db, user, mood=mood, limit=limit, provider=provider
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    return _pack(result)


@router.post("/daily", response_model=DailyCompanionOut, summary="Set today's mood and refresh companion")
def post_daily_mood(
    body: CompanionMoodIn,
    limit: int = Query(12, ge=1, le=30),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MusicProviderAdapter | None = Depends(get_music_provider),
) -> DailyCompanionOut:
    result = companion_svc.build_daily_companion(
        db, user, mood=body.mood, limit=limit, provider=provider
    )
    db.commit()
    return _pack(result)
