"""
Growth Brain routes (ADMIN, x-api-key) — deterministic-first, never 402,
nothing auto-posts/sends.

Two complementary layers live here:

Granular primitives (`/growth-brain/*`):
  POST /growth-brain/score-title       — CTR prediction for one title
  POST /growth-brain/optimized-titles  — generate 10 → score → top 3
  POST /growth-brain/hooks             — viral hooks (short/long/pattern types)
  POST /growth-brain/keywords          — US search keywords for a topic
  GET   /growth-brain/title-performance — saved titles + clicks/CTR
  POST  /growth-brain/title-performance — save a scored title to track
  PATCH /growth-brain/title-performance/{id} — log clicks / set CTR
  GET   /growth-brain/trigger-phrases   — curated high-CTR trigger library
  POST  /growth-brain/trigger-phrases   — topic-tailored trigger phrases
  POST  /growth-brain/conversion-scripts — subscriber conversion scripts

Unified command center (`/growth/*`) — composes the granular engines:
  POST /growth/score-title     — predictive CTR score for a title (or a list)
  POST /growth/brain           — full growth pack for a topic / lead / content idea
  GET  /growth/trigger-phrases — curated Click Trigger Phrases library

Integrations (a topic can be resolved from any of these sources):
  - Content Ideas : `topic_id` → Topic.title
  - Lead Discovery: `lead_id`  → LeadComment.text
  - Traffic Engine: landing CTA is returned in the pack
  - Newsletter    : `create_email_draft=true` queues an EmailQueue draft

All endpoints are admin-only (require the `x-api-key` header) and are
DETERMINISTIC-FIRST: they never 402, even when OpenAI quota is exhausted, because
every composed engine keeps its pure-Python output when AI is unavailable.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.models.db_models import TitlePerformance, LeadComment, Topic
from app.services import (
    click_trigger_library,
    conversion_scripts_service,
    title_scorer,
    us_keyword_engine,
    viral_hook_engine,
    growth_brain_service,
    email_queue_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["growth-brain"])


# ── Granular request models ───────────────────────────────────────────────────

class TitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)


class TopicRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)


class SaveTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    score: int = Field(default=0, ge=0, le=100)


class TitleResultRequest(BaseModel):
    clicks: int = Field(default=0, ge=0)
    ctr: float | None = Field(default=None, ge=0, le=100)


class ScriptsRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    video_title: str = Field(default="", max_length=300)


def _serialize(r: TitlePerformance) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "score": r.score,
        "clicks": r.clicks,
        "ctr": round(r.ctr, 2),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ── Granular primitives (/growth-brain/*) ─────────────────────────────────────

@router.post("/growth-brain/score-title")
async def score_title(payload: TitleRequest, _: None = Depends(verify_admin)) -> dict:
    """Deterministic 0-100 CTR prediction with breakdown + improvements."""
    return title_scorer.score_title(payload.title)


@router.post("/growth-brain/optimized-titles")
async def optimized_titles(payload: TopicRequest, _: None = Depends(verify_admin)) -> dict:
    """Generate 10 candidate titles, score them, return the ranked list + top 3."""
    return await title_scorer.generate_optimized_titles(payload.topic)


@router.post("/growth-brain/hooks")
async def hooks(payload: TopicRequest, _: None = Depends(verify_admin)) -> dict:
    """Viral hooks: short, long, and grouped by psychological pattern."""
    return await viral_hook_engine.generate_hooks(payload.topic)


@router.post("/growth-brain/keywords")
async def keywords(payload: TopicRequest, _: None = Depends(verify_admin)) -> dict:
    """US search-targeted keywords, questions, and video titles for a topic."""
    return await us_keyword_engine.generate_us_keywords(payload.topic)


@router.get("/growth-brain/trigger-phrases")
async def trigger_phrases_library(
    category: str | None = None,
    _: None = Depends(verify_admin),
) -> dict:
    """The curated high-CTR 'click trigger phrases' library (optionally filtered)."""
    return click_trigger_library.get_library(category)


@router.post("/growth-brain/trigger-phrases")
async def trigger_phrases_for_topic(payload: TopicRequest, _: None = Depends(verify_admin)) -> dict:
    """Topic-tailored high-CTR trigger phrases across all categories."""
    return await click_trigger_library.adapt_to_topic(payload.topic)


@router.post("/growth-brain/conversion-scripts")
async def conversion_scripts(payload: ScriptsRequest, _: None = Depends(verify_admin)) -> dict:
    """Subscriber conversion scripts: pinned comment, comment/subscribe CTAs, description CTA."""
    return await conversion_scripts_service.generate_conversion_scripts(
        payload.topic, payload.video_title
    )


@router.get("/growth-brain/title-performance")
async def list_title_performance(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    rows = (
        db.query(TitlePerformance)
        .order_by(TitlePerformance.clicks.desc(), TitlePerformance.score.desc(), TitlePerformance.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_serialize(r) for r in rows]}


@router.post("/growth-brain/title-performance", status_code=201)
async def save_title_performance(
    payload: SaveTitleRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Save a title to track (idempotent per title — updates the stored score)."""
    row = db.query(TitlePerformance).filter(TitlePerformance.title == payload.title[:500]).first()
    if row is None:
        row = TitlePerformance(title=payload.title[:500], score=payload.score)
        db.add(row)
    else:
        row.score = payload.score
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.patch("/growth-brain/title-performance/{perf_id}")
async def update_title_performance(
    perf_id: int,
    payload: TitleResultRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Increment real clicks and/or set the latest known CTR (%)."""
    row = db.get(TitlePerformance, perf_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Title not found")
    row.clicks += max(0, int(payload.clicks))
    if payload.ctr is not None:
        row.ctr = float(payload.ctr)
    db.commit()
    db.refresh(row)
    return _serialize(row)


# ── Unified request models ────────────────────────────────────────────────────

class ScoreTitleRequest(BaseModel):
    title: str | None = None
    titles: list[str] = []


class BrainRequest(BaseModel):
    topic: str | None = None
    lead_id: int | None = None
    topic_id: int | None = None
    create_email_draft: bool = False


# ── Unified Title CTR Scorer (/growth/score-title) ────────────────────────────

@router.post("/growth/score-title", tags=["Growth Brain"])
async def predict_title_ctr(
    body: ScoreTitleRequest,
    _: None = Depends(verify_admin),
) -> dict:
    """Predict a title's click-through strength (0-100) with reasons and tips.

    Provide a single ``title`` or a list of ``titles`` to score and rank.
    """
    candidates = [t for t in ([body.title] + list(body.titles)) if t and t.strip()]
    if not candidates:
        raise HTTPException(status_code=422, detail="Provide a title or a list of titles.")
    if len(candidates) == 1:
        return {"result": growth_brain_service.score_title(candidates[0])}
    return {"results": growth_brain_service.rank_titles(candidates, limit=20)}


# ── Unified Trigger Phrases library (/growth/trigger-phrases) ──────────────────

@router.get("/growth/trigger-phrases", tags=["Growth Brain"])
async def trigger_phrases(
    topic: str | None = None,
    _: None = Depends(verify_admin),
) -> dict:
    """Curated Click Trigger Phrases library, filled for ``topic`` when supplied."""
    return growth_brain_service.list_trigger_phrases(topic)


# ── Unified Growth Brain (/growth/brain) ──────────────────────────────────────

def _resolve_topic(db: Session, body: BrainRequest) -> str:
    """Resolve the working topic from an explicit topic, a lead, or a content idea."""
    if body.topic and body.topic.strip():
        return body.topic.strip()
    if body.lead_id is not None:
        lead = db.query(LeadComment).filter(LeadComment.id == body.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found.")
        return (lead.text or "").strip()[:200]
    if body.topic_id is not None:
        topic_row = db.query(Topic).filter(Topic.id == body.topic_id).first()
        if not topic_row:
            raise HTTPException(status_code=404, detail="Topic not found.")
        return (topic_row.title or "").strip()
    raise HTTPException(status_code=422, detail="Provide a topic, lead_id, or topic_id.")


@router.post("/growth/brain", tags=["Growth Brain"])
async def growth_brain(
    body: BrainRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """One call → optimized titles (ranked by predicted CTR), viral hooks,
    US keywords, conversion scripts, trigger phrases, and a landing CTA.

    Optionally queues a Newsletter draft (``create_email_draft``) for the
    admin's normal draft → approve → send flow — it never bulk-sends.
    """
    topic = _resolve_topic(db, body)
    if not topic:
        raise HTTPException(status_code=422, detail="Could not determine a topic to work with.")

    brain = await growth_brain_service.build_brain(topic)

    if body.create_email_draft:
        landing = brain["landing_cta"]
        best = brain["best_title"]["title"]
        body_lines = [
            landing.get("headline", best),
            "",
            landing.get("subheadline", ""),
            "",
            brain["conversion_scripts"]["pinned_comment"],
        ]
        draft = email_queue_service.create_draft(
            db,
            subject=best[:300],
            body="\n".join([ln for ln in body_lines if ln is not None]),
            source="growth_brain",
            topic_id=body.topic_id,
            dedup=body.topic_id is not None,
        )
        brain["email_draft_id"] = draft.id if draft else None

    return brain
