"""SQLite engine, async session factory, and database location resolution.

The async engine (aiosqlite) backs the FastAPI request path; the synchronous
URL is consumed by Alembic for migrations.
"""

import os
from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

_ENV_DB_PATH = "HAND2NOTES_DB_PATH"


def database_path() -> Path:
    """Resolve the SQLite file path, honouring the HAND2NOTES_DB_PATH override."""
    override = os.environ.get(_ENV_DB_PATH)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "hand2notes" / "hand2notes.db"


def sync_database_url() -> str:
    """Synchronous SQLite URL for Alembic migrations."""
    return f"sqlite:///{database_path()}"


def async_database_url() -> str:
    """Async SQLite URL for the application engine."""
    return f"sqlite+aiosqlite:///{database_path()}"


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    """Return the process-wide async engine, creating it (and its parent dir) on first use."""
    global _engine, _sessionmaker
    if _engine is None:
        database_path().parent.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(async_database_url(), echo=False, future=True)
        _sessionmaker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


async def init_db() -> None:
    """Create all tables. Alembic owns schema in production; this aids tests/dev."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a scoped async session."""
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        yield session
