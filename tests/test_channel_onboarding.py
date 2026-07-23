"""Tests for channel onboarding: parse_channel_input, resolve_channel, add_channel.

Covers the admin "add a channel" flow end-to-end (parsing, YouTube ``channels``
resolution, idempotent storage) without ever touching the real YouTube API —
``httpx.get`` is monkeypatched, same pattern as ``test_youtube_quota.py``.
"""

import httpx
import pytest

from app.services import youtube_api_service as yt
from app.services import lead_discovery_service as lds


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"items": []}
        self.text = text

    def json(self):
        return self._payload


UC_ID = "UC" + "a" * 22


def channels_payload(channel_id=UC_ID, title="Test Channel", handle="@testchannel",
                     uploads="UU" + "a" * 22, with_uploads=True):
    item = {
        "id": channel_id,
        "snippet": {"title": title, "customUrl": handle},
        "contentDetails": {"relatedPlaylists": {"uploads": uploads} if with_uploads else {}},
    }
    return {"items": [item]}


# ── parse_channel_input ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        (f"https://www.youtube.com/channel/{UC_ID}", ("id", UC_ID)),
        (UC_ID, ("id", UC_ID)),
        (f"  {UC_ID}  ", ("id", UC_ID)),
        ("https://www.youtube.com/@BishopBarron", ("handle", "@BishopBarron")),
        ("https://youtube.com/@some.channel-name_1", ("handle", "@some.channel-name_1")),
        ("@MyHandle", ("handle", "@MyHandle")),
        ("BareToken", ("handle", "@BareToken")),
        ("bare_token-123", ("handle", "@bare_token-123")),
    ],
)
def test_parse_channel_input_accepts(raw, expected):
    assert yt.parse_channel_input(raw) == expected


def test_parse_channel_input_prefers_uc_id_over_handle():
    # A URL containing both a UC id and an @handle resolves to the id.
    raw = f"https://www.youtube.com/channel/{UC_ID}?ref=@somebody"
    assert yt.parse_channel_input(raw) == ("id", UC_ID)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        None,
        "https://www.youtube.com/watch?v=abc123",   # video URL, no UC id / handle
        "some words with spaces",
        "https://example.com/not/a/channel",
    ],
)
def test_parse_channel_input_rejects(raw):
    with pytest.raises(yt.YouTubeAPIError):
        yt.parse_channel_input(raw)


# ── resolve_channel ──────────────────────────────────────────────────────────

def test_resolve_channel_by_id(db, monkeypatch):
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen["url"] = url
        seen["params"] = params
        return FakeResponse(payload=channels_payload())

    monkeypatch.setattr(httpx, "get", fake_get)
    info = yt.resolve_channel(db, UC_ID)

    assert seen["url"].endswith("/channels")
    assert seen["params"]["id"] == UC_ID
    assert "forHandle" not in seen["params"]
    assert info == {
        "channel_id": UC_ID,
        "title": "Test Channel",
        "handle": "@testchannel",
        "uploads_playlist_id": "UU" + "a" * 22,
    }
    # Exactly 1 quota unit spent.
    assert yt.units_used_today(db) == 1


def test_resolve_channel_by_handle(db, monkeypatch):
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen["params"] = params
        return FakeResponse(payload=channels_payload())

    monkeypatch.setattr(httpx, "get", fake_get)
    yt.resolve_channel(db, "https://www.youtube.com/@testchannel")

    assert seen["params"]["forHandle"] == "@testchannel"
    assert "id" not in seen["params"]
    assert yt.units_used_today(db) == 1


def test_resolve_channel_missing_channel(db, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(payload={"items": []}))
    with pytest.raises(yt.YouTubeAPIError, match="No YouTube channel found"):
        yt.resolve_channel(db, "@nosuchchannel")
    # Unit is logged conservatively even though resolution failed.
    assert yt.units_used_today(db) == 1


def test_resolve_channel_no_uploads_playlist(db, monkeypatch):
    monkeypatch.setattr(
        httpx, "get",
        lambda *a, **k: FakeResponse(payload=channels_payload(with_uploads=False)),
    )
    with pytest.raises(yt.YouTubeAPIError, match="no accessible uploads playlist"):
        yt.resolve_channel(db, UC_ID)


def test_resolve_channel_invalid_input_costs_nothing(db, monkeypatch):
    def boom(*a, **k):  # pragma: no cover — must never be called
        raise AssertionError("HTTP must not be called for unparseable input")

    monkeypatch.setattr(httpx, "get", boom)
    with pytest.raises(yt.YouTubeAPIError):
        yt.resolve_channel(db, "words with spaces")
    assert yt.units_used_today(db) == 0


# ── add_channel ──────────────────────────────────────────────────────────────

def test_add_channel_creates_then_updates(db, monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(payload=channels_payload())
    )

    ch, created = lds.add_channel(db, UC_ID, category="apologetics")
    assert created is True
    assert ch["channel_id"] == UC_ID
    assert ch["title"] == "Test Channel"
    assert ch["category"] == "apologetics"

    # Re-adding (even via a different input form) resolves to the same channel
    # and updates instead of duplicating.
    monkeypatch.setattr(
        httpx, "get",
        lambda *a, **k: FakeResponse(payload=channels_payload(title="Renamed Channel")),
    )
    ch2, created2 = lds.add_channel(db, "@testchannel", category="conversion")
    assert created2 is False
    assert ch2["id"] == ch["id"]
    assert ch2["title"] == "Renamed Channel"
    assert ch2["category"] == "conversion"
    assert len(lds.list_channels(db)) == 1


def test_add_channel_reactivates_inactive(db, monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(payload=channels_payload())
    )
    ch, created = lds.add_channel(db, UC_ID)
    assert created is True

    # Deactivate directly, then re-add — must flip active back on.
    from app.models.db_models import WatchlistChannel
    row = db.query(WatchlistChannel).filter(WatchlistChannel.id == ch["id"]).one()
    row.active = False
    db.commit()

    ch2, created2 = lds.add_channel(db, UC_ID)
    assert created2 is False
    assert ch2["active"] is True


def test_remove_channel(db, monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(payload=channels_payload())
    )
    ch, _ = lds.add_channel(db, UC_ID)
    assert lds.remove_channel(db, ch["id"]) is True
    assert lds.list_channels(db) == []
    assert lds.remove_channel(db, ch["id"]) is False
