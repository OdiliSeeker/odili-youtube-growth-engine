"""
Topic engagement service.

Powers the PUBLIC funnel's topic section (suggested topics, voting, requests)
and the ADMIN curation view. No AI required — this is a simple, durable
visitor-engagement loop:

  Visitors  → browse approved/featured topics, vote, and request new ones.
  Odili     → reviews requests, approves/features the best, archives the rest.

Voting is deduplicated per visitor using a salted hash of their IP so the same
person cannot inflate a topic's count by clicking repeatedly.
"""

import hashlib
import logging
import os

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import Topic, TopicVote

logger = logging.getLogger(__name__)

PUBLIC_STATUSES = ("featured", "approved")
VALID_STATUSES = ("suggested", "approved", "featured", "archived")

# Seeded once on first boot so the public page is never empty.
_DEFAULT_TOPICS = [
    ("What were Christians REALLY called before the word \u201cChristian\u201d?",
     "The forgotten identity the early believers actually carried.", "featured"),
    ("The truth about Purgatory the modern world forgot",
     "Where it comes from and why the early Church believed it.", "featured"),
    ("Did the Catholic Church really give us the Bible?",
     "The untold story of how Scripture was discerned and preserved.", "approved"),
    ("The Eucharist: just a symbol, or the real presence?",
     "What the first Christians believed about the bread and wine.", "approved"),
    ("Mary in the Bible \u2014 what most people miss",
     "The Scriptural roots of Catholic devotion to the Mother of God.", "approved"),
    ("Why the early Church was unmistakably Catholic",
     "The evidence from the first three centuries.", "approved"),
]


def _voter_hash(ip: str) -> str:
    """Salted SHA-256 of the voter's IP. Salt = SESSION_SECRET (never stores raw IP)."""
    salt = os.getenv("SESSION_SECRET", "odili-topic-salt")
    return hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()


def _serialize(t: Topic, *, public: bool, trending: bool = False, badge: str = "") -> dict:
    data = {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "votes": t.votes,
        "trending": trending,
        "badge": badge,
    }
    if not public:
        data["status"] = t.status
        data["source"] = t.source
        data["sort_order"] = t.sort_order
        data["created_at"] = t.created_at.isoformat() if t.created_at else None
    return data


# A topic is "trending" when it is among the public list AND has the highest
# vote count (with at least this many votes) — a light social-proof signal.
_TRENDING_MIN_VOTES = 3


def list_public_topics(db: Session) -> list[dict]:
    """Approved + featured topics, auto-prioritized by engagement.

    Order: featured first, then engagement score (clicks + 3×signups) desc, then
    the admin's manual order, then votes. When there's no tracking data yet all
    scores are 0, so this gracefully falls back to the manual featured/sort_order
    ordering. Top performers get a badge ("🔥 Most Chosen" / "Popular").
    """
    from app.services.analytics_service import topic_engagement_scores

    rows = (
        db.query(Topic)
        .filter(Topic.status.in_(PUBLIC_STATUSES))
        .all()
    )
    scores = topic_engagement_scores(db)

    def score_of(t: Topic) -> int:
        return scores.get((t.title or "").strip().lower(), 0)

    rows.sort(key=lambda t: (
        0 if t.status == "featured" else 1,
        -score_of(t),
        t.sort_order or 0,
        -t.votes,
        -(t.id or 0),
    ))

    # Badge the top engagement performers (only when they actually have a score).
    ranked = sorted(rows, key=lambda t: -score_of(t))
    badges: dict[int, str] = {}
    for rank, t in enumerate(ranked):
        if score_of(t) <= 0:
            break
        if rank == 0:
            badges[t.id] = "🔥 Most Chosen"
        elif rank <= 2:
            badges[t.id] = "Popular"

    top_votes = max((t.votes for t in rows), default=0)
    return [
        _serialize(
            t,
            public=True,
            trending=(t.votes == top_votes and top_votes >= _TRENDING_MIN_VOTES),
            badge=badges.get(t.id, ""),
        )
        for t in rows
    ]


def list_all_topics(db: Session) -> list[dict]:
    """Every topic for the admin view — pending requests surfaced first."""
    order = {"suggested": 0, "featured": 1, "approved": 2, "archived": 3}
    rows = db.query(Topic).all()
    rows.sort(key=lambda t: (order.get(t.status, 9), t.sort_order or 0, -(t.id or 0)))
    return [_serialize(t, public=False) for t in rows]


def reorder_topics(db: Session, *, ordered_ids: list[int]) -> int:
    """Assign sort_order to topics in the given id sequence (0-based). Returns count updated."""
    updated = 0
    for index, topic_id in enumerate(ordered_ids):
        result = (
            db.query(Topic)
            .filter(Topic.id == topic_id)
            .update({Topic.sort_order: index}, synchronize_session=False)
        )
        updated += result
    db.commit()
    return updated


def create_topic(
    db: Session,
    *,
    title: str,
    description: str | None = None,
    status: str = "approved",
    source: str = "admin",
) -> dict:
    if status not in VALID_STATUSES:
        status = "approved"
    topic = Topic(
        title=title.strip(),
        description=(description.strip() if description else None),
        status=status,
        source=source,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return _serialize(topic, public=False)


def submit_request(db: Session, *, title: str, description: str | None = None) -> dict:
    """A visitor-submitted topic — lands as 'suggested' for admin review."""
    return create_topic(
        db,
        title=title,
        description=description,
        status="suggested",
        source="visitor",
    )


def vote_topic(db: Session, *, topic_id: int, voter_ip: str) -> dict | None:
    """
    Register one vote for a public topic.

    Returns None if the topic does not exist or is not public.
    Otherwise returns {"votes": int, "counted": bool} — counted is False when
    this voter had already voted (idempotent, not an error).
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None or topic.status not in PUBLIC_STATUSES:
        return None

    vote = TopicVote(topic_id=topic_id, voter_hash=_voter_hash(voter_ip))
    db.add(vote)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"votes": topic.votes, "counted": False}

    # Increment at the DB level so concurrent votes can't clobber each other.
    db.query(Topic).filter(Topic.id == topic_id).update(
        {Topic.votes: Topic.votes + 1}, synchronize_session=False
    )
    db.commit()
    db.refresh(topic)
    return {"votes": topic.votes, "counted": True}


def unvote_topic(db: Session, *, topic_id: int, voter_ip: str) -> dict | None:
    """
    Withdraw this visitor's vote (toggle counterpart of vote_topic).

    Returns None if the topic does not exist or is not public.
    Otherwise returns {"votes": int, "removed": bool} — removed is False when
    this voter had no vote to withdraw (idempotent, not an error).
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None or topic.status not in PUBLIC_STATUSES:
        return None

    deleted = (
        db.query(TopicVote)
        .filter(TopicVote.topic_id == topic_id, TopicVote.voter_hash == _voter_hash(voter_ip))
        .delete(synchronize_session=False)
    )
    if not deleted:
        db.rollback()
        return {"votes": topic.votes, "removed": False}

    # Decrement at the DB level, floored at 0, so concurrent toggles can't clobber.
    db.query(Topic).filter(Topic.id == topic_id, Topic.votes > 0).update(
        {Topic.votes: Topic.votes - 1}, synchronize_session=False
    )
    db.commit()
    db.refresh(topic)
    return {"votes": topic.votes, "removed": True}


def update_topic(
    db: Session,
    *,
    topic_id: int,
    status: str | None = None,
    title: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
) -> dict | None:
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        return None
    if status is not None:
        if status not in VALID_STATUSES:
            return None
        topic.status = status
    if title is not None and title.strip():
        topic.title = title.strip()
    if description is not None:
        topic.description = description.strip() or None
    if sort_order is not None:
        topic.sort_order = sort_order
    db.commit()
    db.refresh(topic)
    return _serialize(topic, public=False)


def delete_topic(db: Session, *, topic_id: int) -> bool:
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        return False
    db.query(TopicVote).filter(TopicVote.topic_id == topic_id).delete()
    db.delete(topic)
    db.commit()
    return True


def seed_default_topics(db: Session) -> None:
    """Insert starter topics on first boot so the public page is never empty."""
    existing = db.query(func.count(Topic.id)).scalar() or 0
    if existing:
        return
    for title, description, status in _DEFAULT_TOPICS:
        db.add(Topic(title=title, description=description, status=status, source="admin"))
    db.commit()
    logger.info("Seeded %d default topics.", len(_DEFAULT_TOPICS))
