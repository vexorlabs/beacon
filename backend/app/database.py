from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

settings.db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app import models  # noqa: F401 — import triggers model registration

    Base.metadata.create_all(bind=engine)
    _run_migrations()


def _run_migrations() -> None:
    """Run lightweight column-add migrations for existing tables."""
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(spans)"))
        span_columns = {row[1] for row in result}
        if "annotations" not in span_columns:
            conn.execute(
                text("ALTER TABLE spans ADD COLUMN annotations TEXT DEFAULT '[]'")
            )
            conn.commit()
        if "sdk_language" not in span_columns:
            conn.execute(text("ALTER TABLE spans ADD COLUMN sdk_language TEXT"))
            conn.commit()

        result = conn.execute(text("PRAGMA table_info(traces)"))
        trace_columns = {row[1] for row in result}
        if "sdk_language" not in trace_columns:
            conn.execute(text("ALTER TABLE traces ADD COLUMN sdk_language TEXT"))
            conn.commit()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
