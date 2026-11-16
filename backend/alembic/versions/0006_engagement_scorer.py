"""recommendation_impressions + scorer_models for learned engagement scoring

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-16 09:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_impressions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("song_id", sa.BigInteger(), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "shown_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cosine_score", sa.Float(), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("label", sa.SmallInteger(), nullable=True),
        sa.Column("labeled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("label_source", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_impressions")),
    )
    op.create_index(
        "ix_recommendation_impressions_user_id",
        "recommendation_impressions",
        ["user_id"],
    )
    op.create_index(
        "ix_recommendation_impressions_song_id",
        "recommendation_impressions",
        ["song_id"],
    )
    op.create_index(
        "ix_recommendation_impressions_request_id",
        "recommendation_impressions",
        ["request_id"],
    )
    op.create_index(
        "ix_rec_impressions_user_song_shown",
        "recommendation_impressions",
        ["user_id", "song_id", "shown_at"],
    )
    op.create_index(
        "ix_rec_impressions_labeled",
        "recommendation_impressions",
        ["user_id", "label"],
        postgresql_where=sa.text("label IS NOT NULL"),
    )

    op.create_table(
        "scorer_models",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("algorithm", sa.String(length=40), server_default="logistic_regression", nullable=False),
        sa.Column("feature_names", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("n_samples", sa.Integer(), nullable=False),
        sa.Column("n_positives", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("artifact", sa.LargeBinary(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scorer_models")),
    )
    op.create_index("ix_scorer_models_created_at", "scorer_models", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_scorer_models_created_at", table_name="scorer_models")
    op.drop_table("scorer_models")
    op.drop_index("ix_rec_impressions_labeled", table_name="recommendation_impressions")
    op.drop_index("ix_rec_impressions_user_song_shown", table_name="recommendation_impressions")
    op.drop_index("ix_recommendation_impressions_request_id", table_name="recommendation_impressions")
    op.drop_index("ix_recommendation_impressions_song_id", table_name="recommendation_impressions")
    op.drop_index("ix_recommendation_impressions_user_id", table_name="recommendation_impressions")
    op.drop_table("recommendation_impressions")
