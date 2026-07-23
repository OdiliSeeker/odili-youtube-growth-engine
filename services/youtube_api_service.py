"""
Compliant YouTube Data API v3 client (API-key only, read-only public data).

Used by the Lead Discovery Engine. Reads ONLY public data — channel uploads and
public comment threads — with the ministry's own ``YOUTUBE_API_KEY`` (a private
10,000 units/day quota). It never writes to YouTube (no auto-reply / comment /
post) and never scrapes.

Every metered call routes through the daily quota tracker (``ApiQuotaLog``) and
hard-stops once the safety cap is reached, resuming the next UTC day.
"""

import logging
import os
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.db_models import ApiQuotaLog

logger = logging.getLogger(__name__)

API_BASE = "https://www.googleapis.com/youtube/v3"

# Free tier is 10,000 units/day. We hard-stop at 9,000 to keep a safety margin
# so the existing YouTube Intelligence feature never gets starved.
DAILY_QUOTA_CAP = 9000

# Read "list" calls cost 1 unit each regardless of parts requested.
COST_LIST = 1


class YouTubeNotConfigured(Exception):
    """Raised when YOUTUBE_API_KEY is not set."""


class YouTubeQuotaError(Exception):
    """Raised when the daily quota cap is reached or the API returns quota 403."""


class YouTubeAPIError(Exception):
    """Raised for any other YouTube API failure (bad channel, comments off, etc.)."""


# ── Configuration ────────────────────────────────────────────────────────────

def is_configured() -> bool:
    return bool(os.getenv("YOUTUBE_API_KEY", "").strip())


def _api_key() -> str:
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise YouTubeNotConfigured(
            "YOUTUBE_API_KEY is not set. Create a free YouTube Data API v3 key in "
            "Google Cloud Console and add it as a secret."
        )
    return key


# ── Daily quota tracker ──────────────────────────────────────────────────────

def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def units_used_today(db: Session) -> int:
    row = db.get(ApiQuotaLog, _today())
    return row.units_used if row else 0


def remaining_today(db: Session) -> int:
    return max(0, DAILY_QUOTA_CAP - units_used_today(db))


def quota_status(db: Session) -> dict:
    used = units_used_today(db)
    return {
        "date": _today(),
        "units_used": used,
        "cap": DAILY_QUOTA_CAP,
        "remaining": max(0, DAILY_QUOTA_CAP - used),
    }


def _log_units(db: Session, units: int) -> None:
    # Atomic upsert (single SQL statement) so overlapping scans — e.g. a manual
    # /leads/scan running alongside the 6-hourly scheduler job — can never lose
    # increments via read-modify-write, keeping the daily hard-stop accurate.
    db.execute(
        text(
            "INSERT INTO api_quota_log (log_date, units_used, updated_at) "
            "VALUES (:d, :u, :now) "
            "ON CONFLICT(log_date) DO UPDATE SET "
            "units_used = api_quota_log.units_used + :u, updated_at = :now"
        ),
        {"d": _today(), "u": units, "now": datetime.now(timezone.utc)},
    )
    db.commit()


# ── HTTP helper ──────────────────────────────────────────────────────────────

def _error_reason(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        return (data.get("error", {}).get("errors", [{}])[0].get("reason") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _get(db: Session, path: str, params: dict, cost: int = COST_LIST) -> dict:
    """Metered GET against the YouTube Data API. Logs quota, enforces the cap."""
    if remaining_today(db) < cost:
        raise YouTubeQuotaError(
            f"Daily quota safety cap ({DAILY_QUOTA_CAP} units) reached — scanning "
            "paused until tomorrow (UTC)."
        )
    query = {**params, "key": _api_key()}
    # Log the unit BEFORE the call so a failed/aborted call still counts
    # conservatively against the daily budget.
    _log_units(db, cost)
    try:
        resp = httpx.get(f"{API_BASE}/{path}", params=query, timeout=20.0)
    except httpx.HTTPError as exc:
        raise YouTubeAPIError(f"Network error calling YouTube API: {exc}") from exc

    if resp.status_code == 403:
        reason = _error_reason(resp)
        if reason in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "userRateLimitExceeded"):
            raise YouTubeQuotaError(f"YouTube API quota exceeded (reason={reason or 'quota'}).")
        raise YouTubeAPIError(f"YouTube API 403 (reason={reason or 'forbidden'}).")
    if resp.status_code >= 400:
        raise YouTubeAPIError(f"YouTube API error {resp.status_code}: {resp.text[:200]}")
    return resp.json()


# ── Channel resolution ───────────────────────────────────────────────────────

_UC_RE = re.compile(r"(UC[0-9A-Za-z_-]{20,})")
_HANDLE_RE = re.compile(r"@([A-Za-z0-9._\-]+)")


def parse_channel_input(raw: str) -> tuple[str, str]:
    """Return ("id", "UC...") or ("handle", "@name") from a URL/ID/handle.

    Deliberately avoids the 100-unit search.list — only free channel lookups
    (by id or handle) are supported.
    """
    raw = (raw or "").strip()
    if not raw:
        raise YouTubeAPIError("No channel provided.")
    m = _UC_RE.search(raw)
    if m:
        return ("id", m.group(1))
    hm = _HANDLE_RE.search(raw)
    if hm:
        return ("handle", "@" + hm.group(1))
    # Bare token with no spaces/slashes → treat as a handle.
    if "/" not in raw and " " not in raw:
        return ("handle", "@" + raw.lstrip("@"))
    raise YouTubeAPIError(
        "Could not read a channel ID or @handle. Paste the channel URL "
        "(youtube.com/@handle or youtube.com/channel/UC...), the @handle, or the UC... id."
    )


def resolve_channel(db: Session, raw: str) -> dict:
    """Resolve a channel to its id + uploads playlist (1 quota unit)."""
    kind, value = parse_channel_input(raw)
    params = {"part": "snippet,contentDetails"}
    if kind == "id":
        params["id"] = value
    else:
        params["forHandle"] = value
    data = _get(db, "channels", params, COST_LIST)
    items = data.get("items") or []
    if not items:
        raise YouTubeAPIError(f"No YouTube channel found for {value!r}.")
    it = items[0]
    uploads = (
        it.get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )
    if not uploads:
        raise YouTubeAPIError("Channel has no accessible uploads playlist.")
    return {
        "channel_id": it["id"],
        "title": it.get("snippet", {}).get("title", "Unknown channel"),
        "handle": it.get("snippet", {}).get("customUrl"),
        "uploads_playlist_id": uploads,
    }


# ── Uploads + comments ───────────────────────────────────────────────────────

def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def list_uploads(db: Session, uploads_playlist_id: str, max_results: int = 5) -> list[dict]:
    """Most-recent uploads of a channel (1 quota unit)."""
    data = _get(
        db,
        "playlistItems",
        {
            "part": "snippet,contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": max(1, min(max_results, 50)),
        },
        COST_LIST,
    )
    out: list[dict] = []
    for it in data.get("items", []):
        cd = it.get("contentDetails", {})
        sn = it.get("snippet", {})
        vid = cd.get("videoId")
        if not vid:
            continue
        out.append({
            "video_id": vid,
            "title": sn.get("title", "") or "",
            "published_at": _parse_dt(cd.get("videoPublishedAt") or sn.get("publishedAt")),
        })
    return out


def list_comments(db: Session, video_id: str, max_results: int = 100) -> list[dict]:
    """Top-level public comments on a video (1 quota unit).

    Returns [] when comments are disabled or the video is otherwise
    unavailable (these raise a non-quota 403/404 which we swallow).
    """
    try:
        data = _get(
            db,
            "commentThreads",
            {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": max(1, min(max_results, 100)),
                "order": "relevance",
                "textFormat": "plainText",
            },
            COST_LIST,
        )
    except YouTubeAPIError as exc:
        msg = str(exc).lower()
        # Permanent conditions — comments are off or the video is gone, so no
        # comments will ever arrive; safe for the caller to mark it scanned.
        if "commentsdisabled" in msg or "notfound" in msg or " 404" in msg:
            logger.info("Comments permanently unavailable for %s: %s", video_id, exc)
            return []
        # Transient (network / other API error) — re-raise so the caller leaves
        # the video UNscanned and retries it on the next scan.
        raise
    out: list[dict] = []
    for it in data.get("items", []):
        top = it.get("snippet", {}).get("topLevelComment", {})
        sn = top.get("snippet", {})
        cid = top.get("id")
        if not cid:
            continue
        out.append({
            "comment_id": cid,
            "author": sn.get("authorDisplayName", "") or "",
            "text": sn.get("textDisplay", "") or sn.get("textOriginal", "") or "",
        })
    return out


def comment_link(video_id: str, comment_id: str) -> str:
    """Deep-link straight to the comment on YouTube (human opens & replies there)."""
    return f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}"
