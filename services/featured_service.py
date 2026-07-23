"""
Featured content store for the landing content hub (Part 3 / Part 8).

Since no YouTube Data API key is configured, the landing "content hub" (latest
Shorts, playlists, community link) is ADMIN-CURATED. The admin pastes the YouTube
IDs / URLs in the dashboard; they are stored as a single JSON blob in the
``app_settings`` key-value table and rendered on the public landing page.
"""

import json
import logging

from sqlalchemy.orm import Session

from app.models.db_models import AppSetting

logger = logging.getLogger(__name__)

_SETTING_KEY = "featured_content"

_DEFAULT: dict = {
    "shorts": [],        # [{"id": "<youtube id>", "title": "..."}]
    "playlists": [],     # [{"title": "...", "url": "..."}]
    "community_url": "",  # link to the channel community tab / post
}

_MAX_ITEMS = 12


def _clean_str(v, limit: int = 200) -> str:
    return str(v or "").strip()[:limit]


def get_featured(db: Session) -> dict:
    """Return the curated featured content, always with the full default shape."""
    row = db.query(AppSetting).filter(AppSetting.key == _SETTING_KEY).first()
    if not row or not row.value:
        return {**_DEFAULT, "shorts": [], "playlists": []}
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        logger.warning("featured_content setting was corrupt — returning defaults.")
        return {**_DEFAULT, "shorts": [], "playlists": []}

    shorts = [
        {"id": _clean_str(s.get("id"), 40), "title": _clean_str(s.get("title"))}
        for s in (data.get("shorts") or [])
        if isinstance(s, dict) and _clean_str(s.get("id"), 40)
    ][:_MAX_ITEMS]
    playlists = [
        {"title": _clean_str(p.get("title")), "url": _clean_str(p.get("url"), 500)}
        for p in (data.get("playlists") or [])
        if isinstance(p, dict) and _clean_str(p.get("url"), 500)
    ][:_MAX_ITEMS]
    return {
        "shorts": shorts,
        "playlists": playlists,
        "community_url": _clean_str(data.get("community_url"), 500),
    }


def set_featured(db: Session, *, shorts=None, playlists=None, community_url=None) -> dict:
    """Validate and persist curated featured content. Returns the stored shape."""
    payload = {
        "shorts": [
            {"id": _clean_str(s.get("id"), 40), "title": _clean_str(s.get("title"))}
            for s in (shorts or [])
            if isinstance(s, dict) and _clean_str(s.get("id"), 40)
        ][:_MAX_ITEMS],
        "playlists": [
            {"title": _clean_str(p.get("title")), "url": _clean_str(p.get("url"), 500)}
            for p in (playlists or [])
            if isinstance(p, dict) and _clean_str(p.get("url"), 500)
        ][:_MAX_ITEMS],
        "community_url": _clean_str(community_url, 500),
    }
    row = db.query(AppSetting).filter(AppSetting.key == _SETTING_KEY).first()
    if row is None:
        row = AppSetting(key=_SETTING_KEY, value=json.dumps(payload))
        db.add(row)
    else:
        row.value = json.dumps(payload)
    db.commit()
    return payload
