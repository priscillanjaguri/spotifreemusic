"""eval_snapshots table for continuous recommender metrics

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-14 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_snapshots",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data_volume", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "feedback_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("source", sa.String(length=20), server_default="holdout", nullable=False),
        sa.Column("k", sa.Integer(), server_default="10", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eval_snapshots")),
    )
    op.create_index("ix_eval_snapshots_created_at", "eval_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_eval_snapshots_created_at", table_name="eval_snapshots")
    op.drop_table("eval_snapshots")
