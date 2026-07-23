"""
Video grid routes — landing "Start Exploring the Truth" grid (spec PART 1 / PART 2).

Admin manages the per-category video pool + rotation toggle; the public grid
returns a rotating window of 3 videos per category (all URLs scheme-guarded).

    GET    /video-grid                    PUBLIC: rotated grid for the landing page
    GET    /admin/video-grid              list all videos grouped by category (admin)
    POST   /admin/video-grid              add a video (admin)
    PATCH  /admin/video-grid/{id}         edit a video (admin)
    DELETE /admin/video-grid/{id}         delete a video (admin)
    GET    /admin/video-grid/rotation     current rotation state (admin)
    PUT    /admin/video-grid/rotation     enable/disable / reset rotation (admin)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.services import video_grid_service

router = APIRouter(tags=["Video Grid"])


class VideoIn(BaseModel):
    category: str
    title: str
    youtube_url: str
    thumbnail: str | None = None


class VideoEditIn(BaseModel):
    category: str | None = None
    title: str | None = None
    youtube_url: str | None = None
    thumbnail: str | None = None


class RotationIn(BaseModel):
    enabled: bool | None = None
    reset: bool = False


@router.get("/video-grid", include_in_schema=False)
async def public_video_grid(db: Session = Depends(get_db)) -> dict:
    """PUBLIC: rotating grid (up to 3 safe videos per category) for the landing page."""
    return video_grid_service.get_public_grid(db)


@router.get("/admin/video-grid")
async def admin_list_grid(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    grid = video_grid_service.list_all(db)
    grid["rotation"] = video_grid_service.get_rotation(db)
    return grid


@router.post("/admin/video-grid", status_code=201)
async def admin_add_video(
    payload: VideoIn, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    item = video_grid_service.add_video(
        db, category=payload.category, title=payload.title,
        youtube_url=payload.youtube_url, thumbnail=payload.thumbnail,
    )
    if item is None:
        raise HTTPException(
            status_code=400,
            detail="Valid category, title, and http(s) youtube_url are required.",
        )
    return {"message": "Video added.", "id": item.id}


@router.patch("/admin/video-grid/{video_id}")
async def admin_edit_video(
    video_id: int, payload: VideoEditIn, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    result = video_grid_service.update_video(
        db, video_id, title=payload.title, youtube_url=payload.youtube_url,
        thumbnail=payload.thumbnail, category=payload.category,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Video not found.")
    return result


@router.delete("/admin/video-grid/{video_id}")
async def admin_delete_video(
    video_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    if not video_grid_service.delete_video(db, video_id):
        raise HTTPException(status_code=404, detail="Video not found.")
    return {"message": "Deleted."}


@router.get("/admin/video-grid/rotation")
async def admin_get_rotation(db: Session = Depends(get_db), _: None = Depends(verify_admin)) -> dict:
    return video_grid_service.get_rotation(db)


@router.put("/admin/video-grid/rotation")
async def admin_set_rotation(
    payload: RotationIn, db: Session = Depends(get_db), _: None = Depends(verify_admin)
) -> dict:
    return video_grid_service.set_rotation(db, enabled=payload.enabled, reset=payload.reset)
