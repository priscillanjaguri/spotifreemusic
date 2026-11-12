from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Song, User
from app.providers.base import MusicProviderAdapter, ProviderError
from app.providers.registry import get_music_provider
from app.schemas.music import SongOut, SongSearchResponse
from app.schemas.recommend import ExplanationOut, RecommendationItemOut, RecommendationsOut
from app.services.catalog import import_tracks
from app.services.collection import SONG_LOAD
from app.services import recommender as reco_svc

router = APIRouter(prefix="/songs", tags=["songs"])


@router.get("/search", response_model=SongSearchResponse, summary="Search the music provider's catalogue")
def search_songs(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(20, ge=1, le=50),
    provider: MusicProviderAdapter | None = Depends(get_music_provider),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SongSearchResponse:
    if provider is None:
        raise HTTPException(
            503, detail={"code": "provider_not_configured",
                         "message": "No music provider is configured. Set JAMENDO_CLIENT_ID to enable search and playback."},
        )
    try:
        tracks = provider.search_tracks(q.strip(), limit)
    except ProviderError:
        raise HTTPException(502, detail={"code": "provider_error", "message": "The music provider is unavailable. Try again shortly."})
    songs = import_tracks(db, provider, tracks)  # cache results in our own catalogue
    db.commit()
    return SongSearchResponse(query=q, results=[SongOut.from_song(s) for s in songs])


@router.get("/{song_id}/similar", response_model=RecommendationsOut, summary="More like this")
def similar_songs(
    song_id: int,
    limit: int = Query(12, ge=1, le=40),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MusicProviderAdapter | None = Depends(get_music_provider),
) -> RecommendationsOut:
    try:
        result = reco_svc.similar_songs(db, user, song_id, limit=limit, provider=provider)
    except LookupError:
        raise HTTPException(404, "Song not found")
    db.commit()
    return RecommendationsOut(
        items=[
            RecommendationItemOut(
                song=SongOut.from_song(song),
                score=round(item.score, 4),
                explanations=[ExplanationOut(code=e.code, label=e.label) for e in item.explanations],
            )
            for song, item in result.items
        ],
        cold_start=result.cold_start,
        mode=result.mode,
        short_term_days=result.short_term_days,
        long_term_days=result.long_term_days,
    )


@router.get("/{song_id}", response_model=SongOut)
def get_song(song_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SongOut:
    song = db.get(Song, song_id, options=list(SONG_LOAD))
    if song is None or (song.owner_user_id is not None and song.owner_user_id != user.id):
        raise HTTPException(404, "Song not found")
    return SongOut.from_song(song)
