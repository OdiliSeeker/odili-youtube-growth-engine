"""
Persistent subscriber management backed by SQLite via SQLAlchemy.
Replaces the previous in-memory set.
"""

import logging
from sqlalchemy.orm import Session
from app.models.db_models import Subscriber

logger = logging.getLogger(__name__)


def add_email(db: Session, email: str) -> bool:
    """
    Add an email address to the subscriber list.
    Returns True if newly added, False if already subscribed (even if inactive).
    Re-activates a previously unsubscribed address.
    """
    email = email.strip().lower()
    existing = db.query(Subscriber).filter(Subscriber.email == email).first()
    if existing:
        if not existing.active:
            existing.active = True
            db.commit()
            logger.info("Reactivated subscriber: %s", email)
            return True
        return False
    subscriber = Subscriber(email=email)
    db.add(subscriber)
    db.commit()
    logger.info("New subscriber added: %s", email)
    return True


def remove_email(db: Session, email: str) -> bool:
    """
    Soft-delete a subscriber (sets active=False).
    Returns True if found and deactivated, False if not found.
    """
    email = email.strip().lower()
    subscriber = db.query(Subscriber).filter(
        Subscriber.email == email, Subscriber.active == True  # noqa: E712
    ).first()
    if not subscriber:
        return False
    subscriber.active = False
    db.commit()
    logger.info("Unsubscribed: %s", email)
    return True


def list_emails(db: Session) -> list[str]:
    """Return sorted list of all active subscriber email addresses."""
    rows = db.query(Subscriber.email).filter(Subscriber.active == True).order_by(Subscriber.email).all()  # noqa: E712
    return [row.email for row in rows]


def email_count(db: Session) -> int:
    """Return the number of active subscribers."""
    return db.query(Subscriber).filter(Subscriber.active == True).count()  # noqa: E712
