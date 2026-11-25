from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.config import get_settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    # Keep app loggers alive when migrations run in-process (the test suite does this).
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def get_database_url() -> str:
    # Tests pass an explicit URL via config attributes so they never touch the dev database.
    url = config.attributes.get("database_url") or get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Add it to backend/.env before running migrations.")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_database_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
