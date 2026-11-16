"""Live online metrics from recommendation impressions + listening/feedback labels.

Complements offline hold-out ranking in eval_job: engage/skip/like/play rates over
time for the portfolio /eval dashboard (browser only — not in the APK).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.ml.eval import summarise_online
from app.models.scorer import RecommendationImpression

# Enough labeled outcomes before we treat online rates as meaningful on the dashboard.
MIN_LABELED_FOR_ONLINE = 5
# Daily buckets for the online trend strip.
DEFAULT_SERIES_DAYS = 28

ONLINE_METRIC_BLURBS = {
    "engage_rate": "Of labeled recommendations, how often the user engaged (like or substantial play).",
    "skip_rate": "Of labeled recommendations, how often the user skipped early.",
    "like_rate": "Of labeled recommendations, how often the user explicitly liked the track.",
    "play_rate": "Of labeled recommendations, how often the user played through (play/complete).",
}


def collect_impression_volume(db: Session) -> dict[str, int]:
    shown = int(db.scalar(select(func.count()).select_from(RecommendationImpression)) or 0)
    labeled = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationImpression)
            .where(RecommendationImpression.label.is_not(None))
        )
        or 0
    )
    positives = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationImpression)
            .where(RecommendationImpression.label == 1)
        )
        or 0
    )
    return {
        "impressions_shown": shown,
        "impressions_labeled": labeled,
        "impressions_pending": max(0, shown - labeled),
        "impressions_positive": positives,
        "impressions_negative": max(0, labeled - positives),
    }


def collect_label_source_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(RecommendationImpression.label_source, func.count())
        .where(RecommendationImpression.label.is_not(None))
        .group_by(RecommendationImpression.label_source)
    ).all()
    counts = {str(src or "unknown"): int(n) for src, n in rows}
    for key in ("like", "hide", "play", "complete", "skip"):
        counts.setdefault(key, 0)
    return counts


def collect_online_metrics(db: Session) -> dict[str, float]:
    """Point-in-time online rates from all labeled impressions."""
    volume = collect_impression_volume(db)
    sources = collect_label_source_counts(db)
    return summarise_online(
        impressions_shown=volume["impressions_shown"],
        impressions_labeled=volume["impressions_labeled"],
        positives=volume["impressions_positive"],
        source_counts=sources,
    )


def collect_online_series(db: Session, *, days: int = DEFAULT_SERIES_DAYS) -> list[dict[str, Any]]:
    """Per-day engage / skip rates for the last `days` (UTC calendar days)."""
    days = max(1, min(int(days), 90))
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_bucket = func.date_trunc("day", RecommendationImpression.labeled_at)

    rows = db.execute(
        select(
            day_bucket.label("day"),
            func.count().label("labeled"),
            func.sum(case((RecommendationImpression.label == 1, 1), else_=0)).label("positives"),
            func.sum(case((RecommendationImpression.label_source == "skip", 1), else_=0)).label("skips"),
            func.sum(case((RecommendationImpression.label_source == "like", 1), else_=0)).label("likes"),
            func.sum(
                case(
                    (RecommendationImpression.label_source.in_(("play", "complete")), 1),
                    else_=0,
                )
            ).label("plays"),
        )
        .where(
            RecommendationImpression.label.is_not(None),
            RecommendationImpression.labeled_at.is_not(None),
            RecommendationImpression.labeled_at >= start,
        )
        .group_by(day_bucket)
        .order_by(day_bucket.asc())
    ).all()

    by_day: dict[str, dict[str, Any]] = {}
    for row in rows:
        day = row.day
        if day is None:
            continue
        if getattr(day, "tzinfo", None) is None:
            day = day.replace(tzinfo=timezone.utc)
        key = day.astimezone(timezone.utc).date().isoformat()
        labeled = int(row.labeled or 0)
        positives = int(row.positives or 0)
        skips = int(row.skips or 0)
        likes = int(row.likes or 0)
        plays = int(row.plays or 0)
        by_day[key] = {
            "date": key,
            "labeled": labeled,
            "engage_rate": (positives / labeled) if labeled else 0.0,
            "skip_rate": (skips / labeled) if labeled else 0.0,
            "like_rate": (likes / labeled) if labeled else 0.0,
            "play_rate": (plays / labeled) if labeled else 0.0,
        }

    series: list[dict[str, Any]] = []
    for i in range(days):
        key = (start + timedelta(days=i)).date().isoformat()
        series.append(
            by_day.get(
                key,
                {
                    "date": key,
                    "labeled": 0,
                    "engage_rate": 0.0,
                    "skip_rate": 0.0,
                    "like_rate": 0.0,
                    "play_rate": 0.0,
                },
            )
        )
    return series


def online_ready(db: Session) -> bool:
    volume = collect_impression_volume(db)
    return volume["impressions_labeled"] >= MIN_LABELED_FOR_ONLINE


def build_online_block(db: Session) -> dict[str, Any]:
    metrics = collect_online_metrics(db)
    labeled = int(metrics["impressions_labeled"])
    return {
        "ready": labeled >= MIN_LABELED_FOR_ONLINE,
        "min_labeled_required": MIN_LABELED_FOR_ONLINE,
        "metrics": metrics,
        "label_sources": collect_label_source_counts(db),
        "series": collect_online_series(db),
        "metric_blurbs": ONLINE_METRIC_BLURBS,
    }
