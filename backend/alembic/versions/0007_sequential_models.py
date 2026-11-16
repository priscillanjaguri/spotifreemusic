"""sequential_models for next-track candidate generation

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-16 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sequential_models",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "algorithm",
            sa.String(length=40),
            server_default="markov_cooccurrence",
            nullable=False,
        ),
        sa.Column("n_transitions", sa.Integer(), nullable=False),
        sa.Column("n_sessions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("n_unique_songs", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("artifact", sa.LargeBinary(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sequential_models")),
    )
    op.create_index("ix_sequential_models_created_at", "sequential_models", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_sequential_models_created_at", table_name="sequential_models")
    op.drop_table("sequential_models")
