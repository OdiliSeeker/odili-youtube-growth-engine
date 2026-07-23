"""Shared pytest fixtures for the Lead Discovery / YouTube quota tests.

Every test runs against an isolated, file-backed SQLite database (a fresh temp
file per test) so that:
  * the real ``python-backend/data/odili.db`` is never touched, and
  * multiple independent connections/threads can be opened (needed to prove the
    quota counter increments atomically under concurrency).

No real YouTube API calls are ever made — the HTTP layer is mocked in the
individual tests.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
import app.models.db_models  # noqa: F401 — register models on Base.metadata


@pytest.fixture()
def engine(tmp_path):
    db_file = tmp_path / "test_odili.db"
    eng = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
        echo=False,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def SessionFactory(engine):
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db(SessionFactory):
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _youtube_key(monkeypatch):
    """Make the engine look configured without a real key."""
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key-not-real")
