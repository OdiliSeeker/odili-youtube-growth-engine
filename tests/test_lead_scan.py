"""Tests for the scan loop in ``lead_discovery_service.scan_all``.

Locks in the durable rules from
``.agents/memory/lead-discovery-quota-and-scan.md``:
  * a transient comment-fetch error leaves the video UNscanned (retried next
    scan), while a permanent condition (commentsDisabled) marks it scanned;
  * the daily quota hard-stop halts the scan mid-flight and leaves the pending
    video unscanned.

The YouTube HTTP client is mocked at the ``list_uploads`` / ``list_comments``
seam so no real quota is spent.
"""

import pytest

from app.models.db_models import LeadComment, TrackedVideo, WatchlistChannel
from app.services import lead_discovery_service as lds
from app.services import youtube_api_service as yt


@pytest.fixture()
def channel(db):
    ch = WatchlistChannel(
        channel_id="UCchan1",
        handle="@chan",
        title="Test Channel",
        uploads_playlist_id="UUchan1",
        category="general",
        active=True,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


def _upload(video_id="vid1", title="Test video"):
    return {"video_id": video_id, "title": title, "published_at": None}


def _seeker_comment(comment_id="c1"):
    # Scores well above SAVE_THRESHOLD.
    return {
        "comment_id": comment_id,
        "author": "Seeker",
        "text": "How do I become Catholic? I'm struggling with my faith and prayer.",
    }


def test_transient_comment_error_leaves_video_unscanned(db, channel, monkeypatch):
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: [_upload()])

    def boom(*a, **k):
        raise yt.YouTubeAPIError("network error calling YouTube API")

    monkeypatch.setattr(yt, "list_comments", boom)

    summary = lds.scan_all(db)
    assert summary["status"] == "ok"

    tv = db.query(TrackedVideo).filter(TrackedVideo.video_id == "vid1").first()
    assert tv is not None
    assert tv.scanned is False, "transient failure must leave the video for retry"
    assert summary["comments_scanned"] == 0
    assert summary["leads_found"] == 0


def test_comments_disabled_marks_video_scanned(db, channel, monkeypatch):
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: [_upload()])
    # Permanent condition surfaces to the scan loop as an empty comment list.
    monkeypatch.setattr(yt, "list_comments", lambda *a, **k: [])

    summary = lds.scan_all(db)
    tv = db.query(TrackedVideo).filter(TrackedVideo.video_id == "vid1").first()
    assert tv is not None
    assert tv.scanned is True, "no comments will ever arrive -> mark scanned"
    assert summary["leads_found"] == 0


def test_transient_then_success_rescans_and_finds_lead(db, channel, monkeypatch):
    """A video left unscanned after a blip is picked up and scanned on the next
    scan, producing the lead."""
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: [_upload()])

    def boom(*a, **k):
        raise yt.YouTubeAPIError("transient")

    monkeypatch.setattr(yt, "list_comments", boom)
    lds.scan_all(db)
    tv = db.query(TrackedVideo).filter(TrackedVideo.video_id == "vid1").first()
    assert tv.scanned is False

    # Next scan: comments now available.
    monkeypatch.setattr(yt, "list_comments", lambda *a, **k: [_seeker_comment()])
    summary = lds.scan_all(db)

    db.expire_all()
    tv = db.query(TrackedVideo).filter(TrackedVideo.video_id == "vid1").first()
    assert tv.scanned is True
    assert summary["leads_found"] == 1
    lead = db.query(LeadComment).filter(LeadComment.comment_id == "c1").first()
    assert lead is not None
    assert lead.review_status == "pending"


def test_scanned_video_not_rescanned(db, channel, monkeypatch):
    """An already-scanned video must never have its comments fetched again."""
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: [_upload()])
    calls = {"comments": 0}

    def counting_comments(*a, **k):
        calls["comments"] += 1
        return [_seeker_comment()]

    monkeypatch.setattr(yt, "list_comments", counting_comments)
    lds.scan_all(db)
    assert calls["comments"] == 1

    # Second scan: same upload, already scanned -> no comment fetch.
    lds.scan_all(db)
    assert calls["comments"] == 1


def test_low_intent_comment_not_stored(db, channel, monkeypatch):
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: [_upload()])
    monkeypatch.setattr(
        yt, "list_comments",
        lambda *a, **k: [{"comment_id": "c9", "author": "x", "text": "nice video"}],
    )
    summary = lds.scan_all(db)
    assert summary["leads_found"] == 0
    assert db.query(LeadComment).count() == 0


# ── Quota hard-stop halts the scan ───────────────────────────────────────────

def test_scan_stops_when_already_at_cap(db, channel, monkeypatch):
    """At the cap, the scan checks a channel out and stops before spending."""
    yt._log_units(db, yt.DAILY_QUOTA_CAP)

    def unexpected(*a, **k):  # pragma: no cover
        raise AssertionError("no API call should happen at the cap")

    monkeypatch.setattr(yt, "list_uploads", unexpected)
    monkeypatch.setattr(yt, "list_comments", unexpected)

    summary = lds.scan_all(db)
    assert summary["stopped_early"] is True
    assert summary["channels_checked"] == 0


def test_scan_stops_midflight_leaves_video_unscanned(db, channel, monkeypatch):
    """Uploads are fetched (1 unit) but the per-video budget check trips the
    hard-stop, so the pending video is left unscanned for the next day."""
    # One unit of headroom: uploads call consumes it, then comments can't run.
    monkeypatch.setattr(yt, "DAILY_QUOTA_CAP", 1)

    def real_ish_uploads(_db, *a, **k):
        yt._log_units(_db, yt.COST_LIST)  # emulate the metered upload call
        return [_upload()]

    def unexpected_comments(*a, **k):  # pragma: no cover
        raise AssertionError("comments must not be fetched with no quota left")

    monkeypatch.setattr(yt, "list_uploads", real_ish_uploads)
    monkeypatch.setattr(yt, "list_comments", unexpected_comments)

    summary = lds.scan_all(db)
    assert summary["stopped_early"] is True
    tv = db.query(TrackedVideo).filter(TrackedVideo.video_id == "vid1").first()
    assert tv is not None
    assert tv.scanned is False


def test_quota_error_from_uploads_stops_scan(db, channel, monkeypatch):
    def raise_quota(*a, **k):
        raise yt.YouTubeQuotaError("quota exceeded")

    monkeypatch.setattr(yt, "list_uploads", raise_quota)
    summary = lds.scan_all(db)
    assert summary["stopped_early"] is True


def test_scan_busy_returns_busy(db, channel, monkeypatch):
    """A second scan while the lock is held returns a busy status."""
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: [])
    acquired = lds._scan_lock.acquire(blocking=False)
    assert acquired
    try:
        summary = lds.scan_all(db)
        assert summary["status"] == "busy"
    finally:
        lds._scan_lock.release()


def test_scan_not_configured(db, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    assert lds.scan_all(db) == {"status": "not_configured"}


# ── Admin email on quota-stall transition (deduped) ──────────────────────────

@pytest.fixture()
def notice_spy(monkeypatch):
    """Capture admin-notice sends without touching SendGrid."""
    calls = []

    class _Ok:
        success = True
        error = None

    def _fake_send(subject, body):
        calls.append({"subject": subject, "body": body})
        return _Ok()

    monkeypatch.setattr(
        "app.services.email_sender_service.send_admin_notice", _fake_send
    )
    return calls


def test_quota_stall_emails_admin_once(db, channel, monkeypatch, notice_spy):
    """First scan that stops on quota emails the admin; repeated stalls do not."""
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: (_ for _ in ()).throw(
        yt.YouTubeQuotaError("quota exceeded")
    ))

    summary = lds.scan_all(db)
    assert summary["stopped_early"] is True
    assert len(notice_spy) == 1, "first quota stall must notify the admin"

    # A second stalled scan (still no quota) must NOT re-notify.
    lds.scan_all(db)
    assert len(notice_spy) == 1, "repeated stalls must not spam the admin"


def test_completed_scan_no_email_and_resets_notify(db, channel, monkeypatch, notice_spy):
    """A fully-completed scan sends no email and re-arms the notifier so the next
    quota transition notifies again."""
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: [_upload()])
    monkeypatch.setattr(yt, "list_comments", lambda *a, **k: [_seeker_comment()])

    summary = lds.scan_all(db)
    assert summary["stopped_early"] is False
    assert notice_spy == [], "a normal scan must never email the admin"

    # Now a quota stall happens -> should notify (flag was reset).
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: (_ for _ in ()).throw(
        yt.YouTubeQuotaError("quota exceeded")
    ))
    lds.scan_all(db)
    assert len(notice_spy) == 1


def test_notify_send_failure_retries_next_scan(db, channel, monkeypatch):
    """If the notice fails to send, the flag stays unset so the next stalled
    scan retries the notification."""
    monkeypatch.setattr(yt, "list_uploads", lambda *a, **k: (_ for _ in ()).throw(
        yt.YouTubeQuotaError("quota exceeded")
    ))

    attempts = {"n": 0}

    class _Fail:
        success = False
        error = "smtp down"

    def _failing_send(subject, body):
        attempts["n"] += 1
        return _Fail()

    monkeypatch.setattr(
        "app.services.email_sender_service.send_admin_notice", _failing_send
    )

    lds.scan_all(db)
    lds.scan_all(db)
    assert attempts["n"] == 2, "a failed notice must be retried on the next stall"
