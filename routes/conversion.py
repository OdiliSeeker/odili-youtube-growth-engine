"""
Conversion Engine + Reply Engine + Geo Intelligence routes.

ADMIN (x-api-key) — generation is suggestion-only, NOTHING auto-posts/sends:
  POST /replies/generate          — reply pack for a lead or raw comment text
  POST /replies/continue          — follow-up replies for a pasted thread
  POST /conversion/email          — email conversion pack for a topic
  POST /conversion/landing-cta    — landing headline/subheadline/button copy
  POST /conversion/ctr-phrases    — 10 titles / 10 hooks / 10 CTA phrases
  POST /conversion/us-optimize    — US-audience phrasing/keywords/titles
  GET  /ctr/performance           — tracked phrase performance list
  POST /ctr/performance           — save a phrase as "in use"
  PATCH /ctr/performance/{id}     — log clicks/conversions for a phrase
  GET  /analytics/geo             — coarse audience geography summary

PUBLIC:
  GET /geo/hint — the requester's OWN coarse country only (for US phrasing on
                  the landing page). Nothing stored, no params accepted.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.models.db_models import LeadComment, TrackedVideo, WatchlistChannel
from app.services import (
    comment_reply_service,
    conversion_engine,
    ctr_phrase_engine,
    geo_service,
    us_targeting_engine,
)
from app.services.comment_reply_service import ReplyRateLimitError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversion"])


# ── Reply Engine ─────────────────────────────────────────────────────────────

class ReplyRequest(BaseModel):
    lead_id: int | None = None
    comment_text: str | None = Field(default=None, max_length=3000)
    video_title: str = Field(default="", max_length=300)
    channel_name: str = Field(default="", max_length=200)
    regenerate: int = Field(default=0, ge=0, le=1000)  # nonce → fresh variation


@router.post("/replies/generate")
async def generate_replies(
    payload: ReplyRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Reply pack (intent + 3 tones × primary/expansion/CTAs). Never auto-posts."""
    comment_text = (payload.comment_text or "").strip()
    video_title = payload.video_title.strip()
    channel_name = payload.channel_name.strip()
    lead = None
    if payload.lead_id is not None:
        lead = db.get(LeadComment, payload.lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="Lead not found.")
        comment_text = lead.text
        tv = db.query(TrackedVideo).filter(TrackedVideo.video_id == lead.video_id).first()
        if tv:
            video_title = tv.title
        ch = db.query(WatchlistChannel).filter(WatchlistChannel.channel_id == lead.channel_id).first()
        if ch:
            channel_name = ch.title
    if not comment_text:
        raise HTTPException(status_code=400, detail="Provide lead_id or comment_text.")
    try:
        pack = await comment_reply_service.generate_reply_pack(
            comment_text,
            video_title,
            channel_name or "Odili Truth Seeker",
            nonce=payload.regenerate,
        )
    except ReplyRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    return {
        "lead_id": lead.id if lead else None,
        "comment_text": comment_text,
        "video_title": video_title,
        "channel_name": channel_name,
        **pack,
    }


class ContinueRequest(BaseModel):
    thread_text: str = Field(..., min_length=10, max_length=6000)
    channel_name: str = Field(default="", max_length=200)


@router.post("/replies/continue")
async def continue_replies(
    payload: ContinueRequest,
    _: None = Depends(verify_admin),
) -> dict:
    """Conversation Continuation Mode: follow-ups for a pasted reply thread."""
    try:
        return await comment_reply_service.continue_thread(
            payload.thread_text, payload.channel_name or "Odili Truth Seeker"
        )
    except ReplyRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))


# ── Conversion generators ────────────────────────────────────────────────────

class TopicRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=300)


@router.post("/conversion/email")
async def conversion_email(payload: TopicRequest, _: None = Depends(verify_admin)) -> dict:
    return await conversion_engine.generate_email_conversion(payload.topic)


@router.post("/conversion/landing-cta")
async def conversion_landing_cta(payload: TopicRequest, _: None = Depends(verify_admin)) -> dict:
    return await conversion_engine.generate_landing_cta(payload.topic)


@router.post("/conversion/ctr-phrases")
async def conversion_ctr_phrases(payload: TopicRequest, _: None = Depends(verify_admin)) -> dict:
    return await ctr_phrase_engine.generate_ctr_phrases(payload.topic)


@router.post("/conversion/us-optimize")
async def conversion_us_optimize(payload: TopicRequest, _: None = Depends(verify_admin)) -> dict:
    return await us_targeting_engine.optimize_for_us(payload.topic)


# ── CTR performance tracking ─────────────────────────────────────────────────

class PhraseSave(BaseModel):
    phrase: str = Field(..., min_length=2, max_length=500)
    type: str = Field(default="title", max_length=20)


class PhraseResult(BaseModel):
    clicks: int = Field(default=0, ge=0, le=100000)
    conversions: int = Field(default=0, ge=0, le=100000)


@router.get("/ctr/performance")
async def ctr_performance_list(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    return {"items": ctr_phrase_engine.list_performance(db)}


@router.post("/ctr/performance")
async def ctr_performance_save(
    payload: PhraseSave, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    return ctr_phrase_engine.record_phrase(db, phrase=payload.phrase, phrase_type=payload.type)


@router.patch("/ctr/performance/{perf_id}")
async def ctr_performance_log(
    perf_id: int, payload: PhraseResult, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    out = ctr_phrase_engine.log_result(db, perf_id=perf_id, clicks=payload.clicks, conversions=payload.conversions)
    if out is None:
        raise HTTPException(status_code=404, detail="Phrase not found.")
    return out


# ── Geo ──────────────────────────────────────────────────────────────────────

@router.get("/analytics/geo")
async def analytics_geo(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    return geo_service.get_geo_summary(db, days=days)


@router.get("/geo/hint", include_in_schema=False)
async def geo_hint(request: Request) -> dict:
    """PUBLIC: requester's own coarse country (e.g. {"country": "US"}) or null.

    Used by the landing page for light US phrasing. Accepts no parameters,
    stores nothing, and only ever reveals the caller's own coarse location.
    """
    geo = geo_service.get_geo_from_request(request)
    return {"country": geo["country"] if geo else None}
