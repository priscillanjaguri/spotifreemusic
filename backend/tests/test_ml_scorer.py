"""Unit tests for the pure engagement scorer (no database)."""
import numpy as np
import pytest

from app.ml.rank import RankedItem
from app.ml.scorer import (
    FEATURE_NAMES,
    MIN_LABELED_SAMPLES,
    build_song_features,
    dumps_pipeline,
    feature_matrix,
    loads_pipeline,
    predict_engage_proba,
    train_logistic,
)
from app.services.scorer_job import rerank_by_engagement


def _synth_rows(n: int = 40):
    rows = []
    labels = []
    rng = np.random.default_rng(0)
    for i in range(n):
        # Higher cosine + genre overlap → more likely engage.
        cosine = float(rng.uniform(0.1, 0.95))
        overlap = float(rng.uniform(0.0, 1.0))
        label = 1 if (0.6 * cosine + 0.4 * overlap + rng.normal(0, 0.05)) > 0.55 else 0
        rows.append(
            build_song_features(
                cosine_score=cosine,
                song_genres=["lofi", "jazz"] if overlap > 0.5 else ["metal"],
                profile_genres=["lofi", "jazz"],
                from_library=i % 5 == 0,
                energy=0.3 + 0.5 * cosine,
                tempo=80 + 40 * cosine,
                user_plays=i % 4,
                days_since_play=float(i % 30),
            )
        )
        labels.append(label)
    # Ensure both classes are present.
    if sum(labels) < 5:
        for i in range(5):
            labels[i] = 1
            rows[i]["cosine_score"] = 0.9
            rows[i]["genre_overlap"] = 1.0
    if sum(1 for y in labels if y == 0) < 5:
        for i in range(n - 5, n):
            labels[i] = 0
            rows[i]["cosine_score"] = 0.1
            rows[i]["genre_overlap"] = 0.0
    return rows, labels


def test_build_song_features_stable_keys():
    feat = build_song_features(
        cosine_score=0.7,
        song_genres=["LoFi", "chillout"],
        profile_genres=["lofi", "jazz"],
        from_library=True,
        energy=0.4,
        tempo=90,
        user_plays=3,
        days_since_play=10,
    )
    assert set(feat) == set(FEATURE_NAMES)
    assert feat["from_library"] == 1.0
    assert 0.0 < feat["genre_overlap"] <= 1.0
    assert feat["user_plays"] == pytest.approx(np.log1p(3))


def test_train_predict_roundtrip_and_serialize():
    rows, labels = _synth_rows(48)
    assert len(rows) >= MIN_LABELED_SAMPLES
    result = train_logistic(rows, labels)
    assert result.n_samples == len(rows)
    assert result.n_positives == sum(labels)
    assert "train_accuracy" in result.metrics

    proba = predict_engage_proba(result.pipeline, rows)
    assert proba.shape == (len(rows),)
    assert np.all((proba >= 0) & (proba <= 1))

    blob = dumps_pipeline(result.pipeline)
    restored = loads_pipeline(blob)
    again = predict_engage_proba(restored, rows[:3])
    assert np.allclose(again, proba[:3], atol=1e-9)


def test_train_rejects_cold_start():
    rows, labels = _synth_rows(10)
    with pytest.raises(ValueError, match="at least"):
        train_logistic(rows, labels)


def test_rerank_by_engagement_orders_by_proba():
    ranked = [
        RankedItem(song_id=1, score=0.9),
        RankedItem(song_id=2, score=0.8),
        RankedItem(song_id=3, score=0.7),
    ]
    engage = {1: 0.2, 2: 0.9, 3: 0.5}
    out = rerank_by_engagement(ranked, engage)
    assert [r.song_id for r in out] == [2, 3, 1]
    assert out[0].score == pytest.approx(0.9)


def test_feature_matrix_shape():
    rows, _ = _synth_rows(5)
    X = feature_matrix(rows)
    assert X.shape == (5, len(FEATURE_NAMES))
