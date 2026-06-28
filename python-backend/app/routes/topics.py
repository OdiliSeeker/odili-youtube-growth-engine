"""
Topic engagement routes.

PUBLIC (no auth) — the visitor engagement loop:
    GET    /topics                 list approved/featured topics with vote counts
    POST   /topics/{id}/vote       vote for a topic (deduped per visitor IP)
    POST   /topics/request         submit a new topic request (lands as 'suggested')

ADMIN (require x-api-key) — Odili's curation:
    GET    /topics/all             list every topic (incl. pending requests)
    POST   /topics                 create/curate a topic
    PATCH  /topics/{id}            update status/title/description
    DELETE /topics/{id}            delete a topic
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import topic_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request models ───────────────────────────────────────────────────────────
class TopicRequestIn(BaseModel):
    title: str
    description: str | None = None

    @field_validator("title")
    @classmethod
    def _title_ok(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 5:
            raise ValueError("Please describe the topic in at least 5 characters.")
        if len(v) > 200:
            raise ValueError("Please keep the topic under 200 characters.")
        return v

    @field_validator("description")
    @classmethod
    def _desc_ok(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Please keep the detail under 500 characters.")
        return v or None


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


def _client_ip(request: Request) -> str:
    """Best-effort visitor IP, honouring the reverse proxy's X-Forwarded-For."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Public ───────────────────────────────────────────────────────────────────
@router.get("/topics", tags=["Topics"])
async def get_topics(db: Session = Depends(get_db)) -> dict:
    """Public list of topics the visitor can vote on."""
    topics = topic_service.list_public_topics(db)
    return {"count": len(topics), "topics": topics}


@router.post("/topics/{topic_id}/vote", tags=["Topics"])
async def vote_topic(topic_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """Vote for a public topic. Idempotent per visitor (one vote each)."""
    result = topic_service.vote_topic(db, topic_id=topic_id, voter_ip=_client_ip(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Topic not found.")
    return result


@router.post("/topics/request", status_code=201, tags=["Topics"])
async def request_topic(payload: TopicRequestIn, db: Session = Depends(get_db)) -> dict:
    """Visitor submits a topic they'd like Odili to cover."""
    topic_service.submit_request(db, title=payload.title, description=payload.description)
    return {"message": "Thank you — your topic has been submitted for review."}


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
