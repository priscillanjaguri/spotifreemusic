"""Users and their preferences."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    # UUID (not an incrementing int) so ids in URLs/tokens can't be enumerated.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str] = mapped_column(String(255))  # argon2 hash, never plaintext
    display_name: Mapped[str] = mapped_column(String(100))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    preferences: Mapped["UserPreferences"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Emails are unique case-insensitively: "A@x.com" and "a@x.com" are one account.
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )


class UserPreferences(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # IANA name, e.g. "Africa/Nairobi". Weeks/months are bucketed in the user's
    # local time, so this matters for analytics correctness.
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    week_starts_on: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # 0=Mon..6=Sun
    # Privacy switch: when false the API must not record new listening events.
    record_listening_history: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    # Windows used by the recommender to separate "right now" from "who I am".
    short_term_days: Mapped[int] = mapped_column(Integer, default=28, server_default="28")
    long_term_days: Mapped[int] = mapped_column(Integer, default=365, server_default="365")
    # Onboarding / seed genres for cold start (lowercase names). Empty until the user picks some.
    preferred_genres: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list, server_default="{}")

    user: Mapped[User] = relationship(back_populates="preferences")

    __table_args__ = (
        CheckConstraint("week_starts_on BETWEEN 0 AND 6", name="week_starts_on_range"),
        CheckConstraint("short_term_days > 0 AND long_term_days > short_term_days", name="windows_valid"),
    )
