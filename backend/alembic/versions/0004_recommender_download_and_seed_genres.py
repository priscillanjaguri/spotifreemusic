"""recommender: download_allowed on provider links + preferred_genres for cold start

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-12 09:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "song_provider_links",
        sa.Column("download_allowed", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "preferred_genres",
            postgresql.ARRAY(sa.String(length=100)),
            server_default="{}",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "preferred_genres")
    op.drop_column("song_provider_links", "download_allowed")
