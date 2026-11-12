"""Explicit recommendation feedback (like / not interested)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Song, UserInteraction

# Map the public API verbs onto the schema's interaction_type values.
ACTION_TO_TYPE = {"like": "interested", "not_interested": "not_interested"}


def record_feedback(
    db: Session,
    user_id: uuid.UUID,
    song_id: int,
    action: str,
    *,
    context: str | None = "recommendations",
) -> UserInteraction:
    if action not in ACTION_TO_TYPE:
        raise ValueError(f"Unknown feedback action: {action}")
    song = db.get(Song, song_id)
    if song is None or (song.owner_user_id is not None and song.owner_user_id != user_id):
        raise LookupError("song")
    row = UserInteraction(
        user_id=user_id,
        song_id=song_id,
        interaction_type=ACTION_TO_TYPE[action],
        context=(context or "recommendations")[:30],
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def latest_not_interested_ids(db: Session, user_id: uuid.UUID) -> set[int]:
    """Song ids whose *current* interaction state is not_interested."""
    rows = db.execute(
        select(UserInteraction.song_id, UserInteraction.interaction_type, UserInteraction.created_at)
        .where(UserInteraction.user_id == user_id, UserInteraction.song_id.is_not(None))
        .order_by(UserInteraction.created_at.desc(), UserInteraction.id.desc())
    ).all()
    latest: dict[int, str] = {}
    for song_id, itype, _ in rows:
        if song_id not in latest:
            latest[int(song_id)] = itype
    return {sid for sid, itype in latest.items() if itype == "not_interested"}
