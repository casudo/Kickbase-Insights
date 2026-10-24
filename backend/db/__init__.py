"""Module for DB access."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from db import models  # noqa: F401  - registers the tables on the metadata
from db.models import SCHEMA_VERSION, SchemaInfo

log = logging.getLogger(__name__)


def create_db_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        in_memory = ":memory:" in url or url == "sqlite://"
        if not in_memory:
            Path(url.split("///", 1)[1]).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            ### An in-memory database exists per connection, so every thread has to share one
            poolclass=StaticPool if in_memory else None,
        )

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            ### WAL lets the API keep reading while a sync writes
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        return engine

    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)


def init_db(engine: Engine) -> None:
    """Create the tables, rebuilding them when they were created by an older version.

    Everything except the accounts is synced from Kickbase again afterwards, so a rebuild only costs
    one full sync and the users have to log in once more.
    """
    tables = set(inspect(engine).get_table_names())
    stored: int | None = None
    if "schemainfo" in tables:
        with Session(engine) as session:
            row = session.get(SchemaInfo, 1)
            stored = row.version if row else None
    elif tables & set(SQLModel.metadata.tables):
        ### Tables from before the schema was versioned
        stored = 1

    if stored is not None and stored > SCHEMA_VERSION:
        raise RuntimeError(
            f"The database was created by a newer Kickbase Insights "
            f"(schema {stored}, this is {SCHEMA_VERSION})."
        )
    if stored is not None and stored < SCHEMA_VERSION:
        log.warning("Database schema %s is outdated, rebuilding it as schema %s", stored, SCHEMA_VERSION)
        SQLModel.metadata.drop_all(engine)

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.merge(SchemaInfo(id=1, version=SCHEMA_VERSION))
        session.commit()
    log.info("Database ready (%s)", engine.url.render_as_string(hide_password=True))


def session_scope(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
