from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.models import User
from app.services import lyrics as lyrics_svc

router = APIRouter(tags=["lyrics"])


class LyricsOut(BaseModel):
    title: str
    artist: str
    lyrics: str
    source: str
    genius_url: str | None


@router.get("/lyrics/{song_id}", response_model=LyricsOut, summary="Plain lyrics for a song (Genius)")
def get_lyrics(
    song_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> LyricsOut:
    if not settings.genius_enabled:
        raise HTTPException(
            503,
            detail={
                "code": "lyrics_not_configured",
                "message": "Lyrics are not configured. Set GENIUS_ACCESS_TOKEN (and GENIUS_CLIENT_SECRET if needed).",
            },
        )
    try:
        result = lyrics_svc.get_lyrics_for_song(db, settings, song_id, user.id)
    except LookupError:
        raise HTTPException(404, detail={"code": "song_not_found", "message": "Song not found"})
    except RuntimeError as exc:
        msg = str(exc)
        if msg.startswith("lyrics_fetch_failed"):
            raise HTTPException(
                502,
                detail={
                    "code": "lyrics_fetch_failed",
                    "message": "Genius matched this song but the lyrics page could not be loaded.",
                },
            )
        raise HTTPException(
            503,
            detail={
                "code": "lyrics_not_configured",
                "message": "Lyrics are not configured.",
            },
        )
    if result is None:
        raise HTTPException(
            404,
            detail={"code": "lyrics_not_found", "message": "No lyrics found for this song."},
        )
    return LyricsOut(
        title=result.title,
        artist=result.artist,
        lyrics=result.lyrics,
        source=result.source,
        genius_url=result.genius_url,
    )
