"""Offline recommender evaluation (precision@k, recall@k, coverage, diversity).

Builds a synthetic catalogue + hold-out likes, ranks with the pure ml/ stack, and
prints aggregate metrics. No database or network required.

Usage:
    cd backend && python -m scripts.eval_recommender
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import numpy as np

from app.ml.eval import summarise_run
from app.ml.features import build_feature_matrix
from app.ml.rank import inject_exploration, mmr_select, rank_by_cosine
from app.ml.taste import Signal, blend_profiles, build_taste_profile

GENRES = ["lofi", "ambient", "jazz", "rock", "electronic", "folk", "pop", "hiphop", "piano", "house"]
NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)
RNG = np.random.default_rng(7)


def _synthetic_catalogue(n: int = 120) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        g = list(RNG.choice(GENRES, size=RNG.integers(1, 3), replace=False))
        rows.append({
            "id": i,
            "genres": g,
            "tempo": float(RNG.uniform(60, 180)),
            "energy": float(RNG.uniform(0.1, 0.95)),
            "loudness_db": float(RNG.uniform(-20, -4)),
            "spectral_centroid_hz": float(RNG.uniform(800, 5000)),
            "spectral_rolloff_hz": float(RNG.uniform(2000, 10000)),
            "zero_crossing_rate": float(RNG.uniform(0.02, 0.2)),
            "key": int(RNG.integers(0, 12)),
            "mode": int(RNG.integers(0, 2)),
        })
    return rows


def _user_signals(catalogue: list[dict], liked_genres: list[str], n_train: int = 8) -> tuple[list[Signal], set[int]]:
    """Train signals + held-out relevant set sharing the preferred genres."""
    pool = [r for r in catalogue if set(r["genres"]) & set(liked_genres)]
    RNG.shuffle(pool)
    train = pool[:n_train]
    holdout = pool[n_train: n_train + 6]
    signals = [
        Signal(r["id"], "interested" if i % 2 == 0 else "saved", NOW - timedelta(days=int(i * 3)))
        for i, r in enumerate(train)
    ]
    # A couple of plays outside the preferred genres (noise).
    noise = [r for r in catalogue if not (set(r["genres"]) & set(liked_genres))][:3]
    for i, r in enumerate(noise):
        signals.append(Signal(r["id"], "play", NOW - timedelta(days=2 + i)))
    return signals, {r["id"] for r in holdout}


def main() -> dict:
    catalogue = _synthetic_catalogue()
    features = build_feature_matrix(catalogue)
    user_prefs = [
        ["lofi", "ambient"],
        ["jazz", "piano"],
        ["rock", "electronic"],
        ["folk", "pop"],
        ["hiphop", "lofi"],
        ["house", "electronic"],
        ["ambient", "piano"],
        ["pop", "rock"],
    ]
    lists: list[list[int]] = []
    relevant_sets: list[set[int]] = []
    k = 10
    for prefs in user_prefs:
        signals, relevant = _user_signals(catalogue, prefs)
        if len(relevant) < 2:
            continue
        short = build_taste_profile(features, signals, now=NOW, window_days=28)
        long = build_taste_profile(features, signals, now=NOW, window_days=365)
        profile = blend_profiles(short, long)
        exclude = set()  # no not_interested in this offline fold
        ranked = rank_by_cosine(features, profile, exclude=exclude, limit=k * 5)
        # Don't recommend the training songs themselves.
        train_ids = {s.song_id for s in signals if s.kind in {"interested", "saved"}}
        ranked = [r for r in ranked if r.song_id not in train_ids]
        diverse = mmr_select(features, ranked, k=k, lambda_relevance=0.72)
        final = inject_exploration(
            features, diverse, ranked, k=k, explore_frac=0.1, rng=np.random.default_rng(11),
        )
        lists.append([r.song_id for r in final])
        relevant_sets.append(relevant)

    metrics = summarise_run(features, lists, relevant_sets, k=k)
    metrics["users"] = float(len(lists))
    metrics["catalogue_size"] = float(len(catalogue))
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    main()
