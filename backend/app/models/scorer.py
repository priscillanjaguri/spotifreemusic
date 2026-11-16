"""Engagement scorer: recommendation impressions + persisted model artifacts."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

LABEL_SOURCES = ("like", "hide", "play", "complete", "skip")


class RecommendationImpression(Base):
    """One song shown in a For You (or similar) list, with feature snapshot for training.

    `label` stays NULL until listening/feedback later marks engage (1) or not (0).
    """

    __tablename__ = "recommendation_impressions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    # Groups every item from one /recommendations response.
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    position: Mapped[int] = mapped_column(Integer)
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cosine_score: Mapped[float] = mapped_column(Float)
    # Stable scorer feature dict at impression time (see app.ml.scorer.FEATURE_NAMES).
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # NULL = pending outcome; 1 = engaged; 0 = not engaged.
    label: Mapped[int | None] = mapped_column(SmallInteger)
    labeled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    label_source: Mapped[str | None] = mapped_column(String(20))

    __table_args__ = (
        Index("ix_rec_impressions_user_song_shown", "user_id", "song_id", "shown_at"),
        Index(
            "ix_rec_impressions_labeled",
            "user_id",
            "label",
            postgresql_where="label IS NOT NULL",
        ),
    )


class ScorerModel(Base):
    """Serialized classical engagement model (joblib bytes) + training metadata."""

    __tablename__ = "scorer_models"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    algorithm: Mapped[str] = mapped_column(String(40), server_default="logistic_regression")
    feature_names: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    n_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    n_positives: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    artifact: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
