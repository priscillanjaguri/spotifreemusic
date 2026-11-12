"""Alembic environment.

The DB URL comes from `ALEMBIC_DATABASE_URL` if set (used by the tests to
target the test database), otherwise from the app settings.
"""
import os

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.models.base import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = os.environ.get("ALEMBIC_DATABASE_URL")
    if url:
        return url
    from app.core.config import get_settings
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
