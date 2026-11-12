from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Song, User, UserCollection
from app.schemas.music import (
    CollectionAdd, CollectionFacets, CollectionItemOut, CollectionPage, FacetOut, SongOut,
)
from app.services import collection as svc

router = APIRouter(prefix="/collection", tags=["collection"])


@router.get("", response_model=CollectionPage, summary="List my collection (filter by artist, album, genre)")
def list_my_collection(
    artist_id: int | None = None,
    album_id: int | None = None,
    genre: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionPage:
    total, rows = svc.list_collection(
        db, user.id, artist_id=artist_id, album_id=album_id, genre=genre, limit=limit, offset=offset
    )
    items = [CollectionItemOut(added_at=r.added_at, source=r.source, song=SongOut.from_song(r.song)) for r in rows]
    return CollectionPage(total=total, limit=limit, offset=offset, items=items)


@router.get("/facets", response_model=CollectionFacets, summary="Artists, albums and genres in my collection")
def my_facets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CollectionFacets:
    facets = svc.collection_facets(db, user.id)
    return CollectionFacets(**{k: [FacetOut(id=i, name=n, count=c) for i, n, c in v] for k, v in facets.items()})


@router.post("", response_model=CollectionItemOut, status_code=status.HTTP_201_CREATED)
def add_to_collection(
    body: CollectionAdd, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CollectionItemOut:
    song = db.get(Song, body.song_id)
    if song is None or (song.owner_user_id is not None and song.owner_user_id != user.id):
        raise HTTPException(404, "Song not found")
    if db.scalar(select(UserCollection.id).where(UserCollection.user_id == user.id, UserCollection.song_id == body.song_id)):
        raise HTTPException(409, "Song is already in your collection")
    row = UserCollection(user_id=user.id, song_id=body.song_id, source=body.source)
    db.add(row)
    db.commit()
    _, rows = svc.list_collection(db, user.id, artist_id=None, album_id=None, genre=None, limit=1, offset=0)
    created = rows[0]
    return CollectionItemOut(added_at=created.added_at, source=created.source, song=SongOut.from_song(created.song))


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_collection(song_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    row = db.scalar(select(UserCollection).where(UserCollection.user_id == user.id, UserCollection.song_id == song_id))
    if row is None:
        raise HTTPException(404, "Song is not in your collection")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
