"""My Library: audio files a user owns and uploaded.

The file itself lives in object storage (local disk in development, Cloudflare R2 when
configured); this row records where, plus the hash used to skip duplicate uploads.
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.catalog import Song

STORAGE_BACKENDS = ("local", "r2")
ANALYSIS_STATUSES = ("pending", "running", "done", "failed", "unavailable")


class LibraryUpload(Base):
    __tablename__ = "library_uploads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # SET NULL: if the song row is kept (e.g. it has listening history) the upload can still be deleted.
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id", ondelete="SET NULL"), index=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    original_filename: Mapped[str] = mapped_column(String(300))
    audio_format: Mapped[str] = mapped_column(String(10))  # mp3 | m4a | aac | flac | ogg | wav
    content_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_backend: Mapped[str] = mapped_column(String(10))
    storage_key: Mapped[str] = mapped_column(String(300))
    cover_storage_key: Mapped[str | None] = mapped_column(String(300))
    cover_content_type: Mapped[str | None] = mapped_column(String(50))
    analysis_status: Mapped[str] = mapped_column(String(12), default="pending", server_default="pending")
    analysis_error: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    song: Mapped[Song | None] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "content_sha256", name="uq_library_uploads_user_hash"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint(f"storage_backend IN {STORAGE_BACKENDS}", name="storage_backend_valid"),
        CheckConstraint(f"analysis_status IN {ANALYSIS_STATUSES}", name="analysis_status_valid"),
    )
