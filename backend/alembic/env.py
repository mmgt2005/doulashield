import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.models.base import Base
import app.models  # noqa: F401 — register all models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Read DATABASE_URL directly from environment — bypasses configparser so that
# URL-encoded characters (e.g. %40 for @) are not misinterpreted as interpolation.
_db_url = os.environ["DATABASE_URL"].replace(
    "postgresql+asyncpg://", "postgresql://"
)


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_db_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
