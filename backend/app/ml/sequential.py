"""Classical sequential next-track candidate generator (first-order Markov / co-occurrence).

Pure ml/ — no DB / FastAPI. Services build listening sequences and call train / predict.
Portfolio story: "songs that often follow what you just played" from personal sessions.
"""
from __future__ import annotations

import io
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

import joblib
import numpy as np

# Personal app: need enough ordered transitions before trusting next-track suggestions.
MIN_TRANSITIONS = 20
MIN_SESSIONS = 5
MIN_UNIQUE_SONGS = 5

# Idle gap used when client_session_id / session_id is missing.
DEFAULT_SESSION_GAP = timedelta(minutes=30)

# Drop tiny blips; listening service already filters <1s, but training can be stricter.
MIN_LISTEN_MS = 5_000


@dataclass(frozen=True)
class PlayEvent:
    """Minimal listening row for sequence building."""

    song_id: int
    started_at: datetime
    session_id: int | None = None
    listened_ms: int = 0
    completed: bool | None = None


@dataclass
class SequentialModel:
    """Persisted Markov transition artifact (joblib)."""

    algorithm: str = "markov_cooccurrence"
    # from_song_id -> {to_song_id: probability}
    transitions: dict[int, dict[int, float]] = field(default_factory=dict)
    # Global next-song prior (backoff when seed unseen).
    unigram: dict[int, float] = field(default_factory=dict)
    n_transitions: int = 0
    n_sessions: int = 0
    n_unique_songs: int = 0
    session_gap_minutes: float = 30.0
    alpha: float = 0.5  # Laplace-ish add for sparse counts
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TrainResult:
    model: SequentialModel
    n_transitions: int
    n_sessions: int
    n_unique_songs: int
    metrics: dict[str, float]


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def build_sessions(
    events: Sequence[PlayEvent],
    *,
    gap: timedelta = DEFAULT_SESSION_GAP,
    min_listen_ms: int = MIN_LISTEN_MS,
) -> list[list[int]]:
    """Group ordered listening into sessions of song ids.

    Prefer explicit ``session_id`` when present; otherwise split on idle ``gap``.
    Consecutive duplicate plays of the same song within a session are collapsed
    (self-transitions are not useful for next-track discovery).
    """
    if not events:
        return []

    ordered = sorted(events, key=lambda e: (_aware(e.started_at), e.song_id))
    sessions: list[list[PlayEvent]] = []
    current: list[PlayEvent] = []
    current_key: Any = object()

    for ev in ordered:
        if ev.listened_ms < min_listen_ms and not ev.completed:
            continue
        # Explicit playback session, else synthetic gap key.
        if ev.session_id is not None:
            key: Any = ("sid", ev.session_id)
        else:
            if not current:
                key = ("gap", 0)
            else:
                prev = current[-1]
                delta = _aware(ev.started_at) - _aware(prev.started_at)
                if delta > gap:
                    key = ("gap", len(sessions) + 1)
                else:
                    key = current_key

        if current and key != current_key:
            sessions.append(current)
            current = []
        current_key = key
        current.append(ev)

    if current:
        sessions.append(current)

    out: list[list[int]] = []
    for sess in sessions:
        ids: list[int] = []
        for ev in sess:
            sid = int(ev.song_id)
            if not ids or ids[-1] != sid:
                ids.append(sid)
        if len(ids) >= 2:
            out.append(ids)
    return out


def _transition_counts(sessions: Sequence[Sequence[int]]) -> tuple[dict[int, Counter], Counter, int]:
    bigrams: dict[int, Counter] = defaultdict(Counter)
    unigram: Counter = Counter()
    n = 0
    for sess in sessions:
        for a, b in zip(sess, sess[1:]):
            if a == b:
                continue
            bigrams[int(a)][int(b)] += 1
            unigram[int(b)] += 1
            n += 1
    return bigrams, unigram, n


def train_markov(
    sessions: Sequence[Sequence[int]],
    *,
    alpha: float = 0.5,
    session_gap_minutes: float = 30.0,
) -> TrainResult:
    """Fit first-order transition probabilities with additive smoothing + unigram backoff prior."""
    bigrams, uni_counts, n_trans = _transition_counts(sessions)
    unique = {sid for sess in sessions for sid in sess}
    n_sessions = len(sessions)
    n_unique = len(unique)

    if n_trans < MIN_TRANSITIONS:
        raise ValueError(
            f"Need at least {MIN_TRANSITIONS} song-to-song transitions, got {n_trans}"
        )
    if n_sessions < MIN_SESSIONS:
        raise ValueError(f"Need at least {MIN_SESSIONS} multi-song sessions, got {n_sessions}")
    if n_unique < MIN_UNIQUE_SONGS:
        raise ValueError(f"Need at least {MIN_UNIQUE_SONGS} unique songs, got {n_unique}")

    vocab = sorted(unique)
    v = max(1, len(vocab))
    uni_total = sum(uni_counts.values()) or 1
    unigram = {
        int(sid): float((uni_counts.get(sid, 0) + alpha) / (uni_total + alpha * v))
        for sid in vocab
    }

    transitions: dict[int, dict[int, float]] = {}
    entropy_bits = 0.0
    for src, counter in bigrams.items():
        total = sum(counter.values())
        dests = {int(d): float(c + alpha) for d, c in counter.items()}
        # Mild mass for other vocab items via alpha (sparse: only store observed + normalize).
        denom = total + alpha * max(1, len(dests))
        probs = {d: c / denom for d, c in dests.items()}
        # Renormalize to sum ≈ 1 over stored dests.
        s = sum(probs.values()) or 1.0
        transitions[int(src)] = {d: p / s for d, p in probs.items()}
        for p in transitions[int(src)].values():
            if p > 0:
                entropy_bits -= p * float(np.log2(p))

    mean_branching = float(np.mean([len(v) for v in transitions.values()])) if transitions else 0.0
    metrics = {
        "n_transitions": float(n_trans),
        "n_sessions": float(n_sessions),
        "n_unique_songs": float(n_unique),
        "n_sources": float(len(transitions)),
        "mean_branching": round(mean_branching, 4),
        "avg_source_entropy_bits": round(entropy_bits / max(1, len(transitions)), 4),
    }
    model = SequentialModel(
        algorithm="markov_cooccurrence",
        transitions=transitions,
        unigram=unigram,
        n_transitions=n_trans,
        n_sessions=n_sessions,
        n_unique_songs=n_unique,
        session_gap_minutes=session_gap_minutes,
        alpha=alpha,
        metrics=metrics,
    )
    return TrainResult(
        model=model,
        n_transitions=n_trans,
        n_sessions=n_sessions,
        n_unique_songs=n_unique,
        metrics=metrics,
    )


def predict_next(
    model: SequentialModel,
    seed_song_ids: Sequence[int],
    *,
    exclude: set[int] | None = None,
    limit: int = 50,
    backoff: float = 0.15,
) -> list[tuple[int, float]]:
    """Score next-track candidates from one or more recent seeds (most recent last).

    Uses the last seed's transition row, blended with unigram backoff when sparse.
    Earlier seeds contribute a small discounted boost for portfolio smoothness.
    """
    exclude = set(exclude or ())
    if not seed_song_ids:
        # Pure popularity backoff.
        scored = [
            (sid, p)
            for sid, p in model.unigram.items()
            if sid not in exclude
        ]
        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored[:limit]

    scores: dict[int, float] = defaultdict(float)
    seeds = [int(s) for s in seed_song_ids]
    # Weight recent seeds higher.
    for i, seed in enumerate(seeds):
        age = len(seeds) - 1 - i  # 0 = most recent
        weight = 0.7**age
        row = model.transitions.get(seed, {})
        if row:
            for dest, p in row.items():
                if dest in exclude or dest == seed:
                    continue
                scores[dest] += weight * float(p)
        else:
            # Unseen seed → mild unigram.
            for dest, p in model.unigram.items():
                if dest in exclude or dest == seed:
                    continue
                scores[dest] += weight * backoff * float(p)

    # Global backoff so cold seeds still surface something.
    for dest, p in model.unigram.items():
        if dest in exclude or dest in seeds[-1:]:
            continue
        scores[dest] += backoff * 0.25 * float(p)

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    return ranked[:limit]


def dumps_model(model: SequentialModel) -> bytes:
    buf = io.BytesIO()
    joblib.dump(model, buf)
    return buf.getvalue()


def loads_model(blob: bytes) -> SequentialModel:
    obj = joblib.load(io.BytesIO(blob))
    if isinstance(obj, SequentialModel):
        return obj
    if isinstance(obj, Mapping):
        return SequentialModel(
            algorithm=str(obj.get("algorithm", "markov_cooccurrence")),
            transitions={int(k): {int(d): float(p) for d, p in v.items()} for k, v in (obj.get("transitions") or {}).items()},
            unigram={int(k): float(v) for k, v in (obj.get("unigram") or {}).items()},
            n_transitions=int(obj.get("n_transitions", 0)),
            n_sessions=int(obj.get("n_sessions", 0)),
            n_unique_songs=int(obj.get("n_unique_songs", 0)),
            session_gap_minutes=float(obj.get("session_gap_minutes", 30.0)),
            alpha=float(obj.get("alpha", 0.5)),
            metrics=dict(obj.get("metrics") or {}),
        )
    raise TypeError(f"Unrecognized sequential artifact type: {type(obj)!r}")
