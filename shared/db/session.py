from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from shared.settings import get_settings


settings = get_settings()
_engine: Engine | None = None
_session_local: sessionmaker[Session] | None = None
_engine_init_error: Exception | None = None


def _initialize_session_factory() -> None:
    global _engine, _session_local, _engine_init_error
    if _session_local is not None or _engine_init_error is not None:
        return
    try:
        _engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
        _session_local = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    except Exception as exc:
        _engine_init_error = exc


def _get_session_factory() -> sessionmaker[Session]:
    _initialize_session_factory()
    if _engine_init_error is not None:
        raise RuntimeError(f"Invalid DATABASE_URL configuration: {_engine_init_error}") from _engine_init_error
    if _session_local is None:
        raise RuntimeError("Database session factory was not initialized.")
    return _session_local


def SessionLocal() -> Session:
    session_factory = _get_session_factory()
    return session_factory()


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_database_ready() -> None:
    _initialize_session_factory()
    if _engine_init_error is not None:
        raise RuntimeError(f"Database configuration error: {_engine_init_error}") from _engine_init_error
    if _engine is None:
        raise RuntimeError("Database engine is not initialized.")
    with _engine.connect() as connection:
        connection.execute(text("SELECT 1"))
