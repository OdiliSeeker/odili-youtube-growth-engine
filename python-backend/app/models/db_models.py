from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Text, Boolean, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Topic the visitor clicked before subscribing (conversion entry point) — nullable.
    interest: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Drip-sequence progress: number of drip emails already accounted for (0..5).
    # 0 = brand new (email 1 pending), 5 = full sequence complete.
    drip_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Subscriber email={self.email!r} active={self.active} drip_step={self.drip_step}>"


class NewsletterLog(Base):
    __tablename__ = "newsletter_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    recipients_total: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(50), default="manual")  # "manual" | "scheduler"
    failures_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of failures


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    hook: Mapped[str] = mapped_column(Text, nullable=False)
    script: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<Script id={self.id} topic={self.topic!r}>"


class YouTubePackage(Base):
    __tablename__ = "youtube_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    script_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_text: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<YouTubePackage id={self.id} title={self.title!r}>"


class PipelineItem(Base):
    """A content item moving through the Growth Engine pipeline.

    Stages: idea → script → package → published.
    """

    __tablename__ = "pipeline_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), default="idea", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    package_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    def __repr__(self) -> str:
        return f"<PipelineItem id={self.id} stage={self.stage!r} title={self.title!r}>"


class AppSetting(Base):
    """Tiny key-value store for admin-tunable settings (e.g. posting days).

    Auto-created via ``create_all``; one row per setting key.
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    def __repr__(self) -> str:
        return f"<AppSetting key={self.key!r}>"


class ContentSchedule(Base):
    """A scheduled video on the weekly posting calendar.

    Statuses: scheduled → posted.
    """

    __tablename__ = "content_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    script_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    package_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pipeline_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scheduled_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="scheduled", nullable=False, index=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )

    def __repr__(self) -> str:
        return f"<ContentSchedule id={self.id} status={self.status!r} title={self.title!r}>"


class VideoPerformance(Base):
    """A logged performance record for a published video (Performance Feedback).

    Verdicts: worked | mixed | failed.
    """

    __tablename__ = "video_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verdict: Mapped[str] = mapped_column(String(20), default="mixed", nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<VideoPerformance id={self.id} verdict={self.verdict!r} title={self.title!r}>"


class Topic(Base):
    """A topic shown on the public funnel for visitors to vote on or request.

    status: suggested (visitor request, awaiting review) | approved | featured | archived
    source: admin (curated) | visitor (submitted via the public request form)
    Only 'approved' and 'featured' topics are shown publicly.
    """

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="suggested", nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), default="admin", nullable=False)
    # Manual display order for the public list (lower = earlier). Admin-controlled.
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<Topic id={self.id} status={self.status!r} votes={self.votes} title={self.title!r}>"


class Event(Base):
    """A lightweight funnel-analytics event (page view, CTA click, scroll, etc.).

    ``event_name`` is allow-listed at the API layer; ``data`` is a small JSON
    object stored as text. New table — auto-created via ``create_all``.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON object
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<Event id={self.id} event_name={self.event_name!r}>"


class TopicVote(Base):
    """One vote per (topic, voter) — voter identified by a salted hash of their IP."""

    __tablename__ = "topic_votes"
    __table_args__ = (UniqueConstraint("topic_id", "voter_hash", name="uq_topic_voter"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    voter_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SubscriberTag(Base):
    """A funnel tag attached to a subscriber (segmentation + automation).

    Applied automatically on signup: everyone gets ``new-lead``; voters get
    ``voter`` + the topic name; topic submitters get ``contributor`` + the topic.
    ``source`` records which funnel step created the tag (landing_page / voter /
    contributor). One row per (subscriber, tag) — new table, auto-created via
    ``create_all``.
    """

    __tablename__ = "subscriber_tags"
    __table_args__ = (UniqueConstraint("subscriber_id", "tag", name="uq_subscriber_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def __repr__(self) -> str:
        return f"<SubscriberTag sub={self.subscriber_id} tag={self.tag!r}>"
