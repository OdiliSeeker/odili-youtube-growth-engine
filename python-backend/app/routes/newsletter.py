import logging
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services.scheduler_service import should_send_emails
from app.services.email_service import list_emails
from app.services.newsletter_service import (
    generate_newsletter_content,
    render_newsletter_html,
    render_newsletter_text,
    render_custom_html,
    render_custom_text,
    generate_weekly_plan_content,
)
from app.services.email_sender_service import send_bulk
from app.services.newsletter_log_service import log_send, get_history
from app.services.ai_service import AIQuotaError, AIAuthError, AIConnectionError, AIServiceError

logger = logging.getLogger(__name__)
router = APIRouter()


class CustomNewsletterRequest(BaseModel):
    subject: str
    body: str

    @field_validator("subject")
    @classmethod
    def subject_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("subject must not be empty")
        return v.strip()

    @field_validator("body")
    @classmethod
    def body_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("body must not be empty")
        return v.strip()


class WeeklyPlanRequest(BaseModel):
    topics: list[str] = Field(default_factory=list)


def _handle_ai_error(exc: Exception) -> None:
    if isinstance(exc, AIQuotaError):
        raise HTTPException(status_code=402, detail={
            "error": "openai_quota_exceeded",
            "message": str(exc),
            "action": "Add credits at https://platform.openai.com/account/billing",
        })
    if isinstance(exc, AIAuthError):
        raise HTTPException(status_code=401, detail={"error": "openai_auth_error", "message": str(exc)})
    if isinstance(exc, AIConnectionError):
        raise HTTPException(status_code=503, detail={"error": "openai_unreachable", "message": str(exc)})
    raise HTTPException(status_code=502, detail={"error": "openai_error", "message": str(exc)})


@router.post("/send-newsletter", tags=["Newsletter"])
async def send_newsletter(
    force: bool = Query(default=False, description="Bypass scheduler check — for testing only."),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    Generate and send the weekly Catholic insight newsletter to all active subscribers.

    - Blocked on non-send days (Sun/Wed/Fri) unless `?force=true`.
    - Generates AI content via GPT-4o.
    - Delivers via SendGrid to every active subscriber.
    - Logs every send to the newsletter_log table.
    """
    if not force and not should_send_emails():
        return {
            "status": "skipped",
            "reason": "not scheduled day",
            "detail": "Newsletters are sent on Sundays, Wednesdays, and Fridays only. Pass ?force=true to override.",
        }

    recipients = list_emails(db=db)
    if not recipients:
        return {
            "status": "skipped",
            "reason": "no subscribers",
            "detail": "No active subscribers. Add addresses via POST /emails first.",
        }

    try:
        content = await generate_newsletter_content()
    except (AIQuotaError, AIAuthError, AIConnectionError, AIServiceError) as exc:
        logger.error("Newsletter AI generation failed: %s", exc)
        _handle_ai_error(exc)
    except ValueError as exc:
        logger.error("Newsletter content parse failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Content generation failed: {exc}") from exc

    html_body = render_newsletter_html(content)
    text_body = render_newsletter_text(content)
    subject = content["subject"]

    logger.info("Dispatching newsletter to %d subscribers — subject: %r", len(recipients), subject)
    summary = send_bulk(recipients=recipients, subject=subject, content=html_body, text_content=text_body)

    log_send(
        db=db,
        subject=subject,
        recipients_total=len(recipients),
        sent_count=summary["sent"],
        failed_count=summary["failed"],
        triggered_by="manual",
        failures=summary.get("failures", []),
    )

    status = "success" if summary["failed"] == 0 else "partial"
    response: dict = {
        "status": status,
        "subject": subject,
        "recipients_total": len(recipients),
        "sent": summary["sent"],
        "failed": summary["failed"],
    }
    if summary["failures"]:
        response["failures"] = summary["failures"]

    logger.info(
        "Newsletter dispatch complete — sent=%d failed=%d subject=%r",
        summary["sent"], summary["failed"], subject,
    )
    return response


@router.post("/send-newsletter/custom", tags=["Newsletter"])
async def send_custom_newsletter(
    payload: CustomNewsletterRequest,
    force: bool = Query(default=False, description="Bypass scheduler check — for testing only."),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    Send a hand-written newsletter to all active subscribers — no AI required.

    Provide your own `subject` and `body` (plain text, one paragraph per line).
    The body is wrapped in the same branded HTML template as AI-generated newsletters.
    """
    if not force and not should_send_emails():
        return {
            "status": "skipped",
            "reason": "not scheduled day",
            "detail": "Newsletters are sent on Sundays, Wednesdays, and Fridays only. Pass ?force=true to override.",
        }

    recipients = list_emails(db=db)
    if not recipients:
        return {
            "status": "skipped",
            "reason": "no subscribers",
            "detail": "No active subscribers. Add addresses via POST /emails first.",
        }

    html_body = render_custom_html(subject=payload.subject, body=payload.body)
    text_body = render_custom_text(subject=payload.subject, body=payload.body)

    logger.info(
        "Dispatching custom newsletter to %d subscribers — subject: %r",
        len(recipients), payload.subject,
    )
    summary = send_bulk(recipients=recipients, subject=payload.subject, content=html_body, text_content=text_body)

    log_send(
        db=db,
        subject=payload.subject,
        recipients_total=len(recipients),
        sent_count=summary["sent"],
        failed_count=summary["failed"],
        triggered_by="manual_custom",
        failures=summary.get("failures", []),
    )

    status = "success" if summary["failed"] == 0 else "partial"
    response: dict = {
        "status": status,
        "subject": payload.subject,
        "recipients_total": len(recipients),
        "sent": summary["sent"],
        "failed": summary["failed"],
    }
    if summary["failures"]:
        response["failures"] = summary["failures"]

    logger.info(
        "Custom newsletter dispatch complete — sent=%d failed=%d subject=%r",
        summary["sent"], summary["failed"], payload.subject,
    )
    return response


@router.post("/send-newsletter/custom/preview", tags=["Newsletter"])
async def preview_custom_newsletter(
    payload: CustomNewsletterRequest,
    _: None = Depends(verify_admin),
) -> dict:
    """
    Render a custom newsletter to HTML without sending it.
    Use this to review the branded output before committing to a send.
    """
    html = render_custom_html(subject=payload.subject, body=payload.body)
    text = render_custom_text(subject=payload.subject, body=payload.body)
    return {"subject": payload.subject, "html": html, "text": text}


@router.post("/newsletter/weekly/generate", tags=["Newsletter"])
async def generate_weekly_plan(
    payload: WeeklyPlanRequest = Body(default=WeeklyPlanRequest()),
    _: None = Depends(verify_admin),
) -> dict:
    """
    Generate a "Your Weekly Catholic Content Plan" email body (Step 4).

    Returns ``{subject, body}`` ready to drop into the newsletter composer.
    Optionally seed the plan with trending `topics`.
    """
    try:
        plan = await generate_weekly_plan_content(topics=payload.topics)
    except (AIQuotaError, AIAuthError, AIConnectionError, AIServiceError) as exc:
        _handle_ai_error(exc)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Weekly plan generation failed: {exc}") from exc

    return plan


@router.get("/newsletter/history", tags=["Newsletter"])
async def newsletter_history(
    limit: int = Query(default=20, ge=1, le=100, description="Max records to return."),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Return the most recent newsletter send records, newest first. Admin only."""
    history = get_history(db=db, limit=limit)
    return {"count": len(history), "history": history}


@router.get("/send-newsletter/preview", tags=["Newsletter"])
async def preview_newsletter(_: None = Depends(verify_admin)) -> dict:
    """Generate and return newsletter HTML without sending — useful for review before a send. Admin only."""
    try:
        content = await generate_newsletter_content()
    except (AIQuotaError, AIAuthError, AIConnectionError, AIServiceError) as exc:
        _handle_ai_error(exc)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Content generation failed: {exc}") from exc

    return {
        "subject": content["subject"],
        "greeting": content["greeting"],
        "insights": content["insights"],
        "cta": content["cta"],
        "html": render_newsletter_html(content),
    }
