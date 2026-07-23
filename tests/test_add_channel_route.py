"""Route-level tests for POST /leads/channels error mapping.

The service layer (parse/resolve/add) is covered in test_channel_onboarding.py;
these tests prove the FastAPI route translates every service-layer failure into
a non-500 response with a human-readable message the Lead Discovery admin tab
can display verbatim:

  * unparseable input        → 400 + guidance to paste a channel URL/handle
  * unknown channel          → 400 + "No YouTube channel found"
  * YOUTUBE_API_KEY unset    → 400 + "YOUTUBE_API_KEY is not configured."
  * daily quota exhausted    → 429 + quota message
  * upstream quota 403       → 429 + quota message

No real YouTube calls: httpx.get is monkeypatched, and the router is mounted on
a minimal FastAPI app with get_db overridden to the per-test SQLite session.
"""

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import get_db
from app.routes import lead_discovery
from app.services import youtube_api_service as yt

from tests.test_channel_onboarding import FakeResponse, UC_ID, channels_payload

ADMIN_KEY = "test-admin-key"
HEADERS = {"x-api-key": ADMIN_KEY}


@pytest.fixture()
def client(db, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
    app = FastAPI()
    app.include_router(lead_discovery.router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app, raise_server_exceptions=False)


def _post(client, url="https://www.youtube.com/@testchannel"):
    return client.post("/leads/channels", json={"url": url}, headers=HEADERS)


def test_unparseable_input_returns_400_with_guidance(client, monkeypatch):
    def boom(*a, **k):  # pragma: no cover — must never be called
        raise AssertionError("HTTP must not be called for unparseable input")

    monkeypatch.setattr(httpx, "get", boom)
    res = _post(client, url="some words with spaces")
    assert res.status_code == 400
    detail = res.json()["detail"]
    # Human-readable guidance, not a raw traceback/500.
    assert "channel" in detail.lower()
    assert "URL" in detail or "handle" in detail.lower() or "@" in detail


def test_unknown_channel_returns_400(client, monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(payload={"items": []})
    )
    res = _post(client, url="@nosuchchannel")
    assert res.status_code == 400
    assert "No YouTube channel found" in res.json()["detail"]


def test_missing_api_key_returns_400(client, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    def boom(*a, **k):  # pragma: no cover
        raise AssertionError("HTTP must not be called without an API key")

    monkeypatch.setattr(httpx, "get", boom)
    res = _post(client)
    assert res.status_code == 400
    assert "YOUTUBE_API_KEY is not configured." == res.json()["detail"]


def test_daily_quota_cap_returns_429(client, db, monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(payload=channels_payload())
    )
    # Exhaust the local daily budget so the pre-flight cap check trips.
    yt._log_units(db, yt.DAILY_QUOTA_CAP)
    res = _post(client)
    assert res.status_code == 429
    assert "quota" in res.json()["detail"].lower()


def test_upstream_quota_403_returns_429(client, monkeypatch):
    payload = {"error": {"errors": [{"reason": "quotaExceeded"}]}}
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(status_code=403, payload=payload)
    )
    res = _post(client)
    assert res.status_code == 429
    assert "quota" in res.json()["detail"].lower()


@pytest.mark.parametrize(
    "exc",
    [
        httpx.TimeoutException("request timed out"),
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("read timed out"),
    ],
)
def test_network_failure_returns_readable_400_not_500(client, monkeypatch, exc):
    def raise_network_error(*a, **k):
        raise exc

    monkeypatch.setattr(httpx, "get", raise_network_error)
    res = _post(client)
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "Network error calling YouTube API" in detail
    # Not a raw traceback / opaque server error.
    assert "Internal Server Error" not in detail
    assert "Traceback" not in detail


def test_missing_auth_header_rejected(client):
    res = client.post("/leads/channels", json={"url": UC_ID})
    assert res.status_code in (401, 403)


def test_happy_path_still_works(client, monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(payload=channels_payload())
    )
    res = _post(client, url=UC_ID)
    assert res.status_code == 200
    body = res.json()
    assert body["created"] is True
    assert body["channel"]["channel_id"] == UC_ID
