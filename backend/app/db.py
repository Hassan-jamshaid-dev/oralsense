from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.errors import AppError, database_not_configured

PLACEHOLDER_PASSWORD = "CHANGE_ME"


@lru_cache
def get_engine() -> Engine:
    database_url = get_settings().database_url
    # The .env.example placeholder means setup was never finished; say so instead of "auth failed".
    if not database_url or PLACEHOLDER_PASSWORD in database_url:
        raise database_not_configured()
    try:
        return create_engine(database_url, pool_pre_ping=True)
    except ArgumentError as exc:
        raise database_not_configured() from exc


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database_status() -> str:
    """Return "ok", "not_configured", or "unavailable" without raising."""
    try:
        engine = get_engine()
    except AppError:
        return "not_configured"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return "unavailable"
    return "ok"
