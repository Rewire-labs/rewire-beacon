"""Async SQLAlchemy engine + session factories.

Two engines:
- `engine` — application engine (RLS enforced via GUC).
- `worker_engine` — beacon_worker role (BYPASSRLS). Same DSN if no override.

Sessions:
- `app_session()` — async context for request-scoped DB work (RLS-bound).
- `worker_session()` — async context for cross-tenant background work.
- `tenant_scoped_session(org_id)` — convenience: app_session + SET GUC.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from beacon.settings import get_settings

_engine: AsyncEngine | None = None
_worker_engine: AsyncEngine | None = None
_app_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_worker_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _build_engine(dsn: str, **kwargs: Any) -> AsyncEngine:
    return create_async_engine(
        dsn,
        pool_pre_ping=True,
        future=True,
        **kwargs,
    )


def get_engine() -> AsyncEngine:
    global _engine, _app_sessionmaker
    if _engine is None:
        s = get_settings()
        _engine = _build_engine(s.database_url)
        _app_sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_worker_engine() -> AsyncEngine:
    global _worker_engine, _worker_sessionmaker
    if _worker_engine is None:
        s = get_settings()
        dsn = getattr(s, "worker_database_url", None) or s.database_url
        _worker_engine = _build_engine(dsn)
        _worker_sessionmaker = async_sessionmaker(_worker_engine, expire_on_commit=False)
    return _worker_engine


@asynccontextmanager
async def app_session() -> AsyncIterator[AsyncSession]:
    get_engine()  # ensure factory built
    assert _app_sessionmaker is not None
    async with _app_sessionmaker() as session:
        yield session


@asynccontextmanager
async def worker_session() -> AsyncIterator[AsyncSession]:
    get_worker_engine()
    assert _worker_sessionmaker is not None
    async with _worker_sessionmaker() as session:
        yield session


@asynccontextmanager
async def tenant_scoped_session(organization_id: str) -> AsyncIterator[AsyncSession]:
    """Open a session with `beacon.current_org_id` GUC set (RLS-bound).

    Postgres-only — SQLite (dev fallback) silently no-ops on SET LOCAL.
    """
    async with app_session() as session:
        # SET LOCAL applies until COMMIT/ROLLBACK; safe per-request.
        try:
            await session.execute(
                text("SELECT set_config('beacon.current_org_id', :v, true)").bindparams(v=organization_id)
            )
        except Exception:
            # SQLite or pre-migration DB — skip silently.
            pass
        yield session


async def dispose_engines() -> None:
    global _engine, _worker_engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    if _worker_engine is not None:
        await _worker_engine.dispose()
        _worker_engine = None
