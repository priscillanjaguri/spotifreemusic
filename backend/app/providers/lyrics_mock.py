"""Local mock lyrics fallback when Musixmatch has no API key.

Used so the LRCLIB → second-source chain is testable without secrets.
Only a tiny allowlist of demo title/artist pairs resolve; everything else misses.
Not scraping — hardcoded plain text for local/dev/test only.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MockLyricsHit:
    title: str
    artist: str
    plain_lyrics: str


# Keys are (title.lower(), artist.lower()) — first artist name only for matching.
_MOCK_CATALOGUE: dict[tuple[str, str], MockLyricsHit] = {
    (
        "demo mock anthem",
        "spotifree mock",
    ): MockLyricsHit(
        title="Demo Mock Anthem",
        artist="Spotifree Mock",
        plain_lyrics=(
            "This is a local mock lyric line.\n"
            "Used when MUSIXMATCH_API_KEY is unset.\n"
            "Not a real song — Spotifree lyrics fallback demo."
        ),
    ),
}


def _norm(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


class LocalLyricsFallback:
    """In-process allowlist lookup. No network."""

    source = "mock_local"

    def get_lyrics(self, title: str, artist: str) -> MockLyricsHit | None:
        title_n = _norm(title)
        # Catalogue songs may list multiple artists joined by ", ".
        artist_first = _norm(artist.split(",")[0] if artist else "")
        if not title_n or not artist_first:
            return None
        return _MOCK_CATALOGUE.get((title_n, artist_first))
