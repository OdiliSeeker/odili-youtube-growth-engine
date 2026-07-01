"""
Subscriber tagging — lightweight funnel segmentation.

Every signup is tagged so the mailing list can later be segmented and automated:

    • ``new-lead``     — applied to everyone who subscribes
    • ``voter``        — subscribed via a topic vote popup (+ the topic name)
    • ``contributor``  — subscribed via a topic-request submission (+ the topic)

Tags are stored one row per (subscriber, tag) in ``subscriber_tags`` and applied
idempotently, so re-subscribing or voting again never creates duplicates.
"""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import Subscriber, SubscriberTag

logger = logging.getLogger(__name__)


def _add_tag(db: Session, *, subscriber_id: int, tag: str, source: str | None) -> None:
    """Insert one (subscriber, tag) row, ignoring duplicates."""
    tag = (tag or "").strip()[:120]
    if not tag:
        return
    exists = (
        db.query(SubscriberTag)
        .filter(
            SubscriberTag.subscriber_id == subscriber_id,
            SubscriberTag.tag == tag,
        )
        .first()
    )
    if exists:
        return
    db.add(SubscriberTag(subscriber_id=subscriber_id, tag=tag, source=source))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # lost a race — the tag already exists, which is fine


def apply_signup_tags(
    db: Session, *, email: str, source: str | None, interest: str | None = None
) -> list[str]:
    """
    Apply funnel tags for a subscriber based on how they signed up.

    Returns the list of tags applied (for logging/testing). Safe to call on
    existing subscribers — tags are idempotent, so an existing subscriber who
    votes still earns the ``voter`` tag without duplicating ``new-lead``.
    """
    sub = db.query(Subscriber).filter(Subscriber.email == email.strip().lower()).first()
    if sub is None:
        return []

    src = (source or "landing_page").strip().lower()[:60]

    tags = ["new-lead"]
    if src == "voter":
        tags.append("voter")
    elif src == "contributor":
        tags.append("contributor")

    interest = (interest or "").strip()[:120]
    if interest and src in ("voter", "contributor"):
        tags.append(interest)

    for tag in tags:
        _add_tag(db, subscriber_id=sub.id, tag=tag, source=src)
    return tags
