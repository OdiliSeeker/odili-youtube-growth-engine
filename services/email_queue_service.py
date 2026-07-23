"""
Email queue service — auto-compose + admin approval + send (spec PART 2).

Every outbound broadcast email lands here as a *draft* first. Drafts are
auto-generated (trending topic, video marked posted) or created manually from
the content plan. The admin previews/edits, then approves: send now or
schedule. A scheduler job sends due scheduled emails.

Flow: draft → approved → sent. Nothing sends without explicit approval.

Deterministic-first: auto-drafts are pure-Python templates (never 402); the
mark-posted path passes in its AI-enriched draft when available.
"""

import html
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.db_models import EmailQueue, Event, Topic, TopicVote

logger = logging.getLogger(__name__)

VALID_STATUSES = ("draft", "approved", "sent")

# A topic is "trending enough" for an auto-draft with this many votes in 7 days.
TRENDING_DRAFT_MIN_7D = 3


def _naive_utc_now() -> datetime:
    """Naive UTC now — SQLite stores naive timestamps (see drip service note)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize(item: EmailQueue) -> dict:
    return {
        "id": item.id,
        "subject": item.subject,
        "body": item.body,
        "status": item.status,
        "source": item.source,
        "topic_id": item.topic_id,
        "video_url": item.video_url,
        "scheduled_at": item.scheduled_at.isoformat() if item.scheduled_at else None,
        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
        "error": item.error,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


# ── Rendering ───────────────────────────────────────────────────────────────

def render_queue_email_html(item: EmailQueue) -> str:
    """Render a queue item through the shared branded shell (1:1 with send)."""
    from app.services.newsletter_service import email_shell
    from app.services.token_service import get_base_url

    paragraphs = "".join(
        f'<p style="margin:0 0 18px;color:#e8e8e8;font-size:16px">{html.escape(line.strip())}</p>'
        for line in item.body.splitlines() if line.strip()
    )
    inner = paragraphs or '<p style="margin:0 0 18px;color:#e8e8e8;font-size:16px"></p>'

    # Tracked watch button: /go/{id} logs an email_click, then redirects to the
    # stored video URL (server-side target — no open redirect).
    if item.video_url:
        go_url = f"{get_base_url()}/go/{item.id}"
        inner += (
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:6px 0 18px">'
            f'<tr><td style="border-radius:8px;background:#FFD700">'
            f'<a href="{html.escape(go_url)}" style="display:inline-block;padding:13px 30px;color:#000000;'
            f'font-weight:700;text-decoration:none;font-size:15px">&#9654;&nbsp; Watch the video</a>'
            f"</td></tr></table>"
        )

    return email_shell("New Teaching", item.subject, inner)


# ── CRUD ────────────────────────────────────────────────────────────────────

def create_draft(
    db: Session,
    *,
    subject: str,
    body: str,
    source: str = "manual",
    topic_id: int | None = None,
    video_url: str | None = None,
    dedup: bool = True,
) -> EmailQueue | None:
    """Insert a draft. When dedup=True, skip if a queue row already exists for
    the same (topic_id, source) — prevents auto-draft spam for one topic."""
    subject = (subject or "").strip()[:300]
    body = (body or "").strip()
    if not subject or not body:
        return None
    if video_url and not str(video_url).lower().startswith(("http://", "https://")):
        video_url = None

    if dedup and topic_id is not None:
        exists = (
            db.query(EmailQueue)
            .filter(EmailQueue.topic_id == topic_id, EmailQueue.source == source)
            .first()
        )
        if exists:
            return None

    item = EmailQueue(subject=subject, body=body, source=source, topic_id=topic_id, video_url=video_url)
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info("Email draft queued (id=%s source=%s): %r", item.id, source, subject)
    return item


def list_queue(db: Session) -> list[dict]:
    rows = db.query(EmailQueue).order_by(EmailQueue.created_at.desc()).all()
    return [_serialize(r) for r in rows]


def get_item(db: Session, queue_id: int) -> EmailQueue | None:
    return db.query(EmailQueue).filter(EmailQueue.id == queue_id).first()


def update_draft(db: Session, queue_id: int, *, subject: str | None, body: str | None) -> dict | None:
    item = get_item(db, queue_id)
    if item is None or item.status == "sent":
        return None
    if subject is not None and subject.strip():
        item.subject = subject.strip()[:300]
    if body is not None and body.strip():
        item.body = body.strip()
    db.commit()
    db.refresh(item)
    return _serialize(item)


def delete_item(db: Session, queue_id: int) -> bool:
    item = get_item(db, queue_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


# ── Approval + sending ──────────────────────────────────────────────────────

def approve(db: Session, queue_id: int, *, scheduled_at: datetime | None = None) -> dict | None:
    """Approve a draft. With scheduled_at → the scheduler sends it when due;
    without → send immediately."""
    item = get_item(db, queue_id)
    if item is None or item.status == "sent":
        return None
    item.status = "approved"
    item.error = None
    if scheduled_at is not None:
        # Store naive UTC so SQLite comparisons stay consistent.
        if scheduled_at.tzinfo is not None:
            scheduled_at = scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)
        item.scheduled_at = scheduled_at
        db.commit()
        db.refresh(item)
        return _serialize(item)
    item.scheduled_at = None
    db.commit()
    return send_item(db, queue_id)


def send_item(db: Session, queue_id: int) -> dict | None:
    """Send an approved (or draft — explicit admin 'Send now') email to all
    active subscribers. On failure the item stays approved with the error.

    Duplicate-send safety: the item is claimed with an atomic compare-and-set
    UPDATE (status → 'sending') before any transport happens, so concurrent
    callers (manual send, approve-now, scheduler process_due) can never send
    the same email twice. Same pattern as the drip step claim."""
    from app.services.email_sender_service import send_bulk
    from app.services.email_service import list_emails

    item = get_item(db, queue_id)
    if item is None or item.status == "sent":
        return None

    # Atomic claim: only one caller wins the draft/approved → sending transition.
    claimed = (
        db.query(EmailQueue)
        .filter(EmailQueue.id == queue_id, EmailQueue.status.in_(("draft", "approved")))
        .update({"status": "sending", "sent_at": _naive_utc_now()}, synchronize_session=False)
    )
    db.commit()
    if not claimed:
        return None  # someone else is sending / already sent it
    db.refresh(item)

    def _release(error: str) -> dict:
        item.status = "approved"
        item.sent_at = None
        item.error = error
        db.commit()
        return _serialize(item)

    recipients = list_emails(db)
    if not recipients:
        return _release("No active subscribers to send to.")

    html_body = render_queue_email_html(item)
    try:
        summary = send_bulk(recipients=recipients, subject=item.subject, content=html_body)
    except Exception as exc:  # noqa: BLE001 — keep queue usable on transport errors
        logger.error("Queue send failed (id=%s): %s", queue_id, exc, exc_info=True)
        return _release(f"Send failed: {exc}")

    sent, failed = summary.get("sent", 0), summary.get("failed", 0)
    if sent > 0:
        item.status = "sent"
        item.sent_at = _naive_utc_now()
        item.error = None if failed == 0 else f"{failed} of {len(recipients)} recipients failed."
    else:
        item.status = "approved"
        item.error = f"All {len(recipients)} sends failed."
    db.commit()
    db.refresh(item)
    logger.info("Queue email id=%s sent=%d failed=%d", queue_id, sent, failed)
    result = _serialize(item)
    result["send_summary"] = {"sent": sent, "failed": failed, "recipients": len(recipients)}
    return result


# ── Scheduler hooks ─────────────────────────────────────────────────────────

def process_due(db: Session) -> int:
    """Send approved emails whose scheduled time has arrived. Returns count sent."""
    now = _naive_utc_now()

    # Crash recovery: a 'sending' claim older than 30 min means the server died
    # mid-send — release it back to approved so it can be retried/inspected.
    from datetime import timedelta
    stale_cutoff = now - timedelta(minutes=30)
    stale = (
        db.query(EmailQueue)
        .filter(EmailQueue.status == "sending", EmailQueue.sent_at < stale_cutoff)
        .update(
            {"status": "approved", "sent_at": None, "error": "Send interrupted — released for retry."},
            synchronize_session=False,
        )
    )
    if stale:
        db.commit()
        logger.warning("Released %d stale 'sending' queue item(s).", stale)
    due = (
        db.query(EmailQueue)
        .filter(
            EmailQueue.status == "approved",
            EmailQueue.scheduled_at.isnot(None),
            EmailQueue.scheduled_at <= now,
        )
        .all()
    )
    count = 0
    for item in due:
        result = send_item(db, item.id)
        if result and result.get("status") == "sent":
            count += 1
    return count


def draft_trending_topics(db: Session) -> int:
    """Auto-draft one email per newly-trending public topic (deduped).
    Deterministic template — no AI, never fails on quota."""
    cutoff = _naive_utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    cutoff = cutoff - timedelta(days=7)

    topics = db.query(Topic).filter(Topic.status.in_(("featured", "approved"))).all()
    created = 0
    for t in topics:
        recent = (
            db.query(TopicVote)
            .filter(TopicVote.topic_id == t.id, TopicVote.created_at >= cutoff)
            .count()
        )
        if recent < TRENDING_DRAFT_MIN_7D:
            continue
        subject = f"Everyone is asking about this: {t.title}"
        body = "\n".join([
            f"Something doesn't add up — and you've probably sensed it too.",
            f"\"{t.title}\" is the question our community is voting on more than any other this week.",
            (t.description or "The answer goes deeper than most people have ever been told."),
            "We're preparing the full teaching now. Watch the channel — and if you have a question of your own, just reply to this email. We read every one.",
        ])
        if create_draft(db, subject=subject, body=body, source="trending_topic", topic_id=t.id) is not None:
            created += 1
    if created:
        logger.info("Auto-drafted %d trending-topic email(s).", created)
    return created


# ── Email click tracking (/go/{id}) ─────────────────────────────────────────

def record_email_click(db: Session, item: EmailQueue) -> None:
    """Log an email_click event (feedback loop for topic ranking)."""
    try:
        payload = json.dumps({"queue_id": item.id, "topic_id": item.topic_id})
        db.add(Event(event_name="email_click", data=payload))
        db.commit()
    except Exception:  # noqa: BLE001 — tracking must never break the redirect
        db.rollback()
