"""Classical engagement scorer: logistic P(engage) from impression feature snapshots.

Pure ml/ — no DB / FastAPI. Services build feature dicts and call train / predict.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Stable order for training rows and serve-time vectors.
FEATURE_NAMES: tuple[str, ...] = (
    "cosine_score",
    "genre_overlap",
    "from_library",
    "has_audio",
    "energy",
    "tempo_norm",
    "user_plays",
    "days_since_play",
)

# Personal app: need enough labeled impressions before trusting the model.
MIN_LABELED_SAMPLES = 20
MIN_POSITIVES = 3
MIN_NEGATIVES = 3


@dataclass(frozen=True)
class TrainResult:
    pipeline: Pipeline
    feature_names: tuple[str, ...]
    n_samples: int
    n_positives: int
    metrics: dict[str, float]


def feature_vector(features: Mapping[str, Any], names: Sequence[str] = FEATURE_NAMES) -> np.ndarray:
    """Map a feature dict onto a dense float row (missing keys → 0)."""
    return np.array([float(features.get(name, 0.0) or 0.0) for name in names], dtype=float)


def feature_matrix(
    rows: Sequence[Mapping[str, Any]],
    names: Sequence[str] = FEATURE_NAMES,
) -> np.ndarray:
    if not rows:
        return np.zeros((0, len(names)), dtype=float)
    return np.vstack([feature_vector(r, names) for r in rows])


def build_song_features(
    *,
    cosine_score: float,
    song_genres: Sequence[str],
    profile_genres: Sequence[str],
    from_library: bool,
    energy: float | None,
    tempo: float | None,
    user_plays: int = 0,
    days_since_play: float | None = None,
) -> dict[str, float]:
    """Assemble the stable feature dict stored on impressions and used at serve time."""
    sg = {str(g).strip().lower() for g in song_genres if g}
    pg = {str(g).strip().lower() for g in profile_genres if g}
    if sg and pg:
        overlap = len(sg & pg) / max(1, len(sg))
    else:
        overlap = 0.0
    has_audio = 1.0 if energy is not None or tempo is not None else 0.0
    energy_v = float(energy) if energy is not None else 0.5
    tempo_v = min(1.0, max(0.0, float(tempo) / 200.0)) if tempo is not None else 0.5
    # Never played → treat as "old" (capped at 365 days).
    days = float(days_since_play) if days_since_play is not None else 365.0
    days = min(365.0, max(0.0, days))
    return {
        "cosine_score": float(cosine_score),
        "genre_overlap": float(overlap),
        "from_library": 1.0 if from_library else 0.0,
        "has_audio": has_audio,
        "energy": energy_v,
        "tempo_norm": tempo_v,
        "user_plays": float(np.log1p(max(0, user_plays))),
        "days_since_play": days / 365.0,
    }


def train_logistic(
    feature_rows: Sequence[Mapping[str, Any]],
    labels: Sequence[int],
    *,
    feature_names: Sequence[str] = FEATURE_NAMES,
    random_state: int = 42,
) -> TrainResult:
    """Fit StandardScaler + LogisticRegression. Raises ValueError if too few labels."""
    y = np.asarray(list(labels), dtype=int)
    if y.size < MIN_LABELED_SAMPLES:
        raise ValueError(f"Need at least {MIN_LABELED_SAMPLES} labeled samples, got {y.size}")
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos < MIN_POSITIVES or n_neg < MIN_NEGATIVES:
        raise ValueError(
            f"Need ≥{MIN_POSITIVES} positives and ≥{MIN_NEGATIVES} negatives "
            f"(got pos={n_pos}, neg={n_neg})"
        )
    X = feature_matrix(feature_rows, feature_names)
    pipe = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=500,
                    class_weight="balanced",
                    random_state=random_state,
                ),
            ),
        ]
    )
    pipe.fit(X, y)
    proba = pipe.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    acc = float((pred == y).mean())
    # Simple positive-class precision/recall on the train set (portfolio transparency, not CV).
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return TrainResult(
        pipeline=pipe,
        feature_names=tuple(feature_names),
        n_samples=int(y.size),
        n_positives=n_pos,
        metrics={
            "train_accuracy": round(acc, 4),
            "train_precision": round(precision, 4),
            "train_recall": round(recall, 4),
            "n_negatives": float(n_neg),
        },
    )


def predict_engage_proba(
    pipeline: Pipeline,
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    feature_names: Sequence[str] = FEATURE_NAMES,
) -> np.ndarray:
    """Return P(engage=1) for each row."""
    if not feature_rows:
        return np.array([], dtype=float)
    X = feature_matrix(feature_rows, feature_names)
    return pipeline.predict_proba(X)[:, 1]


def dumps_pipeline(pipeline: Pipeline) -> bytes:
    buf = io.BytesIO()
    joblib.dump(pipeline, buf)
    return buf.getvalue()


def loads_pipeline(blob: bytes) -> Pipeline:
    return joblib.load(io.BytesIO(blob))
