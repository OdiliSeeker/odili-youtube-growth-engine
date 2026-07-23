"""
Geo Intelligence — privacy-safe, coarse visitor geography.

PRIVACY RULES (non-negotiable):
  - Raw IPs are NEVER stored — not in the DB, not in logs.
  - Only coarse country + region are persisted (VisitorGeo rows).
  - Lookup results are cached in-memory keyed by a salted SHA-256 of the IP
    (short TTL) so repeat visitors don't trigger repeat lookups.
  - Everything is best-effort and fail-silent: a lookup failure never breaks
    or slows the public funnel (lookups run in the background).

Lookup provider: ip-api.com free endpoint (country + region only requested).
Private/loopback addresses are skipped entirely.
"""

import hashlib
import ipaddress
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.db_models import VisitorGeo

logger = logging.getLogger(__name__)

_LOOKUP_URL = "http://ip-api.com/json/{ip}?fields=status,countryCode,regionName"
_CACHE_TTL = 6 * 3600
_CACHE_MAX = 5000

_cache_lock = threading.Lock()
_geo_cache: dict[str, tuple[float, dict | None]] = {}  # salted-hash → (ts, geo)

_salt = os.getenv("SESSION_SECRET", "odili-geo")[:32]


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        ip = fwd.split(",")[0].strip()
        if ip:
            return ip
    return request.client.host if request.client else None


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(f"{_salt}|{ip}".encode()).hexdigest()


def _is_public_ip(ip: str) -> bool:
    try:
        parsed = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_reserved)


def _lookup(ip: str) -> dict | None:
    """Country/region for an IP via ip-api. Returns None on any failure."""
    key = _hash_ip(ip)
    now = time.time()
    with _cache_lock:
        hit = _geo_cache.get(key)
        if hit and now - hit[0] < _CACHE_TTL:
            return hit[1]
    geo: dict | None = None
    try:
        resp = httpx.get(_LOOKUP_URL.format(ip=ip), timeout=3.0)
        data = resp.json()
        if data.get("status") == "success" and data.get("countryCode"):
            geo = {
                "country": str(data["countryCode"])[:4].upper(),
                "region": str(data.get("regionName") or "")[:100],
            }
    except Exception:
        geo = None  # fail-silent; negative result is cached too
    with _cache_lock:
        if len(_geo_cache) >= _CACHE_MAX:
            _geo_cache.clear()
        _geo_cache[key] = (now, geo)
    return geo


def get_geo_from_request(request: Request) -> dict | None:
    """Coarse {country, region} for the requester, or None. Never raises."""
    try:
        ip = _client_ip(request)
        if not ip or not _is_public_ip(ip):
            return None
        return _lookup(ip)
    except Exception:
        return None


def record_visit_background(ip: str | None, page: str) -> None:
    """Background-task target: look up coarse geo and store a VisitorGeo row.

    Runs AFTER the response is sent (FastAPI BackgroundTasks), so the network
    lookup never adds latency to the public funnel. Opens its own DB session.
    """
    try:
        if not ip or not _is_public_ip(ip):
            return
        geo = _lookup(ip)
        if not geo:
            return
        from app.db import SessionLocal
        db = SessionLocal()
        try:
            db.add(VisitorGeo(country=geo["country"], region=geo["region"], page=page[:120]))
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.debug("Geo record skipped: %s", exc)


# ── Admin analytics ──────────────────────────────────────────────────────────

def get_geo_summary(db: Session, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))
    base = db.query(VisitorGeo).filter(VisitorGeo.created_at >= since)
    total = base.count()

    countries = (
        db.query(VisitorGeo.country, func.count(VisitorGeo.id))
        .filter(VisitorGeo.created_at >= since)
        .group_by(VisitorGeo.country)
        .order_by(func.count(VisitorGeo.id).desc())
        .limit(15)
        .all()
    )
    us_regions = (
        db.query(VisitorGeo.region, func.count(VisitorGeo.id))
        .filter(VisitorGeo.created_at >= since, VisitorGeo.country == "US", VisitorGeo.region != "")
        .group_by(VisitorGeo.region)
        .order_by(func.count(VisitorGeo.id).desc())
        .limit(15)
        .all()
    )
    us_count = base.filter(VisitorGeo.country == "US").count()

    # Daily trend (SQLite-safe: aggregate in Python by date).
    rows = base.order_by(VisitorGeo.created_at.asc()).all()
    trend: dict[str, dict] = {}
    for r in rows:
        day = (r.created_at.date().isoformat() if r.created_at else "unknown")
        d = trend.setdefault(day, {"date": day, "total": 0, "us": 0})
        d["total"] += 1
        if r.country == "US":
            d["us"] += 1

    return {
        "days": days,
        "total_located_visits": total,
        "pct_usa": round(100.0 * us_count / total, 1) if total else 0.0,
        "top_countries": [{"country": c, "visits": n} for c, n in countries],
        "top_us_regions": [{"region": r, "visits": n} for r, n in us_regions],
        "trend": sorted(trend.values(), key=lambda d: d["date"]),
    }
