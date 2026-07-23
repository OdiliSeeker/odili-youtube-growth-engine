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

from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/plan")
async def content_plan(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Vote data → ranked content plan: top topics with why/angle/title/hook +
    video ideas + high-demand alerts. Deterministic — no AI required."""
    from app.services import content_plan_service
    return content_plan_service.get_plan(db)


@router.post("/plan/{topic_id}/email-draft", status_code=201)
async def content_plan_email_draft(
    topic_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Generate an email draft for a planned topic straight into the queue."""
    from app.models.db_models import Topic
    from app.services import email_queue_service

    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found.")
    t = topic.title.rstrip("?.!")
    body = "\n".join([
        f"Something doesn't add up about {t.lower()} — and deep down, you've probably sensed it.",
        (topic.description or "The answer goes deeper than most people have ever been told."),
        "We're preparing the full teaching now. Keep an eye on the channel — and if you have a question about this topic, just reply to this email. We read every one.",
    ])
    item = email_queue_service.create_draft(
        db,
        subject=f"The truth about {t} is coming",
        body=body,
        source="content_plan",
        topic_id=topic_id,
        dedup=False,
    )
    if item is None:
        raise HTTPException(status_code=400, detail="Could not create draft.")
    return {"message": "Email draft queued for review.", "id": item.id}


@router.get("/youtube-ctas")
async def youtube_ctas(
    video_title: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Ready-to-paste YouTube → landing-page CTA pack: description block,
    pinned comment, end-screen script. Deterministic. All links carry ?src=youtube."""
    from app.services.token_service import get_base_url

    landing = f"{get_base_url()}/?src=youtube"
    title_bit = f' from "{video_title.strip()}"' if video_title and video_title.strip() else ""
    return {
        "landing_link": landing,
        "description_cta": (
            "Something doesn't add up.\n"
            f"Get the full teaching{title_bit} — free, straight to your inbox:\n"
            f"→ {landing}\n\n"
            "New teachings released weekly. Rooted in Scripture, Tradition, and 2,000 years of Catholic teaching."
        ),
        "pinned_comment": (
            "Something doesn't add up… and deep down, you know it. "
            f"Get the full teaching here → {landing}"
        ),
        "end_screen_script": (
            "If this raised more questions than it answered — good. That means you're seeking. "
            "I put the full teaching in a free email you can read in 2 minutes. "
            "The link is in the description and the pinned comment. "
            "Something doesn't add up — get the full teaching. See you there."
        ),
    }
