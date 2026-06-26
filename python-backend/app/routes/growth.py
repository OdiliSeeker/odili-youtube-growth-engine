"""
Growth Engine routes — YouTube Growth Automation Engine.

All endpoints are admin-only (require the `x-api-key` header).

Pipeline tracker (persisted):
  GET    /growth/pipeline            — list items grouped by stage
  POST   /growth/pipeline            — create an item
  PATCH  /growth/pipeline/{id}       — update stage / title / notes
  DELETE /growth/pipeline/{id}       — delete an item

Automation:
  GET    /growth/insights            — strategy highlights from YouTube Intelligence
  POST   /growth/weekly-plan         — 5-video weekly content plan (AI)
  POST   /growth/hooks               — 5 viral hooks for a topic (AI)
  POST   /growth/cta                 — Subscribe + Watch-Next CTA blocks (deterministic)
  POST   /growth/content-flow        — one-click idea → script → package → save (AI)
"""

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.models.db_models import (
    ContentSchedule,
    PipelineItem,
    Script,
    VideoPerformance,
    YouTubePackage,
)
from app.services.ai_service import (
    AIAuthError,
    AIConnectionError,
    AIQuotaError,
    AIServiceError,
)
from app.services.growth_service import (
    PIPELINE_STAGES,
    REPURPOSE_FORMATS,
    analyse_performance,
    boost_hook,
    build_ctas,
    derive_growth_insights,
    generate_evangelization_email,
    generate_optimization,
    generate_hooks,
    generate_idea_bundle,
    generate_package,
    generate_shorts,
    generate_weekly_plan,
    make_viral,
    performance_verdict,
    repurpose_script,
    rewrite_title,
    score_hook_intensity,
    score_topic,
    weekly_schedule_dates,
    get_posting_days,
    set_posting_days,
    VALID_DAYS,
    DEFAULT_POSTING_DAYS,
)
from app.services.youtube_intelligence_service import (
    get_channel_insights,
    peek_cached_insights,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── AI error mapping ──────────────────────────────────────────────────────────

def _ai_to_http(exc: Exception) -> HTTPException:
    """Translate an AI/service exception into an HTTPException."""
    if isinstance(exc, AIQuotaError):
        return HTTPException(status_code=402, detail={
            "error": "openai_quota_exceeded",
            "message": str(exc),
            "action": "Add credits at https://platform.openai.com/account/billing",
        })
    if isinstance(exc, AIAuthError):
        return HTTPException(status_code=401, detail={
            "error": "openai_auth_error", "message": str(exc),
        })
    if isinstance(exc, (AIConnectionError, AIServiceError)):
        return HTTPException(status_code=502, detail={
            "error": "openai_error", "message": str(exc),
        })
    if isinstance(exc, EnvironmentError):
        return HTTPException(status_code=503, detail={
            "error": "openai_not_configured", "message": str(exc),
        })
    if isinstance(exc, (ValueError, KeyError, TypeError, json.JSONDecodeError)):
        return HTTPException(
            status_code=502,
            detail=f"AI returned an unexpected format: {exc}",
        )
    return HTTPException(status_code=502, detail="AI request failed.")


async def _ai_call(coro):
    """Run an AI coroutine and translate service errors into HTTP responses."""
    try:
        return await coro
    except (
        AIQuotaError, AIAuthError, AIConnectionError, AIServiceError,
        EnvironmentError, ValueError, KeyError, TypeError, json.JSONDecodeError,
    ) as exc:
        raise _ai_to_http(exc) from exc


# ── Serialisation ─────────────────────────────────────────────────────────────

def _serialise(item: PipelineItem) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "stage": item.stage,
        "notes": item.notes,
        "script_id": item.script_id,
        "package_id": item.package_id,
        "created_at": item.created_at.replace(tzinfo=timezone.utc).isoformat()
        if item.created_at else None,
        "updated_at": item.updated_at.replace(tzinfo=timezone.utc).isoformat()
        if item.updated_at else None,
    }


# ── Request models ────────────────────────────────────────────────────────────

class PipelineCreate(BaseModel):
    title: str
    notes: str | None = None
    stage: str = "idea"


class PipelineUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    stage: str | None = None


class TopicRequest(BaseModel):
    topic: str


class CTARequest(BaseModel):
    next_video_title: str | None = None


class BatchRequest(BaseModel):
    count: int = 5
    topics: list[str] = []


class RepurposeRequest(BaseModel):
    format: str
    script_id: int | None = None
    title: str | None = None
    hook: str | None = None
    script: str | None = None


class WeeklyAutoRequest(BaseModel):
    count: int = 5


class PostingDaysRequest(BaseModel):
    days: list[str] = []


class ShortsRequest(BaseModel):
    script_id: int | None = None
    title: str | None = None
    hook: str | None = None
    script: str | None = None


class OptimizeRequest(BaseModel):
    script_id: int | None = None
    title: str | None = None
    topic: str | None = None
    script: str | None = None


class ScoreTopicRequest(BaseModel):
    topic: str


class RewriteTitleRequest(BaseModel):
    title: str


class ScoreHookRequest(BaseModel):
    topic: str | None = None
    hook: str | None = None
    script: str | None = None


class MakeViralRequest(BaseModel):
    script_id: int | None = None
    title: str | None = None
    topic: str | None = None
    hook: str | None = None
    script: str | None = None


class PerformanceCreate(BaseModel):
    title: str
    views: int = 0
    ctr: float = 0.0
    likes: int = 0


# ── Content Pipeline Tracker ──────────────────────────────────────────────────

@router.get("/growth/pipeline", tags=["Growth Engine"])
async def list_pipeline(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Return all pipeline items, plus a stage-keyed grouping for the board."""
    rows = db.query(PipelineItem).order_by(PipelineItem.updated_at.desc()).all()
    items = [_serialise(r) for r in rows]
    stages: dict[str, list] = {stage: [] for stage in PIPELINE_STAGES}
    for item in items:
        stages.setdefault(item["stage"], []).append(item)
    return {"stages": stages, "stage_order": PIPELINE_STAGES, "count": len(items)}


@router.post("/growth/pipeline", tags=["Growth Engine"], status_code=201)
async def create_pipeline_item(
    body: PipelineCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title is required.")
    stage = body.stage.strip().lower()
    if stage not in PIPELINE_STAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stage. Must be one of: {', '.join(PIPELINE_STAGES)}.",
        )
    row = PipelineItem(
        title=title,
        stage=stage,
        notes=(body.notes or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialise(row)


@router.patch("/growth/pipeline/{item_id}", tags=["Growth Engine"])
async def update_pipeline_item(
    item_id: int,
    body: PipelineUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    row = db.query(PipelineItem).filter(PipelineItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline item not found.")
    if body.stage is not None:
        stage = body.stage.strip().lower()
        if stage not in PIPELINE_STAGES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid stage. Must be one of: {', '.join(PIPELINE_STAGES)}.",
            )
        row.stage = stage
    if body.title is not None:
        new_title = body.title.strip()
        if not new_title:
            raise HTTPException(status_code=422, detail="Title cannot be empty.")
        row.title = new_title
    if body.notes is not None:
        row.notes = body.notes.strip() or None
    db.commit()
    db.refresh(row)
    return _serialise(row)


@router.delete("/growth/pipeline/{item_id}", tags=["Growth Engine"])
async def delete_pipeline_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    row = db.query(PipelineItem).filter(PipelineItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline item not found.")
    db.delete(row)
    db.commit()
    return {"message": "Pipeline item deleted."}


# ── Auto Strategy Insights ────────────────────────────────────────────────────

@router.get("/growth/insights", tags=["Growth Engine"])
async def growth_insights(_: None = Depends(verify_admin)) -> dict:
    """
    Strategy highlights derived from the YouTube Intelligence engine.

    Degrades gracefully (returns ``configured: false`` with a message) when the
    YouTube API is not configured or unreachable, so the dashboard never errors.
    """
    try:
        raw = await get_channel_insights()
    except ValueError as exc:
        return {"configured": False, "message": str(exc)}
    except (httpx.HTTPStatusError, httpx.RequestError):
        return {
            "configured": False,
            "message": "Could not reach the YouTube API — check YOUTUBE_API_KEY / "
                       "YOUTUBE_CHANNEL_ID.",
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Growth insights error: %s", exc)
        return {
            "configured": False,
            "message": "The intelligence engine hit an unexpected error. Please try again.",
        }
    return derive_growth_insights(raw)


# ── Weekly Content Plan ───────────────────────────────────────────────────────

@router.post("/growth/weekly-plan", tags=["Growth Engine"])
async def weekly_plan(_: None = Depends(verify_admin)) -> dict:
    """Generate a 5-video weekly content plan with posting schedule (AI)."""
    plan = await _ai_call(generate_weekly_plan())
    return {"plan": plan, "count": len(plan)}


# ── Hook Optimization ─────────────────────────────────────────────────────────

@router.post("/growth/hooks", tags=["Growth Engine"])
async def hooks(
    body: TopicRequest,
    _: None = Depends(verify_admin),
) -> dict:
    """Generate 5 viral hooks for a video topic (AI)."""
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Topic is required.")
    result = await _ai_call(generate_hooks(topic))
    return {"topic": topic, "hooks": result}


# ── CTA Booster ───────────────────────────────────────────────────────────────

@router.post("/growth/cta", tags=["Growth Engine"])
async def cta(
    body: CTARequest,
    _: None = Depends(verify_admin),
) -> dict:
    """Return ready-to-paste Subscribe and Watch-Next CTA blocks (no AI needed)."""
    return build_ctas(body.next_video_title)


# ── One-Click Content Flow ────────────────────────────────────────────────────

@router.post("/growth/content-flow", tags=["Growth Engine"], status_code=201)
async def content_flow(
    body: TopicRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    One-click flow: generate an idea + script, generate a YouTube package,
    save both, and create a pipeline item at the 'package' stage.
    """
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Topic is required.")

    bundle = await _ai_call(generate_idea_bundle(topic))
    package = await _ai_call(
        generate_package(bundle["title"], bundle["hook"], bundle["script"])
    )

    script_row = Script(
        topic=topic,
        title=bundle["title"],
        hook=bundle["hook"],
        script=bundle["script"],
    )
    pkg_row = YouTubePackage(
        title=package["title"],
        description=package["description"],
        tags=package["tags"],
        thumbnail_text=package["thumbnail_text"],
    )
    item = PipelineItem(
        title=bundle["title"],
        stage="package",
        notes=f"Auto-generated via one-click flow for topic: {topic}",
    )
    try:
        db.add(script_row)
        db.flush()  # assign script_row.id without committing
        pkg_row.script_id = script_row.id
        db.add(pkg_row)
        db.flush()
        item.script_id = script_row.id
        item.package_id = pkg_row.id
        db.add(item)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the generated content. Please try again.",
        )
    db.refresh(script_row)
    db.refresh(pkg_row)
    db.refresh(item)

    return {
        "topic": topic,
        "title": bundle["title"],
        "hook": bundle["hook"],
        "script": bundle["script"],
        "package": package,
        "script_id": script_row.id,
        "package_id": pkg_row.id,
        "pipeline_id": item.id,
    }


# ── Batch Generation ──────────────────────────────────────────────────────────

def _save_content(db: Session, topic: str, bundle: dict, package: dict) -> dict:
    """Persist a script + package + pipeline item; return the saved record's ids."""
    script_row = Script(
        topic=topic,
        title=bundle["title"],
        hook=bundle["hook"],
        script=bundle["script"],
    )
    pkg_row = YouTubePackage(
        title=package["title"],
        description=package["description"],
        tags=package["tags"],
        thumbnail_text=package["thumbnail_text"],
    )
    item = PipelineItem(
        title=bundle["title"],
        stage="package",
        notes=f"Auto-generated via batch flow for topic: {topic}",
    )
    db.add(script_row)
    db.flush()
    pkg_row.script_id = script_row.id
    db.add(pkg_row)
    db.flush()
    item.script_id = script_row.id
    item.package_id = pkg_row.id
    db.add(item)
    db.commit()
    db.refresh(script_row)
    db.refresh(pkg_row)
    db.refresh(item)
    return {
        "topic": topic,
        "title": bundle["title"],
        "hook": bundle["hook"],
        "script": bundle["script"],
        "package": package,
        "script_id": script_row.id,
        "package_id": pkg_row.id,
        "pipeline_id": item.id,
    }


@router.post("/growth/batch", tags=["Growth Engine"], status_code=201)
async def batch_generate(
    body: BatchRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    Batch flow: generate a full content package (idea → script → YouTube package)
    for up to 5 topics at once, saving each and adding it to the pipeline.

    If no topics are supplied, a fresh weekly plan is generated and its titles are
    used as the topics. Per-item failures are captured so one bad item never sinks
    the whole batch.
    """
    count = max(1, min(body.count, 5))
    topics = [t.strip() for t in body.topics if t and t.strip()][:count]

    if not topics:
        plan = await _ai_call(generate_weekly_plan())
        topics = [p["title"] for p in plan if p.get("title")][:count]
    if not topics:
        raise HTTPException(
            status_code=502,
            detail="Could not determine topics for the batch. Try again.",
        )

    created: list[dict] = []
    failed: list[dict] = []
    for topic in topics:
        try:
            bundle = await generate_idea_bundle(topic)
            package = await generate_package(
                bundle["title"], bundle["hook"], bundle["script"]
            )
            created.append(_save_content(db, topic, bundle, package))
        except (
            AIQuotaError, AIAuthError, AIConnectionError, AIServiceError,
            EnvironmentError,
        ) as exc:
            # Systemic failures (quota, auth, connectivity, config) will hit every
            # item — stop early. Surface proper HTTP semantics if nothing saved yet,
            # otherwise report a partial batch.
            db.rollback()
            if not created:
                raise _ai_to_http(exc)
            failed.append({"topic": topic, "error": str(exc)})
            break
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            # Malformed AI output for this topic — skip it, keep the batch going.
            db.rollback()
            logger.warning("Batch item failed for topic %r: %s", topic, exc)
            failed.append({"topic": topic, "error": "Generation failed for this topic."})

    return {"created": created, "failed": failed, "count": len(created)}


# ── Content Reuse / Repurposing ───────────────────────────────────────────────

@router.post("/growth/repurpose", tags=["Growth Engine"])
async def repurpose(
    body: RepurposeRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    Repurpose an existing script into another format (youtube_post | shorts).

    Provide either a ``script_id`` (loaded from the DB) or the raw
    ``title`` / ``hook`` / ``script`` fields directly.
    """
    fmt = (body.format or "").strip().lower()
    if fmt not in REPURPOSE_FORMATS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid format. Must be one of: {', '.join(REPURPOSE_FORMATS)}.",
        )

    title, hook, script = (body.title or ""), (body.hook or ""), (body.script or "")
    if body.script_id is not None:
        row = db.query(Script).filter(Script.id == body.script_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Script not found.")
        title, hook, script = row.title, row.hook, row.script

    if not script.strip():
        raise HTTPException(status_code=422, detail="A script is required to repurpose.")

    return await _ai_call(repurpose_script(fmt, title, hook, script))


# ── Shorts generator ──────────────────────────────────────────────────────────

@router.post("/growth/shorts", tags=["Growth Engine"])
async def shorts(
    body: ShortsRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    Generate a full Shorts package (3 hooks + 15-30s script + caption + hashtags).

    Provide either a ``script_id`` (loaded from the DB) or raw
    ``title`` / ``hook`` / ``script`` fields directly.
    """
    title, hook, script = (body.title or ""), (body.hook or ""), (body.script or "")
    if body.script_id is not None:
        row = db.query(Script).filter(Script.id == body.script_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Script not found.")
        title, hook, script = row.title, row.hook, row.script

    if not script.strip():
        raise HTTPException(status_code=422, detail="A script is required to generate Shorts.")

    return await _ai_call(generate_shorts(title, hook, script))


# ── YouTube Studio Optimisation ───────────────────────────────────────────────

@router.post("/youtube/optimize", tags=["Growth Engine"])
async def optimize_youtube(
    body: OptimizeRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    Return a complete YouTube Studio publishing blueprint for a video — every
    upload setting pre-tuned with SAFE, growth-optimised defaults.

    Provide a ``script_id`` (loaded from the DB) or raw ``title`` / ``topic`` /
    ``script`` fields. Deterministic and resilient: it layers in live YouTube
    Intelligence (best posting time + top topic clusters) only when a fresh
    cached payload is available, and never fails on missing keys or quota.
    """
    title, topic, script = (body.title or ""), (body.topic or ""), (body.script or "")
    if body.script_id is not None:
        row = db.query(Script).filter(Script.id == body.script_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Script not found.")
        title, script = row.title, row.script
        topic = topic or row.title

    if not (title.strip() or topic.strip() or script.strip()):
        raise HTTPException(
            status_code=422,
            detail="Provide a title, topic, or script to optimise.",
        )

    best_posting_time: str | None = None
    top_clusters: list[dict] = []
    try:
        cached = peek_cached_insights()
        if cached:
            derived = derive_growth_insights(cached)
            best_posting_time = derived.get("best_posting_time")
            top_clusters = derived.get("top_clusters") or []
    except Exception as exc:  # noqa: BLE001 — intelligence is optional here
        logger.info("Optimize: cached intelligence unavailable (%s)", exc)

    return generate_optimization(
        title=title,
        topic=topic,
        script=script,
        best_posting_time=best_posting_time,
        top_clusters=top_clusters,
    )


# ── Viral Conversion Layer (scoring / rewrite / hook / make-viral) ────────────

def _resolve_script(db: Session, script_id: int | None) -> Script | None:
    if script_id is None:
        return None
    row = db.query(Script).filter(Script.id == script_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Script not found.")
    return row


def _cached_intelligence() -> tuple[str | None, list[dict]]:
    """Best posting time + top clusters from cached intelligence (no network)."""
    try:
        cached = peek_cached_insights()
        if cached:
            derived = derive_growth_insights(cached)
            return derived.get("best_posting_time"), (derived.get("top_clusters") or [])
    except Exception as exc:  # noqa: BLE001 — intelligence is optional here
        logger.info("Cached intelligence unavailable (%s)", exc)
    return None, []


@router.post("/growth/score-topic", tags=["Growth Engine"])
async def score_topic_route(
    body: ScoreTopicRequest,
    _: None = Depends(verify_admin),
) -> dict:
    """Score a topic's viral potential (0-100) with sub-scores, a Use/Improve/
    Avoid recommendation, and an improved viral angle."""
    if not body.topic.strip():
        raise HTTPException(status_code=422, detail="Provide a topic to score.")
    return await score_topic(body.topic)


@router.post("/growth/rewrite-title", tags=["Growth Engine"])
async def rewrite_title_route(
    body: RewriteTitleRequest,
    _: None = Depends(verify_admin),
) -> dict:
    """Rewrite a title into 5 viral options (each under 70 characters)."""
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Provide a title to rewrite.")
    return await rewrite_title(body.title)


@router.post("/growth/score-hook", tags=["Growth Engine"])
async def score_hook_route(
    body: ScoreHookRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Score a hook's intensity (0-100) and auto-regenerate a stronger one if < 70."""
    topic, hook, script = (body.topic or ""), (body.hook or ""), (body.script or "")
    if not (hook.strip() or topic.strip()):
        raise HTTPException(status_code=422, detail="Provide a hook or topic.")
    original_score = score_hook_intensity(hook)
    boosted = await boost_hook(topic, hook, script)
    return {
        "original_hook": hook,
        "original_score": original_score,
        "hook": boosted["hook"],
        "hook_intensity_score": boosted["hook_intensity_score"],
        "regenerated": boosted["regenerated"],
    }


@router.post("/growth/make-viral", tags=["Growth Engine"])
async def make_viral_route(
    body: MakeViralRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """🔥 One-click viral package: score topic → 5 viral titles → boost hook →
    thumbnail psychology → full YouTube Studio blueprint."""
    title, topic, hook, script = (
        (body.title or ""), (body.topic or ""), (body.hook or ""), (body.script or ""),
    )
    row = _resolve_script(db, body.script_id)
    if row:
        title = title or row.title
        topic = topic or row.title
        hook = hook or row.hook
        script = script or row.script

    if not (title.strip() or topic.strip() or script.strip()):
        raise HTTPException(
            status_code=422,
            detail="Provide a script_id, title, topic, or script.",
        )

    best_posting_time, top_clusters = _cached_intelligence()
    return await make_viral(
        title=title,
        topic=topic,
        hook=hook,
        script=script,
        best_posting_time=best_posting_time,
        top_clusters=top_clusters,
    )


# ── Performance Feedback Loop (manual logging) ────────────────────────────────

def _serialise_performance(row: VideoPerformance) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "views": row.views,
        "ctr": row.ctr,
        "likes": row.likes,
        "verdict": row.verdict,
        "note": row.note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/growth/performance", tags=["Growth Engine"])
async def list_performance(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """List logged video performance records + an aggregated takeaway."""
    rows = (
        db.query(VideoPerformance)
        .order_by(VideoPerformance.created_at.desc())
        .all()
    )
    items = [_serialise_performance(r) for r in rows]
    return {"items": items, "summary": analyse_performance(items)}


@router.post("/growth/performance", tags=["Growth Engine"], status_code=201)
async def log_performance(
    body: PerformanceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Log a video's real numbers; returns a verdict + do-more/avoid note."""
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Provide a video title.")
    verdict, note = performance_verdict(body.views, body.ctr, body.likes)
    row = VideoPerformance(
        title=body.title.strip(),
        views=max(0, int(body.views or 0)),
        ctr=max(0.0, float(body.ctr or 0)),
        likes=max(0, int(body.likes or 0)),
        verdict=verdict,
        note=note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialise_performance(row)


@router.delete("/growth/performance/{record_id}", tags=["Growth Engine"])
async def delete_performance(
    record_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Delete a logged performance record."""
    row = db.query(VideoPerformance).filter(VideoPerformance.id == record_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Performance record not found.")
    db.delete(row)
    db.commit()
    return {"deleted": True, "id": record_id}


# ── Weekly Auto-Generation + Scheduling ───────────────────────────────────────

def _serialise_schedule(row: ContentSchedule) -> dict:
    sd = row.scheduled_date
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "script_id": row.script_id,
        "package_id": row.package_id,
        "pipeline_id": row.pipeline_id,
        "scheduled_date": sd.isoformat() if sd else None,
        "day": sd.strftime("%A") if sd else None,
        "date": sd.strftime("%b %d") if sd else None,
        "posted_at": row.posted_at.isoformat() if row.posted_at else None,
    }


async def _gather_weekly_topics(count: int) -> list[str]:
    """Build a list of topics for the week from YouTube Intelligence, falling
    back to an AI-generated weekly plan when intelligence is unavailable."""
    topics: list[str] = []
    try:
        derived = derive_growth_insights(await get_channel_insights())
        topics.extend(derived.get("suggested_topics") or [])
        for cluster in derived.get("top_clusters") or []:
            pattern = (cluster.get("pattern") or "").strip()
            if pattern:
                topics.append(f"More {pattern} content")
    except Exception as exc:  # noqa: BLE001 - intelligence is optional here
        logger.info("Weekly-auto: YouTube intelligence unavailable (%s)", exc)

    seen: set[str] = set()
    unique: list[str] = []
    for topic in topics:
        topic = (topic or "").strip()
        if topic and topic.lower() not in seen:
            seen.add(topic.lower())
            unique.append(topic)

    if len(unique) < count:
        plan = await _ai_call(generate_weekly_plan())
        for item in plan:
            title = (item.get("title") or "").strip()
            if title and title.lower() not in seen:
                seen.add(title.lower())
                unique.append(title)

    return unique[:count]


def _save_scheduled(
    db: Session, topic: str, bundle: dict, package: dict, scheduled_date: datetime,
) -> dict:
    """Persist script + package + pipeline (idea) + schedule entry."""
    script_row = Script(
        topic=topic, title=bundle["title"], hook=bundle["hook"], script=bundle["script"],
    )
    pkg_row = YouTubePackage(
        title=package["title"], description=package["description"],
        tags=package["tags"], thumbnail_text=package["thumbnail_text"],
    )
    item = PipelineItem(
        title=bundle["title"], stage="idea",
        notes=f"Auto-generated via weekly factory for topic: {topic}",
    )
    db.add(script_row)
    db.flush()
    pkg_row.script_id = script_row.id
    db.add(pkg_row)
    db.flush()
    item.script_id = script_row.id
    item.package_id = pkg_row.id
    db.add(item)
    db.flush()
    sched = ContentSchedule(
        title=bundle["title"], script_id=script_row.id, package_id=pkg_row.id,
        pipeline_id=item.id, scheduled_date=scheduled_date, status="scheduled",
    )
    db.add(sched)
    db.commit()
    db.refresh(script_row)
    db.refresh(pkg_row)
    db.refresh(item)
    db.refresh(sched)
    return {
        "topic": topic,
        "title": bundle["title"],
        "script_id": script_row.id,
        "package_id": pkg_row.id,
        "pipeline_id": item.id,
        "schedule_id": sched.id,
        "scheduled_date": scheduled_date.isoformat() if scheduled_date else None,
        "scheduled_label": scheduled_date.strftime("%a %b %d") if scheduled_date else None,
    }


@router.post("/growth/weekly-auto", tags=["Growth Engine"], status_code=201)
async def weekly_auto(
    body: WeeklyAutoRequest = WeeklyAutoRequest(),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    One-click weekly content factory: pull topics from YouTube Intelligence,
    generate full packages (idea → script → YouTube package) for each, save them,
    add them to the pipeline at the 'idea' stage, and auto-schedule them on the
    admin-selected posting days (see GET/PUT /growth/schedule/days) @ 09:00 UTC.
    """
    count = max(1, min(body.count, 5))
    topics = await _gather_weekly_topics(count)
    if not topics:
        raise HTTPException(
            status_code=502,
            detail="Could not determine topics for the week. Try again.",
        )

    dates = weekly_schedule_dates(len(topics), days=get_posting_days(db))
    created: list[dict] = []
    failed: list[dict] = []
    for index, topic in enumerate(topics):
        try:
            bundle = await generate_idea_bundle(topic)
            package = await generate_package(
                bundle["title"], bundle["hook"], bundle["script"]
            )
        except (
            AIQuotaError, AIAuthError, AIConnectionError, AIServiceError,
            EnvironmentError,
        ) as exc:
            db.rollback()
            if not created:
                raise _ai_to_http(exc)
            failed.append({"topic": topic, "error": str(exc)})
            break
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            db.rollback()
            logger.warning("Weekly-auto item failed for topic %r: %s", topic, exc)
            failed.append({"topic": topic, "error": "Generation failed for this topic."})
            continue
        scheduled_date = dates[index] if index < len(dates) else dates[-1]
        created.append(_save_scheduled(db, topic, bundle, package, scheduled_date))

    return {"created": created, "failed": failed, "count": len(created)}


@router.get("/growth/schedule/days", tags=["Growth Engine"])
async def get_schedule_days(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Return the admin-selected posting days plus the valid/default options."""
    return {
        "days": get_posting_days(db),
        "valid_days": VALID_DAYS,
        "default_days": DEFAULT_POSTING_DAYS,
    }


@router.put("/growth/schedule/days", tags=["Growth Engine"])
async def update_schedule_days(
    request: PostingDaysRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Persist the posting days used by the weekly content factory."""
    try:
        saved = set_posting_days(db, request.days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"days": saved, "message": "Posting days saved."}


@router.get("/growth/schedule", tags=["Growth Engine"])
async def list_schedule(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Return the full posting calendar, ordered by scheduled date."""
    rows = (
        db.query(ContentSchedule)
        .order_by(ContentSchedule.scheduled_date.asc())
        .all()
    )
    return {"items": [_serialise_schedule(r) for r in rows], "count": len(rows)}


@router.get("/growth/today", tags=["Growth Engine"])
async def todays_video(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Return the video scheduled for today (script + package), if any."""
    today = datetime.now(timezone.utc).date()
    rows = db.query(ContentSchedule).all()
    todays = [r for r in rows if r.scheduled_date and r.scheduled_date.date() == today]
    if not todays:
        return {"scheduled": False}
    # Prefer a still-scheduled item over an already-posted one.
    todays.sort(key=lambda r: (r.status == "posted", r.scheduled_date))
    row = todays[0]

    script = (
        db.query(Script).filter(Script.id == row.script_id).first()
        if row.script_id else None
    )
    package = (
        db.query(YouTubePackage).filter(YouTubePackage.id == row.package_id).first()
        if row.package_id else None
    )
    return {
        "scheduled": True,
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "pipeline_id": row.pipeline_id,
        "scheduled_date": row.scheduled_date.isoformat() if row.scheduled_date else None,
        "script": {
            "title": script.title, "hook": script.hook, "script": script.script,
        } if script else None,
        "package": {
            "title": package.title, "description": package.description,
            "tags": package.tags, "thumbnail_text": package.thumbnail_text,
        } if package else None,
    }


@router.post("/growth/schedule/{schedule_id}/posted", tags=["Growth Engine"])
async def mark_schedule_posted(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """
    Mark a scheduled video as posted: flip its status, move its pipeline item to
    'published', and return a ready-to-send announcement email draft so the
    posting → email → YouTube growth loop closes automatically.
    """
    row = db.query(ContentSchedule).filter(ContentSchedule.id == schedule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled item not found.")

    if row.status != "posted":
        row.status = "posted"
        row.posted_at = datetime.now(timezone.utc)

    if row.pipeline_id:
        item = (
            db.query(PipelineItem).filter(PipelineItem.id == row.pipeline_id).first()
        )
        if item:
            item.stage = "published"

    script = (
        db.query(Script).filter(Script.id == row.script_id).first()
        if row.script_id else None
    )
    email = await generate_evangelization_email(
        row.title,
        script.hook if script else "",
        script.script if script else "",
    )

    db.commit()
    return {
        "message": "Marked as posted.",
        "schedule_id": row.id,
        "email": email,
    }
