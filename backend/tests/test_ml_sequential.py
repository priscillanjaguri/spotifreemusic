"""Unit tests for the pure sequential next-track model (no database)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.ml.rank import RankedItem
from app.ml.sequential import (
    MIN_SESSIONS,
    MIN_TRANSITIONS,
    PlayEvent,
    build_sessions,
    dumps_model,
    loads_model,
    predict_next,
    train_markov,
)
from app.services.sequential_job import merge_candidates


def _now():
    return datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def _synth_sessions(n_sessions: int = 8, songs_per: int = 5):
    """Build enough sessions with overlapping transitions for training."""
    # Cycle through a small catalog so A→B, B→C etc. repeat.
    catalog = list(range(1, 12))
    sessions: list[list[int]] = []
    for s in range(n_sessions):
        start = s % (len(catalog) - songs_per)
        sess = catalog[start : start + songs_per]
        # Alternate a popular path 1→2→3.
        if s % 2 == 0:
            sess = [1, 2, 3, 4, 5][:songs_per]
        sessions.append(sess)
    return sessions


def test_build_sessions_uses_session_id_and_gap():
    t0 = _now()
    events = [
        PlayEvent(song_id=1, started_at=t0, session_id=10, listened_ms=30_000),
        PlayEvent(song_id=2, started_at=t0 + timedelta(minutes=2), session_id=10, listened_ms=30_000),
        PlayEvent(song_id=2, started_at=t0 + timedelta(minutes=3), session_id=10, listened_ms=30_000),  # dup
        PlayEvent(song_id=3, started_at=t0 + timedelta(minutes=4), session_id=10, listened_ms=30_000),
        # New session via session_id
        PlayEvent(song_id=4, started_at=t0 + timedelta(minutes=5), session_id=11, listened_ms=30_000),
        PlayEvent(song_id=5, started_at=t0 + timedelta(minutes=6), session_id=11, listened_ms=30_000),
        # Gap-based (no session_id), far later
        PlayEvent(song_id=6, started_at=t0 + timedelta(hours=3), session_id=None, listened_ms=30_000),
        PlayEvent(song_id=7, started_at=t0 + timedelta(hours=3, minutes=2), session_id=None, listened_ms=30_000),
    ]
    sessions = build_sessions(events)
    assert [1, 2, 3] in sessions
    assert [4, 5] in sessions
    assert [6, 7] in sessions


def test_train_predict_roundtrip_and_serialize():
    sessions = _synth_sessions(10, 5)
    result = train_markov(sessions)
    assert result.n_transitions >= MIN_TRANSITIONS
    assert result.n_sessions >= MIN_SESSIONS
    assert "mean_branching" in result.metrics

    ranked = predict_next(result.model, [1], exclude={1}, limit=5)
    assert ranked
    assert all(sid != 1 for sid, _ in ranked)
    # 1→2 is the strongest path in synth data.
    assert ranked[0][0] == 2

    blob = dumps_model(result.model)
    restored = loads_model(blob)
    again = predict_next(restored, [1], exclude={1}, limit=5)
    assert [s for s, _ in again] == [s for s, _ in ranked]


def test_train_rejects_cold_start():
    with pytest.raises(ValueError, match="at least"):
        train_markov([[1, 2], [2, 3]])


def test_predict_backoff_without_seed():
    sessions = _synth_sessions(10, 5)
    model = train_markov(sessions).model
    ranked = predict_next(model, [], exclude=set(), limit=3)
    assert len(ranked) == 3


def test_merge_candidates_unions_and_keeps_explanations():
    cosine = [
        RankedItem(song_id=1, score=0.9),
        RankedItem(song_id=2, score=0.5),
    ]
    from app.ml.rank import Explanation

    sequential = [
        RankedItem(song_id=2, score=0.8, explanations=(Explanation("next_track", "Often follows"),)),
        RankedItem(song_id=3, score=0.7, explanations=(Explanation("next_track", "Often follows"),)),
    ]
    merged, seq_ids = merge_candidates(cosine, sequential)
    assert seq_ids == {2, 3}
    ids = [r.song_id for r in merged]
    assert set(ids) == {1, 2, 3}
    # Song 2 should carry next_track explanation.
    item2 = next(r for r in merged if r.song_id == 2)
    assert any(e.code == "next_track" for e in item2.explanations)
