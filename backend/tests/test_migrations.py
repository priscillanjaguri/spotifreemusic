import os
import subprocess
import sys

from sqlalchemy import inspect

from tests.conftest import BACKEND_DIR, TEST_URL
from app.models import Base


def test_every_model_table_exists_after_migrating(engine):
    existing = set(inspect(engine).get_table_names())
    assert set(Base.metadata.tables) <= existing


def test_models_and_migrations_have_not_drifted(engine):
    """`alembic check` fails if models changed without a new migration."""
    env = {**os.environ, "ALEMBIC_DATABASE_URL": TEST_URL}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "check"], cwd=BACKEND_DIR, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
