"""
Lead Discovery Engine — admin API (all endpoints require x-api-key).

Compliant, API-only YouTube lead discovery. NO endpoint here replies to,
comments on, or posts to YouTube — the only actions are watch a channel, scan
public comments, and review (approve/skip) surfaced leads.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import lead_discovery_service as leads
from app.services import youtube_api_service as yt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leads", tags=["Lead Discovery"])


class AddChannelRequest(BaseModel):
    url: str = Field(..., min_length=2, max_length=500)
    category: str = Field(default="general", max_length=60)


class BulkSkipRequest(BaseModel):
    max_score: float = Field(..., ge=0.0, le=1.0)


@router.get("/status")
async def leads_status(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    return leads.status(db)


@router.get("/channels")
async def get_channels(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    return {"channels": leads.list_channels(db)}


@router.post("/channels")
async def add_channel(
    body: AddChannelRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    if not yt.is_configured():
        raise HTTPException(status_code=400, detail="YOUTUBE_API_KEY is not configured.")
    try:
        channel, created = leads.add_channel(db, body.url, body.category)
    except yt.YouTubeNotConfigured:
        raise HTTPException(status_code=400, detail="YOUTUBE_API_KEY is not configured.")
    except yt.YouTubeQuotaError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except yt.YouTubeAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"channel": channel, "created": created}


@router.delete("/channels/{channel_pk}")
async def delete_channel(
    channel_pk: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    if not leads.remove_channel(db, channel_pk):
        raise HTTPException(status_code=404, detail="Channel not found.")
    return {"ok": True}


@router.get("")
async def get_leads(
    status: str = "pending",
    sort: str = "intent",
    channel_id: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    if sort not in ("intent", "newest"):
        raise HTTPException(status_code=422, detail="sort must be 'intent' or 'newest'.")
    return {
        "leads": leads.list_leads(
            db,
            status=status,
            sort=sort,
            channel_id=channel_id or None,
            category=category or None,
        )
    }


@router.post("/scan")
async def run_scan(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    if not yt.is_configured():
        raise HTTPException(status_code=400, detail="YOUTUBE_API_KEY is not configured.")
    summary = leads.scan_all(db)
    return summary


@router.post("/{lead_id}/approve")
async def approve(lead_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    result = await leads.approve_lead(db, lead_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return result


@router.post("/{lead_id}/skip")
async def skip(lead_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    if not leads.skip_lead(db, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found.")
    return {"ok": True}


@router.get("/bulk-skip/count")
async def bulk_skip_count(
    max_score: float,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    if not (0.0 <= max_score <= 1.0):
        raise HTTPException(status_code=422, detail="max_score must be between 0 and 1.")
    return leads.count_bulk_skip_leads(db, max_score)


@router.post("/bulk-skip")
async def bulk_skip(
    body: BulkSkipRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    skipped = leads.bulk_skip_leads(db, body.max_score)
    return {"ok": True, "skipped": skipped}


@router.post("/bulk-skip/undo")
async def bulk_skip_undo(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    restored = leads.undo_bulk_skip(db)
    return {"ok": True, "restored": restored}
