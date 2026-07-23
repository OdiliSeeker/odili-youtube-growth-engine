"""
Email queue routes — auto-compose + approval + send (spec PART 2).

    GET    /email-queue               list queue (admin)
    PATCH  /email-queue/{id}          edit subject/body (admin)
    POST   /email-queue/{id}/approve  approve: send now or schedule (admin)
    POST   /email-queue/{id}/send     explicit send now (admin)
    GET    /email-queue/{id}/preview  rendered HTML preview (admin)
    DELETE /email-queue/{id}          delete (admin)
    GET    /go/{id}                   PUBLIC: tracked redirect from email → video
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import email_queue_service

router = APIRouter(tags=["Email Queue"])

YOUTUBE_FALLBACK = "https://www.youtube.com/@odilitheseekeroftruth"


class QueueEditIn(BaseModel):
    subject: str | None = None
    body: str | None = None


class QueueApproveIn(BaseModel):
    scheduled_at: datetime | None = None  # omit → send immediately


class QueueCreateIn(BaseModel):
    subject: str
    body: str
    video_url: str | None = None


@router.get("/email-queue")
async def list_email_queue(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    items = email_queue_service.list_queue(db)
    return {"count": len(items), "items": items}


@router.post("/email-queue", status_code=201)
async def create_queue_draft(
    payload: QueueCreateIn, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    item = email_queue_service.create_draft(
        db, subject=payload.subject, body=payload.body,
        source="manual", video_url=payload.video_url, dedup=False,
    )
    if item is None:
        raise HTTPException(status_code=400, detail="Subject and body are required.")
    return {"message": "Draft created.", "id": item.id}


@router.patch("/email-queue/{queue_id}")
async def edit_queue_item(
    queue_id: int, payload: QueueEditIn, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    result = email_queue_service.update_draft(db, queue_id, subject=payload.subject, body=payload.body)
    if result is None:
        raise HTTPException(status_code=404, detail="Queue item not found or already sent.")
    return result


@router.post("/email-queue/{queue_id}/approve")
async def approve_queue_item(
    queue_id: int, payload: QueueApproveIn, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    result = email_queue_service.approve(db, queue_id, scheduled_at=payload.scheduled_at)
    if result is None:
        raise HTTPException(status_code=404, detail="Queue item not found or already sent.")
    return result


@router.post("/email-queue/{queue_id}/send")
async def send_queue_item(
    queue_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    result = email_queue_service.send_item(db, queue_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Queue item not found or already sent.")
    return result


@router.get("/email-queue/{queue_id}/preview", response_class=HTMLResponse)
async def preview_queue_item(
    queue_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> HTMLResponse:
    item = email_queue_service.get_item(db, queue_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Queue item not found.")
    return HTMLResponse(email_queue_service.render_queue_email_html(item))


@router.delete("/email-queue/{queue_id}")
async def delete_queue_item(
    queue_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    if not email_queue_service.delete_item(db, queue_id):
        raise HTTPException(status_code=404, detail="Queue item not found.")
    return {"message": "Deleted."}


@router.get("/go/{queue_id}", include_in_schema=False)
async def email_click_redirect(queue_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    """PUBLIC tracked redirect: logs an email_click, then sends the reader to
    the email's stored video URL (server-side target — no open redirect)."""
    item = email_queue_service.get_item(db, queue_id)
    target = YOUTUBE_FALLBACK
    if item is not None:
        email_queue_service.record_email_click(db, item)
        if item.video_url and str(item.video_url).lower().startswith(("http://", "https://")):
            target = item.video_url
    return RedirectResponse(url=target, status_code=302)
