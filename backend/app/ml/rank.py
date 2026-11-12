"""Cosine ranking, MMR diversity, light exploration, and explanation chips."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from app.ml.features import FeatureMatrix
from app.ml.taste import TasteProfile


@dataclass(frozen=True)
class Explanation:
    """A short chip shown next to a recommendation."""

    code: str  # stable machine id, e.g. "genre_match"
    label: str  # human text, e.g. "Matches your love of lofi"


@dataclass(frozen=True)
class RankedItem:
    song_id: int
    score: float
    explanations: tuple[Explanation, ...] = ()


def rank_by_cosine(
    features: FeatureMatrix,
    profile: TasteProfile,
    *,
    exclude: set[int] | None = None,
    limit: int | None = None,
) -> list[RankedItem]:
    """Score every candidate by cosine similarity to the taste profile."""
    if profile.is_empty or features.matrix.size == 0:
        return []
    exclude = exclude or set()
    scores = features.matrix @ profile.vector  # rows are L2-normalised
    order = np.argsort(-scores)
    out: list[RankedItem] = []
    for idx in order:
        sid = int(features.song_ids[idx])
        if sid in exclude:
            continue
        out.append(RankedItem(song_id=sid, score=float(scores[idx])))
        if limit is not None and len(out) >= limit:
            break
    return out


def similar_to_seed(
    features: FeatureMatrix,
    seed_song_id: int,
    *,
    exclude: set[int] | None = None,
    limit: int = 20,
) -> list[RankedItem]:
    """Nearest neighbours of one song (More like this)."""
    seed = features.vector(seed_song_id)
    if seed is None:
        return []
    profile = TasteProfile(vector=seed, song_ids=(seed_song_id,), window_days=0, signal_count=1)
    ban = set(exclude or ())
    ban.add(seed_song_id)
    return rank_by_cosine(features, profile, exclude=ban, limit=limit)


def mmr_select(
    features: FeatureMatrix,
    ranked: Sequence[RankedItem],
    *,
    k: int,
    lambda_relevance: float = 0.7,
) -> list[RankedItem]:
    """Maximal Marginal Relevance: keep relevance high while spreading genres/sound."""
    if k <= 0 or not ranked:
        return []
    id_to_idx = {int(sid): i for i, sid in enumerate(features.song_ids)}
    candidates = [r for r in ranked if r.song_id in id_to_idx]
    if not candidates:
        return []

    selected: list[RankedItem] = []
    selected_idxs: list[int] = []
    remaining = list(candidates)
    lam = min(1.0, max(0.0, lambda_relevance))

    while remaining and len(selected) < k:
        best_i = 0
        best_score = -1e18
        for i, item in enumerate(remaining):
            rel = item.score
            if not selected_idxs:
                mmr = rel
            else:
                vec = features.matrix[id_to_idx[item.song_id]]
                max_sim = float(max(vec @ features.matrix[j] for j in selected_idxs))
                mmr = lam * rel - (1.0 - lam) * max_sim
            if mmr > best_score:
                best_score = mmr
                best_i = i
        chosen = remaining.pop(best_i)
        selected.append(chosen)
        selected_idxs.append(id_to_idx[chosen.song_id])
    return selected


def inject_exploration(
    features: FeatureMatrix,
    selected: Sequence[RankedItem],
    pool: Sequence[RankedItem],
    *,
    k: int,
    explore_frac: float = 0.15,
    rng: np.random.Generator | None = None,
) -> list[RankedItem]:
    """Replace a few slots with lower-ranked candidates the user hasn't seen yet."""
    if k <= 0:
        return []
    rng = rng or np.random.default_rng()
    n_explore = min(len(pool), max(0, int(round(k * explore_frac))))
    keep = list(selected[: max(0, k - n_explore)])
    chosen_ids = {r.song_id for r in keep}
    explorers = [r for r in pool if r.song_id not in chosen_ids]
    if not explorers or n_explore == 0:
        return list(selected[:k])
    picks = rng.choice(len(explorers), size=min(n_explore, len(explorers)), replace=False)
    for i in picks:
        item = explorers[int(i)]
        keep.append(RankedItem(
            song_id=item.song_id,
            score=item.score,
            explanations=(Explanation("exploration", "A little something different"),),
        ))
        chosen_ids.add(item.song_id)
    # Preserve roughly relevance order for the non-exploration slots; explorers at the end.
    return keep[:k]


def explain_recommendations(
    features: FeatureMatrix,
    profile: TasteProfile,
    items: Sequence[RankedItem],
    *,
    song_meta: dict[int, dict] | None = None,
) -> list[RankedItem]:
    """Attach up to two explanation chips per item (genre overlap + audio / source)."""
    song_meta = song_meta or {}
    profile_genres = _top_profile_genres(features, profile, n=5)
    out: list[RankedItem] = []
    for item in items:
        chips: list[Explanation] = list(item.explanations)
        meta = song_meta.get(item.song_id) or {}
        genres = [str(g).lower() for g in (meta.get("genres") or [])]
        overlap = [g for g in genres if g in profile_genres]
        if overlap and not any(c.code == "genre_match" for c in chips):
            label = f"Matches your love of {overlap[0]}"
            chips.append(Explanation("genre_match", label))
        if meta.get("from_library") and not any(c.code == "library" for c in chips):
            chips.append(Explanation("library", "From your library vibe"))
        if item.score >= 0.55 and not any(c.code == "sound_alike" for c in chips):
            chips.append(Explanation("sound_alike", "Sounds like what you've been into"))
        elif item.score >= 0.35 and not any(c.code.startswith("genre") or c.code == "sound_alike" for c in chips):
            chips.append(Explanation("taste_fit", "Fits your recent taste"))
        if profile.window_days and profile.window_days <= 45 and not any(c.code == "recent" for c in chips):
            if item.score >= 0.4:
                chips.append(Explanation("recent", "Based on your recent listens"))
        # Cap at two chips so the UI stays calm.
        out.append(RankedItem(song_id=item.song_id, score=item.score, explanations=tuple(chips[:2])))
    return out


def _top_profile_genres(features: FeatureMatrix, profile: TasteProfile, n: int) -> set[str]:
    if profile.is_empty or not features.genre_vocab:
        return set()
    gdim = len(features.genre_vocab)
    weights = profile.vector[:gdim]
    order = np.argsort(-weights)[:n]
    return {features.genre_vocab[i] for i in order if weights[i] > 0}
