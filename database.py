"""
Database engine and session-factory setup.

Two independent async SQLAlchemy engines are maintained:

- ``questions_engine`` points at the supplied, read-only trivia database.
- ``app_engine`` points at the bot's own state database.

Keeping them separate guarantees the source trivia data can never be
mutated by an application bug, and lets each database be backed up /
migrated independently.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import config
from models.base import AppBase

logger = logging.getLogger(__name__)


def _to_async_sqlite_url(path_or_url: str) -> str:
    """Normalize a plain filesystem path or sync URL into an async sqlite URL."""
    if path_or_url.startswith("sqlite+aiosqlite://"):
        return path_or_url
    if path_or_url.startswith("sqlite://"):
        return path_or_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return f"sqlite+aiosqlite:///{path_or_url}"


questions_engine = create_async_engine(
    _to_async_sqlite_url(config.questions_db_path),
    echo=False,
    future=True,
)
QuestionsSession = async_sessionmaker(
    bind=questions_engine, expire_on_commit=False, class_=AsyncSession
)

app_engine = create_async_engine(
    _to_async_sqlite_url(config.app_db_url),
    echo=False,
    future=True,
)
AppSession = async_sessionmaker(
    bind=app_engine, expire_on_commit=False, class_=AsyncSession
)


async def init_app_db() -> None:
    """Create tables on the app database if they don't already exist.

    This is a safety net for fresh deployments; the canonical way to
    evolve the schema is Alembic (``alembic upgrade head``). This call is
    idempotent and never touches the questions database.
    """
    async with app_engine.begin() as conn:
        await conn.run_sync(AppBase.metadata.create_all)
    logger.info("App database ready at %s", config.app_db_url)


async def dispose_engines() -> None:
    """Cleanly close both database engines on shutdown."""
    await questions_engine.dispose()
    await app_engine.dispose()
