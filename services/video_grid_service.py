"""
Video grid service — landing "Start Exploring the Truth" grid (spec PART 1 / PART 2).

Six fixed categories, each holding an admin-managed pool of videos. The public
grid shows a rotating window of 3 videos per category; the window advances every
7 days when rotation is enabled. Rotation state lives in the ``app_settings``
key-value table (see featured_service for the pattern).

Deterministic + safe: all URLs/thumbnails are scheme-guarded (^https?:) so a bad
paste can never inject javascript:/data: into the landing page.
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.models.db_models import AppSetting, VideoGridItem

logger = logging.getLogger(__name__)

# Fixed grid categories: (key, display label, column). Left column then right.
CATEGORIES: list[tuple[str, str, str]] = [
    ("story_quizzes", "Story Quizzes for the Soul", "left"),
    ("ancient_heresies", "Ancient Heresies Exposed", "left"),
    ("battles_church_catholic", "The Battles to Keep the Church Catholic", "left"),
    ("venom_series", "The Venom Series", "right"),
    ("prayers", "Prayers", "right"),
    ("other_videos", "Discover More", "right"),
]
CATEGORY_KEYS = [c[0] for c in CATEGORIES]
CATEGORY_LABELS = {c[0]: c[1] for c in CATEGORIES}

VIDEOS_PER_CATEGORY = 3
ROTATION_KEY = "video_rotation"
ROTATION_DAYS = 7

_DEFAULT_ROTATION = {"enabled": True, "rotated_at": None, "window": 0}


def _clean(v, limit: int = 300) -> str:
    return str(v or "").strip()[:limit]


def _safe_url(v, limit: int = 500) -> str | None:
    """Return the URL only if it is http(s); else None (anti-injection)."""
    u = _clean(v, limit)
    if u.lower().startswith(("http://", "https://")):
        return u
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Rotation state (AppSetting JSON) ─────────────────────────────────────────

def get_rotation(db: Session) -> dict:
    row = db.query(AppSetting).filter(AppSetting.key == ROTATION_KEY).first()
    if not row or not row.value:
        return dict(_DEFAULT_ROTATION)
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return dict(_DEFAULT_ROTATION)
    return {
        "enabled": bool(data.get("enabled", True)),
        "rotated_at": data.get("rotated_at"),
        "window": int(data.get("window") or 0),
    }


def _save_rotation(db: Session, state: dict) -> dict:
    row = db.query(AppSetting).filter(AppSetting.key == ROTATION_KEY).first()
    payload = json.dumps({
        "enabled": bool(state.get("enabled", True)),
        "rotated_at": state.get("rotated_at"),
        "window": int(state.get("window") or 0),
    })
    if row is None:
        db.add(AppSetting(key=ROTATION_KEY, value=payload))
    else:
        row.value = payload
    db.commit()
    return get_rotation(db)


def set_rotation(db: Session, *, enabled: bool | None = None, reset: bool = False) -> dict:
    """Admin toggle: enable/disable auto-rotation, or reset the window (manual override)."""
    state = get_rotation(db)
    if enabled is not None:
        state["enabled"] = bool(enabled)
    if reset:
        state["window"] = 0
        state["rotated_at"] = _now().isoformat()
    return _save_rotation(db, state)


def advance_rotation(db: Session) -> dict:
    """Advance the rotation window by one and stamp the time. Returns new state."""
    state = get_rotation(db)
    state["window"] = int(state.get("window") or 0) + 1
    state["rotated_at"] = _now().isoformat()
    return _save_rotation(db, state)


def _maybe_rotate(db: Session, state: dict) -> dict:
    """If rotation is enabled and 7 days have elapsed, advance the window."""
    if not state.get("enabled"):
        return state
    stamp = state.get("rotated_at")
    if not stamp:
        # First run — stamp now, keep window 0.
        return _save_rotation(db, {**state, "rotated_at": _now().isoformat()})
    try:
        last = datetime.fromisoformat(stamp)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return _save_rotation(db, {**state, "rotated_at": _now().isoformat()})
    elapsed = _now() - last
    if elapsed >= timedelta(days=ROTATION_DAYS):
        # Advance by however many full weeks elapsed (self-healing after downtime).
        steps = int(elapsed.days // ROTATION_DAYS)
        state["window"] = int(state.get("window") or 0) + steps
        state["rotated_at"] = _now().isoformat()
        return _save_rotation(db, state)
    return state


# ── Pool CRUD (admin) ────────────────────────────────────────────────────────

def _serialize(v: VideoGridItem) -> dict:
    return {
        "id": v.id,
        "category": v.category,
        "category_label": CATEGORY_LABELS.get(v.category, v.category),
        "title": v.title,
        "youtube_url": v.youtube_url,
        "thumbnail": v.thumbnail,
        "sort_order": v.sort_order,
    }


def list_all(db: Session) -> dict:
    """Admin view: every video grouped by category (in fixed category order)."""
    rows = (
        db.query(VideoGridItem)
        .order_by(VideoGridItem.category, VideoGridItem.sort_order, VideoGridItem.id)
        .all()
    )
    grouped: dict[str, list[dict]] = {k: [] for k in CATEGORY_KEYS}
    for r in rows:
        grouped.setdefault(r.category, []).append(_serialize(r))
    return {
        "categories": [
            {"key": k, "label": CATEGORY_LABELS[k], "videos": grouped.get(k, [])}
            for k in CATEGORY_KEYS
        ]
    }


def add_video(db: Session, *, category: str, title: str, youtube_url: str, thumbnail: str | None = None) -> VideoGridItem | None:
    category = _clean(category, 60)
    if category not in CATEGORY_KEYS:
        return None
    title = _clean(title)
    url = _safe_url(youtube_url)
    if not title or not url:
        return None
    thumb = _safe_url(thumbnail)
    max_order = (
        db.query(VideoGridItem)
        .filter(VideoGridItem.category == category)
        .count()
    )
    item = VideoGridItem(
        category=category, title=title, youtube_url=url, thumbnail=thumb, sort_order=max_order
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_video(db: Session, video_id: int, *, title=None, youtube_url=None, thumbnail=None, category=None) -> dict | None:
    item = db.query(VideoGridItem).filter(VideoGridItem.id == video_id).first()
    if item is None:
        return None
    if title is not None and _clean(title):
        item.title = _clean(title)
    if youtube_url is not None:
        url = _safe_url(youtube_url)
        if url:
            item.youtube_url = url
    if thumbnail is not None:
        item.thumbnail = _safe_url(thumbnail)
    if category is not None and _clean(category, 60) in CATEGORY_KEYS:
        item.category = _clean(category, 60)
    db.commit()
    db.refresh(item)
    return _serialize(item)


def delete_video(db: Session, video_id: int) -> bool:
    item = db.query(VideoGridItem).filter(VideoGridItem.id == video_id).first()
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


# ── Public grid (rotated + safe) ─────────────────────────────────────────────

def get_public_grid(db: Session) -> dict:
    """Return 6 categories, each with a rotating window of up to 3 safe videos."""
    state = _maybe_rotate(db, get_rotation(db))
    window = int(state.get("window") or 0) if state.get("enabled") else 0

    rows = (
        db.query(VideoGridItem)
        .order_by(VideoGridItem.category, VideoGridItem.sort_order, VideoGridItem.id)
        .all()
    )
    pools: dict[str, list[VideoGridItem]] = {k: [] for k in CATEGORY_KEYS}
    for r in rows:
        if r.category in pools:
            pools[r.category].append(r)

    out = []
    for key, label, column in CATEGORIES:
        pool = pools.get(key, [])
        videos: list[dict] = []
        if pool:
            n = len(pool)
            start = (window * VIDEOS_PER_CATEGORY) % n
            for i in range(min(VIDEOS_PER_CATEGORY, n)):
                v = pool[(start + i) % n]
                safe = _safe_url(v.youtube_url)
                if not safe:
                    continue
                videos.append({
                    "title": v.title,
                    "youtube_url": safe,
                    "thumbnail": _safe_url(v.thumbnail),
                })
        out.append({"key": key, "label": label, "column": column, "videos": videos})
    return {"categories": out, "rotation_enabled": bool(state.get("enabled"))}
