"""Record playback sessions and listening events (audible segments only)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ListeningEvent, PlaybackSession, Song, User, UserPreferences


class ListeningRejected(Exception):
    """Business-rule rejection (privacy off, bad span, overlap, ...)."""


def _prefs(user: User) -> UserPreferences:
    return user.preferences


def ensure_session(
    db: Session, user_id: uuid.UUID, client_session_id: str | None,
) -> PlaybackSession | None:
    if not client_session_id:
        return None
    existing = db.scalar(
        select(PlaybackSession).where(
            PlaybackSession.user_id == user_id,
            PlaybackSession.client_session_id == client_session_id,
        )
    )
    if existing is not None:
        return existing
    session = PlaybackSession(user_id=user_id, client_session_id=client_session_id)
    db.add(session)
    db.flush()
    return session


def record_event(
    db: Session,
    user: User,
    *,
    song_id: int,
    started_at: datetime,
    ended_at: datetime,
    listened_ms: int,
    song_duration_ms: int,
    completed: bool | None = None,
    client_session_id: str | None = None,
) -> ListeningEvent | None:
    """Insert one listening segment. Returns None when history recording is off."""
    prefs = _prefs(user)
    if not prefs.record_listening_history:
        return None

    song = db.get(Song, song_id)
    if song is None or (song.owner_user_id is not None and song.owner_user_id != user.id):
        raise LookupError("song")

    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if ended_at.tzinfo is None:
        ended_at = ended_at.replace(tzinfo=timezone.utc)
    if ended_at < started_at:
        raise ListeningRejected("ended_at must be >= started_at")
    if listened_ms < 0:
        raise ListeningRejected("listened_ms must be >= 0")
    if song_duration_ms <= 0:
        raise ListeningRejected("song_duration_ms must be > 0")

    span_ms = (ended_at - started_at).total_seconds() * 1000
    if listened_ms > span_ms + 1000:
        raise ListeningRejected("listened_ms exceeds the wall-clock span")

    # Tiny / accidental blips aren't useful signals.
    if listened_ms < 1_000:
        return None

    try:
        tz = ZoneInfo(prefs.timezone or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    play_date = started_at.astimezone(tz).date()

    session = ensure_session(db, user.id, client_session_id)
    # Infer completion when the client didn't say: audible time ≥ 90% of duration.
    if completed is None and song_duration_ms > 0:
        completed = listened_ms >= int(song_duration_ms * 0.9)

    event = ListeningEvent(
        user_id=user.id,
        song_id=song_id,
        session_id=session.id if session else None,
        started_at=started_at,
        ended_at=ended_at,
        listened_ms=listened_ms,
        song_duration_ms=song_duration_ms,
        completed=completed,
        play_date=play_date,
    )
    db.add(event)
    try:
        db.flush()
    except Exception as exc:
        # Exclusion constraint (overlapping events) surfaces as IntegrityError.
        raise ListeningRejected("listening event overlaps an existing one") from exc
    return event
