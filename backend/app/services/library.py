"""My Library: ingest uploads into the catalogue, delete them, and analyse their audio."""
import hashlib
import logging
import tempfile
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Literal

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.analysis import AnalysisUnavailable, analyze_file, librosa_available
from app.models import (
    Album, Artist, LibraryUpload, ListeningEvent, Song, SongArtist, SongFeatures, SongProviderLink, UserCollection,
)
from app.providers.base import ProviderArtist, ProviderTrack
from app.providers.my_library import MyLibraryAdapter
from app.services.audio_tags import ACCEPTED_EXTENSIONS, CONTENT_TYPES, UnreadableAudio, read_tags, sniff_format
from app.services.catalog import import_tracks
from app.services.collection import SONG_LOAD
from app.storage import ObjectStorage, StorageError

log = logging.getLogger(__name__)
CHUNK = 1024 * 1024
COVER_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

UPLOAD_LOAD = (selectinload(LibraryUpload.song).options(*SONG_LOAD), selectinload(LibraryUpload.song).selectinload(Song.features))

SessionFactory = Callable[[], AbstractContextManager[Session]]


@dataclass
class IngestResult:
    filename: str
    status: Literal["added", "duplicate", "rejected"]
    message: str
    upload: LibraryUpload | None = None


def _spool(stream: BinaryIO, dest: Path, max_bytes: int) -> tuple[str, int, bytes] | None:
    """Copy to `dest`, hashing as we go. None if larger than `max_bytes`."""
    digest, size, head = hashlib.sha256(), 0, b""
    with dest.open("wb") as out:
        while chunk := stream.read(CHUNK):
            size += len(chunk)
            if size > max_bytes:
                return None
            if len(head) < 64:
                head += chunk[: 64 - len(head)]
            digest.update(chunk)
            out.write(chunk)
    return digest.hexdigest(), size, head


def _ensure_in_collection(db: Session, user_id: uuid.UUID, song_id: int) -> bool:
    """Add to the user's collection unless already there. True if it was added."""
    if db.scalar(select(UserCollection.id).where(UserCollection.user_id == user_id, UserCollection.song_id == song_id)):
        return False
    db.add(UserCollection(user_id=user_id, song_id=song_id, source="upload"))
    return True


def ingest(
    db: Session, storage: ObjectStorage, user_id: uuid.UUID, filename: str, stream: BinaryIO, *, max_bytes: int,
) -> IngestResult:
    """Validate, dedupe, tag, store and catalogue one uploaded file. Commits on success."""
    filename = Path(filename or "upload").name[:300] or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in ACCEPTED_EXTENSIONS:
        return IngestResult(filename, "rejected", "Unsupported file type. Use MP3, M4A/AAC, FLAC, OGG or WAV.")

    with tempfile.TemporaryDirectory(prefix="spotifree-upload-") as tmp:
        path = Path(tmp) / f"audio{ext}"
        spooled = _spool(stream, path, max_bytes)
        if spooled is None:
            return IngestResult(filename, "rejected", f"File is larger than {max_bytes // (1024 * 1024)} MB.")
        sha256, size, head = spooled
        if size == 0:
            return IngestResult(filename, "rejected", "File is empty.")
        fmt = sniff_format(head)
        if fmt is None or fmt not in ACCEPTED_EXTENSIONS[ext]:
            return IngestResult(filename, "rejected", f"This doesn't look like a real {ext[1:].upper()} file.")

        existing = db.scalar(
            select(LibraryUpload).where(LibraryUpload.user_id == user_id, LibraryUpload.content_sha256 == sha256)
        )
        if existing is not None:
            return _duplicate(db, user_id, filename, existing)

        try:
            tags = read_tags(path, filename)
        except UnreadableAudio as exc:
            return IngestResult(filename, "rejected", str(exc))

        upload = LibraryUpload(
            user_id=user_id, content_sha256=sha256, original_filename=filename, audio_format=fmt,
            content_type=CONTENT_TYPES[fmt], size_bytes=size, storage_backend=storage.key, storage_key="pending",
            analysis_status="pending",
        )
        db.add(upload)
        try:
            db.flush()  # assigns the id; the (user, hash) unique constraint catches a concurrent duplicate
        except IntegrityError:
            db.rollback()
            existing = db.scalar(
                select(LibraryUpload).where(LibraryUpload.user_id == user_id, LibraryUpload.content_sha256 == sha256)
            )
            if existing is None:
                raise
            return _duplicate(db, user_id, filename, existing)

        prefix = f"users/{user_id}/{upload.id}-{sha256[:16]}"
        upload.storage_key = f"{prefix}{ext}"
        stored: list[str] = []
        try:
            storage.put_file(upload.storage_key, path, upload.content_type)
            stored.append(upload.storage_key)
            if tags.cover:
                upload.cover_storage_key = f"{prefix}-cover.{COVER_EXT[tags.cover.content_type]}"
                upload.cover_content_type = tags.cover.content_type
                cover_path = Path(tmp) / "cover"
                cover_path.write_bytes(tags.cover.data)
                storage.put_file(upload.cover_storage_key, cover_path, tags.cover.content_type)
                stored.append(upload.cover_storage_key)

            track = ProviderTrack(
                provider_track_id=str(upload.id), title=tags.title, duration_ms=tags.duration_ms,
                artists=[ProviderArtist(a) for a in tags.artists], album_title=tags.album,
                release_date=tags.release_date,
                cover_url=MyLibraryAdapter.cover_path(upload.id) if tags.cover else None,
                genres=tags.genres, stream_url=MyLibraryAdapter.stream_path(upload.id), license_url=None,
            )
            [song] = import_tracks(db, MyLibraryAdapter(), [track])
            song.owner_user_id = user_id
            upload.song = song
            _ensure_in_collection(db, user_id, song.id)
            db.commit()
        except Exception:
            db.rollback()
            for key in stored:
                try:
                    storage.delete(key)
                except StorageError:
                    log.warning("Could not clean up %s after a failed upload", key)
            raise

    note = " Title taken from the filename (no tags found)." if tags.from_filename else ""
    return IngestResult(filename, "added", f"Added to your library.{note}", get_upload(db, user_id, upload.id))


def _duplicate(db: Session, user_id: uuid.UUID, filename: str, existing: LibraryUpload) -> IngestResult:
    message = "Already in your library."
    if existing.song_id is not None and _ensure_in_collection(db, user_id, existing.song_id):
        db.commit()
        message = "Already in your library, added back to your collection."
    return IngestResult(filename, "duplicate", message, get_upload(db, user_id, existing.id))


def get_upload(db: Session, user_id: uuid.UUID, upload_id: int) -> LibraryUpload | None:
    """The user's own upload, or None (also for other users' uploads, so ids can't be probed)."""
    return db.scalar(
        select(LibraryUpload)
        .where(LibraryUpload.id == upload_id, LibraryUpload.user_id == user_id)
        .options(*UPLOAD_LOAD)
        .execution_options(populate_existing=True)
    )


def list_uploads(db: Session, user_id: uuid.UUID) -> list[LibraryUpload]:
    return list(
        db.scalars(
            select(LibraryUpload).where(LibraryUpload.user_id == user_id)
            .order_by(LibraryUpload.created_at.desc(), LibraryUpload.id.desc())
            .options(*UPLOAD_LOAD)
        ).all()
    )


def delete_upload(db: Session, storage: ObjectStorage, upload: LibraryUpload) -> None:
    """Remove the upload and its files. The song goes too unless listening history still refers to it."""
    keys = [k for k in (upload.storage_key, upload.cover_storage_key) if k]
    song = upload.song
    db.delete(upload)
    if song is not None:
        has_history = db.scalar(select(exists().where(ListeningEvent.song_id == song.id)))
        if has_history:
            # Keep the row for history, but it can no longer be played or collected.
            for link in list(song.provider_links):
                song.provider_links.remove(link)
            db.query(UserCollection).filter(UserCollection.song_id == song.id).delete()
        else:
            album, artists = song.album, [l.artist for l in song.artist_links]
            db.delete(song)
            db.flush()
            _delete_if_unused(db, album, artists)
    db.commit()
    # Files are removed after the commit: a leftover file is harmless, a row pointing at nothing is not.
    for key in keys:
        try:
            storage.delete(key)
        except StorageError:
            log.warning("Could not delete stored object %s", key)


def _delete_if_unused(db: Session, album: Album | None, artists: list[Artist]) -> None:
    if album is not None and album.data_source == "user_provided":
        if not db.scalar(select(exists().where(Song.album_id == album.id))):
            db.delete(album)
            db.flush()
    for artist in artists:
        if artist.data_source != "user_provided":
            continue
        used = db.scalar(select(exists().where(SongArtist.artist_id == artist.id))) or db.scalar(
            select(exists().where(Album.primary_artist_id == artist.id))
        )
        if not used:
            db.delete(artist)
    db.flush()


def analysis_available() -> bool:
    return librosa_available()


def run_analysis(upload_id: int, session_factory: SessionFactory, storage: ObjectStorage, enabled: bool = True) -> None:
    """Background job: measure the upload's audio and store it in song_features."""
    with session_factory() as db:
        upload = db.get(LibraryUpload, upload_id)
        if upload is None or upload.song_id is None:
            return
        if not enabled or not librosa_available():
            upload.analysis_status = "unavailable"
            upload.analysis_error = "Audio analysis is not installed on this server."
            db.commit()
            return
        upload.analysis_status, upload.analysis_error = "running", None
        db.commit()
        try:
            with storage.local_copy(upload.storage_key) as path:
                features = analyze_file(path)
        except AnalysisUnavailable as exc:
            upload.analysis_status, upload.analysis_error = "unavailable", str(exc)[:300]
            db.commit()
            return
        except Exception as exc:
            log.exception("Audio analysis failed for upload %s", upload_id)
            upload.analysis_status, upload.analysis_error = "failed", (str(exc) or exc.__class__.__name__)[:300]
            db.commit()
            return

        row = db.get(SongFeatures, upload.song_id) or SongFeatures(song_id=upload.song_id)
        for name, value in features.as_dict().items():
            setattr(row, name, value)
        row.analyzed_at = datetime.now(timezone.utc)
        row.feature_source = "user_provided"
        db.add(row)
        upload.analysis_status = "done"
        db.commit()
