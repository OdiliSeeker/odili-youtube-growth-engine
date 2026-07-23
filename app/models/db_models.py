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


class VideoGridItem(Base):
    """An admin-managed video in the landing "Start Exploring the Truth" grid.

    Videos are grouped by ``category`` (one of the 6 fixed grid categories) and
    form the rotation pool: the public grid shows a rotating window of 3 per
    category. New table — auto-created via ``create_all``.
    """

    __tablename__ = "video_grid_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    youtube_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<VideoGridItem id={self.id} category={self.category!r} title={self.title!r}>"


class Article(Base):
    """An SEO/blog article rendered at the public ``/truth/{slug}`` route.

    Generated by the SEO engine (deterministic template + optional AI enrich),
    saved as a draft or published. Cross-links to a YouTube video + the landing
    page (Traffic Engine loop). New table — auto-created via ``create_all``.
    """

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)  # plain text, paragraph per line
    meta_description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="published", nullable=False, index=True)  # draft | published
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<Article id={self.id} slug={self.slug!r} status={self.status!r}>"


class EmailQueue(Base):
    """A queued outbound email awaiting admin approval (draft → approved → sent).

    Auto-drafted when a topic starts trending or a video is marked posted, or
    created manually from the content plan. Admin reviews/edits in the
    dashboard, then approves (send now or schedule). New table — auto-created
    via ``create_all``.
    """

    __tablename__ = "email_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)  # plain text, one paragraph per line
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)  # trending_topic | video_posted | content_plan | manual
    topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<EmailQueue id={self.id} status={self.status!r} subject={self.subject!r}>"


# ── Lead Discovery Engine ────────────────────────────────────────────────────
# Compliant, API-only YouTube lead discovery: watch channels, track their new
# uploads, scan public comments, and surface high-intent "seeker" comments for
# HUMAN review. Nothing here auto-replies or posts to YouTube. All four tables
# are new — auto-created via ``create_all`` (no ALTERs needed).

class WatchlistChannel(Base):
    """A YouTube channel the ministry watches for new uploads to scan.

    Resolved once via the YouTube Data API (channel id + uploads playlist) so
    subsequent polls cost only 1 quota unit each. ``category`` groups leads by
    theme. New table — auto-created via ``create_all``.
    """

    __tablename__ = "watchlist_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    handle: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    uploads_playlist_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<WatchlistChannel id={self.id} channel_id={self.channel_id!r} title={self.title!r}>"


class TrackedVideo(Base):
    """A video seen on a watched channel's uploads feed.

    Once ``scanned`` is True its comments have been fetched, so re-polling the
    channel never re-scans it (quota safety). New table — auto-created.
    """

    __tablename__ = "tracked_videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scanned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<TrackedVideo id={self.id} video_id={self.video_id!r} scanned={self.scanned}>"


class LeadComment(Base):
    """A high-intent public comment surfaced for HUMAN review (never auto-reply).

    ``review_status``: pending (awaiting review) | approved (fed into content
    systems) | skipped (dismissed). ``intent_score`` is a pure-Python heuristic
    (0..1); only comments scoring >= the save threshold are stored. The exact
    YouTube deep-link is rebuilt from ``video_id`` + ``comment_id``. New table.
    """

    __tablename__ = "lead_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    video_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    intent_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    generated_content: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON AI content pack
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<LeadComment id={self.id} score={self.intent_score} status={self.review_status!r}>"


class ApiQuotaLog(Base):
    """Daily YouTube Data API quota counter (one row per UTC date).

    Every metered API call increments today's row; scanning hard-stops once the
    daily safety cap is reached, resuming the next UTC day. New table.
    """

    __tablename__ = "api_quota_log"

    log_date: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD (UTC)
    units_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    def __repr__(self) -> str:
        return f"<ApiQuotaLog date={self.log_date!r} units_used={self.units_used}>"


class VisitorGeo(Base):
    """Privacy-safe visitor geography: coarse country/region ONLY — never raw IP.

    One row per tracked page view where a lookup succeeded. New table.
    """

    __tablename__ = "visitor_geo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country: Mapped[str] = mapped_column(String(4), nullable=False, index=True)   # ISO code e.g. "US"
    region: Mapped[str] = mapped_column(String(100), nullable=False, default="")  # e.g. "Maryland"
    page: Mapped[str] = mapped_column(String(120), nullable=False, default="/")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<VisitorGeo id={self.id} country={self.country!r} region={self.region!r}>"


class CtrPerformance(Base):
    """Tracks which generated CTR phrases are used and how they perform.

    ``phrase_type``: title | hook | cta. Clicks/conversions are incremented by
    admin logging endpoints — future scoring input. New table.
    """

    __tablename__ = "ctr_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phrase: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    phrase_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<CtrPerformance id={self.id} type={self.phrase_type!r} clicks={self.clicks}>"


class TitlePerformance(Base):
    """Growth Brain title memory: a scored title the admin saved, plus real
    clicks/CTR logged over time so future scoring can learn what performs.

    Deterministic score (0-100) captured at save time; clicks/ctr updated by
    admin logging. New table.
    """

    __tablename__ = "title_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<TitlePerformance id={self.id} score={self.score} clicks={self.clicks}>"


class EvangelistOutreach(Base):
    """Lead Evangelist outreach log: one row per human outreach action.

    The admin copies a personalized message, posts it manually on a platform,
    then logs it here so pace guidance (anti-spam) and conversion attribution
    work. ``status``: logged | responded | subscribed. New table.
    """

    __tablename__ = "evangelist_outreach"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    message_type: Mapped[str] = mapped_column(String(40), nullable=False, default="universal")
    message_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="logged", index=True)
    notes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<EvangelistOutreach id={self.id} platform={self.platform!r} status={self.status!r}>"


class PlaylistResource(Base):
    """Playlist Resources: curated authority sources (books, councils, Fathers).

    Evergreen Catholic knowledge base organized into 5 fixed sections; each
    resource can link to a source text and a YouTube teaching (insight-first
    conversion flow). ``tags`` is a JSON array string. New table, auto-creates.
    """

    __tablename__ = "playlist_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    relevance: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="book")
    source_name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    seo_title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    seo_description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    seo_keywords: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    def __repr__(self) -> str:
        return f"<PlaylistResource id={self.id} category={self.category!r} title={self.title!r}>"
