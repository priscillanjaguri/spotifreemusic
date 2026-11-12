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
    source: Literal["search", "recommendation", "daily_companion", "manual"] = "manual"  # "upload" is set by My Library only


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


class AudioFeaturesOut(BaseModel):
    tempo: float | None
    energy: float | None
    loudness_db: float | None
    spectral_centroid_hz: float | None
    key: int | None
    mode: int | None
    key_name: str | None
    analyzer: str | None


class LibraryUploadOut(BaseModel):
    id: int
    original_filename: str
    audio_format: str
    size_bytes: int
    created_at: datetime
    analysis_status: Literal["pending", "running", "done", "failed", "unavailable"]
    analysis_error: str | None
    song: SongOut | None
    features: AudioFeaturesOut | None

    @classmethod
    def from_upload(cls, upload) -> "LibraryUploadOut":
        from app.analysis.audio_features import PITCH_CLASSES

        f = upload.song.features if upload.song is not None else None
        features = None
        if f is not None:
            key_name = (
                f"{PITCH_CLASSES[f.key]} {'major' if f.mode == 1 else 'minor'}"
                if f.key is not None and f.mode is not None else None
            )
            features = AudioFeaturesOut(
                tempo=f.tempo, energy=f.energy, loudness_db=f.loudness_db, spectral_centroid_hz=f.spectral_centroid_hz,
                key=f.key, mode=f.mode, key_name=key_name, analyzer=f.analyzer,
            )
        return cls(
            id=upload.id, original_filename=upload.original_filename, audio_format=upload.audio_format,
            size_bytes=upload.size_bytes, created_at=upload.created_at, analysis_status=upload.analysis_status,
            analysis_error=upload.analysis_error, song=SongOut.from_song(upload.song) if upload.song else None,
            features=features,
        )


class LibraryLimits(BaseModel):
    accepted_extensions: list[str]
    max_file_mb: int
    max_files_per_request: int
    storage_backend: str
    analysis_available: bool


class LibraryPage(BaseModel):
    total: int
    items: list[LibraryUploadOut]
    limits: LibraryLimits


class UploadResultOut(BaseModel):
    filename: str
    status: Literal["added", "duplicate", "rejected"]
    message: str
    upload: LibraryUploadOut | None


class UploadResponse(BaseModel):
    results: list[UploadResultOut]
