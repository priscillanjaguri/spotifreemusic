"""Collection queries and commands (kept out of the HTTP layer)."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Album, Artist, Genre, Song, SongArtist, SongGenre, SongProviderLink, UserCollection

# Everything SongOut needs, loaded in a few queries instead of one per song (avoids "N+1").
SONG_LOAD = (
    selectinload(Song.artist_links).selectinload(SongArtist.artist),
    selectinload(Song.album),
    selectinload(Song.genres),
    selectinload(Song.provider_links).selectinload(SongProviderLink.provider),
)


def list_collection(
    db: Session, user_id: uuid.UUID, *, artist_id: int | None, album_id: int | None,
    genre: str | None, limit: int, offset: int,
) -> tuple[int, list[UserCollection]]:
    query = (
        select(UserCollection)
        .join(Song, Song.id == UserCollection.song_id)
        .where(UserCollection.user_id == user_id)
    )
    if artist_id is not None:
        query = query.where(
            select(SongArtist.song_id)
            .where(SongArtist.song_id == Song.id, SongArtist.artist_id == artist_id).exists()
        )
    if album_id is not None:
        query = query.where(Song.album_id == album_id)
    if genre:
        query = query.where(
            select(SongGenre.song_id)
            .join(Genre, Genre.id == SongGenre.genre_id)
            .where(SongGenre.song_id == Song.id, Genre.name == genre.strip().lower()).exists()
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(UserCollection.added_at.desc(), UserCollection.id.desc())
        .limit(limit).offset(offset)
        .options(selectinload(UserCollection.song).options(*SONG_LOAD))
    ).all()
    return total, list(items)


def collection_facets(db: Session, user_id: uuid.UUID) -> dict[str, list[tuple[int, str, int]]]:
    """Artists/albums/genres present in the user's collection, with counts (for filter menus)."""
    mine = UserCollection.user_id == user_id

    def rows(stmt):
        return [(r[0], r[1], r[2]) for r in db.execute(stmt).all()]

    base = select(UserCollection).where(mine).subquery()
    return {
        "artists": rows(
            select(Artist.id, Artist.name, func.count(func.distinct(base.c.song_id)))
            .join(SongArtist, SongArtist.artist_id == Artist.id)
            .join(base, base.c.song_id == SongArtist.song_id)
            .group_by(Artist.id, Artist.name).order_by(Artist.name)
        ),
        "albums": rows(
            select(Album.id, Album.title, func.count())
            .join(Song, Song.album_id == Album.id)
            .join(base, base.c.song_id == Song.id)
            .group_by(Album.id, Album.title).order_by(Album.title)
        ),
        "genres": rows(
            select(Genre.id, Genre.name, func.count())
            .join(SongGenre, SongGenre.genre_id == Genre.id)
            .join(base, base.c.song_id == SongGenre.song_id)
            .group_by(Genre.id, Genre.name).order_by(Genre.name)
        ),
    }
