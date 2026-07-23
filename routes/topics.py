"""
Topic curation routes (ADMIN ONLY).

The public landing-page voting loop was removed (landing redesign): the former
public GET /topics, vote, and /topics/request endpoints no longer exist. Topics
remain an internal admin/content-engine concept.

ADMIN (require x-api-key) — Odili's curation:
    GET    /topics/all             list every topic (incl. pending requests)
    POST   /topics                 create/curate a topic
    PATCH  /topics/{id}            update status/title/description
    DELETE /topics/{id}            delete a topic
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import topic_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request models ───────────────────────────────────────────────────────────
class TopicCreateIn(BaseModel):
    title: str
    description: str | None = None
    status: str = "approved"

    @field_validator("title")
    @classmethod
    def _title_ok(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Title is required.")
        return v


class TopicUpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    sort_order: int | None = None


class TopicReorderIn(BaseModel):
    ordered_ids: list[int]


# ── Admin ────────────────────────────────────────────────────────────────────
@router.get("/topics/all", tags=["Topics"])
async def list_all(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    """Every topic, including pending visitor requests. Admin only."""
    topics = topic_service.list_all_topics(db)
    return {"count": len(topics), "topics": topics}


@router.post("/topics", status_code=201, tags=["Topics"])
async def create_topic(
    payload: TopicCreateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Curate a new topic for the public list. Admin only."""
    return topic_service.create_topic(
        db,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        source="admin",
    )


@router.post("/topics/reorder", tags=["Topics"])
async def reorder_topics(
    payload: TopicReorderIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Set the public display order of topics by id sequence. Admin only."""
    updated = topic_service.reorder_topics(db, ordered_ids=payload.ordered_ids)
    return {"message": "Topics reordered.", "updated": updated}


@router.patch("/topics/{topic_id}", tags=["Topics"])
async def patch_topic(
    topic_id: int,
    payload: TopicUpdateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Approve / feature / archive or edit a topic. Admin only."""
    updated = topic_service.update_topic(
        db,
        topic_id=topic_id,
        status=payload.status,
        title=payload.title,
        description=payload.description,
        sort_order=payload.sort_order,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Topic not found or invalid status.")
    return updated


@router.delete("/topics/{topic_id}", tags=["Topics"])
async def remove_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Delete a topic and its votes. Admin only."""
    if not topic_service.delete_topic(db, topic_id=topic_id):
        raise HTTPException(status_code=404, detail="Topic not found.")
    return {"message": "Topic deleted.", "id": topic_id}
