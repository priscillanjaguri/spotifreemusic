"""Taste profiles from weighted listening / feedback signals.

Skips are neutral and never contribute. Explicit `not_interested` is handled by
the service layer (candidate exclusion), not here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

import numpy as np

from app.ml.features import FeatureMatrix

# Relative weights for positive / engagement signals. Higher = stronger pull.
DEFAULT_WEIGHTS: dict[str, float] = {
    "interested": 1.0,  # explicit like
    "saved": 0.85,
    "replay": 0.9,  # played again after completing (or a second distinct play)
    "completed": 0.65,
    "play": 0.35,
}


@dataclass(frozen=True)
class Signal:
    song_id: int
    kind: str  # interested | saved | play | completed | replay
    at: datetime
    weight: float | None = None  # override DEFAULT_WEIGHTS when set


@dataclass(frozen=True)
class TasteProfile:
    vector: np.ndarray  # L2-normalised, same dim as FeatureMatrix.matrix
    song_ids: tuple[int, ...]  # songs that contributed
    window_days: int
    signal_count: int

    @property
    def is_empty(self) -> bool:
        return self.signal_count == 0 or self.vector.size == 0


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    return vec if norm == 0 else vec / norm


def build_taste_profile(
    features: FeatureMatrix,
    signals: Sequence[Signal],
    *,
    now: datetime | None = None,
    window_days: int,
    weights: dict[str, float] | None = None,
) -> TasteProfile:
    """Weighted average of song vectors for signals inside the window.

    Signals whose kind is unknown or whose weight is <= 0 are ignored.
    Songs missing from `features` are skipped.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(days=window_days)
    table = weights or DEFAULT_WEIGHTS

    acc = np.zeros(features.matrix.shape[1] if features.matrix.size else 0, dtype=float)
    used: list[int] = []
    count = 0
    if acc.size == 0:
        return TasteProfile(vector=acc, song_ids=(), window_days=window_days, signal_count=0)

    for signal in signals:
        at = signal.at if signal.at.tzinfo else signal.at.replace(tzinfo=timezone.utc)
        if at < cutoff:
            continue
        w = signal.weight if signal.weight is not None else table.get(signal.kind, 0.0)
        if w <= 0:
            continue
        vec = features.vector(signal.song_id)
        if vec is None:
            continue
        # Recency soft boost inside the window (newer ≈ up to +25%).
        age_frac = (now - at).total_seconds() / max(window_days * 86400, 1)
        recency = 1.0 + 0.25 * max(0.0, 1.0 - age_frac)
        acc = acc + (w * recency) * vec
        used.append(signal.song_id)
        count += 1

    return TasteProfile(
        vector=_normalize(acc),
        song_ids=tuple(dict.fromkeys(used)),
        window_days=window_days,
        signal_count=count,
    )


def blend_profiles(
    short: TasteProfile,
    long: TasteProfile,
    *,
    short_weight: float = 0.6,
) -> TasteProfile:
    """Combine short- and long-term profiles. Falls back to whichever is non-empty."""
    if short.is_empty and long.is_empty:
        dim = max(short.vector.size, long.vector.size)
        return TasteProfile(vector=np.zeros(dim), song_ids=(), window_days=short.window_days, signal_count=0)
    if short.is_empty:
        return long
    if long.is_empty:
        return short
    if short.vector.shape != long.vector.shape:
        raise ValueError("short and long profiles must share dimensionality")
    sw = min(1.0, max(0.0, short_weight))
    blended = _normalize(sw * short.vector + (1.0 - sw) * long.vector)
    songs = tuple(dict.fromkeys([*short.song_ids, *long.song_ids]))
    return TasteProfile(
        vector=blended,
        song_ids=songs,
        window_days=long.window_days,
        signal_count=short.signal_count + long.signal_count,
    )


def cold_start_from_genres(features: FeatureMatrix, genres: Sequence[str]) -> TasteProfile:
    """Average of songs that share any of the seed genres (onboarding / preferred)."""
    wanted = {g.strip().lower() for g in genres if g and str(g).strip()}
    if not wanted or features.matrix.size == 0:
        return TasteProfile(
            vector=np.zeros(features.matrix.shape[1] if features.matrix.ndim == 2 else 0),
            song_ids=(),
            window_days=0,
            signal_count=0,
        )
    genre_index = {g: i for i, g in enumerate(features.genre_vocab)}
    cols = [genre_index[g] for g in wanted if g in genre_index]
    if not cols:
        return TasteProfile(
            vector=np.zeros(features.matrix.shape[1]), song_ids=(), window_days=0, signal_count=0,
        )
    # Songs with any of the seed genre bits set.
    mask = features.matrix[:, cols].sum(axis=1) > 0
    if not np.any(mask):
        return TasteProfile(
            vector=np.zeros(features.matrix.shape[1]), song_ids=(), window_days=0, signal_count=0,
        )
    mean = features.matrix[mask].mean(axis=0)
    ids = tuple(int(i) for i in features.song_ids[mask])
    return TasteProfile(vector=_normalize(mean), song_ids=ids, window_days=0, signal_count=len(ids))
