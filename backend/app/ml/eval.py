"""Offline recommender metrics: precision@k, recall@k, coverage, diversity."""
from __future__ import annotations

from typing import Sequence

import numpy as np

from app.ml.features import FeatureMatrix


def precision_at_k(recommended: Sequence[int], relevant: set[int], k: int) -> float:
    if k <= 0:
        return 0.0
    top = list(recommended)[:k]
    if not top:
        return 0.0
    return sum(1 for s in top if s in relevant) / k


def recall_at_k(recommended: Sequence[int], relevant: set[int], k: int) -> float:
    if not relevant or k <= 0:
        return 0.0
    top = list(recommended)[:k]
    return sum(1 for s in top if s in relevant) / len(relevant)


def coverage(recommended_lists: Sequence[Sequence[int]], catalog_size: int) -> float:
    """Fraction of the catalogue that appeared in at least one recommendation list."""
    if catalog_size <= 0:
        return 0.0
    seen: set[int] = set()
    for lst in recommended_lists:
        seen.update(lst)
    return len(seen) / catalog_size


def diversity(features: FeatureMatrix, recommended: Sequence[int]) -> float:
    """Mean pairwise (1 - cosine) among recommended items. Higher = more diverse."""
    idxs = [features.index_of(sid) for sid in recommended]
    idxs = [i for i in idxs if i is not None]
    if len(idxs) < 2:
        return 0.0
    vecs = features.matrix[idxs]
    sims = vecs @ vecs.T
    n = len(idxs)
    # Upper triangle only
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += 1.0 - float(sims[i, j])
            count += 1
    return total / count if count else 0.0


def summarise_run(
    features: FeatureMatrix,
    recommended_lists: Sequence[Sequence[int]],
    relevant_sets: Sequence[set[int]],
    *,
    k: int = 10,
) -> dict[str, float]:
    """Aggregate metrics across users/folds."""
    if not recommended_lists:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "coverage": 0.0, "diversity": 0.0, "k": float(k)}
    precs = [precision_at_k(r, rel, k) for r, rel in zip(recommended_lists, relevant_sets)]
    recs = [recall_at_k(r, rel, k) for r, rel in zip(recommended_lists, relevant_sets)]
    divs = [diversity(features, r[:k]) for r in recommended_lists]
    return {
        "precision_at_k": float(np.mean(precs)),
        "recall_at_k": float(np.mean(recs)),
        "coverage": coverage(recommended_lists, len(features.song_ids)),
        "diversity": float(np.mean(divs)) if divs else 0.0,
        "k": float(k),
    }
