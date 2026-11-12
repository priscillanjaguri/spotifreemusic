"""On-demand listening analytics, taste timeline and memory lane.

Computed from `listening_events` (+ interactions for milestones). No cached
aggregate tables — the indexes on (user_id, play_date) / (user_id, started_at)
keep this cheap for personal-scale history.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ListeningEvent,
    PlaybackSession,
    Song,
    User,
    UserCollection,
    UserInteraction,
    UserPreferences,
)
from app.services.collection import SONG_LOAD


def _tz(prefs: UserPreferences) -> ZoneInfo:
    try:
        return ZoneInfo(prefs.timezone or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def _today(prefs: UserPreferences, now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    return now.astimezone(_tz(prefs)).date()


def period_bounds(
    prefs: UserPreferences,
    period: str,
    offset: int = 0,
    *,
    now: datetime | None = None,
) -> tuple[date, date]:
    """Return inclusive [start, end] dates in the user's local calendar."""
    today = _today(prefs, now)
    if period == "week":
        # week_starts_on: 0=Mon … 6=Sun. Python weekday(): Mon=0 … Sun=6.
        start_dow = prefs.week_starts_on % 7
        delta = (today.weekday() - start_dow) % 7
        this_start = today - timedelta(days=delta)
        start = this_start - timedelta(weeks=offset)
        end = start + timedelta(days=6)
        return start, end
    if period == "month":
        # Walk back `offset` calendar months from the current month.
        y, m = today.year, today.month
        m -= offset
        while m <= 0:
            m += 12
            y -= 1
        start = date(y, m, 1)
        if m == 12:
            end = date(y, 12, 31)
        else:
            end = date(y, m + 1, 1) - timedelta(days=1)
        return start, end
    raise ValueError("period must be 'week' or 'month'")


@dataclass
class NamedStat:
    id: int | None
    name: str
    play_count: int
    listened_ms: int


@dataclass
class SongStat:
    song: Song
    play_count: int
    listened_ms: int
    completed_count: int


@dataclass
class DailyStat:
    day: date
    play_count: int
    listened_ms: int


@dataclass
class AnalyticsPeriod:
    period: str
    offset: int
    start: date
    end: date
    timezone: str
    total_listened_ms: int
    play_count: int
    unique_songs: int
    unique_artists: int
    completion_rate: float | None
    top_artists: list[NamedStat]
    top_genres: list[NamedStat]
    top_songs: list[SongStat]
    daily: list[DailyStat]


def _events_in_range(db: Session, user_id: uuid.UUID, start: date, end: date) -> list[ListeningEvent]:
    return list(
        db.scalars(
            select(ListeningEvent)
            .where(
                ListeningEvent.user_id == user_id,
                ListeningEvent.play_date >= start,
                ListeningEvent.play_date <= end,
            )
            .options(
                selectinload(ListeningEvent.song).options(*SONG_LOAD),
            )
            .order_by(ListeningEvent.started_at.asc())
        ).unique().all()
    )


def compute_period(
    db: Session,
    user: User,
    period: str,
    offset: int = 0,
    *,
    top_n: int = 10,
    now: datetime | None = None,
) -> AnalyticsPeriod:
    prefs = user.preferences
    start, end = period_bounds(prefs, period, offset, now=now)
    events = _events_in_range(db, user.id, start, end)

    total_ms = sum(e.listened_ms for e in events)
    play_count = len(events)
    song_ids = {e.song_id for e in events}

    artist_ms: dict[int, int] = defaultdict(int)
    artist_plays: dict[int, int] = defaultdict(int)
    artist_name: dict[int, str] = {}
    genre_ms: dict[str, int] = defaultdict(int)
    genre_plays: dict[str, int] = defaultdict(int)
    song_ms: dict[int, int] = defaultdict(int)
    song_plays: dict[int, int] = defaultdict(int)
    song_completed: dict[int, int] = defaultdict(int)
    song_obj: dict[int, Song] = {}
    daily_ms: dict[date, int] = defaultdict(int)
    daily_plays: dict[date, int] = defaultdict(int)
    known = 0
    completed = 0

    for e in events:
        song = e.song
        song_obj[e.song_id] = song
        song_ms[e.song_id] += e.listened_ms
        song_plays[e.song_id] += 1
        if e.completed is True:
            song_completed[e.song_id] += 1
            completed += 1
            known += 1
        elif e.completed is False:
            known += 1
        daily_ms[e.play_date] += e.listened_ms
        daily_plays[e.play_date] += 1
        for link in song.artist_links:
            artist_ms[link.artist.id] += e.listened_ms
            artist_plays[link.artist.id] += 1
            artist_name[link.artist.id] = link.artist.name
        for g in song.genres:
            genre_ms[g.name] += e.listened_ms
            genre_plays[g.name] += 1

    top_artists = sorted(
        (
            NamedStat(aid, artist_name[aid], artist_plays[aid], artist_ms[aid])
            for aid in artist_ms
        ),
        key=lambda s: (-s.listened_ms, -s.play_count, s.name),
    )[:top_n]
    top_genres = sorted(
        (
            NamedStat(None, name, genre_plays[name], genre_ms[name])
            for name in genre_ms
        ),
        key=lambda s: (-s.listened_ms, -s.play_count, s.name),
    )[:top_n]
    top_songs = sorted(
        (
            SongStat(
                song_obj[sid],
                song_plays[sid],
                song_ms[sid],
                song_completed[sid],
            )
            for sid in song_ms
        ),
        key=lambda s: (-s.listened_ms, -s.play_count, s.song.title),
    )[:top_n]

    daily: list[DailyStat] = []
    day = start
    while day <= end:
        daily.append(DailyStat(day, daily_plays.get(day, 0), daily_ms.get(day, 0)))
        day += timedelta(days=1)

    return AnalyticsPeriod(
        period=period,
        offset=offset,
        start=start,
        end=end,
        timezone=prefs.timezone or "UTC",
        total_listened_ms=total_ms,
        play_count=play_count,
        unique_songs=len(song_ids),
        unique_artists=len(artist_ms),
        completion_rate=(completed / known) if known else None,
        top_artists=top_artists,
        top_genres=top_genres,
        top_songs=top_songs,
        daily=daily,
    )


@dataclass
class TimelineWeek:
    week_start: date
    week_end: date
    listened_ms: int
    play_count: int
    unique_songs: int
    top_genres: list[NamedStat]


@dataclass
class Milestone:
    at: datetime
    kind: str
    label: str
    song: Song | None


@dataclass
class TasteTimeline:
    weeks: list[TimelineWeek]
    milestones: list[Milestone]


def taste_timeline(
    db: Session,
    user: User,
    *,
    weeks: int = 12,
    now: datetime | None = None,
) -> TasteTimeline:
    prefs = user.preferences
    weeks = max(1, min(weeks, 52))
    out_weeks: list[TimelineWeek] = []
    for offset in range(weeks - 1, -1, -1):
        start, end = period_bounds(prefs, "week", offset, now=now)
        events = _events_in_range(db, user.id, start, end)
        genre_ms: dict[str, int] = defaultdict(int)
        for e in events:
            for g in e.song.genres:
                genre_ms[g.name] += e.listened_ms
        top = sorted(
            (NamedStat(None, n, 0, ms) for n, ms in genre_ms.items()),
            key=lambda s: (-s.listened_ms, s.name),
        )[:5]
        # Fill play_count as share proxy for UI bars.
        total = sum(s.listened_ms for s in top) or 1
        top = [
            NamedStat(None, s.name, int(round(100 * s.listened_ms / total)), s.listened_ms)
            for s in top
        ]
        out_weeks.append(
            TimelineWeek(
                week_start=start,
                week_end=end,
                listened_ms=sum(e.listened_ms for e in events),
                play_count=len(events),
                unique_songs=len({e.song_id for e in events}),
                top_genres=top,
            )
        )

    milestones: list[Milestone] = []

    first_event = db.scalar(
        select(ListeningEvent)
        .where(ListeningEvent.user_id == user.id)
        .options(selectinload(ListeningEvent.song).options(*SONG_LOAD))
        .order_by(ListeningEvent.started_at.asc())
        .limit(1)
    )
    if first_event is not None:
        milestones.append(
            Milestone(
                first_event.started_at,
                "first_listen",
                f"First listen · {first_event.song.title}",
                first_event.song,
            )
        )

    first_like = db.scalar(
        select(UserInteraction)
        .where(
            UserInteraction.user_id == user.id,
            UserInteraction.interaction_type == "interested",
            UserInteraction.song_id.is_not(None),
        )
        .order_by(UserInteraction.created_at.asc())
        .limit(1)
    )
    if first_like is not None and first_like.song_id is not None:
        song = db.get(Song, first_like.song_id, options=list(SONG_LOAD))
        if song is not None:
            milestones.append(
                Milestone(first_like.created_at, "first_like", f"First like · {song.title}", song)
            )

    first_save = db.scalar(
        select(UserCollection)
        .where(UserCollection.user_id == user.id)
        .options(selectinload(UserCollection.song).options(*SONG_LOAD))
        .order_by(UserCollection.added_at.asc())
        .limit(1)
    )
    if first_save is not None:
        milestones.append(
            Milestone(
                first_save.added_at,
                "first_save",
                f"First save · {first_save.song.title}",
                first_save.song,
            )
        )

    # Most-replayed song overall (by play_count of events).
    replay = db.execute(
        select(
            ListeningEvent.song_id,
            func.count().label("n"),
            func.min(ListeningEvent.started_at).label("first_at"),
        )
        .where(ListeningEvent.user_id == user.id)
        .group_by(ListeningEvent.song_id)
        .order_by(func.count().desc())
        .limit(1)
    ).first()
    if replay is not None and replay.n >= 2:
        song = db.get(Song, replay.song_id, options=list(SONG_LOAD))
        if song is not None:
            milestones.append(
                Milestone(
                    replay.first_at,
                    "most_replayed",
                    f"Most replayed · {song.title} ({replay.n}×)",
                    song,
                )
            )

    milestones.sort(key=lambda m: m.at)
    return TasteTimeline(weeks=out_weeks, milestones=milestones)


@dataclass
class MemoryItem:
    kind: str
    label: str
    at: datetime | None
    song: Song
    listened_ms: int | None = None
    play_count: int | None = None


@dataclass
class MemoryLane:
    items: list[MemoryItem]


def memory_lane(
    db: Session,
    user: User,
    *,
    limit: int = 24,
    now: datetime | None = None,
) -> MemoryLane:
    prefs = user.preferences
    today = _today(prefs, now)
    items: list[MemoryItem] = []
    seen: set[tuple[str, int]] = set()

    def add(item: MemoryItem) -> None:
        key = (item.kind, item.song.id)
        if key in seen:
            return
        seen.add(key)
        items.append(item)

    # On this day: same month-day in prior years/months of history (any past play_date matching day).
    past = list(
        db.scalars(
            select(ListeningEvent)
            .where(
                ListeningEvent.user_id == user.id,
                ListeningEvent.play_date < today,
                func.extract("day", ListeningEvent.play_date) == today.day,
                func.extract("month", ListeningEvent.play_date) == today.month,
            )
            .options(selectinload(ListeningEvent.song).options(*SONG_LOAD))
            .order_by(ListeningEvent.started_at.desc())
            .limit(12)
        ).unique().all()
    )
    for e in past:
        add(
            MemoryItem(
                "on_this_day",
                f"On this day · {e.play_date.isoformat()}",
                e.started_at,
                e.song,
                e.listened_ms,
                1,
            )
        )

    # Fallback "same weekday last week" if no calendar match.
    if not past:
        last_week = today - timedelta(days=7)
        week_ago = list(
            db.scalars(
                select(ListeningEvent)
                .where(
                    ListeningEvent.user_id == user.id,
                    ListeningEvent.play_date == last_week,
                )
                .options(selectinload(ListeningEvent.song).options(*SONG_LOAD))
                .order_by(ListeningEvent.listened_ms.desc())
                .limit(6)
            ).unique().all()
        )
        for e in week_ago:
            add(
                MemoryItem(
                    "flashback",
                    f"This time last week · {e.song.title}",
                    e.started_at,
                    e.song,
                    e.listened_ms,
                    1,
                )
            )

    # Rediscovered: listened, gap ≥ 14 days, then listened again.
    rows = db.execute(
        select(
            ListeningEvent.song_id,
            func.min(ListeningEvent.started_at).label("first_at"),
            func.max(ListeningEvent.started_at).label("last_at"),
            func.count().label("n"),
            func.sum(ListeningEvent.listened_ms).label("ms"),
        )
        .where(ListeningEvent.user_id == user.id)
        .group_by(ListeningEvent.song_id)
        .having(func.count() >= 2)
        .order_by(func.max(ListeningEvent.started_at).desc())
        .limit(40)
    ).all()
    for row in rows:
        gap = (row.last_at - row.first_at).total_seconds()
        if gap < 14 * 86_400:
            continue
        # Require a mid-gap silence: check that there is a stretch ≥ 14d between consecutive plays.
        times = list(
            db.scalars(
                select(ListeningEvent.started_at)
                .where(
                    ListeningEvent.user_id == user.id,
                    ListeningEvent.song_id == row.song_id,
                )
                .order_by(ListeningEvent.started_at.asc())
            ).all()
        )
        rediscovered = any(
            (times[i] - times[i - 1]).total_seconds() >= 14 * 86_400
            for i in range(1, len(times))
        )
        if not rediscovered:
            continue
        song = db.get(Song, row.song_id, options=list(SONG_LOAD))
        if song is None:
            continue
        add(
            MemoryItem(
                "rediscovered",
                f"Rediscovered · {song.title}",
                row.last_at,
                song,
                int(row.ms or 0),
                int(row.n),
            )
        )
        if sum(1 for i in items if i.kind == "rediscovered") >= 6:
            break

    first_save = db.scalar(
        select(UserCollection)
        .where(UserCollection.user_id == user.id)
        .options(selectinload(UserCollection.song).options(*SONG_LOAD))
        .order_by(UserCollection.added_at.asc())
        .limit(1)
    )
    if first_save is not None:
        add(
            MemoryItem(
                "first_save",
                f"Your first save · {first_save.song.title}",
                first_save.added_at,
                first_save.song,
            )
        )

    first_like = db.scalar(
        select(UserInteraction)
        .where(
            UserInteraction.user_id == user.id,
            UserInteraction.interaction_type == "interested",
            UserInteraction.song_id.is_not(None),
        )
        .order_by(UserInteraction.created_at.asc())
        .limit(1)
    )
    if first_like is not None and first_like.song_id is not None:
        song = db.get(Song, first_like.song_id, options=list(SONG_LOAD))
        if song is not None:
            add(
                MemoryItem(
                    "first_like",
                    f"Your first like · {song.title}",
                    first_like.created_at,
                    song,
                )
            )

    top = db.execute(
        select(
            ListeningEvent.song_id,
            func.count().label("n"),
            func.sum(ListeningEvent.listened_ms).label("ms"),
            func.max(ListeningEvent.started_at).label("last_at"),
        )
        .where(ListeningEvent.user_id == user.id)
        .group_by(ListeningEvent.song_id)
        .order_by(func.count().desc(), func.sum(ListeningEvent.listened_ms).desc())
        .limit(5)
    ).all()
    for row in top:
        if row.n < 2:
            continue
        song = db.get(Song, row.song_id, options=list(SONG_LOAD))
        if song is None:
            continue
        add(
            MemoryItem(
                "most_replayed",
                f"A favourite · {song.title} ({row.n}×)",
                row.last_at,
                song,
                int(row.ms or 0),
                int(row.n),
            )
        )

    return MemoryLane(items=items[:limit])


def delete_listening_history(db: Session, user_id: uuid.UUID) -> tuple[int, int]:
    """Wipe listening_events and playback_sessions for the user. Interactions stay."""
    events = db.execute(
        delete(ListeningEvent).where(ListeningEvent.user_id == user_id)
    ).rowcount or 0
    sessions = db.execute(
        delete(PlaybackSession).where(PlaybackSession.user_id == user_id)
    ).rowcount or 0
    db.flush()
    return int(events), int(sessions)
