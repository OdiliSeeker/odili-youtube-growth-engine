"""
Newsletter send history — persists every dispatch to the DB.
"""

import json
import logging
from sqlalchemy.orm import Session
from app.models.db_models import NewsletterLog

logger = logging.getLogger(__name__)


def log_send(
    db: Session,
    subject: str,
    recipients_total: int,
    sent_count: int,
    failed_count: int,
    triggered_by: str = "manual",
    failures: list[dict] | None = None,
) -> NewsletterLog:
    """Persist a newsletter send result to the log table."""
    entry = NewsletterLog(
        subject=subject,
        recipients_total=recipients_total,
        sent_count=sent_count,
        failed_count=failed_count,
        triggered_by=triggered_by,
        failures_json=json.dumps(failures) if failures else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info(
        "Newsletter logged — id=%d subject=%r sent=%d failed=%d by=%s",
        entry.id, subject, sent_count, failed_count, triggered_by,
    )
    return entry


def get_history(db: Session, limit: int = 20) -> list[dict]:
    """Return the most recent newsletter send records, newest first."""
    rows = (
        db.query(NewsletterLog)
        .order_by(NewsletterLog.sent_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "sent_at": r.sent_at.isoformat(),
            "subject": r.subject,
            "recipients_total": r.recipients_total,
            "sent": r.sent_count,
            "failed": r.failed_count,
            "triggered_by": r.triggered_by,
            "failures": json.loads(r.failures_json) if r.failures_json else [],
        }
        for r in rows
    ]
