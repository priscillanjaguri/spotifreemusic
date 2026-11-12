"""My Library: upload music files you own, stream them back, delete them."""
from collections.abc import Callable
from contextlib import AbstractContextManager

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.db import SessionLocal, get_db
from app.models import LibraryUpload, User
from app.schemas.music import LibraryLimits, LibraryPage, LibraryUploadOut, UploadResponse, UploadResultOut
from app.services import library as svc
from app.services.audio_tags import ACCEPTED_EXTENSIONS
from app.storage import ObjectStorage, StorageError, get_storage

router = APIRouter(prefix="/library", tags=["my library"])


def get_session_factory() -> Callable[[], AbstractContextManager[Session]]:
    """Background jobs open their own session (the request's is closed by then). Tests override this."""
    return SessionLocal


def _limits(settings: Settings, storage: ObjectStorage) -> LibraryLimits:
    return LibraryLimits(
        accepted_extensions=sorted(ACCEPTED_EXTENSIONS), max_file_mb=settings.library_max_file_mb,
        max_files_per_request=settings.library_max_files_per_request, storage_backend=storage.key,
        analysis_available=settings.library_analysis_enabled and svc.analysis_available(),
    )


def _own_upload(db: Session, user: User, upload_id: int) -> LibraryUpload:
    upload = svc.get_upload(db, user.id, upload_id)
    if upload is None:
        raise HTTPException(404, "File not found in your library")
    return upload


@router.get("", response_model=LibraryPage, summary="My uploaded files, newest first")
def list_library(
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage), settings: Settings = Depends(get_settings),
) -> LibraryPage:
    uploads = svc.list_uploads(db, user.id)
    return LibraryPage(
        total=len(uploads), items=[LibraryUploadOut.from_upload(u) for u in uploads], limits=_limits(settings, storage)
    )


@router.post("/uploads", response_model=UploadResponse, summary="Upload one or more audio files you own")
def upload_files(
    background: BackgroundTasks,
    files: list[UploadFile] = File(description="MP3, M4A/AAC, FLAC, OGG or WAV"),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage), settings: Settings = Depends(get_settings),
    session_factory=Depends(get_session_factory),
) -> UploadResponse:
    if len(files) > settings.library_max_files_per_request:
        raise HTTPException(413, f"Upload at most {settings.library_max_files_per_request} files at a time")
    results: list[UploadResultOut] = []
    for f in files:
        try:
            r = svc.ingest(db, storage, user.id, f.filename or "upload", f.file,
                           max_bytes=settings.library_max_file_mb * 1024 * 1024)
        except StorageError:
            raise HTTPException(503, detail={"code": "storage_unavailable",
                                             "message": "File storage is unavailable right now. Try again shortly."})
        finally:
            f.file.close()
        if r.status == "added" and r.upload is not None:
            background.add_task(
                svc.run_analysis, r.upload.id, session_factory, storage, settings.library_analysis_enabled
            )
        results.append(UploadResultOut(
            filename=r.filename, status=r.status, message=r.message,
            upload=LibraryUploadOut.from_upload(r.upload) if r.upload else None,
        ))
    return UploadResponse(results=results)


@router.get("/{upload_id}", response_model=LibraryUploadOut)
def get_library_item(upload_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return LibraryUploadOut.from_upload(_own_upload(db, user, upload_id))


def _serve(storage: ObjectStorage, upload: LibraryUpload, key: str, content_type: str, settings: Settings) -> Response:
    if upload.storage_backend != storage.key:
        raise HTTPException(503, detail={"code": "storage_mismatch",
                                         "message": "This file is stored in a different storage backend than the one configured."})
    local = storage.local_path(key)
    if local is not None:
        if not local.is_file():
            raise HTTPException(404, "The stored file is missing")
        # FileResponse answers Range requests with 206 Partial Content, which the browser needs to seek.
        return FileResponse(local, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"})
    url = storage.presigned_url(key, content_type, settings.r2_presign_seconds)
    if url is None:
        raise HTTPException(503, "Storage backend cannot serve files")
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Cache-Control": "no-store"})


@router.get("/{upload_id}/stream", summary="Stream my file (supports Range requests)")
def stream(
    upload_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage), settings: Settings = Depends(get_settings),
) -> Response:
    upload = _own_upload(db, user, upload_id)
    return _serve(storage, upload, upload.storage_key, upload.content_type, settings)


@router.get("/{upload_id}/cover", summary="Embedded cover art of my file")
def cover(
    upload_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage), settings: Settings = Depends(get_settings),
) -> Response:
    upload = _own_upload(db, user, upload_id)
    if not upload.cover_storage_key:
        raise HTTPException(404, "This file has no cover art")
    return _serve(storage, upload, upload.cover_storage_key, upload.cover_content_type or "image/jpeg", settings)


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete my file and its song")
def delete(
    upload_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage),
) -> Response:
    svc.delete_upload(db, storage, _own_upload(db, user, upload_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
