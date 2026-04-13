"""Alembic environment for Annotation Hub.

- The database URL is resolved from the same package-resource path that
  ``D3TextDB`` uses at runtime, so migrations always target the live database.
- ``SQLModel.metadata`` is used as the target metadata so that
  ``--autogenerate`` picks up all SQLModel table definitions automatically.
- ``render_as_batch=True`` enables SQLite-compatible batch ALTER TABLE support
  (SQLite cannot drop/rename columns directly; Alembic rewrites the table).
"""

from importlib import resources
from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context

# Import ALL models so that SQLModel.metadata is fully populated before we
# hand it to Alembic.  Importing from d3textdb.schema is sufficient because
# every SQLModel table in the project lives there.
from d3textdb.schema import SQLModel  # noqa: F401 – side-effect: registers models
import d3textdb.schema  # noqa: F401 – ensure subclasses are registered

# --------------------------------------------------------------------------- #
# Alembic Config object
# --------------------------------------------------------------------------- #

config = context.config

# Interpret the config file's logging configuration.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at SQLModel's shared metadata.
target_metadata = SQLModel.metadata

# --------------------------------------------------------------------------- #
# Resolve the database URL from the package resource path
# --------------------------------------------------------------------------- #


def _db_url() -> str:
    """Return the SQLite URL for the live database."""
    db_path = resources.files("ahbackend.db") / "database.db"
    # resources.files() returns a Traversable; convert to a concrete path.
    return f"sqlite:///{db_path}"


# --------------------------------------------------------------------------- #
# Migration runners
# --------------------------------------------------------------------------- #


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    url = _db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = sa.create_engine(_db_url())
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
