"""
Funnel analytics + auto-optimization.

Stores lightweight behavior events (page views, CTA clicks, scroll depth,
headline variants, topic clicks, signups) and derives:

  • funnel metrics for the admin dashboard (:func:`get_summary`)
  • an auto-selected best-converting headline (:func:`get_best_headline`)
  • topic engagement scores for auto-prioritization (:func:`topic_engagement_scores`)

All metrics are event-driven (single source of truth) and aggregated in Python
over loaded rows, so we never depend on the SQLite JSON1 extension. ``signup``
events — fired by the landing page on a successful subscribe with the headline
and interest the visitor saw — are what attribute conversions.
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.db_models import Event
from app.services.headlines import HEADLINES_SET

logger = logging.getLogger(__name__)

# Events the public /track endpoint accepts. Anything else is rejected so
# visitors cannot spam arbitrary rows into the table.
ALLOWED_EVENTS = {
    "page_view",
    "cta_click",
    "topic_click",
    "video_loaded",
    "scroll_depth",
    "headline_variant",
    "signup",
    "vote",
    "discover_click",
}

_MAX_DATA_BYTES = 2000  # cap stored JSON size per event
_SCROLL_LEVELS = [25, 50, 75, 100]

# Acquisition sources the public funnel may claim (?src= on inbound links).
# Extended for the Lead Evangelist so every platform's outreach is attributable.
_ALLOWED_SRC = {"youtube", "email", "facebook", "tiktok", "instagram", "reddit", "x"}

# Auto-optimization safety guards (spec PART 5).
_MIN_TOTAL_VISITS = 50    # don't auto-pick a headline until enough traffic
_MIN_HEADLINE_VIEWS = 20  # ignore headlines with too few views (noise floor)
_BEST_HEADLINE_TTL = 600  # cache the best-headline result for 10 minutes


def _naive_utc_cutoff(days: int) -> datetime:
    """A naive UTC cutoff that compares correctly against SQLite's stored
    (naive) timestamps — see the SQLite DateTime note in the drip service."""
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


def _sanitize(event_name: str, data: dict) -> dict:
    """Drop untrusted/invalid fields from a public event payload.

    The /track endpoint is public, so we cannot trust the contents. We only
    keep ``headline`` values that match a real A/B variant (prevents biasing
    best-headline selection or defacing the live H1) and only well-formed
    scroll percentages.
    """
    clean = dict(data)
    if event_name in ("headline_variant", "signup"):
        h = clean.get("headline")
        if h is not None and h not in HEADLINES_SET:
            clean.pop("headline", None)
    if event_name == "scroll_depth":
        try:
            if int(clean.get("percent")) not in _SCROLL_LEVELS:
                clean.pop("percent", None)
        except (TypeError, ValueError):
            clean.pop("percent", None)
    # Acquisition source + session id (page_view / signup): allow-list src,
    # cap session_id to a short opaque token so visitors can't stuff data.
    src = clean.get("src")
    if src is not None and src not in _ALLOWED_SRC:
        clean.pop("src", None)
    sid = clean.get("session_id")
    if sid is not None and not (isinstance(sid, str) and 1 <= len(sid) <= 40 and sid.replace("-", "").isalnum()):
        clean.pop("session_id", None)
    return clean


def record_event(db: Session, *, event_name: str, data: dict | None = None) -> bool:
    """Persist one analytics event. Returns False if the event isn't allowed."""
    name = (event_name or "").strip()
    if name not in ALLOWED_EVENTS:
        return False
    payload = None
    if data:
        try:
            payload = json.dumps(_sanitize(name, data), ensure_ascii=False)[:_MAX_DATA_BYTES]
        except (TypeError, ValueError):
            payload = None
    db.add(Event(event_name=name, data=payload))
    db.commit()
    return True


def _data_of(ev: Event) -> dict:
    if not ev.data:
        return {}
    try:
        parsed = json.loads(ev.data)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _load_events(db: Session, *, days: int | None = None) -> list[Event]:
    q = db.query(Event)
    if days and days > 0:
        q = q.filter(Event.created_at >= _naive_utc_cutoff(days))
    return q.all()


def get_summary(db: Session, *, days: int | None = None) -> dict:
    """Aggregate funnel metrics for the admin Analytics dashboard.

    Everything is derived from tracked events so the numbers are internally
    consistent: conversions are ``signup`` events (not the all-time subscriber
    count), which keeps ``conversion_rate`` a true funnel rate.
    """
    events = _load_events(db, days=days)

    total_visits = 0
    cta_clicks = 0
    signups = 0
    votes = 0
    headline_views: dict[str, int] = {}
    topic_clicks: dict[str, int] = {}
    interest_counts: dict[str, int] = {}
    signup_sources: dict[str, int] = {}
    scroll_depth = {str(level): 0 for level in _SCROLL_LEVELS}

    for ev in events:
        if ev.event_name == "page_view":
            total_visits += 1
        elif ev.event_name == "cta_click":
            cta_clicks += 1
        elif ev.event_name == "vote":
            votes += 1
        elif ev.event_name == "signup":
            signups += 1
            d = _data_of(ev)
            i = str(d.get("interest", "")).strip()
            if i:
                interest_counts[i] = interest_counts.get(i, 0) + 1
            s = str(d.get("source", "")).strip() or "landing_page"
            signup_sources[s] = signup_sources.get(s, 0) + 1
        elif ev.event_name == "headline_variant":
            h = str(_data_of(ev).get("headline", "")).strip()
            if h:
                headline_views[h] = headline_views.get(h, 0) + 1
        elif ev.event_name == "topic_click":
            t = str(_data_of(ev).get("topic", "")).strip()
            if t:
                topic_clicks[t] = topic_clicks.get(t, 0) + 1
        elif ev.event_name == "scroll_depth":
            p = str(_data_of(ev).get("percent", "")).strip()
            if p in scroll_depth:
                scroll_depth[p] += 1

    conversion_rate = (
        round((signups / total_visits) * 100, 1) if total_visits else 0.0
    )

    top_headlines = [
        {"headline": h, "views": v}
        for h, v in sorted(headline_views.items(), key=lambda kv: -kv[1])
    ]
    top_topics = [
        {"topic": t, "count": c}
        for t, c in sorted(interest_counts.items(), key=lambda kv: -kv[1])
    ]

    return {
        "total_visits": total_visits,
        "cta_clicks": cta_clicks,
        "subscriptions": signups,
        "votes": votes,
        "conversion_rate": conversion_rate,
        "top_headlines": top_headlines,
        "top_topics": top_topics,
        "topic_clicks": topic_clicks,
        "signup_sources": signup_sources,
        "scroll_depth": scroll_depth,
        "window_days": days,
    }


# ── Auto-select best headline ──────────────────────────────────────────────
_best_cache: dict = {"ts": 0.0, "value": None}


def get_best_headline(db: Session, *, force: bool = False) -> str | None:
    """The highest-converting headline once enough data exists, else ``None``.

    Conversion is attributed inside the Event table: ``headline_variant`` events
    count views; ``signup`` events (fired on subscribe with the seen headline)
    count conversions. Both are validated against the real headline set at write
    time. Guards: ≥50 total visits and ≥20 views per headline. Result is cached
    for 10 minutes to avoid recomputing on every page load.
    """
    now = time.time()
    if not force and (now - _best_cache["ts"]) < _BEST_HEADLINE_TTL:
        return _best_cache["value"]

    views: dict[str, int] = {}
    conversions: dict[str, int] = {}
    total_visits = 0
    for ev in db.query(Event).all():
        if ev.event_name == "page_view":
            total_visits += 1
        elif ev.event_name == "headline_variant":
            h = str(_data_of(ev).get("headline", "")).strip()
            if h in HEADLINES_SET:  # ignore retired headlines from old A/B sets
                views[h] = views.get(h, 0) + 1
        elif ev.event_name == "signup":
            h = str(_data_of(ev).get("headline", "")).strip()
            if h in HEADLINES_SET:
                conversions[h] = conversions.get(h, 0) + 1

    best: str | None = None
    if total_visits >= _MIN_TOTAL_VISITS:
        best_rate = -1.0
        for headline, view_count in views.items():
            if view_count < _MIN_HEADLINE_VIEWS:
                continue
            rate = conversions.get(headline, 0) / view_count
            if rate > best_rate:
                best_rate = rate
                best = headline

    _best_cache["ts"] = now
    _best_cache["value"] = best
    return best


def topic_engagement_scores(db: Session) -> dict[str, int]:
    """Map ``topic title (lowercased)`` → engagement score.

    score = topic_click count + 3 × signups whose interest matches the title.
    Both signals come from tracked events (single source of truth). Returns an
    empty dict when there's no tracking data yet, so callers fall back cleanly
    to their manual ordering. Matching is by lowercased title, so a topic only
    earns a score once its title aligns with the clicked/selected interest label.
    """
    clicks: dict[str, int] = {}
    signups: dict[str, int] = {}
    for ev in db.query(Event).filter(
        Event.event_name.in_(["topic_click", "signup"])
    ).all():
        d = _data_of(ev)
        if ev.event_name == "topic_click":
            t = str(d.get("topic", "")).strip().lower()
            if t:
                clicks[t] = clicks.get(t, 0) + 1
        else:  # signup
            i = str(d.get("interest", "")).strip().lower()
            if i:
                signups[i] = signups.get(i, 0) + 1

    scores: dict[str, int] = {}
    for key in set(clicks) | set(signups):
        scores[key] = clicks.get(key, 0) + 3 * signups.get(key, 0)
    return scores
