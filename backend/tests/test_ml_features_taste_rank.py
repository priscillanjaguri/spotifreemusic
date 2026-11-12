"""Unit tests for the pure ml/ package (no database)."""
from datetime import datetime, timedelta, timezone

import numpy as np

from app.ml.eval import coverage, diversity, precision_at_k, recall_at_k, summarise_run
from app.ml.features import build_feature_matrix
from app.ml.rank import inject_exploration, mmr_select, rank_by_cosine, similar_to_seed
from app.ml.taste import Signal, blend_profiles, build_taste_profile, cold_start_from_genres


NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def _songs():
    return [
        {"id": 1, "genres": ["lofi", "chillout"], "tempo": 80, "energy": 0.3, "loudness_db": -14,
         "spectral_centroid_hz": 1200, "spectral_rolloff_hz": 3000, "zero_crossing_rate": 0.05, "key": 0, "mode": 0},
        {"id": 2, "genres": ["lofi"], "tempo": 85, "energy": 0.35, "loudness_db": -12,
         "spectral_centroid_hz": 1300, "spectral_rolloff_hz": 3200, "zero_crossing_rate": 0.06, "key": 0, "mode": 0},
        {"id": 3, "genres": ["metal", "rock"], "tempo": 160, "energy": 0.95, "loudness_db": -5,
         "spectral_centroid_hz": 4500, "spectral_rolloff_hz": 9000, "zero_crossing_rate": 0.2, "key": 7, "mode": 1},
        {"id": 4, "genres": ["jazz"], "tempo": 110, "energy": 0.5, "loudness_db": -10,
         "spectral_centroid_hz": 2000, "spectral_rolloff_hz": 5000, "zero_crossing_rate": 0.08, "key": 5, "mode": 1},
        {"id": 5, "genres": ["lofi", "jazz"], "tempo": 90, "energy": 0.4, "loudness_db": -11,
         "spectral_centroid_hz": 1500, "spectral_rolloff_hz": 3500, "zero_crossing_rate": 0.07, "key": 2, "mode": 0},
        # Tag-only song (no audio features)
        {"id": 6, "genres": ["ambient"]},
    ]


def test_feature_matrix_tag_only_fallback_and_normalization():
    fm = build_feature_matrix(_songs())
    assert len(fm.song_ids) == 6
    norms = np.linalg.norm(fm.matrix, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-6)
    assert "lofi" in fm.genre_vocab

    tags = build_feature_matrix(_songs(), tag_only=True)
    assert tags.tag_only is True
    assert tags.matrix.shape[1] == len(tags.genre_vocab)


def test_taste_profile_skips_unknown_and_weights_likes():
    fm = build_feature_matrix(_songs())
    signals = [
        Signal(1, "interested", NOW - timedelta(days=1)),
        Signal(2, "saved", NOW - timedelta(days=2)),
        Signal(3, "skipped", NOW - timedelta(days=1)),  # ignored (weight 0)
        Signal(99, "interested", NOW - timedelta(days=1)),  # missing song
        Signal(3, "interested", NOW - timedelta(days=400)),  # outside short window
    ]
    short = build_taste_profile(fm, signals, now=NOW, window_days=28)
    assert short.signal_count == 2
    assert set(short.song_ids) == {1, 2}

    long = build_taste_profile(fm, signals, now=NOW, window_days=365)
    # Day-400 signal still outside 365 from NOW? 400 > 365 so still out.
    assert long.signal_count == 2
    blended = blend_profiles(short, long)
    assert not blended.is_empty


def test_cold_start_from_genres_and_ranking():
    fm = build_feature_matrix(_songs())
    profile = cold_start_from_genres(fm, ["lofi"])
    assert not profile.is_empty
    ranked = rank_by_cosine(fm, profile, exclude={1}, limit=3)
    assert ranked[0].song_id in {2, 5}
    assert all(r.song_id != 1 for r in ranked)

    similar = similar_to_seed(fm, 1, limit=3)
    assert similar[0].song_id in {2, 5}
    assert all(r.song_id != 1 for r in similar)


def test_mmr_and_exploration_and_eval_metrics():
    fm = build_feature_matrix(_songs())
    profile = cold_start_from_genres(fm, ["lofi", "jazz"])
    ranked = rank_by_cosine(fm, profile, limit=10)
    diverse = mmr_select(fm, ranked, k=4, lambda_relevance=0.7)
    assert len(diverse) == 4
    explored = inject_exploration(
        fm, diverse, ranked, k=4, explore_frac=0.5, rng=np.random.default_rng(0),
    )
    assert len(explored) == 4

    relevant = {2, 5}
    recs = [r.song_id for r in diverse]
    assert 0.0 <= precision_at_k(recs, relevant, 4) <= 1.0
    assert 0.0 <= recall_at_k(recs, relevant, 4) <= 1.0
    assert coverage([recs], len(fm.song_ids)) > 0
    assert diversity(fm, recs) >= 0
    summary = summarise_run(fm, [recs], [relevant], k=4)
    assert "precision_at_k" in summary and summary["k"] == 4.0
