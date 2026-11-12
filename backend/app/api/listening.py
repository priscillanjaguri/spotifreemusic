from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.recommend import ListeningEventIn, ListeningEventOut
from app.services.listening import ListeningRejected, record_event

router = APIRouter(prefix="/listening", tags=["listening"])


@router.post(
    "/events",
    response_model=ListeningEventOut | None,
    status_code=status.HTTP_201_CREATED,
    summary="Record one audible listening segment",
)
def post_listening_event(
    body: ListeningEventIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ListeningEventOut | None:
    try:
        event = record_event(
            db,
            user,
            song_id=body.song_id,
            started_at=body.started_at,
            ended_at=body.ended_at,
            listened_ms=body.listened_ms,
            song_duration_ms=body.song_duration_ms,
            completed=body.completed,
            client_session_id=body.client_session_id,
        )
    except LookupError:
        raise HTTPException(404, "Song not found")
    except ListeningRejected as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    if event is None:
        # Privacy off or sub-second blip — acknowledge without storing.
        return None
    return ListeningEventOut(
        id=event.id,
        song_id=event.song_id,
        listened_ms=event.listened_ms,
        completed=event.completed,
        play_date=event.play_date.isoformat(),
    )
