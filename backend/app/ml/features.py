"""Song feature vectors: multi-hot genres/tags + standardized Librosa audio features.

When audio features are missing, the audio dims are zeroed and the vector is still
usable (tag-only fallback). Callers can also request a tag-only matrix.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler

# Continuous features we can standardize when present. Key/mode are handled as
# cyclic (sin/cos) encodings separately so C and B are neighbours.
AUDIO_FEATURE_NAMES: tuple[str, ...] = (
    "tempo",
    "energy",
    "loudness_db",
    "spectral_centroid_hz",
    "spectral_rolloff_hz",
    "zero_crossing_rate",
    # Spotify audio-features (and any future provider) when Librosa leaves them empty.
    "danceability",
    "acousticness",
    "valence",
    "instrumentalness",
)


@dataclass(frozen=True)
class FeatureMatrix:
    """Aligned song ids and L2-ready feature rows (already unit-normalised)."""

    song_ids: np.ndarray  # shape (n,)
    matrix: np.ndarray  # shape (n, d), each row L2-normalised
    genre_vocab: tuple[str, ...]
    tag_only: bool

    def index_of(self, song_id: int) -> int | None:
        matches = np.where(self.song_ids == song_id)[0]
        return int(matches[0]) if len(matches) else None

    def vector(self, song_id: int) -> np.ndarray | None:
        idx = self.index_of(song_id)
        return None if idx is None else self.matrix[idx]

    def as_dataframe(self) -> pd.DataFrame:
        cols = [f"g:{g}" for g in self.genre_vocab]
        if not self.tag_only:
            cols += list(AUDIO_FEATURE_NAMES) + ["key_sin", "key_cos", "mode"]
        return pd.DataFrame(self.matrix, index=self.song_ids, columns=cols[: self.matrix.shape[1]])


def _genres_series(rows: Sequence[dict]) -> list[list[str]]:
    out: list[list[str]] = []
    for row in rows:
        raw = row.get("genres") or row.get("tags") or []
        cleaned = sorted({str(g).strip().lower() for g in raw if g and str(g).strip()})
        out.append(cleaned)
    return out


def _audio_block(rows: Sequence[dict], *, tag_only: bool) -> np.ndarray:
    """Return (n, a) float matrix. Missing values become column means (or 0)."""
    n = len(rows)
    if tag_only or n == 0:
        return np.zeros((n, 0), dtype=float)

    raw = np.full((n, len(AUDIO_FEATURE_NAMES)), np.nan, dtype=float)
    key_sin = np.zeros(n, dtype=float)
    key_cos = np.zeros(n, dtype=float)
    mode = np.full(n, np.nan, dtype=float)

    for i, row in enumerate(rows):
        for j, name in enumerate(AUDIO_FEATURE_NAMES):
            val = row.get(name)
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                raw[i, j] = float(val)
        key = row.get("key")
        if key is not None:
            angle = 2.0 * np.pi * (int(key) % 12) / 12.0
            key_sin[i] = np.sin(angle)
            key_cos[i] = np.cos(angle)
        m = row.get("mode")
        if m is not None:
            mode[i] = float(m)

    # Impute continuous columns with column means; fall back to 0 when an entire column is empty.
    for j in range(raw.shape[1]):
        col = raw[:, j]
        mean = np.nanmean(col) if np.any(~np.isnan(col)) else 0.0
        col[np.isnan(col)] = mean
        raw[:, j] = col
    mode[np.isnan(mode)] = 0.5  # unknown mode sits between major/minor

    if np.any(raw):
        scaler = StandardScaler()
        scaled = scaler.fit_transform(raw)
    else:
        scaled = raw

    return np.column_stack([scaled, key_sin, key_cos, mode])


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms


def build_feature_matrix(
    rows: Sequence[dict],
    *,
    tag_only: bool = False,
    genre_vocab: Iterable[str] | None = None,
) -> FeatureMatrix:
    """Build a feature matrix from song dicts.

    Each row dict needs at least `id` and `genres` (list[str]). Optional audio keys:
    tempo, energy, loudness_db, spectral_centroid_hz, spectral_rolloff_hz,
    zero_crossing_rate, key (0..11), mode (0|1).

    If every song is missing audio features, the result is effectively tag-only
    even when `tag_only=False` (zeros for the audio block after imputation).
    """
    if not rows:
        return FeatureMatrix(
            song_ids=np.array([], dtype=int),
            matrix=np.zeros((0, 0)),
            genre_vocab=tuple(),
            tag_only=tag_only,
        )

    song_ids = np.array([int(r["id"]) for r in rows], dtype=int)
    genre_lists = _genres_series(rows)
    mlb = MultiLabelBinarizer(classes=list(genre_vocab) if genre_vocab is not None else None)
    # sklearn raises if classes=None and the data is empty-of-labels; handle that.
    if genre_vocab is None and not any(genre_lists):
        genre_block = np.zeros((len(rows), 0), dtype=float)
        vocab: tuple[str, ...] = ()
    else:
        genre_block = mlb.fit_transform(genre_lists).astype(float)
        vocab = tuple(str(c) for c in mlb.classes_)

    # Force tag-only when the caller asked, or when no song has any audio value.
    use_tag_only = tag_only
    if not use_tag_only:
        has_audio = any(
            any(r.get(name) is not None for name in AUDIO_FEATURE_NAMES) or r.get("key") is not None
            for r in rows
        )
        if not has_audio:
            use_tag_only = True

    audio = _audio_block(rows, tag_only=use_tag_only)
    matrix = np.hstack([genre_block, audio]) if audio.size or genre_block.size else np.zeros((len(rows), 1))
    if matrix.shape[1] == 0:
        matrix = np.zeros((len(rows), 1))
    return FeatureMatrix(
        song_ids=song_ids,
        matrix=_l2_normalize(matrix),
        genre_vocab=vocab,
        tag_only=use_tag_only,
    )
