"""Persisted recommender evaluation snapshots (continuous offline metrics)."""
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EvalSnapshot(Base):
    """One hold-out ranking run: metrics + data-volume counters at that moment."""

    __tablename__ = "eval_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    # precision_at_k, recall_at_k, coverage, diversity, k, users_evaluated, ...
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # listening_events, interactions, users, catalogue_songs, ...
    data_volume: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Aggregated feedback counts only (no song ids / titles).
    feedback_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    # "holdout" when enough real signals; "synthetic" fallback for empty DB.
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default="holdout")
    k: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
