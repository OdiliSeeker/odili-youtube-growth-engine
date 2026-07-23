"""
The Lead Evangelist — admin-only routes for compliant multi-platform outreach.

  GET   /evangelist/playbook        — core messages + platform etiquette + pace caps
  POST  /evangelist/personalize     — personalized non-spammy message for a target
  GET   /evangelist/outreach        — outreach log (optionally per platform)
  POST  /evangelist/outreach        — log a manual outreach action
  PATCH /evangelist/outreach/{id}   — mark responded / subscribed
  GET   /evangelist/dashboard       — funnel + signup attribution + pace status

NOTHING auto-posts to any platform — the admin copies and posts as a human.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import lead_evangelist_service

router = APIRouter(tags=["lead-evangelist"])


class PersonalizeRequest(BaseModel):
    platform: str = Field(min_length=1, max_length=20)
    message_type: str = Field(default="", max_length=40)
    context: str = Field(default="", max_length=1000)


class OutreachRequest(BaseModel):
    platform: str = Field(min_length=1, max_length=20)
    target: str = Field(default="", max_length=500)
    message_type: str = Field(default="universal", max_length=40)
    message_text: str = Field(default="", max_length=5000)
    notes: str = Field(default="", max_length=1000)


class StatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class AutoRequest(BaseModel):
    enabled: bool


@router.get("/evangelist/playbook")
async def playbook(_: None = Depends(verify_admin)) -> dict:
    """The Lead Evangelist playbook: messages, platforms, etiquette, pace caps."""
    return lead_evangelist_service.get_playbook()


@router.post("/evangelist/personalize")
async def personalize(
    payload: PersonalizeRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """A personalized, platform-fit message with a tracked link + spam-safety info."""
    return await lead_evangelist_service.personalize(
        db,
        platform=payload.platform.strip().lower(),
        message_type=payload.message_type.strip().lower(),
        context=payload.context,
    )


@router.get("/evangelist/outreach")
async def list_outreach(
    platform: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """The outreach log, newest first (optionally one platform)."""
    return lead_evangelist_service.list_outreach(db, platform=(platform or "").strip().lower() or None)


@router.post("/evangelist/outreach")
async def log_outreach(
    payload: OutreachRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Log one manual outreach action (after YOU posted it as a human)."""
    row = lead_evangelist_service.log_outreach(
        db,
        platform=payload.platform.strip().lower(),
        target=payload.target,
        message_type=payload.message_type.strip().lower(),
        message_text=payload.message_text,
        notes=payload.notes,
    )
    return {"ok": True, "id": row.id}


@router.patch("/evangelist/outreach/{outreach_id}")
async def update_outreach(
    outreach_id: int,
    payload: StatusRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Update an outreach row's status: logged | responded | subscribed."""
    row = lead_evangelist_service.update_status(db, outreach_id, payload.status.strip().lower())
    if row is None:
        raise HTTPException(status_code=404, detail="Outreach entry not found or invalid status.")
    return {"ok": True, "id": row.id, "status": row.status}


@router.get("/evangelist/auto")
async def auto_status(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    """Auto-Cadence status: enabled, best hour, last/next post, next platform."""
    return lead_evangelist_service.auto_status(db)


@router.put("/evangelist/auto")
async def auto_toggle(
    payload: AutoRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Turn the every-2-days Auto-Cadence on or off."""
    return lead_evangelist_service.set_auto_enabled(db, payload.enabled)


@router.get("/evangelist/dashboard")
async def dashboard(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    """Per-platform outreach funnel, signup attribution, and pace status."""
    return lead_evangelist_service.dashboard(db)
