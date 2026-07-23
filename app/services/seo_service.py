"""
SEO engine service (spec PART 3 / PART 4 / PART 7).

Three generators — keywords, video SEO, and full articles — plus Article CRUD
for the public ``/truth/{slug}`` blog. Every generator is DETERMINISTIC-FIRST:
a pure-Python template always produces usable output; the OpenAI call only
*enriches* it and any AI failure silently keeps the deterministic result, so
these endpoints NEVER 402 (matches the Growth/Content philosophy).

Articles cross-link to the landing page (?src=... ) and a YouTube video to close
the Traffic Engine loop (PART 7).
"""

import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.db_models import Article

logger = logging.getLogger(__name__)

_STOP = {"the", "a", "an", "of", "to", "and", "or", "is", "are", "why", "what",
         "how", "did", "do", "does", "about", "for", "in", "on", "was", "were"}


def _safe_url(v, limit: int = 500) -> str | None:
    u = str(v or "").strip()[:limit]
    return u if u.lower().startswith(("http://", "https://")) else None


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:80] or "teaching"


def unique_slug(db: Session, title: str) -> str:
    base = slugify(title)
    slug = base
    i = 2
    while db.query(Article).filter(Article.slug == slug).first() is not None:
        slug = f"{base}-{i}"
        i += 1
    return slug


def _landing_link(src: str = "article") -> str:
    from app.services.token_service import get_base_url
    return f"{get_base_url()}/?src={src}"


def _youtube_link() -> str:
    from app.branding import YOUTUBE_URL
    return YOUTUBE_URL


# ── Keyword generator ────────────────────────────────────────────────────────

def _deterministic_keywords(topic: str) -> list[str]:
    t = topic.strip().rstrip("?.!")
    tl = t.lower()
    return [
        f"what does the Catholic Church teach about {tl}",
        f"{tl} explained catholic",
        f"is {tl} biblical",
        f"catholic answers {tl}",
        f"history of {tl} in the early church",
        f"church fathers on {tl}",
        f"scripture verses about {tl}",
        f"protestant vs catholic view of {tl}",
        f"why do catholics believe in {tl}",
        f"the truth about {tl}",
    ]


async def generate_keywords(topic: str) -> dict:
    topic = (topic or "").strip()
    if not topic:
        return {"topic": topic, "keywords": [], "source": "empty"}
    keywords = _deterministic_keywords(topic)
    source = "deterministic"
    try:
        from app.services.ai_service import generate_with_ai
        prompt = (
            f"List 10 high-intent Google search queries a truth-seeker would type about "
            f"'{topic}' from a Catholic perspective. One query per line, no numbering, "
            f"no extra text. Keep each under 12 words."
        )
        raw = await generate_with_ai(prompt)
        lines = [
            re.sub(r"^[\d\.\)\-\*\s]+", "", ln).strip()
            for ln in raw.splitlines() if ln.strip()
        ]
        lines = [ln for ln in lines if 3 <= len(ln) <= 120][:10]
        if len(lines) >= 5:
            keywords = lines
            source = "ai"
    except Exception as exc:  # noqa: BLE001 — never 402, keep deterministic
        logger.info("Keyword AI enrich skipped: %s", exc)

    # Growth Brain: blend in US-targeted, question-based search demand so SEO
    # keywords lean American. Fail-silent — never blocks keyword generation.
    us_keywords: list[str] = []
    try:
        from app.services import us_keyword_engine
        us = await us_keyword_engine.generate_us_keywords(topic)
        us_keywords = (us.get("questions") or []) + (us.get("long_tail_keywords") or [])
        seen = {k.lower() for k in keywords}
        for k in us_keywords:
            if k.lower() not in seen:
                keywords.append(k)
                seen.add(k.lower())
    except Exception as exc:  # noqa: BLE001 — never blocks
        logger.info("US keyword blend skipped: %s", exc)

    return {"topic": topic, "keywords": keywords, "source": source, "us_keywords": us_keywords}


# ── Video SEO generator ──────────────────────────────────────────────────────

def _deterministic_video_seo(topic: str) -> dict:
    t = topic.strip().rstrip("?.!")
    tl = t.lower()
    words = [w for w in re.split(r"[^a-z0-9]+", tl) if w and w not in _STOP]
    tags = list(dict.fromkeys(
        words + ["catholic", "apologetics", "scripture", "church fathers",
                 "truth", "faith", "bible", "tradition"]
    ))[:15]
    description = "\n".join([
        f"The truth about {tl} — rooted in Scripture, Tradition, and 2,000 years of Catholic teaching.",
        "",
        "Something doesn't add up, and deep down you've probably sensed it. In this video we go "
        f"deeper into {tl} than most people have ever been told.",
        "",
        f"Get the full teaching free → {_landing_link('youtube')}",
        f"Subscribe on YouTube → {_youtube_link()}",
        "",
        "#Catholic #Apologetics #Truth",
    ])
    return {
        "title": f"The Truth About {t} (What the Early Church Really Believed)",
        "description": description,
        "tags": tags,
    }


async def generate_video_seo(topic: str) -> dict:
    topic = (topic or "").strip()
    if not topic:
        return {"topic": topic, "source": "empty", "title": "", "description": "", "tags": []}
    result = _deterministic_video_seo(topic)
    result["topic"] = topic
    result["source"] = "deterministic"
    try:
        from app.services.ai_service import generate_with_ai
        prompt = (
            f"Write a YouTube title (<70 chars, curiosity-driven) for a Catholic video about "
            f"'{topic}'. Output ONLY the title on one line."
        )
        raw = (await generate_with_ai(prompt)).strip().splitlines()[0].strip().strip('"')
        if 8 <= len(raw) <= 90:
            result["title"] = raw
            result["source"] = "ai"
    except Exception as exc:  # noqa: BLE001
        logger.info("Video SEO AI enrich skipped: %s", exc)
    return result


# ── Article generator + CRUD ─────────────────────────────────────────────────

def _deterministic_article_body(topic: str, video_url: str | None) -> str:
    t = topic.strip().rstrip("?.!")
    tl = t.lower()
    landing = _landing_link("article")
    yt = _safe_url(video_url) or _youtube_link()
    paras = [
        f"Something doesn't add up about {tl} — and if you've felt that quiet unease, you are not alone. "
        f"For centuries, faithful Catholics have wrestled with this very question, and the answer runs "
        f"deeper than most people have ever been told.",
        f"To understand {tl}, we have to begin where the Church always begins: with Sacred Scripture and "
        f"the living Tradition handed down from the Apostles. The earliest Christians did not invent their "
        f"beliefs in a vacuum. They received them, guarded them, and were willing to die for them.",
        f"The Church Fathers — men who learned the faith from the Apostles themselves or their immediate "
        f"successors — spoke clearly on matters surrounding {tl}. Their witness is not a footnote to history; "
        f"it is a window into what the first Christians actually believed and practiced.",
        f"Objections to the Catholic understanding of {tl} are worth taking seriously. But when we examine "
        f"them fairly, we find that the fullest, most historically grounded answer is the one the Catholic "
        f"Church has always taught. The pieces fit together in a way that no other account can match.",
        f"This matters because truth is not merely academic. What you believe about {tl} shapes how you pray, "
        f"how you worship, and how you understand your own salvation. The stakes could not be higher.",
        f"If this has raised more questions than it answered — good. That means you are seeking. And seekers "
        f"are exactly who the Odili Truth Seeker ministry exists to serve.",
        f"Watch the full teaching on video here: {yt}",
        f"And get the complete teaching, free, delivered to your inbox: {landing}",
    ]
    return "\n\n".join(paras)


async def generate_article(db: Session, topic: str, *, video_url: str | None = None, status: str = "published") -> dict | None:
    topic = (topic or "").strip()
    if not topic:
        return None
    t = topic.rstrip("?.!")
    title = f"The Truth About {t}: What the Early Church Really Believed"
    body = _deterministic_article_body(topic, video_url)
    meta = f"A Catholic teaching on {t.lower()} — rooted in Scripture, the Church Fathers, and Tradition."[:315]
    source = "deterministic"

    try:
        from app.services.ai_service import generate_with_ai
        landing = _landing_link("article")
        yt = _safe_url(video_url) or _youtube_link()
        prompt = (
            f"Write an 800-1200 word Catholic teaching article about '{topic}'. "
            f"Ground it in Scripture, the Church Fathers, and Catholic Tradition. "
            f"Warm, clear, evangelistic tone. Plain text, one paragraph per line, no markdown headings. "
            f"End with two short calls to action: watch the video at {yt} and get the free email teaching at {landing}."
        )
        raw = (await generate_with_ai(prompt)).strip()
        if len(raw.split()) >= 300:
            body = raw
            source = "ai"
    except Exception as exc:  # noqa: BLE001 — never 402
        logger.info("Article AI enrich skipped: %s", exc)

    slug = unique_slug(db, title)
    article = Article(
        slug=slug, title=title, body=body, meta_description=meta,
        video_url=_safe_url(video_url), topic=topic, status=status,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    result = _serialize(article)
    result["source"] = source
    result["word_count"] = len(body.split())
    return result


def _serialize(a: Article, *, full: bool = True) -> dict:
    d = {
        "id": a.id,
        "slug": a.slug,
        "title": a.title,
        "meta_description": a.meta_description,
        "video_url": a.video_url,
        "topic": a.topic,
        "status": a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
    if full:
        d["body"] = a.body
    return d


def list_articles(db: Session, *, published_only: bool = False, limit: int = 100) -> list[dict]:
    q = db.query(Article)
    if published_only:
        q = q.filter(Article.status == "published")
    rows = q.order_by(Article.created_at.desc()).limit(limit).all()
    return [_serialize(r, full=False) for r in rows]


def get_by_slug(db: Session, slug: str) -> Article | None:
    return db.query(Article).filter(Article.slug == slug).first()


def delete_article(db: Session, article_id: int) -> bool:
    a = db.query(Article).filter(Article.id == article_id).first()
    if a is None:
        return False
    db.delete(a)
    db.commit()
    return True
