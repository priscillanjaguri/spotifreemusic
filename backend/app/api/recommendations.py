from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.providers.base import MusicProviderAdapter
from app.providers.registry import get_music_provider
from app.schemas.music import SongOut
from app.schemas.recommend import (
    ExplanationOut,
    FeedbackIn,
    FeedbackOut,
    RecommendationItemOut,
    RecommendationsOut,
)
from app.services import feedback as feedback_svc
from app.services import recommender as reco_svc

router = APIRouter(tags=["recommendations"])


def _pack(result: reco_svc.RecommendationResult) -> RecommendationsOut:
    items = [
        RecommendationItemOut(
            song=SongOut.from_song(song),
            score=round(item.score, 4),
            explanations=[ExplanationOut(code=e.code, label=e.label) for e in item.explanations],
        )
        for song, item in result.items
    ]
    return RecommendationsOut(
        items=items,
        cold_start=result.cold_start,
        mode=result.mode,
        short_term_days=result.short_term_days,
        long_term_days=result.long_term_days,
    )


@router.get("/recommendations", response_model=RecommendationsOut, summary="Personalised For You recommendations")
def get_recommendations(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MusicProviderAdapter | None = Depends(get_music_provider),
) -> RecommendationsOut:
    result = reco_svc.recommend_for_user(db, user, limit=limit, provider=provider)
    db.commit()
    return _pack(result)


@router.post("/feedback", response_model=FeedbackOut, summary="Like or mark not interested")
def post_feedback(
    body: FeedbackIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FeedbackOut:
    try:
        row = feedback_svc.record_feedback(db, user.id, body.song_id, body.action, context=body.context)
    except LookupError:
        raise HTTPException(404, "Song not found")
    db.commit()
    return FeedbackOut(song_id=body.song_id, interaction_type=row.interaction_type, created_at=row.created_at)
