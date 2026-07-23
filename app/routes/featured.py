"""
Featured content hub routes.

PUBLIC (no auth):
    GET  /featured-content   curated Shorts / playlists / community link for the landing hub

ADMIN (require x-api-key):
    PUT  /featured-content   update the curated featured content
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import featured_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ShortIn(BaseModel):
    id: str
    title: str | None = ""


class PlaylistIn(BaseModel):
    title: str | None = ""
    url: str


class FeaturedIn(BaseModel):
    shorts: list[ShortIn] = []
    playlists: list[PlaylistIn] = []
    community_url: str | None = ""


@router.get("/featured-content", tags=["Content Hub"])
async def get_featured(db: Session = Depends(get_db)) -> dict:
    """Public: curated featured content for the landing hub."""
    return featured_service.get_featured(db)


@router.put("/featured-content", tags=["Content Hub"])
async def put_featured(
    payload: FeaturedIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    """Admin: replace the curated featured content."""
    return featured_service.set_featured(
        db,
        shorts=[s.model_dump() for s in payload.shorts],
        playlists=[p.model_dump() for p in payload.playlists],
        community_url=payload.community_url,
    )
