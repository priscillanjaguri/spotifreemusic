"""Sequential next-track model artifacts (Markov / co-occurrence)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SequentialModelRow(Base):
    """Serialized classical sequential model (joblib bytes) + training metadata."""

    __tablename__ = "sequential_models"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    algorithm: Mapped[str] = mapped_column(String(40), server_default="markov_cooccurrence")
    n_transitions: Mapped[int] = mapped_column(Integer, nullable=False)
    n_sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    n_unique_songs: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    artifact: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
