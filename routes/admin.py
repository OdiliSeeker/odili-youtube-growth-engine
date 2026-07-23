import logging
import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services.email_service import email_count
from app.services.scheduler_service import should_send_emails, next_send_day
from app.services.newsletter_log_service import get_history
from app.services import auto_scheduler

logger = logging.getLogger(__name__)
router = APIRouter()

APP_VERSION = "1.3.0"


@router.get("/admin/status", tags=["Admin"])
async def admin_status(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    """
    System health and status overview:
    - Active subscriber count
    - Scheduler state
    - Whether today is a send day
    - Most recent newsletter send
    """
    history = get_history(db=db, limit=1)
    last = history[0] if history else None

    return {
        "status": "ok",
        "version": APP_VERSION,
        "subscriber_count": email_count(db=db),
        "scheduler_running": auto_scheduler._scheduler.running,
        "send_today": should_send_emails(),
        "next_send_day": next_send_day(),
        "last_newsletter": last,
        "youtube_channel_url": os.getenv("YOUTUBE_CHANNEL_URL", ""),
    }
