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

# ---------------------------------------------------------------------------
# Silent-failure alerting
#
# Each scheduler job's exceptions are only written to the server log, so a
# persistent failure (SendGrid outage, bad AI response) could go unnoticed for
# days. Track consecutive failures per job in memory (the scheduler only lives
# while the server runs, so in-process state is exactly the right scope) and
# email the admin ONCE per incident when a job fails repeatedly. A successful
# run resets the counter and the alert flag so a future incident notifies
# again. All alerting is fail-silent — it never breaks the job wrapper.
# ---------------------------------------------------------------------------

# Consecutive failures required before alerting, tuned to each job's cadence
# so infrequent jobs (the newsletter fires 3x/week) don't take a week to
# surface while frequent jobs (drip, every 30 min) don't alert on one blip.
_ALERT_THRESHOLDS = {
    "weekly_newsletter": 1,   # fires 3x/week — one failure is already a big deal
    "drip_sequence": 3,       # every 30 min — alert after ~1.5h of failures
    "email_queue": 2,         # hourly — alert after ~2h of failures
    "lead_discovery": 2,      # every 6h — alert after ~12h of failures
    "evangelist_auto": 3,     # hourly check — alert after ~3h of failures
}
_DEFAULT_ALERT_THRESHOLD = 2

_JOB_LABELS = {
    "weekly_newsletter": "Weekly newsletter send",
    "drip_sequence": "Subscriber drip sequence",
    "email_queue": "Email queue processor",
    "lead_discovery": "Lead Discovery scan",
    "evangelist_auto": "Lead Evangelist Auto-Cadence",
}

# job_id -> {"failures": int, "alerted": bool}
_job_health: dict = {}


def _record_job_success(job_id: str) -> None:
    """Reset the failure streak after a clean run. If an alert had been sent
    for this incident, email a short recovery notice so the admin knows it's
    resolved — and re-arm alerting for the next incident."""
    state = _job_health.get(job_id)
    if not state:
        return
    was_alerted = state.get("alerted", False)
    _job_health[job_id] = {"failures": 0, "alerted": False}
    if was_alerted:
        label = _JOB_LABELS.get(job_id, job_id)
        try:
            from app.services.email_sender_service import send_admin_notice

            send_admin_notice(
                f"✅ Odili background job recovered — {label}",
                f"The background job \"{label}\" completed successfully again "
                "after the earlier failures. No action needed — alerting for "
                "this job has been re-armed.",
            )
        except Exception as exc:  # noqa: BLE001 — never break the job on a notice
            logger.warning("Recovery notice for %s failed to send: %s", job_id, exc)


def _record_job_failure(job_id: str, exc: Exception) -> None:
    """Count a failed run and email the admin once per incident when the job
    has failed repeatedly. Fail-silent: notice errors are only logged."""
    state = _job_health.setdefault(job_id, {"failures": 0, "alerted": False})
    state["failures"] += 1
    threshold = _ALERT_THRESHOLDS.get(job_id, _DEFAULT_ALERT_THRESHOLD)
    if state["alerted"] or state["failures"] < threshold:
        return
    label = _JOB_LABELS.get(job_id, job_id)
    try:
        from app.services.email_sender_service import send_admin_notice

        body = "\n".join([
            f"The background job \"{label}\" has failed "
            f"{state['failures']} time(s) in a row.",
            "",
            f"Latest error: {type(exc).__name__}: {exc}",
            "",
            "The job keeps retrying on its normal schedule; you'll get a "
            "recovery email when it succeeds again. Until then, check the "
            "server logs for the full traceback (common causes: SendGrid "
            "outage or misconfigured sender, OpenAI quota/billing, database "
            "issues).",
            "",
            "This notice is sent once per incident — it won't repeat on "
            "every failed run.",
        ])
        result = send_admin_notice(
            f"🚨 Odili background job failing — {label}", body
        )
        if result and result.success:
            state["alerted"] = True
            logger.info("Admin failure notice sent for job %s.", job_id)
        else:
            logger.warning(
                "Admin failure notice for %s not sent: %s",
                job_id,
                (result.error if result else "no result"),
            )
    except Exception as notice_exc:  # noqa: BLE001 — never break the job wrapper
        logger.warning(
            "Admin failure notice for %s failed to send: %s", job_id, notice_exc
        )


def _run_drip_job() -> None:
    """Advance the automated subscriber drip sequence (runs every 30 minutes)."""
    from app.services.drip_service import process_due_drips
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        process_due_drips(db)
        _record_job_success("drip_sequence")
    except Exception as exc:
        logger.error("Drip job failed: %s", exc, exc_info=True)
        _record_job_failure("drip_sequence", exc)
    finally:
        db.close()


def _run_email_queue_job() -> None:
    """Send due scheduled queue emails + auto-draft trending topics (hourly)."""
    from app.services.email_queue_service import process_due, draft_trending_topics
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        sent = process_due(db)
        drafted = draft_trending_topics(db)
        if sent or drafted:
            logger.info("Email queue job: sent=%d auto-drafted=%d", sent, drafted)
        _record_job_success("email_queue")
    except Exception as exc:
        logger.error("Email queue job failed: %s", exc, exc_info=True)
        _record_job_failure("email_queue", exc)
    finally:
        db.close()


def _run_lead_discovery_job() -> None:
    """Poll watched YouTube channels for new comment leads (every 6 hours).

    Quota-safe and read-only. Skips entirely when YOUTUBE_API_KEY is unset.
    """
    from app.services import youtube_api_service as yt
    from app.services.lead_discovery_service import scan_all
    from app.db import SessionLocal

    if not yt.is_configured():
        return
    db = SessionLocal()
    try:
        summary = scan_all(db)
        if summary.get("leads_found") or summary.get("new_videos"):
            logger.info("Lead discovery scan: %s", summary)
        _record_job_success("lead_discovery")
    except Exception as exc:
        logger.error("Lead discovery job failed: %s", exc, exc_info=True)
        _record_job_failure("lead_discovery", exc)
    finally:
        db.close()


def _run_evangelist_auto_job() -> None:
    """Lead Evangelist Auto-Cadence: every 2 days, at the audience's best hour,
    prepare ONE personalized outreach post and email it to the admin to paste.
    Checks hourly; the service decides whether a post is actually due.
    NEVER posts to any platform itself — that would be bannable bot behavior."""
    from app.services.lead_evangelist_service import run_auto_cadence
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        result = run_auto_cadence(db)
        if result.get("prepared"):
            logger.info("Evangelist Auto-Cadence: %s", result)
        _record_job_success("evangelist_auto")
    except Exception as exc:
        logger.error("Evangelist Auto-Cadence job failed: %s", exc, exc_info=True)
        _record_job_failure("evangelist_auto", exc)
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
            _record_job_success("weekly_newsletter")
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
        _record_job_success("weekly_newsletter")
    except Exception as exc:
        logger.error("Scheduled newsletter job failed: %s", exc, exc_info=True)
        _record_job_failure("weekly_newsletter", exc)
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
    # Email queue: sends due scheduled emails + auto-drafts trending topics.
    _scheduler.add_job(
        _run_email_queue_job,
        trigger=IntervalTrigger(minutes=60, timezone="UTC"),
        id="email_queue",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Lead Discovery: poll watched YouTube channels for new comment leads.
    _scheduler.add_job(
        _run_lead_discovery_job,
        trigger=IntervalTrigger(hours=6, timezone="UTC"),
        id="lead_discovery",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Lead Evangelist Auto-Cadence: hourly check, fires at most every 2 days.
    _scheduler.add_job(
        _run_evangelist_auto_job,
        trigger=CronTrigger(minute=10, timezone="UTC"),  # :10 every hour
        id="evangelist_auto",
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
