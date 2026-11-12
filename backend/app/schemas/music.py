from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import Song


class ArtistOut(BaseModel):
    id: int
    name: str


class AlbumOut(BaseModel):
    id: int
    title: str


class PlaybackOut(BaseModel):
    provider: str
    stream_url: str
    license_url: str | None


class SongOut(BaseModel):
    id: int
    title: str
    duration_ms: int
    artists: list[ArtistOut]
    album: AlbumOut | None
    genres: list[str]
    cover_url: str | None
    # 'provider' = real catalogue data; 'mock_dev' = fake development data (UI must label it).
    data_source: str
    # None when no configured provider can play this song.
    playback: PlaybackOut | None

    @classmethod
    def from_song(cls, song: Song) -> "SongOut":
        playback = next(
            (
                PlaybackOut(provider=l.provider.key, stream_url=l.playback_uri, license_url=l.license_url)
                for l in song.provider_links
                if l.playback_uri and l.provider.is_configured and l.provider.supports_playback
            ),
            None,
        )
        return cls(
            id=song.id,
            title=song.title,
            duration_ms=song.duration_ms,
            artists=[ArtistOut(id=l.artist.id, name=l.artist.name) for l in song.artist_links],
            album=AlbumOut(id=song.album.id, title=song.album.title) if song.album else None,
            genres=sorted(g.name for g in song.genres),
            cover_url=song.cover_url,
            data_source=song.data_source,
            playback=playback,
        )


class SongSearchResponse(BaseModel):
    query: str
    results: list[SongOut]


class CollectionAdd(BaseModel):
    song_id: int
    source: Literal["search", "recommendation", "daily_companion", "manual"] = "manual"


class CollectionItemOut(BaseModel):
    added_at: datetime
    source: str
    song: SongOut


class CollectionPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[CollectionItemOut]


class FacetOut(BaseModel):
    id: int
    name: str
    count: int


class CollectionFacets(BaseModel):
    artists: list[FacetOut]
    albums: list[FacetOut]
    genres: list[FacetOut]
