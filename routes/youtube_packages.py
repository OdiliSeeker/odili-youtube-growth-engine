"""
YouTube Package routes.

POST /youtube-packages/generate — AI-generate a YouTube package from a script
GET  /youtube-packages          — list all packages (admin)
DELETE /youtube-packages/{id}   — delete a package (admin)
"""

import json
import logging
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.models.db_models import YouTubePackage
from app.services.ai_service import (
    generate_with_ai,
    AIQuotaError,
    AIAuthError,
    AIConnectionError,
    AIServiceError,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_YT_PACKAGE_PROMPT = """
You are an expert YouTube content strategist for the Odili Truth Seeker Catholic media channel.

Given this video script:
Title: {title}
Hook: {hook}
Script: {script}

Return ONLY a valid JSON object with exactly these four keys:
- "title": An SEO-optimized YouTube title (max 70 chars, compelling and keyword-rich)
- "description": A full YouTube description (200-300 words) ending with 8-10 relevant hashtags and a CTA to subscribe
- "tags": Comma-separated tags (12-15 relevant tags for YouTube search)
- "thumbnail_text": Short punchy overlay text for the thumbnail (max 5 words, high CTR)

No extra text, no markdown, no code fences. Pure JSON only.
"""


class YTPackageRequest(BaseModel):
    script_id: int | None = None
    title: str
    hook: str
    script: str


@router.post("/youtube-packages/generate", tags=["YouTube Packages"], status_code=201)
async def generate_youtube_package(
    body: YTPackageRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Generate and save a YouTube package (title, description, tags, thumbnail text) for a script."""
    prompt = _YT_PACKAGE_PROMPT.format(
        title=body.title.strip(),
        hook=body.hook.strip(),
        script=body.script.strip(),
    )

    try:
        raw = await generate_with_ai(prompt)
    except AIQuotaError as exc:
        raise HTTPException(status_code=402, detail={
            "error": "openai_quota_exceeded",
            "message": str(exc),
            "action": "Add credits at https://platform.openai.com/account/billing",
        }) from exc
    except AIAuthError as exc:
        raise HTTPException(status_code=401, detail={"error": "openai_auth_error", "message": str(exc)}) from exc
    except (AIConnectionError, AIServiceError) as exc:
        raise HTTPException(status_code=502, detail={"error": "openai_error", "message": str(exc)}) from exc

    try:
        data = json.loads(raw)
        pkg_title = data["title"]
        pkg_desc = data["description"]
        pkg_tags = data["tags"]
        pkg_thumb = data["thumbnail_text"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI returned an unexpected format: {exc}. Raw: {raw[:300]}",
        ) from exc

    row = YouTubePackage(
        script_id=body.script_id,
        title=pkg_title.strip(),
        description=pkg_desc.strip(),
        tags=pkg_tags.strip(),
        thumbnail_text=pkg_thumb.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "script_id": row.script_id,
        "title": row.title,
        "description": row.description,
        "tags": row.tags,
        "thumbnail_text": row.thumbnail_text,
        "created_at": row.created_at.replace(tzinfo=timezone.utc).isoformat(),
    }


@router.get("/youtube-packages", tags=["YouTube Packages"])
async def list_youtube_packages(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    rows = db.query(YouTubePackage).order_by(YouTubePackage.created_at.desc()).all()
    return {
        "packages": [
            {
                "id": r.id,
                "script_id": r.script_id,
                "title": r.title,
                "description": r.description,
                "tags": r.tags,
                "thumbnail_text": r.thumbnail_text,
                "created_at": r.created_at.replace(tzinfo=timezone.utc).isoformat()
                if r.created_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.delete("/youtube-packages/{package_id}", tags=["YouTube Packages"])
async def delete_youtube_package(
    package_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    row = db.query(YouTubePackage).filter(YouTubePackage.id == package_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Package not found.")
    db.delete(row)
    db.commit()
    return {"message": "Package deleted."}
