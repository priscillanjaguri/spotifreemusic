"""Turns provider tracks into rows in our provider-independent catalogue."""
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Album, Artist, Genre, MusicProvider, Song, SongArtist, SongProviderLink
from app.providers.base import MusicProviderAdapter, ProviderTrack


def ensure_provider_row(db: Session, adapter: MusicProviderAdapter) -> MusicProvider:
    row = db.scalar(select(MusicProvider).where(MusicProvider.key == adapter.key))
    if row is None:
        # Two first-ever requests can race here (e.g. parallel uploads); ON CONFLICT makes creation idempotent.
        db.execute(
            insert(MusicProvider)
            .values(key=adapter.key, display_name=adapter.display_name)
            .on_conflict_do_nothing(index_elements=["key"])
        )
        row = db.scalar(select(MusicProvider).where(MusicProvider.key == adapter.key))
    # An adapter only exists in the registry when it is configured.
    row.is_configured = True
    row.supports_playback = adapter.supports_playback
    row.is_mock = adapter.is_mock
    db.flush()
    return row


def _artist(db: Session, name: str, source: str) -> Artist:
    # Simplification: artists are matched by case-insensitive name. Two different
    # artists with an identical name would be merged; fine until we need provider artist ids.
    artist = db.scalars(select(Artist).where(func.lower(Artist.name) == name.lower())).first()
    if artist is None:
        artist = Artist(name=name, data_source=source)
        db.add(artist)
        db.flush()  # autoflush is off, so flush so later lookups in this batch find it
    return artist


def _album(db: Session, title: str, artist: Artist, track: ProviderTrack, source: str) -> Album:
    album = db.scalars(
        select(Album).where(func.lower(Album.title) == title.lower(), Album.primary_artist_id == artist.id)
    ).first()
    if album is None:
        album = Album(
            title=title, primary_artist=artist, release_date=track.release_date,
            cover_url=track.cover_url, data_source=source,
        )
        db.add(album)
        db.flush()
    return album


def _genre(db: Session, name: str) -> Genre:
    genre = db.scalars(select(Genre).where(Genre.name == name)).first()
    if genre is None:
        genre = Genre(name=name)
        db.add(genre)
        db.flush()
    return genre


def import_tracks(db: Session, adapter: MusicProviderAdapter, tracks: list[ProviderTrack]) -> list[Song]:
    """Upsert tracks and return the matching catalogue songs (same order, no duplicates)."""
    provider = ensure_provider_row(db, adapter)
    songs: list[Song] = []
    for track in tracks:
        link = db.scalar(
            select(SongProviderLink).where(
                SongProviderLink.provider_id == provider.id,
                SongProviderLink.provider_track_id == track.provider_track_id,
            )
        )
        if link is not None:  # already known: just refresh playback/licence/download info
            link.playback_uri = track.stream_url
            link.license_url = track.license_url
            link.download_allowed = bool(track.download_allowed)
            song = link.song
        else:
            song = _create_song(db, provider, track, adapter.data_source)
        if song not in songs:
            songs.append(song)
    db.flush()
    return songs


def _create_song(db: Session, provider: MusicProvider, track: ProviderTrack, source: str) -> Song:
    artists: list[Artist] = []
    for pa in track.artists:
        a = _artist(db, pa.name, source)
        if a not in artists:
            artists.append(a)
    genre_names = sorted({g.strip().lower() for g in track.genres if g.strip()})

    song = Song(
        title=track.title,
        duration_ms=track.duration_ms,
        cover_url=track.cover_url,
        data_source=source,
        album=_album(db, track.album_title, artists[0], track, source) if track.album_title else None,
        genres=[_genre(db, n) for n in genre_names],
    )
    for position, artist in enumerate(artists):
        song.artist_links.append(SongArtist(artist=artist, position=position))
    song.provider_links.append(
        SongProviderLink(
            provider=provider, provider_track_id=track.provider_track_id,
            playback_uri=track.stream_url, license_url=track.license_url,
            download_allowed=bool(track.download_allowed),
        )
    )
    db.add(song)
    db.flush()
    return song
