"""
Funnel analytics routes.

  POST /track                  — PUBLIC: record a behavior event (allow-listed)
  GET  /analytics/summary      — ADMIN:  funnel metrics for the dashboard
  GET  /analytics/best-headline — PUBLIC: the auto-selected best headline (or null)
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import analytics_service, geo_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])


class TrackPayload(BaseModel):
    event: str = Field(..., max_length=60)
    data: dict | None = None


@router.post("/track", include_in_schema=False)
async def track_event(
    payload: TrackPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """Record a funnel behavior event. Unknown event names are ignored (ok=False)."""
    ok = analytics_service.record_event(db, event_name=payload.event, data=payload.data)
    # Privacy-safe coarse geo (country/region only, raw IP never stored) —
    # looked up AFTER the response is sent so the funnel never slows down.
    if ok and payload.event == "page_view":
        ip = geo_service._client_ip(request)
        background_tasks.add_task(geo_service.record_visit_background, ip, "/")
    return {"ok": ok}


@router.get("/analytics/summary")
async def analytics_summary(
    days: int | None = Query(default=None, ge=1, le=365),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Funnel metrics. Optional ``?days=N`` limits the window (e.g. last 7 days)."""
    return analytics_service.get_summary(db, days=days)


@router.get("/analytics/best-headline")
async def best_headline(db: Session = Depends(get_db)) -> dict:
    """The auto-selected best-converting headline, or null to fall back to A/B."""
    return {"best_headline": analytics_service.get_best_headline(db)}
