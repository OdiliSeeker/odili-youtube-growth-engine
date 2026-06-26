"""
APScheduler integration — automatically sends the weekly newsletter
on Sundays, Wednesdays, and Fridays at 09:00 UTC.

The scheduler is started/stopped via FastAPI's lifespan context manager.
"""

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")


def _run_drip_job() -> None:
    """Advance the automated subscriber drip sequence (runs every 30 minutes)."""
    from app.services.drip_service import process_due_drips
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        process_due_drips(db)
    except Exception as exc:
        logger.error("Drip job failed: %s", exc, exc_info=True)
    finally:
        db.close()


def _run_newsletter_job() -> None:
    """
    Synchronous wrapper that runs the async newsletter dispatch
    in a new event loop (APScheduler runs in a thread).
    """
    from app.services.newsletter_service import generate_newsletter_content, render_newsletter_html
    from app.services.email_sender_service import send_bulk
    from app.services.newsletter_log_service import log_send
    from app.db import SessionLocal

    logger.info("Scheduled newsletter job triggered.")
    db = SessionLocal()
    try:
        from app.services.email_service import list_emails
        recipients = list_emails(db)
        if not recipients:
            logger.info("Scheduler: no active subscribers — skipping send.")
            return

        content = asyncio.run(generate_newsletter_content())
        html = render_newsletter_html(content)
        subject = content["subject"]

        summary = send_bulk(recipients=recipients, subject=subject, content=html)
        log_send(
            db=db,
            subject=subject,
            recipients_total=len(recipients),
            sent_count=summary["sent"],
            failed_count=summary["failed"],
            triggered_by="scheduler",
            failures=summary.get("failures", []),
        )

        logger.info(
            "Scheduler newsletter sent — sent=%d failed=%d subject=%r",
            summary["sent"], summary["failed"], subject,
        )
    except Exception as exc:
        logger.error("Scheduled newsletter job failed: %s", exc, exc_info=True)
    finally:
        db.close()


def start_scheduler() -> None:
    """Start the background scheduler. Called once at server startup."""
    # Sun=0, Wed=3, Fri=5 in APScheduler's day_of_week numbering
    _scheduler.add_job(
        _run_newsletter_job,
        trigger=CronTrigger(day_of_week="sun,wed,fri", hour=9, minute=0, timezone="UTC"),
        id="weekly_newsletter",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1 hour late if server was down
    )
    # Automated subscriber drip sequence — checks for due emails every 30 minutes.
    _scheduler.add_job(
        _run_drip_job,
        trigger=IntervalTrigger(minutes=30, timezone="UTC"),
        id="drip_sequence",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info("Newsletter scheduler started — fires Sun/Wed/Fri at 09:00 UTC.")
    logger.info("Drip-sequence job started — checks every 30 minutes.")
    logger.warning(
        "Automated drip emails only fire while the server is running. Reliable "
        "delivery requires an always-on deployment (Reserved VM), NOT a "
        "scale-to-zero one."
    )


def stop_scheduler() -> None:
    """Gracefully stop the scheduler. Called on server shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Newsletter scheduler stopped.")
