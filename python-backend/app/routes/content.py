"""
Traffic Engine routes — multi-platform content generation + distribution.

All endpoints are admin-only (require the `x-api-key` header), consistent with
the public/admin split: every content/AI tool lives behind auth. None of these
auto-post anywhere — they produce copy-ready text for manual distribution.

  POST /content/generate-weekly-posts  — Sunday/Wednesday/Friday posts + image prompt
  GET  /content/facebook-pack          — ready post + authorised groups to share into
  POST /content/generate-shorts        — 3-5 Shorts packages
  POST /content/generate-hooks         — 5 viral hooks for a topic
  POST /content/repurpose              — one topic/script → Shorts + FB + TikTok + YT + email
  GET  /content/posting-plan           — static weekly posting strategy
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import content_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/content", tags=["content"])


class ShortsRequest(BaseModel):
    video_topic: str | None = None
    script: str | None = None
    count: int | None = None


class HooksRequest(BaseModel):
    topic: str


class RepurposeRequest(BaseModel):
    topic: str | None = None
    script: str | None = None


def _subject(*candidates: str | None) -> str:
    for c in candidates:
        if c and c.strip():
            return c.strip()
    return ""


@router.post("/generate-weekly-posts")
async def generate_weekly_posts(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    return await content_service.generate_weekly_posts(db)


@router.get("/facebook-pack")
async def facebook_pack(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    return content_service.facebook_pack(db)


@router.post("/generate-shorts")
async def generate_shorts(
    body: ShortsRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    subject = _subject(body.video_topic, body.script)
    if not subject:
        # Fall back to the latest video as the source topic.
        title, _url = content_service.latest_video_link(db)
        subject = title or "the truth the earliest Christians believed"
    count = body.count or 3
    return await content_service.generate_shorts(subject, count)


@router.post("/generate-hooks")
async def generate_hooks(
    body: HooksRequest,
    _: None = Depends(verify_admin),
) -> dict:
    return await content_service.generate_hooks(body.topic.strip())


@router.post("/repurpose")
async def repurpose(
    body: RepurposeRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    subject = _subject(body.topic, body.script)
    if not subject:
        title, _url = content_service.latest_video_link(db)
        subject = title or "the truth the earliest Christians believed"
    return await content_service.repurpose(subject)


@router.get("/posting-plan")
async def posting_plan(
    _: None = Depends(verify_admin),
) -> dict:
    return content_service.posting_plan()
