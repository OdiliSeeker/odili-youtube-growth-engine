"""
YouTube Intelligence route.

GET /youtube/intelligence — admin-only endpoint that returns channel performance
data, keyword analysis, and AI-generated content strategy suggestions.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import verify_admin
from app.services.youtube_intelligence_service import get_channel_insights

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/youtube/intelligence", tags=["YouTube Intelligence"])
async def youtube_intelligence(
    refresh: bool = False,
    _: None = Depends(verify_admin),
) -> dict:
    """
    Fetch the latest 20 videos from the configured YouTube channel and return:
    - Top 5 performing videos (by views)
    - Keyword patterns extracted from titles
    - Detected topic clusters (Pope, Hell, Quiz, etc.)
    - 10 AI-generated viral topic ideas (GPT-4o)
    - 5 improved titles for underperforming videos (GPT-4o)
    - 3 new playlist ideas (GPT-4o)

    Requires `x-api-key` header (ADMIN_API_KEY).
    Requires `YOUTUBE_API_KEY` and `YOUTUBE_CHANNEL_ID` environment secrets.
    """
    try:
        return await get_channel_insights(force_refresh=refresh)

    except ValueError as exc:
        # Configuration errors — bad channel ID, missing secrets, etc.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 400:
            raise HTTPException(
                status_code=400,
                detail="YouTube API rejected the request — check YOUTUBE_CHANNEL_ID.",
            ) from exc
        if status == 403:
            raise HTTPException(
                status_code=403,
                detail=(
                    "YouTube API key is invalid or the YouTube Data API v3 is not "
                    "enabled on your Google Cloud project."
                ),
            ) from exc
        logger.error("YouTube API HTTP error %s: %s", status, exc)
        raise HTTPException(
            status_code=502,
            detail=f"YouTube API returned HTTP {status}.",
        ) from exc

    except httpx.RequestError as exc:
        logger.error("YouTube API network error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Could not reach the YouTube API — network error.",
        ) from exc

    except Exception as exc:
        logger.exception("YouTube intelligence engine error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Intelligence engine error: {exc}",
        ) from exc
