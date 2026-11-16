from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Song, User
from app.providers.base import MusicProviderAdapter, ProviderError
from app.providers.registry import get_music_providers
from app.schemas.music import SongOut, SongSearchResponse
from app.schemas.recommend import ExplanationOut, RecommendationItemOut, RecommendationsOut
from app.services.catalog import import_tracks
from app.services.collection import SONG_LOAD
from app.services import recommender as reco_svc

router = APIRouter(prefix="/songs", tags=["songs"])


def _interleave_songs(batches: list[list[Song]], limit: int) -> list[Song]:
    """Round-robin merge provider batches; keep first occurrence of each song id."""
    out: list[Song] = []
    seen: set[int] = set()
    index = 0
    while len(out) < limit:
        progressed = False
        for batch in batches:
            if index >= len(batch):
                continue
            song = batch[index]
            progressed = True
            if song.id not in seen:
                seen.add(song.id)
                out.append(song)
                if len(out) >= limit:
                    break
        if not progressed:
            break
        index += 1
    return out


@router.get("/search", response_model=SongSearchResponse, summary="Search configured music catalogues")
def search_songs(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(20, ge=1, le=50),
    providers: list[MusicProviderAdapter] = Depends(get_music_providers),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SongSearchResponse:
    if not providers:
        raise HTTPException(
            503,
            detail={
                "code": "provider_not_configured",
                "message": (
                    "No music provider is configured. Audius is on by default "
                    "(AUDIUS_ENABLED=true); set JAMENDO_CLIENT_ID for Jamendo, "
                    "or enable DEV_MOCK_PROVIDER in development."
                ),
            },
        )
    query = q.strip()
    batches: list[list[Song]] = []
    errors = 0
    for provider in providers:
        try:
            tracks = provider.search_tracks(query, limit)
        except ProviderError:
            errors += 1
            continue
        if tracks:
            batches.append(import_tracks(db, provider, tracks))
    if not batches and errors:
        raise HTTPException(
            502,
            detail={"code": "provider_error", "message": "The music provider is unavailable. Try again shortly."},
        )
    db.commit()
    songs = _interleave_songs(batches, limit)
    return SongSearchResponse(query=q, results=[SongOut.from_song(s) for s in songs])


@router.get("/{song_id}/similar", response_model=RecommendationsOut, summary="More like this")
def similar_songs(
    song_id: int,
    limit: int = Query(12, ge=1, le=40),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    providers: list[MusicProviderAdapter] = Depends(get_music_providers),
) -> RecommendationsOut:
    try:
        result = reco_svc.similar_songs(db, user, song_id, limit=limit, providers=providers)
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
