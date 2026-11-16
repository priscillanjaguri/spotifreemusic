"""Pure online-rate helpers (no DB)."""
from app.ml.eval import engage_rate, rate_for_source, summarise_online


def test_engage_rate_empty():
    assert engage_rate(0, 0) == 0.0
    assert engage_rate(0, 5) == 0.0


def test_engage_rate_basic():
    assert engage_rate(10, 4) == 0.4


def test_rate_for_source():
    sources = {"skip": 3, "like": 2, "play": 4, "complete": 1}
    assert rate_for_source(10, sources, "skip") == 0.3
    assert rate_for_source(10, sources, "play", "complete") == 0.5
    assert rate_for_source(0, sources, "skip") == 0.0


def test_summarise_online():
    metrics = summarise_online(
        impressions_shown=20,
        impressions_labeled=10,
        positives=6,
        source_counts={"like": 2, "skip": 3, "play": 3, "complete": 1, "hide": 1},
    )
    assert metrics["impressions_pending"] == 10.0
    assert metrics["engage_rate"] == 0.6
    assert metrics["skip_rate"] == 0.3
    assert metrics["like_rate"] == 0.2
    assert metrics["play_rate"] == 0.4
    assert metrics["hide_rate"] == 0.1
