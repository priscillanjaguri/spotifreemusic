"""Explicit user feedback on songs and artists (recommendation signals)."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Deliberately NO "dislike derived from skip". A skip is recorded as its own
# neutral signal; only 'not_interested' is explicit negative feedback.
INTERACTION_TYPES = ("interested", "not_interested", "saved", "skipped", "dismissed")


class UserInteraction(Base):
    """Append-only log; the latest row per (user, target) is the current state."""

    __tablename__ = "user_interactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"))
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"))
    interaction_type: Mapped[str] = mapped_column(String(20))
    # Where the feedback was given: "discover", "daily_companion", "collection"...
    context: Mapped[str | None] = mapped_column(String(30))
    # Only set when the user explicitly chose a mood/context -- never inferred.
    selected_mood: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(f"interaction_type IN {INTERACTION_TYPES}", name="type_valid"),
        # Exactly one target: a song XOR an artist.
        CheckConstraint("(song_id IS NULL) <> (artist_id IS NULL)", name="exactly_one_target"),
        Index("ix_user_interactions_user_created", "user_id", "created_at"),
        Index("ix_user_interactions_user_song", "user_id", "song_id"),
        Index("ix_user_interactions_user_artist", "user_id", "artist_id"),
    )
