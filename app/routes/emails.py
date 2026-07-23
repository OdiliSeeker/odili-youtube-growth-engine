import csv
import io
import logging
from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from app.dependencies.auth import verify_admin
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import Subscriber
from app.models.schemas import EmailRequest, EmailListResponse, SubscribeRequest
from app.services.email_service import add_email, remove_email, list_emails, email_count
from app.services.scheduler_service import should_send_emails, next_send_day

logger = logging.getLogger(__name__)
router = APIRouter()


def _start_drip(email: str) -> None:
    """Fire-and-forget: kick off the automated drip sequence (sends email 1)."""
    from app.services.drip_service import start_drip
    start_drip(email)


def _register_subscriber(db: Session, email: str, interest: str | None) -> bool:
    """
    Add (or reactivate) a subscriber and record the topic interest they arrived
    with. Returns True if newly added/reactivated, False if already active.
    """
    added = add_email(db=db, email=email)
    interest = (interest or "").strip()[:120] or None
    if interest:
        row = db.query(Subscriber).filter(Subscriber.email == email.strip().lower()).first()
        if row is not None:
            row.interest = interest
            db.commit()
    return added

_MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/subscribe", status_code=201, tags=["Email List"])
async def subscribe_public(
    request: SubscribeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """
    Public funnel subscribe endpoint. Records the visitor's topic interest (if
    they arrived via a topic button) and starts the automated 5-email drip
    sequence (email 1 sends immediately).
    """
    email = str(request.email)
    added = _register_subscriber(db=db, email=email, interest=request.interest)
    # Tag the subscriber for segmentation (new-lead / voter / contributor + topic).
    # Applied even for existing subscribers so a returning visitor who votes or
    # submits a topic still earns the funnel tag — tags are idempotent.
    from app.services import tag_service
    tag_service.apply_signup_tags(
        db, email=email, source=request.source, interest=request.interest
    )
    if not added:
        raise HTTPException(status_code=409, detail="Email already subscribed.")
    background_tasks.add_task(_start_drip, email)
    return {"message": "Subscribed successfully.", "email": email}


@router.post("/emails", status_code=201, tags=["Email List"])
async def subscribe(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """Add an email address to the mailing list (or reactivate an unsubscribed one). Starts the drip sequence."""
    added = add_email(db=db, email=str(request.email))
    if not added:
        raise HTTPException(status_code=409, detail="Email already subscribed.")
    background_tasks.add_task(_start_drip, str(request.email))
    return {"message": "Subscribed successfully.", "email": str(request.email)}


@router.post("/subscribers/import", tags=["Email List"])
async def import_subscribers(
    file: UploadFile = File(..., description="CSV file. Must contain an 'email' column or a single column of addresses."),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    Bulk-import email subscribers from a CSV file.

    Accepted CSV formats:
    - Single column (no header): one email per row
    - Multi-column with an 'email' header column (case-insensitive)

    Returns a summary: imported, skipped (already subscribed), invalid, and failed rows.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    raw = await file.read()
    if len(raw) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5 MB.")

    text = raw.decode("utf-8-sig").strip()  # utf-8-sig strips Excel BOM
    if not text:
        raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")

    results = {"imported": 0, "skipped": 0, "invalid": [], "failed": []}

    reader = csv.DictReader(io.StringIO(text))

    # Detect format: if there's an 'email' column use it; otherwise treat first column as email
    fieldnames = reader.fieldnames or []
    email_col = next(
        (f for f in fieldnames if f.strip().lower() == "email"),
        None,
    )

    # If no header found at all, re-read as plain list (one email per line)
    if not fieldnames:
        plain_emails = [line.strip() for line in text.splitlines() if line.strip()]
        rows = [{"_email": e} for e in plain_emails]
        email_col = "_email"
    else:
        rows = list(reader)
        if email_col is None:
            # Use first column value
            first_col = fieldnames[0]
            rows = [{**row, "_email": row.get(first_col, "")} for row in rows]
            email_col = "_email"

    for i, row in enumerate(rows, start=1):
        raw_email = (row.get(email_col) or "").strip()
        if not raw_email:
            results["invalid"].append({"row": i, "value": raw_email, "reason": "empty"})
            continue

        # Validate email format
        try:
            validated = validate_email(raw_email, check_deliverability=False)
            clean = validated.normalized
        except EmailNotValidError as exc:
            results["invalid"].append({"row": i, "value": raw_email, "reason": str(exc)})
            continue

        # Insert into DB
        try:
            added = add_email(db=db, email=clean)
            if added:
                results["imported"] += 1
            else:
                results["skipped"] += 1
        except Exception as exc:
            logger.error("Failed to import row %d (%s): %s", i, clean, exc)
            results["failed"].append({"row": i, "email": clean, "reason": str(exc)})

    logger.info(
        "CSV import complete — imported=%d skipped=%d invalid=%d failed=%d",
        results["imported"], results["skipped"],
        len(results["invalid"]), len(results["failed"]),
    )

    return {
        "status": "complete",
        "imported": results["imported"],
        "skipped_already_subscribed": results["skipped"],
        "invalid_rows": len(results["invalid"]),
        "failed_rows": len(results["failed"]),
        "details": {
            "invalid": results["invalid"],
            "failed": results["failed"],
        },
    }


@router.delete("/emails/{email}", tags=["Email List"])
async def unsubscribe(email: str, db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    """Remove an email address from the mailing list (soft-delete). Requires admin key."""
    removed = remove_email(db=db, email=email)
    if not removed:
        raise HTTPException(status_code=404, detail="Email not found or already unsubscribed.")
    return {"message": "Unsubscribed successfully.", "email": email}


@router.get("/emails", response_model=EmailListResponse, tags=["Email List"])
async def get_emails(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> EmailListResponse:
    """Return all active subscriber email addresses. Requires admin key."""
    return EmailListResponse(emails=list_emails(db=db), count=email_count(db=db))


@router.get("/emails/scheduler", tags=["Email List"])
async def scheduler_status() -> dict:
    """Check whether emails should be sent today (Sunday, Wednesday, or Friday)."""
    send_today = should_send_emails()
    return {
        "send_today": send_today,
        "next_send_day": next_send_day(),
        "message": "Emails should be sent today." if send_today else "No send scheduled for today.",
    }


@router.get("/subscribers/export", tags=["Email List"])
async def export_subscribers(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> StreamingResponse:
    """
    Download all active subscribers as a CSV file.

    Returns a file named ``subscribers.csv`` with a single ``email`` column.
    """
    emails = list_emails(db=db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email"])
    for address in emails:
        writer.writerow([address])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=subscribers.csv"},
    )
