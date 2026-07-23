"""
SQLite database setup via SQLAlchemy.

The database file lives at  python-backend/data/odili.db
and is created automatically on first boot.
"""

import logging
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

logger = logging.getLogger(__name__)

_DB_DIR = Path(__file__).parent.parent / "data"
_DB_DIR.mkdir(exist_ok=True)
_DB_PATH = _DB_DIR / "odili.db"

# Always use SQLite — DATABASE_URL in this monorepo belongs to the Node.js service.
DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    """FastAPI dependency — yields a DB session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_columns() -> None:
    """
    Lightweight SQLite migration: add columns introduced after the table was
    first created. ``create_all`` only creates missing *tables*, never adds
    columns to an existing one, so we patch them in by hand.
    """
    # table_name -> {column_name -> ALTER definition}
    wanted = {
        "subscribers": {
            "interest": "ALTER TABLE subscribers ADD COLUMN interest VARCHAR(120)",
            "drip_step": "ALTER TABLE subscribers ADD COLUMN drip_step INTEGER NOT NULL DEFAULT 0",
        },
        "topics": {
            "sort_order": "ALTER TABLE topics ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0",
        },
    }
    with engine.begin() as conn:
        for table, cols in wanted.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if not existing:
                continue  # table not created yet — create_all handles it fresh
            for col, ddl in cols.items():
                if col not in existing:
                    conn.execute(text(ddl))
                    logger.info("Migrated %s table: added column %r", table, col)


def init_db() -> None:
    """Create all tables. Safe to call on every startup."""
    from app.models import db_models  # noqa: F401 — import to register models
    Base.metadata.create_all(bind=engine)
    _ensure_columns()

    # Seed starter topics so the public funnel is never empty on first boot.
    from app.services.topic_service import seed_default_topics
    db = SessionLocal()
    try:
        seed_default_topics(db)
    finally:
        db.close()
