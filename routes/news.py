"""
Catholic news routes (admin only).

News is a supportive intelligence layer for content creation — it feeds topic
ideas and email hooks. It is never a doctrinal authority.
"""

import logging

from fastapi import APIRouter, Depends

from app.dependencies.auth import verify_admin
from app.services import news_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/news", tags=["News"])
async def get_news(_: None = Depends(verify_admin)) -> dict:
    """Recent Catholic headlines (cached). Admin only."""
    return await news_service.get_catholic_news()


@router.post("/news/refresh", tags=["News"])
async def refresh_news(_: None = Depends(verify_admin)) -> dict:
    """Force a fresh fetch of Catholic headlines, bypassing the cache. Admin only."""
    return await news_service.get_catholic_news(force_refresh=True)
