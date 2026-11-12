"""Provider-independent contract for music sources.

A provider adapter turns *its* API into these plain dataclasses. Nothing else in
the app talks to a provider directly, so adding another source means writing one
new adapter class, not changing the catalogue, analytics or recommender.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


class ProviderError(Exception):
    """The provider failed or returned something unusable (network, auth, bad payload)."""


@dataclass(frozen=True)
class ProviderArtist:
    name: str
    provider_artist_id: str | None = None


@dataclass(frozen=True)
class ProviderTrack:
    provider_track_id: str
    title: str
    duration_ms: int
    artists: list[ProviderArtist]
    album_title: str | None = None
    release_date: date | None = None
    cover_url: str | None = None
    genres: list[str] = field(default_factory=list)
    stream_url: str | None = None  # a URL for the provider's own player; never a download
    license_url: str | None = None


class MusicProviderAdapter(ABC):
    key: str  # stable code, stored in music_providers.key
    display_name: str
    supports_playback: bool

    @abstractmethod
    def search_tracks(self, query: str, limit: int = 20) -> list[ProviderTrack]:
        """Search the provider's catalogue. Raises ProviderError on failure."""
