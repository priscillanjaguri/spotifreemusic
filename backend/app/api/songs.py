from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Song, User
from app.providers.base import MusicProviderAdapter, ProviderError
from app.providers.registry import get_music_provider
from app.schemas.music import SongOut, SongSearchResponse
from app.services.catalog import import_tracks
from app.services.collection import SONG_LOAD

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


@router.get("/{song_id}", response_model=SongOut)
def get_song(song_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> SongOut:
    song = db.get(Song, song_id, options=list(SONG_LOAD))
    if song is None:
        raise HTTPException(404, "Song not found")
    return SongOut.from_song(song)
