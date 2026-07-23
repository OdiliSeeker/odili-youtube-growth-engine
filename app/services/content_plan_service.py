"""
Content planning engine — vote data → ranked video plan (spec PART 3 + 5).

Turns audience demand signals into a concrete "make this next" list:

    score = 2×votes + 3×votes_last_7d + subscriber interest tags
            + engagement (topic clicks + 3×signups) + 2×email clicks

All aggregation is pure Python over existing tables (Topic, TopicVote,
SubscriberTag, Event) — deterministic, instant, no AI required. Suggested
angles/titles/hooks/outlines are template-built so the endpoint never 402s.

Also raises "High Demand" alerts for topics surging in the last 7 days.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.db_models import Event, SubscriberTag, Topic, TopicVote
from app.services.analytics_service import topic_engagement_scores

logger = logging.getLogger(__name__)

SURGE_MIN_7D = 3      # votes in the last 7 days that count as "surging"
HIGH_DEMAND_TOTAL = 10  # total votes that always warrant an alert


def _naive_utc_cutoff(days: int) -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


def _email_clicks_by_topic(db: Session) -> dict[int, int]:
    """topic_id → email_click count (from /go/{queue_id} redirects)."""
    counts: dict[int, int] = {}
    for ev in db.query(Event).filter(Event.event_name == "email_click").all():
        try:
            d = json.loads(ev.data) if ev.data else {}
        except (TypeError, ValueError):
            continue
        tid = d.get("topic_id")
        if isinstance(tid, int):
            counts[tid] = counts.get(tid, 0) + 1
    return counts


def _votes_last_7d(db: Session) -> dict[int, int]:
    cutoff = _naive_utc_cutoff(7)
    rows = (
        db.query(TopicVote.topic_id, func.count(TopicVote.id))
        .filter(TopicVote.created_at >= cutoff)
        .group_by(TopicVote.topic_id)
        .all()
    )
    return {tid: n for tid, n in rows}


def _tag_counts(db: Session, titles_lower: dict[str, int]) -> dict[int, int]:
    """topic_id → count of subscriber interest tags matching the topic title."""
    counts: dict[int, int] = {}
    if not titles_lower:
        return counts
    rows = (
        db.query(func.lower(SubscriberTag.tag), func.count(SubscriberTag.id))
        .group_by(func.lower(SubscriberTag.tag))
        .all()
    )
    for tag, n in rows:
        tid = titles_lower.get(tag)
        if tid is not None:
            counts[tid] = counts.get(tid, 0) + n
    return counts


# ── Deterministic creative suggestions ──────────────────────────────────────

def _suggestions(title: str) -> dict:
    t = title.rstrip("?.!")
    return {
        "suggested_angle": (
            f"Open with the tension: most people assume they already know the answer to \"{t}\" — "
            "then show what Scripture and the early Church actually say, step by step."
        ),
        "suggested_title": f"The Truth About {t} (What Most Christians Were Never Told)",
        "suggested_hook": (
            f"Everything you think you know about {t.lower()} might be missing one crucial piece — "
            "and it was written down in the first centuries of the Church."
        ),
        "thumbnail_idea": (
            "Close-up face, shocked/serious expression, dark background with gold text: "
            f"3-5 word version of the claim (e.g. \"{t[:28]}...\"), high contrast."
        ),
        "script_outline": [
            "HOOK (0:00) — state the tension in one sentence, promise the answer.",
            "BUILD (0:30) — what people commonly believe, and why it feels convincing.",
            "EVIDENCE (1:30) — Scripture first, then the early Church Fathers / Magisterium.",
            "DELIVER (3:30) — the full Catholic answer, plainly stated.",
            "CTA (4:30) — 'Get the full teaching by email' → landing page link.",
        ],
    }


def _why(votes: int, recent: int, tags: int, engagement: int, clicks: int) -> str:
    parts = []
    if recent:
        parts.append(f"{recent} vote{'s' if recent != 1 else ''} in the last 7 days")
    if votes:
        parts.append(f"{votes} total vote{'s' if votes != 1 else ''}")
    if tags:
        parts.append(f"{tags} subscriber{'s' if tags != 1 else ''} tagged with this interest")
    if engagement:
        parts.append("strong landing-page engagement")
    if clicks:
        parts.append(f"{clicks} email click{'s' if clicks != 1 else ''}")
    return "Demand signals: " + ", ".join(parts) + "." if parts else "No demand signals yet — manual pick."


def _enrich_with_growth_brain(entry: dict) -> None:
    """Attach a Growth Brain title score + trigger phrases (fail-silent, additive).

    Pure-deterministic (no AI / no quota) so the content plan never blocks or 402s.
    """
    try:
        from app.services import click_trigger_library, title_scorer

        scored = title_scorer.score_title(entry["suggested_title"])
        entry["title_score"] = scored.get("score")
        entry["title_verdict"] = scored.get("verdict")
        entry["trigger_phrases"] = click_trigger_library.top_phrases(entry["topic"])
    except Exception as exc:  # noqa: BLE001 — enrichment must never break the plan
        logger.info("Content-plan Growth Brain enrichment skipped (%s)", exc)


def get_plan(db: Session, *, limit: int = 5) -> dict:
    """Ranked content plan + high-demand alerts."""
    topics = db.query(Topic).filter(Topic.status.in_(("featured", "approved"))).all()
    titles_lower = {t.title.strip().lower(): t.id for t in topics}

    recent_votes = _votes_last_7d(db)
    tag_counts = _tag_counts(db, titles_lower)
    engagement = topic_engagement_scores(db)
    email_clicks = _email_clicks_by_topic(db)

    ranked = []
    for t in topics:
        recent = recent_votes.get(t.id, 0)
        tags = tag_counts.get(t.id, 0)
        eng = engagement.get(t.title.strip().lower(), 0)
        clicks = email_clicks.get(t.id, 0)
        score = 2 * (t.votes or 0) + 3 * recent + tags + eng + 2 * clicks
        ranked.append((score, recent, t, tags, eng, clicks))

    ranked.sort(key=lambda r: (-r[0], -(r[2].votes or 0), r[2].id))

    plan = []
    for score, recent, t, tags, eng, clicks in ranked[:limit]:
        entry = {
            "topic_id": t.id,
            "topic": t.title,
            "votes": t.votes or 0,
            "votes_last_7_days": recent,
            "subscriber_tags": tags,
            "email_clicks": clicks,
            "score": score,
            "why": _why(t.votes or 0, recent, tags, eng, clicks),
        }
        entry.update(_suggestions(t.title))
        _enrich_with_growth_brain(entry)
        plan.append(entry)

    alerts = []
    for score, recent, t, tags, eng, clicks in ranked:
        if recent >= SURGE_MIN_7D or (t.votes or 0) >= HIGH_DEMAND_TOTAL:
            alerts.append({
                "topic_id": t.id,
                "topic": t.title,
                "message": f"⚡ \"{t.title}\" is surging ({recent} votes this week, {t.votes or 0} total) — consider making this next.",
            })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan": plan,
        "alerts": alerts,
    }
