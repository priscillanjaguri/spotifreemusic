"""A user's private music collection."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.catalog import Song

COLLECTION_SOURCES = ("search", "recommendation", "daily_companion", "import", "manual")


class UserCollection(Base):
    __tablename__ = "user_collections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # How the song got here. The recommender uses this: adding a song from a
    # recommendation is a stronger "it worked" signal than a manual add.
    source: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")

    song: Mapped[Song] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "song_id", name="uq_user_collections_user_song"),
        CheckConstraint(f"source IN {COLLECTION_SOURCES}", name="source_valid"),
    )
