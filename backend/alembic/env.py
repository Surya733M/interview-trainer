"""
alembic/env.py — Alembic Migration Environment
================================================
Alembic is a database migration tool for SQLAlchemy.

WHY ALEMBIC?
  In production (PostgreSQL), you cannot simply run create_all() after every
  schema change — that would overwrite data. Instead you write "migration scripts"
  that describe exactly what changed (e.g., "add column X to table Y").
  Alembic manages and tracks which migrations have been applied.

HOW TO USE:
  Initial setup (already done — this file):
    cd backend
    alembic init alembic

  Create a new migration after changing a model:
    alembic revision --autogenerate -m "add_new_column"

  Apply all pending migrations:
    alembic upgrade head

  Roll back the last migration:
    alembic downgrade -1

  See current migration version:
    alembic current
"""

from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Allow importing app modules ───────────────────────────────────────────────
# Add the parent directory to sys.path so we can import `app`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Alembic config ────────────────────────────────────────────────────────────
# `config` is the alembic.ini configuration object
config = context.config

# Set up Python logging (reads from alembic.ini [loggers] section)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import our models so Alembic knows about them ─────────────────────────────
# target_metadata is used by --autogenerate to detect schema changes
from app.config import settings
from app.database import Base

# Import all models so they register with Base.metadata
from app.models import user, interview, report  # noqa: F401

target_metadata = Base.metadata

# Override the sqlalchemy.url from alembic.ini with our settings value
# This ensures Alembic uses the same database URL as the application
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    In offline mode, Alembic generates SQL scripts without actually connecting
    to the database. Useful for reviewing migrations before applying them.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (normal usage).
    Creates a real database connection and applies migrations.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool: don't reuse connections in migrations
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
