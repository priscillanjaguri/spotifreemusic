"""Daily companion: a mood-aware briefing + playlist from recommender + recent listening."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models import User
from app.providers.base import MusicProviderAdapter
from app.services import analytics as analytics_svc
from app.services import recommender as reco_svc
from app.services.analytics import MemoryItem

AVAILABLE_MOODS = ("soft", "dreamy", "focus", "energy", "chill", "glow")

# Mood → soft genre seeds that nudge cold-start / exploration without inventing audio.
MOOD_GENRES: dict[str, list[str]] = {
    "soft": ["ambient", "lofi", "piano", "folk"],
    "dreamy": ["dream pop", "ambient", "shoegaze", "lofi"],
    "focus": ["lofi", "classical", "ambient", "piano"],
    "energy": ["electronic", "house", "rock", "pop"],
    "chill": ["chillout", "lofi", "jazz", "soul"],
    "glow": ["pop", "synthwave", "disco", "indie"],
}

MOOD_LABELS = {
    "soft": "soft & tender",
    "dreamy": "dreamy haze",
    "focus": "deep focus",
    "energy": "high energy",
    "chill": "easy chill",
    "glow": "main-character glow",
}


@dataclass
class CompanionInsight:
    code: str
    label: str


@dataclass
class DailyCompanion:
    date: date
    timezone: str
    greeting: str
    briefing: str
    mood: str | None
    insights: list[CompanionInsight]
    playlist: reco_svc.RecommendationResult
    spotlight: MemoryItem | None


def _greeting(hour: int, name: str) -> str:
    first = name.split()[0] if name else "there"
    if hour < 5:
        return f"Still glowing, {first}"
    if hour < 12:
        return f"Good morning, {first}"
    if hour < 18:
        return f"Good afternoon, {first}"
    return f"Good evening, {first}"


def build_daily_companion(
    db: Session,
    user: User,
    *,
    mood: str | None = None,
    limit: int = 12,
    provider: MusicProviderAdapter | None = None,
    now: datetime | None = None,
) -> DailyCompanion:
    now = now or datetime.now(timezone.utc)
    prefs = user.preferences
    today = analytics_svc._today(prefs, now)
    local = now.astimezone(analytics_svc._tz(prefs))

    mood = mood.lower().strip() if mood else None
    if mood and mood not in AVAILABLE_MOODS:
        raise ValueError("unknown mood")

    # Temporarily blend mood seeds into preferred_genres for this request only.
    original = list(prefs.preferred_genres or [])
    if mood:
        seeds = MOOD_GENRES[mood]
        prefs.preferred_genres = list(dict.fromkeys([*seeds, *original]))[:20]

    try:
        playlist = reco_svc.recommend_for_user(db, user, limit=limit, provider=provider, now=now)
    finally:
        prefs.preferred_genres = original

    week = analytics_svc.compute_period(db, user, "week", 0, top_n=5, now=now)
    insights: list[CompanionInsight] = []
    if week.total_listened_ms > 0:
        mins = max(1, round(week.total_listened_ms / 60_000))
        insights.append(
            CompanionInsight("listen_time", f"You've listened about {mins} min this week.")
        )
    if week.top_genres:
        g = week.top_genres[0].name
        insights.append(CompanionInsight("top_genre", f"Your week leans {g}."))
    if week.completion_rate is not None:
        pct = int(round(week.completion_rate * 100))
        insights.append(
            CompanionInsight("completion", f"Completion rate this week: {pct}%.")
        )
    if week.unique_songs:
        insights.append(
            CompanionInsight(
                "variety",
                f"{week.unique_songs} different songs so far this week.",
            )
        )
    if not insights:
        insights.append(
            CompanionInsight(
                "fresh",
                "Play a few tracks and Spotifree will start shaping today's mix around you.",
            )
        )

    lane = analytics_svc.memory_lane(db, user, limit=8, now=now)
    spotlight = lane.items[0] if lane.items else None

    if mood:
        briefing = (
            f"Today's companion is tuned to {MOOD_LABELS[mood]}. "
            f"Here's a mix drawn from your taste"
            + (", recent listens," if week.play_count else "")
            + " and a little exploration."
        )
    elif week.top_genres:
        briefing = (
            f"Based on your recent {week.top_genres[0].name} streak, "
            "here's a companion playlist for the day — familiar colours, fresh picks."
        )
    else:
        briefing = (
            "A gentle start: Spotifree mixed what it knows about you with a few new shades. "
            "Pick a mood anytime to steer the day."
        )

    return DailyCompanion(
        date=today,
        timezone=prefs.timezone or "UTC",
        greeting=_greeting(local.hour, user.display_name),
        briefing=briefing,
        mood=mood,
        insights=insights,
        playlist=playlist,
        spotlight=spotlight,
    )
