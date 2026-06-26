"""
Growth Engine service.

Pure helpers and AI generators that power the Growth Engine dashboard:
  - Weekly content plan generation (GPT-4o)
  - Viral hook generation (GPT-4o)
  - One-click content flow generators (idea bundle + YouTube package)
  - Deterministic CTA blocks (no AI / no quota needed)
  - Strategy-insight derivation from YouTube Intelligence data

Routes stay thin; all business logic lives here.
"""

import json
import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from app.branding import APP_NAME, YOUTUBE_URL
from app.services.ai_service import generate_with_ai

logger = logging.getLogger(__name__)

# Ordered pipeline stages used by the Content Pipeline Tracker.
PIPELINE_STAGES = ["idea", "script", "package", "published"]


# ── JSON parsing ──────────────────────────────────────────────────────────────

def parse_ai_json(raw: str) -> Any:
    """Parse JSON from an AI response, tolerating stray prose or code fences."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for opener, closer in (("{", "}"), ("[", "]")):
            start = raw.find(opener)
            end = raw.rfind(closer)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start:end + 1])
                except json.JSONDecodeError:
                    continue
        raise


# ── Weekly content plan ───────────────────────────────────────────────────────

_WEEKLY_PLAN_PROMPT = """You are planning one week of YouTube content for Odili Truth Seeker, a Catholic media ministry that teaches authentic Catholic faith, defends truth, and engages culture from a Catholic perspective.

Create a weekly content plan with EXACTLY 5 video ideas spread across different days of the week.

Return ONLY a valid JSON object (no markdown, no code fences, no preamble) in this exact structure:
{
  "plan": [
    {"day": "Sunday", "time": "09:00 UTC", "title": "<clickable YouTube title>", "idea": "<one-sentence concept>"}
  ]
}

Rules:
- Exactly 5 items.
- Vary the posting days across the week.
- Titles must be punchy, curiosity-driven, faith-rooted, and work as real YouTube titles. Favour truth-revelation, myth-breaking, salvation urgency, and identity over a flat teaching tone.
- Keep each "idea" to a single concise sentence."""


async def generate_weekly_plan() -> list[dict]:
    """Generate a 5-item weekly content plan via GPT-4o."""
    raw = await generate_with_ai(_WEEKLY_PLAN_PROMPT)
    data = parse_ai_json(raw)
    plan = data.get("plan", []) if isinstance(data, dict) else data
    if not isinstance(plan, list):
        raise ValueError("AI did not return a plan list.")
    cleaned: list[dict] = []
    for item in plan[:5]:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "day": str(item.get("day", "")).strip(),
            "time": str(item.get("time", "")).strip() or "09:00 UTC",
            "title": str(item.get("title", "")).strip(),
            "idea": str(item.get("idea", "")).strip(),
        })
    if not cleaned:
        raise ValueError("AI returned an empty plan.")
    return cleaned


# ── Hook optimization ─────────────────────────────────────────────────────────

_HOOKS_PROMPT = """You are a viral YouTube hook writer for Odili Truth Seeker, a Catholic media ministry.

Write EXACTLY 5 scroll-stopping opening hooks (the first 1-2 spoken lines of a video) for a video about:
{topic}

Each hook must grab attention instantly, create curiosity or tension, and stay faithful to authentic Catholic teaching. Vary the angles (question, bold claim, story, statistic, challenge).

Return ONLY a valid JSON object (no markdown, no code fences, no preamble):
{{"hooks": ["...", "...", "...", "...", "..."]}}"""


async def generate_hooks(topic: str) -> list[str]:
    """Generate 5 viral hooks for a topic via GPT-4o."""
    raw = await generate_with_ai(_HOOKS_PROMPT.format(topic=topic.strip()))
    data = parse_ai_json(raw)
    hooks = data.get("hooks", []) if isinstance(data, dict) else data
    hooks = [str(h).strip() for h in hooks if str(h).strip()]
    if not hooks:
        raise ValueError("AI returned no hooks.")
    return hooks[:5]


# ── One-click content flow ────────────────────────────────────────────────────

# Shared viral style directive (Part 7 — content style shift). No format braces.
_VIRAL_STYLE = (
    "STYLE (critical): Do NOT sound like a flat Bible lesson or generic teaching. "
    "Lead with TRUTH REVELATION, MYTH-BREAKING, SALVATION URGENCY, and IDENTITY "
    "(e.g. \"What Christians were REALLY called\"). Challenge a common assumption, "
    "open a curiosity gap, and make the viewer feel they MUST keep watching to "
    "know the truth. Stay faithful to authentic Catholic teaching."
)

_IDEA_PROMPT = """You are generating content for the Odili Truth Seeker Catholic media channel.

Topic: {topic}

""" + _VIRAL_STYLE + """

Return ONLY a valid JSON object with exactly these three keys (no markdown, no code fences):
- "title": a compelling, curiosity-driven YouTube title (max 12 words) that reveals a truth or breaks a myth — avoid a flat teaching tone
- "hook": a scroll-stopping opening hook (1-2 sentences) that interrupts scrolling and creates tension in the first 5 seconds
- "script": a 150-220 word script for a short video"""

_PACKAGE_PROMPT = """You are an expert YouTube content strategist for the Odili Truth Seeker Catholic media channel.

Given this video script:
Title: {title}
Hook: {hook}
Script: {script}

Return ONLY a valid JSON object with exactly these four keys (no markdown, no code fences):
- "title": an SEO-optimized YouTube title (max 70 chars, compelling and keyword-rich)
- "description": a full YouTube description (200-300 words) ending with 8-10 relevant hashtags and a CTA to subscribe
- "tags": comma-separated tags (12-15 relevant tags for YouTube search)
- "thumbnail_text": short punchy overlay text for the thumbnail (max 5 words, high CTR)"""


async def generate_idea_bundle(topic: str) -> dict:
    """Generate a title + hook + script bundle for a topic via GPT-4o."""
    raw = await generate_with_ai(_IDEA_PROMPT.format(topic=topic.strip()))
    data = parse_ai_json(raw)
    return {
        "title": str(data["title"]).strip(),
        "hook": str(data["hook"]).strip(),
        "script": str(data["script"]).strip(),
    }


async def generate_package(title: str, hook: str, script: str) -> dict:
    """Generate a YouTube SEO package from a script via GPT-4o."""
    raw = await generate_with_ai(_PACKAGE_PROMPT.format(
        title=title.strip(), hook=hook.strip(), script=script.strip(),
    ))
    data = parse_ai_json(raw)
    return {
        "title": str(data["title"]).strip(),
        "description": str(data["description"]).strip(),
        "tags": str(data["tags"]).strip(),
        "thumbnail_text": str(data["thumbnail_text"]).strip(),
    }


# ── Content reuse / repurposing ───────────────────────────────────────────────

REPURPOSE_FORMATS = ("youtube_post", "shorts")

_YT_POST_PROMPT = """You are the social manager for the Odili Truth Seeker Catholic media channel.

Turn this video into a YouTube Community post that drives people to watch it.
Title: {title}
Hook: {hook}
Script: {script}

Write a single engaging Community post (60-90 words): open with a curiosity hook, tease the core insight WITHOUT giving everything away, end with a clear call to watch the full video and 3-5 relevant hashtags. Stay faithful to authentic Catholic teaching.

Return ONLY the post text — no markdown, no quotes, no preamble."""

_SHORTS_PROMPT = """You are a YouTube Shorts strategist for the Odili Truth Seeker Catholic media channel.

Spin this long-form video into a punchy 30-45 second Shorts idea.
Title: {title}
Hook: {hook}
Script: {script}

Return ONLY a valid JSON object (no markdown, no code fences) with exactly these keys:
- "title": a scroll-stopping Shorts title (max 60 chars)
- "hook": the first spoken line (must grab attention in under 3 seconds)
- "script": a tight 30-45 second spoken script (50-90 words) that delivers one sharp point
- "caption": the Shorts caption with 3-5 hashtags"""


async def repurpose_script(fmt: str, title: str, hook: str, script: str) -> dict:
    """Repurpose a script into another format (youtube_post | shorts) via GPT-4o."""
    fmt = (fmt or "").strip().lower()
    if fmt not in REPURPOSE_FORMATS:
        raise ValueError(
            f"Invalid format. Must be one of: {', '.join(REPURPOSE_FORMATS)}."
        )
    title, hook, script = title.strip(), hook.strip(), script.strip()
    if not script:
        raise ValueError("A script is required to repurpose.")

    if fmt == "youtube_post":
        raw = await generate_with_ai(
            _YT_POST_PROMPT.format(title=title, hook=hook, script=script)
        )
        return {"format": fmt, "content": raw.strip()}

    raw = await generate_with_ai(
        _SHORTS_PROMPT.format(title=title, hook=hook, script=script)
    )
    data = parse_ai_json(raw)
    return {
        "format": fmt,
        "title": str(data.get("title", "")).strip(),
        "hook": str(data.get("hook", "")).strip(),
        "script": str(data.get("script", "")).strip(),
        "caption": str(data.get("caption", "")).strip(),
    }


# ── Shorts generator ──────────────────────────────────────────────────────────

_SHORTS_FULL_PROMPT = """You are a YouTube Shorts strategist for the Odili Truth Seeker Catholic media channel.

Turn this long-form video into a complete short-form (Shorts/Reels/TikTok) package.
Title: {title}
Hook: {hook}
Script: {script}

Return ONLY a valid JSON object (no markdown, no code fences) with exactly these keys:
- "hooks": an array of EXACTLY 3 scroll-stopping opening lines (each must grab attention in under 3 seconds)
- "script": a tight 15-30 second spoken script (40-75 words) that delivers one sharp, faithful point
- "caption": a short caption for the post
- "hashtags": a single string of 5-8 relevant hashtags separated by spaces

Stay faithful to authentic Catholic teaching."""


async def generate_shorts(title: str, hook: str, script: str) -> dict:
    """Generate a full Shorts package (3 hooks + script + caption + hashtags)."""
    raw = await generate_with_ai(_SHORTS_FULL_PROMPT.format(
        title=title.strip(), hook=hook.strip(), script=script.strip(),
    ))
    data = parse_ai_json(raw)
    hooks = [str(h).strip() for h in (data.get("hooks") or []) if str(h).strip()][:3]
    return {
        "hooks": hooks,
        "script": str(data.get("script", "")).strip(),
        "caption": str(data.get("caption", "")).strip(),
        "hashtags": str(data.get("hashtags", "")).strip(),
    }


# ── Weekly auto-scheduling (deterministic — no AI) ────────────────────────────

# Valid weekday names and their Python weekday() numbers (Mon=0 … Sun=6).
VALID_DAYS: list[str] = [
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
]
_DAY_TO_WEEKDAY = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}
# Default posting days when the admin hasn't chosen any yet.
DEFAULT_POSTING_DAYS: list[str] = ["Monday", "Thursday"]
_POSTING_DAYS_KEY = "posting_days"


def normalise_days(days: list[str] | None) -> list[str]:
    """Clean, validate, de-dupe and order (Sun→Sat) a list of day names."""
    seen: set[str] = set()
    for d in days or []:
        name = str(d).strip().capitalize()
        if name in _DAY_TO_WEEKDAY:
            seen.add(name)
    return [d for d in VALID_DAYS if d in seen]


def get_posting_days(db) -> list[str]:
    """Return the admin-selected posting days, or the default if none saved."""
    from app.models.db_models import AppSetting

    row = db.query(AppSetting).filter(AppSetting.key == _POSTING_DAYS_KEY).first()
    if row and row.value:
        days = normalise_days(row.value.split(","))
        if days:
            return days
    return list(DEFAULT_POSTING_DAYS)


def set_posting_days(db, days: list[str]) -> list[str]:
    """Validate and persist the posting days. Raises ValueError if none valid."""
    from app.models.db_models import AppSetting

    cleaned = normalise_days(days)
    if not cleaned:
        raise ValueError("Select at least one valid posting day (Sunday–Saturday).")
    row = db.query(AppSetting).filter(AppSetting.key == _POSTING_DAYS_KEY).first()
    if row:
        row.value = ",".join(cleaned)
    else:
        db.add(AppSetting(key=_POSTING_DAYS_KEY, value=",".join(cleaned)))
    db.commit()
    return cleaned


def weekly_schedule_dates(
    count: int = 5,
    now: datetime | None = None,
    days: list[str] | None = None,
) -> list[datetime]:
    """Return ``count`` posting datetimes (09:00 UTC) across the selected days.

    Posts land on the chosen weekdays (``days``; defaults to
    :data:`DEFAULT_POSTING_DAYS`), always today-or-future. When more videos are
    requested than there are posting days in a week, the schedule rolls into the
    following weeks so every video gets a future slot.
    """
    now = now or datetime.now(timezone.utc)
    names = normalise_days(days) or list(DEFAULT_POSTING_DAYS)
    weekdays = sorted(_DAY_TO_WEEKDAY[d] for d in names)

    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=9, minute=0, second=0, microsecond=0)

    dates: list[datetime] = []
    week = 0
    while len(dates) < max(0, count) and week < 104:  # safety cap (~2 years)
        for wd in weekdays:
            day = monday + timedelta(weeks=week, days=wd)
            if day > now:
                dates.append(day)
                if len(dates) >= count:
                    break
        week += 1
    return sorted(dates)


# ── Video announcement email (deterministic — no AI) ──────────────────────────

def _first_sentences(text: str, count: int = 2) -> str:
    """Return roughly the first ``count`` sentences of ``text``."""
    text = (text or "").strip()
    if not text:
        return ""
    parts = text.replace("! ", ". ").replace("? ", ". ").split(". ")
    summary = ". ".join(p.strip() for p in parts[:count] if p.strip())
    if summary and not summary.endswith((".", "!", "?")):
        summary += "."
    return summary


def build_video_email(title: str, hook: str, script: str) -> dict:
    """Build a ready-to-send video announcement email (subject + body)."""
    ctas = build_ctas(None)
    lines: list[str] = []
    if hook.strip():
        lines.append(hook.strip())
    summary = _first_sentences(script, 2)
    if summary:
        lines.append(summary)
    lines.append(f"▶ Watch now: {ctas['youtube_url']}")
    lines.append(ctas["subscribe_cta"])
    return {
        "subject": f"New Video: {title}".strip(),
        "body": "\n\n".join(line for line in lines if line).strip(),
    }


# ── High-conversion evangelisation email funnel ───────────────────────────────

def tracked_youtube_url() -> str:
    """Channel URL with lightweight email click-tracking params."""
    sep = "&" if "?" in YOUTUBE_URL else "?"
    return f"{YOUTUBE_URL}{sep}src=email&utm=odili_email"


_EVANGELIZATION_PROMPT = """You are writing a short, high-converting announcement email that drives readers to WATCH a new Catholic YouTube video from {app_name}.

VIDEO TITLE: {title}
VIDEO HOOK: {hook}
SCRIPT (context only — NEVER copy or summarise it into the email): {script}

Write a conversion-focused email that makes the reader NEED to click and watch.
Rules:
- Tease, do NOT explain. Never resolve the curiosity in the email.
- Do NOT dump or summarise the script.
- Total reading time under 60 seconds.
- Open with an emotional, curiosity-gap hook.

Return ONLY a valid JSON object (no markdown, no code fences, no preamble):
{{
  "subject": "<curiosity + urgency subject line, max 9 words, no quotes>",
  "hook": "<1-2 punchy opening lines that create tension and a curiosity gap>",
  "teaser": ["<short paragraph 1>", "<short paragraph 2>", "<optional short paragraph 3>"]
}}

Each teaser paragraph must be 1-2 sentences only and point toward the video."""


def _fallback_evangelization(title: str, hook: str, script: str) -> dict:
    """Deterministic funnel email when AI is unavailable (no quota / no key)."""
    t = title.strip() or "this new video"
    body_hook = hook.strip() or f"What if the truth about {t} isn't the full story you were told?"
    summary = _first_sentences(script, 1)
    teaser = [
        summary or "We go deeper than the surface on this one — and it may challenge what you believe.",
        "I won't give it away here. Some truths have to be seen to be understood.",
    ]
    subject = f"{title} — what most Christians miss" if title else "A truth most Christians miss"
    return {"subject": subject, "hook": body_hook, "teaser": teaser}


async def generate_evangelization_email(title: str, hook: str = "", script: str = "") -> dict:
    """
    Generate a high-conversion evangelisation email for a video.

    Returns {subject, hook, body, cta_text, youtube_url}. `body` is the plain-text
    funnel body (hook + short teaser) for the newsletter editor — the branded email
    template supplies the gold "Watch on YouTube" + "Subscribe" CTA buttons. AI is
    non-blocking: on any failure it falls back to a deterministic funnel.
    """
    title = (title or "").strip()
    hook = (hook or "").strip()
    script = (script or "").strip()

    try:
        raw = await generate_with_ai(_EVANGELIZATION_PROMPT.format(
            app_name=APP_NAME,
            title=title or "(untitled)",
            hook=hook or "(none provided)",
            script=(script[:1500] or "(none provided)"),
        ))
        data = parse_ai_json(raw)
        if not isinstance(data, dict):
            raise ValueError("AI did not return an object.")
        subject = str(data.get("subject") or "").strip()
        body_hook = str(data.get("hook") or "").strip()
        raw_teaser = data.get("teaser")
        teaser = (
            [str(x).strip() for x in raw_teaser if str(x).strip()][:4]
            if isinstance(raw_teaser, list) else []
        )
        if not subject or not body_hook or not teaser:
            raise ValueError("AI response missing required fields.")
    except Exception as exc:  # noqa: BLE001 — AI must never block the loop
        logger.info("Evangelisation email AI unavailable — using funnel fallback: %s", exc)
        fb = _fallback_evangelization(title, hook, script)
        subject, body_hook, teaser = fb["subject"], fb["hook"], fb["teaser"]

    # P8 — email subject mirrors the viral title style; the email opening line IS
    # the video hook (1:1 message-match between the video and the email) when one
    # is supplied, so the email funnels into the exact same promise as the video.
    if hook:
        body_hook = hook
    if title:
        subject = subject or title

    cta_text = "▶ Watch the Full Video"
    lines = [body_hook, *teaser, "▶ Watch the full video now — the link is in this email."]
    body = "\n".join(line for line in lines if line).strip()

    return {
        "subject": subject or (f"New Video: {title}".strip()),
        "hook": body_hook,
        "body": body,
        "cta_text": cta_text,
        "youtube_url": tracked_youtube_url(),
    }


# ── YouTube Studio optimisation engine (deterministic — no AI / no quota) ──────

# Catholic-niche tag seeds layered on top of words mined from the script/title.
_NICHE_TAGS = [
    "Catholic", "Catholic faith", "Catholic truth", "Catholicism",
    "Christianity", "faith", "Bible", "Jesus", "God",
    "Odili", "Odili the seeker of truth", "Catholic apologetics",
]

_OPT_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "it", "my", "your", "we", "they", "this", "that",
    "are", "was", "be", "have", "has", "by", "from", "not", "no", "as",
    "do", "did", "will", "can", "about", "how", "what", "why", "when",
    "who", "all", "you", "our", "its", "i", "am", "up", "he", "she",
    "his", "her", "their", "more", "new", "get", "got", "so", "if", "then",
    "than", "very", "just", "now", "here", "there", "also", "only", "even",
    "into", "out", "over", "them", "these", "those", "been", "were", "would",
}


def _derive_tags(text: str, top_clusters: list[dict] | None) -> list[str]:
    """Build a deduped YouTube tag list from content text + niche + cluster data."""
    tags: list[str] = []
    seen: set[str] = set()

    def _add(tag: str) -> None:
        tag = tag.strip()
        key = tag.lower()
        if tag and key not in seen:
            seen.add(key)
            tags.append(tag)

    # 1. Cluster patterns from the intelligence engine (strongest signal).
    for cluster in (top_clusters or []):
        pattern = str(cluster.get("pattern") or "").strip()
        if pattern:
            _add(pattern)

    # 2. Significant words mined from the title/topic/script.
    cleaned = re.sub(r"[^\w\s'-]", " ", (text or "").lower())
    word_counts = Counter(
        w for w in cleaned.split() if w not in _OPT_STOPWORDS and len(w) > 3
    )
    for word, _count in word_counts.most_common(10):
        _add(word)

    # 3. Always anchor the Catholic niche + brand.
    for tag in _NICHE_TAGS:
        _add(tag)

    return tags[:18]


def _suggest_playlist(text: str) -> str:
    """Pick a sensible playlist bucket from the content's dominant theme."""
    t = (text or "").lower()
    buckets = [
        (("pope", "vatican", "church", "magisterium"), "The Church & Her Authority"),
        (("mary", "rosary", "saint", "saints"), "Mary & the Saints"),
        (("hell", "sin", "devil", "satan", "demon", "purgatory"), "Spiritual Warfare & the Last Things"),
        (("prayer", "mass", "confession", "grace", "sacrament"), "Prayer & the Sacraments"),
        (("bible", "scripture", "gospel", "jesus", "god"), "Scripture & the Gospel"),
    ]
    for keywords, name in buckets:
        if any(k in t for k in keywords):
            return name
    return "Catholic Truth Explained"


def _thumbnail_psychology(text: str) -> dict:
    """Derive a high-CTR thumbnail psychology brief from the content theme.

    Deterministic (no AI) — picks an emotion/face/text combination tuned to the
    dominant theme so the thumbnail wins the click.
    """
    t = (text or "").lower()
    themes = [
        (
            ("hell", "sin", "devil", "satan", "demon", "judgment", "damn", "soul"),
            {
                "emotion": "fear",
                "face_expression": "concerned",
                "text": "ARE YOU SAFE?",
                "example_texts": ["YOU MISSED THIS", "THIS DAMNS SOULS", "DON'T RISK IT"],
            },
        ),
        (
            ("wrong", "myth", "lie", "heresy", "false", "mistake", "misunderstood"),
            {
                "emotion": "shock",
                "face_expression": "intense",
                "text": "WRONG TEACHING",
                "example_texts": ["YOU'VE BEEN LIED TO", "MOST GET THIS WRONG", "WRONG TEACHING"],
            },
        ),
        (
            ("really", "truth", "secret", "hidden", "revealed", "nobody", "exposed"),
            {
                "emotion": "shock",
                "face_expression": "bold",
                "text": "TRUTH REVEALED",
                "example_texts": ["TRUTH REVEALED", "THEY HID THIS", "NOBODY TELLS YOU"],
            },
        ),
    ]
    chosen = {
        "emotion": "authority",
        "face_expression": "bold",
        "text": "THE REAL TRUTH",
        "example_texts": ["THE REAL TRUTH", "WHAT THEY MISS", "SEEK THE TRUTH"],
    }
    for keywords, brief in themes:
        if any(k in t for k in keywords):
            chosen = brief
            break
    return {
        "emotion": chosen["emotion"],
        "face_expression": chosen["face_expression"],
        "text": chosen["text"],
        "contrast": "high",
        "example_texts": chosen["example_texts"],
    }


def generate_optimization(
    title: str,
    topic: str = "",
    script: str = "",
    best_posting_time: str | None = None,
    top_clusters: list[dict] | None = None,
) -> dict:
    """
    Deterministic YouTube Studio publishing blueprint for a video.

    Returns every upload "dial" pre-set with SAFE, growth-optimised defaults so a
    creator can mirror them in YouTube Studio. Uses live intelligence data
    (best posting time, top topic clusters) when supplied, but never depends on
    AI or external keys — it always returns a complete, valid strategy.
    """
    text = " ".join(p for p in (title, topic, script) if p)
    tags = _derive_tags(text, top_clusters)
    posting_time = (best_posting_time or "").strip() or "Thursday 18:00 UTC"

    return {
        "category": "Education",
        "audience": "No, it's not made for kids",
        "tags": tags,
        "title_style": "Curiosity gap + authority (8–11 words, front-load the hook)",
        "thumbnail_style": "High-contrast expressive face + 3–4 bold gold words, dark background",
        "description_structure": [
            "Open with the curiosity-gap hook (restate the title's tension).",
            "2–3 sentence summary of the core truth — without spoiling the answer.",
            "Chapters / timestamps for retention.",
            "Subscribe CTA + channel link.",
            "Relevant hashtags (#Catholic #Faith #Truth).",
            "Scripture references & sources for credibility.",
        ],
        "posting_time": posting_time,
        "language": "English",
        "captions": "Recommended — upload an SRT or enable auto-captions for reach & accessibility.",
        "visibility": "Public",
        "thumbnail_psychology": _thumbnail_psychology(text),
        "playlist": _suggest_playlist(text),
        "advanced_settings": {
            "allow_comments": True,
            "allow_embedding": True,
            "notify_subscribers": True,
            "show_in_subscriptions_feed": True,
            "license": "Standard YouTube License",
        },
    }


# ── Viral topic scoring engine (Part 1) ──────────────────────────────────────

_CURIOSITY_WORDS = {
    "really", "secret", "hidden", "truth", "revealed", "nobody", "no one",
    "what", "why", "how", "this", "shocking", "untold", "exposed", "behind",
}
_CONTROVERSY_WORDS = {
    "wrong", "lie", "lies", "myth", "myths", "heresy", "false", "fake",
    "against", "most", "everyone", "misunderstood", "mistake", "banned",
    "forbidden", "danger", "dangerous", "deceived", "deception",
}
_EMOTION_WORDS = {
    "salvation", "hell", "heaven", "soul", "souls", "death", "die", "dying",
    "fear", "eternity", "eternal", "sin", "saved", "damned", "judgment",
    "love", "suffering", "cross", "sacrifice", "warning", "urgent",
}
_DEMAND_WORDS = {
    "catholic", "christian", "christians", "bible", "jesus", "christ", "god",
    "prayer", "mass", "rosary", "pope", "saint", "saints", "mary", "gospel",
    "scripture", "church", "faith", "confession", "eucharist",
}


def _kw_score(text: str, words: set[str], cap: int = 3) -> int:
    """0-100 score for how strongly ``text`` hits a keyword bucket."""
    t = f" {text.lower()} "
    hits = sum(1 for w in words if (f" {w} " in t or f" {w}" in t))
    return min(100, int(round((min(hits, cap) / cap) * 100)))


def _topic_recommendation(score: int) -> str:
    if score >= 70:
        return "Use"
    if score >= 40:
        return "Improve"
    return "Avoid"


def _core_subject(text: str) -> str:
    """Extract a short core subject phrase from a topic/title for rewrites."""
    cleaned = re.sub(r"[^\w\s'-]", " ", (text or "")).strip()
    words = [w for w in cleaned.split() if w.lower() not in _OPT_STOPWORDS]
    core = " ".join(words[:5]).strip() or (text or "").strip()
    return core[:48].strip()


def _fallback_improved_angle(topic: str) -> str:
    core = _core_subject(topic) or "this"
    return f"What Most Christians Get WRONG About {core.title()}"


def _viral_title_templates(core: str) -> list[str]:
    core = (core or "this").strip()
    c_title = core.title()
    candidates = [
        f"What Jesus REALLY Meant by {c_title}",
        f"Most Christians Get {c_title} Wrong",
        f"The Truth About {c_title} Nobody Tells You",
        f"{c_title}: This Could Cost You Salvation",
        f"Why {c_title} Changes Everything You Believe",
        f"They Hid the Truth About {c_title}",
    ]
    out: list[str] = []
    for t in candidates:
        t = t.strip()
        if len(t) <= 70 and t not in out:
            out.append(t)
        if len(out) == 5:
            break
    while len(out) < 5 and candidates:
        for t in candidates:
            t = t[:70].strip()
            if t not in out:
                out.append(t)
            if len(out) == 5:
                break
    return out[:5]


async def score_topic(topic: str) -> dict:
    """Score a topic's viral potential (deterministic) + an improved angle.

    Resilient: scores are computed without AI; the improved angle is enriched by
    AI when available and falls back to a deterministic viral rewrite otherwise.
    """
    topic = (topic or "").strip()
    curiosity = _kw_score(topic, _CURIOSITY_WORDS)
    controversy = _kw_score(topic, _CONTROVERSY_WORDS)
    emotional = _kw_score(topic, _EMOTION_WORDS)
    demand = _kw_score(topic, _DEMAND_WORDS)
    # Question framing is a strong curiosity signal.
    if "?" in topic or re.match(r"^\s*(what|why|how|is|are|did|can|should)\b", topic.lower()):
        curiosity = min(100, curiosity + 25)
    virality = int(round(
        0.35 * curiosity + 0.25 * controversy + 0.25 * emotional + 0.15 * demand
    ))

    improved = ""
    try:
        prompt = (
            "Rewrite this Catholic video topic into ONE irresistible, viral angle "
            "(a single line, under 70 characters) using truth-revelation, "
            "myth-breaking or salvation urgency. Return ONLY the rewritten line, "
            "no quotes, no preamble.\n\nTopic: " + (topic or "(none)")
        )
        raw = (await generate_with_ai(prompt)).strip().strip('"').splitlines()[0]
        if raw:
            improved = raw[:90].strip()
    except Exception as exc:  # noqa: BLE001 — AI is optional here
        logger.info("score_topic improved-angle AI unavailable: %s", exc)
    if not improved:
        improved = _fallback_improved_angle(topic)

    return {
        "topic": topic,
        "virality_score": virality,
        "curiosity_gap": curiosity,
        "controversy_level": controversy,
        "emotional_trigger": emotional,
        "search_demand": demand,
        "recommendation": _topic_recommendation(virality),
        "improved_angle": improved,
    }


# ── Title rewrite engine (Part 2) ─────────────────────────────────────────────

_REWRITE_TITLE_PROMPT = """You are a viral YouTube title writer for Odili Truth Seeker, a Catholic media ministry.

Rewrite this into EXACTLY 5 viral title options:
{title}

Rules:
- Each MUST trigger curiosity and tension — never a flat teaching tone.
- Each MUST be under 70 characters.
- Use proven viral patterns, e.g. "What Jesus REALLY Meant…", "Most Christians Get This Wrong…", "This Could Cost You Salvation…".
- Stay faithful to authentic Catholic teaching.

Return ONLY a valid JSON object (no markdown, no code fences):
{{"viral_titles": ["...", "...", "...", "...", "..."]}}"""


async def rewrite_title(title: str) -> dict:
    """Return 5 viral title rewrites (AI primary, deterministic fallback)."""
    title = (title or "").strip()
    titles: list[str] = []
    try:
        raw = await generate_with_ai(_REWRITE_TITLE_PROMPT.format(title=title or "(untitled)"))
        data = parse_ai_json(raw)
        candidate = data.get("viral_titles") if isinstance(data, dict) else data
        if isinstance(candidate, list):
            titles = [str(t).strip()[:70] for t in candidate if str(t).strip()][:5]
    except Exception as exc:  # noqa: BLE001 — AI is optional here
        logger.info("rewrite_title AI unavailable — using templates: %s", exc)
    if len(titles) < 5:
        titles = _viral_title_templates(_core_subject(title))
    return {"viral_titles": titles[:5]}


# ── Hook intensity booster (Part 4) ───────────────────────────────────────────

_HOOK_TENSION_WORDS = {
    "what if", "imagine", "nobody", "no one", "secret", "wrong", "truth",
    "never", "stop", "warning", "most", "really", "lie", "hidden", "shocking",
    "the real", "before you", "don't", "they don't want", "you've been",
}


def score_hook_intensity(hook: str) -> int:
    """Deterministic 0-100 score for how scroll-stopping a hook is."""
    h = (hook or "").strip()
    if not h:
        return 0
    low = h.lower()
    score = 30
    words = len(h.split())
    if 4 <= words <= 22:
        score += 15
    elif words <= 30:
        score += 5
    if "?" in h:
        score += 12
    if any(p in low for p in _HOOK_TENSION_WORDS):
        score += 20
    if any(p in low for p in _EMOTION_WORDS):
        score += 13
    if "you" in re.findall(r"[a-z']+", low):
        score += 10
    if h[:1].isupper() and any(c in h for c in "!?."):
        score += 5
    return max(0, min(100, score))


_BOOST_HOOK_PROMPT = """You are a viral hook writer for Odili Truth Seeker, a Catholic media ministry.

Write ONE scroll-stopping opening hook (the first spoken line of a short video) about:
{topic}

It MUST interrupt scrolling and create instant tension/curiosity in the first 5 seconds — truth-revelation, myth-breaking or salvation urgency. 1-2 short sentences. Stay faithful to authentic Catholic teaching.

Return ONLY the hook line — no quotes, no markdown, no preamble."""


async def boost_hook(topic: str, hook: str = "", script: str = "") -> dict:
    """Score a hook; auto-regenerate a stronger one if intensity < 70.

    Returns {hook, hook_intensity_score, regenerated}. Resilient: if AI is
    unavailable the original hook is kept with its computed score.
    """
    topic = (topic or "").strip()
    hook = (hook or "").strip()
    base_score = score_hook_intensity(hook)
    if hook and base_score >= 70:
        return {"hook": hook, "hook_intensity_score": base_score, "regenerated": False}

    seed = topic or hook or "the truth most Christians miss"
    try:
        new_hook = (await generate_with_ai(_BOOST_HOOK_PROMPT.format(topic=seed))).strip()
        new_hook = new_hook.strip('"').splitlines()[0].strip() if new_hook else ""
        new_score = score_hook_intensity(new_hook)
        if new_hook and new_score >= base_score:
            return {"hook": new_hook, "hook_intensity_score": new_score, "regenerated": True}
    except Exception as exc:  # noqa: BLE001 — AI is optional here
        logger.info("boost_hook AI unavailable: %s", exc)
    return {"hook": hook, "hook_intensity_score": base_score, "regenerated": False}


# ── "Make This Viral" pipeline (Part 6) ───────────────────────────────────────

async def make_viral(
    title: str = "",
    topic: str = "",
    hook: str = "",
    script: str = "",
    best_posting_time: str | None = None,
    top_clusters: list[dict] | None = None,
) -> dict:
    """One-shot viral package: score topic → rewrite title → boost hook →
    thumbnail text → full optimisation blueprint. Fully resilient."""
    title = (title or "").strip()
    topic = (topic or title).strip()
    hook = (hook or "").strip()
    script = (script or "").strip()

    topic_score = await score_topic(topic or title)
    titles = (await rewrite_title(title or topic)).get("viral_titles", [])
    best_title = titles[0] if titles else (title or topic)
    boosted = await boost_hook(topic or title, hook, script)
    optimization = generate_optimization(
        title=best_title,
        topic=topic,
        script=script,
        best_posting_time=best_posting_time,
        top_clusters=top_clusters,
    )
    return {
        "topic_score": topic_score,
        "viral_titles": titles,
        "best_title": best_title,
        "hook": boosted["hook"],
        "hook_intensity_score": boosted["hook_intensity_score"],
        "hook_regenerated": boosted["regenerated"],
        "thumbnail_psychology": optimization.get("thumbnail_psychology", {}),
        "optimization": optimization,
    }


# ── Performance feedback loop (Part 5) ────────────────────────────────────────

def performance_verdict(views: int, ctr: float, likes: int) -> tuple[str, str]:
    """Classify a video's performance into a verdict + actionable note.

    CTR is the dominant signal (YouTube's own ranking lever). Returns one of
    "worked" | "mixed" | "failed" plus a short do-more / avoid note.
    """
    ctr = max(0.0, float(ctr or 0))
    views = max(0, int(views or 0))
    likes = max(0, int(likes or 0))
    like_rate = (likes / views * 100) if views else 0.0

    if ctr >= 6 or (ctr >= 4 and like_rate >= 4):
        return "worked", "Do more of this — the title/thumbnail earned the click."
    if ctr < 3:
        return "failed", "Avoid this pattern — the title/thumbnail isn't earning clicks."
    return "mixed", "Okay — tighten the hook and sharpen the thumbnail to lift CTR."


def analyse_performance(rows: list[dict]) -> dict:
    """Aggregate logged videos into worked/failed buckets + a takeaway."""
    worked = [r for r in rows if r.get("verdict") == "worked"]
    failed = [r for r in rows if r.get("verdict") == "failed"]
    avg_ctr = round(sum(float(r.get("ctr") or 0) for r in rows) / len(rows), 2) if rows else 0.0
    best = max(rows, key=lambda r: float(r.get("ctr") or 0), default=None)
    worst = min(rows, key=lambda r: float(r.get("ctr") or 0), default=None)
    takeaway = ""
    if best and worked:
        takeaway = (
            f"Your best performer is \"{best.get('title')}\" "
            f"({best.get('ctr')}% CTR) — do more like it."
        )
    elif rows:
        takeaway = "Not enough wins yet — push harder on curiosity-gap titles and bold thumbnails."
    return {
        "count": len(rows),
        "avg_ctr": avg_ctr,
        "worked_count": len(worked),
        "failed_count": len(failed),
        "best_title": best.get("title") if best else None,
        "worst_title": worst.get("title") if worst else None,
        "takeaway": takeaway,
    }


# ── CTA booster (deterministic — no AI / no quota) ────────────────────────────

def build_ctas(next_video_title: str | None = None) -> dict:
    """Return ready-to-paste Subscribe and Watch-Next CTA blocks."""
    subscribe_cta = (
        f"🔔 If this strengthened your faith, subscribe to {APP_NAME} and tap the bell "
        "so you never miss the truth. Join our growing community seeking Christ together — "
        "like, comment, and share this with someone who needs to hear it."
    )
    nv = (next_video_title or "").strip()
    if nv:
        watch_next_cta = (
            f"▶ Don't stop seeking — watch \"{nv}\" next. Click the link on screen now "
            "to continue your journey into the truth."
        )
    else:
        watch_next_cta = (
            "▶ Don't stop seeking — the next video is on screen right now. Click it to keep "
            "growing in faith and uncovering the truth."
        )
    return {
        "subscribe_cta": subscribe_cta,
        "watch_next_cta": watch_next_cta,
        "youtube_url": YOUTUBE_URL,
    }


# ── Strategy insight derivation ───────────────────────────────────────────────

def _best_posting_time(videos: list[dict]) -> str | None:
    """Heuristic best posting window from video publish timestamps (UTC)."""
    days: Counter = Counter()
    hours: Counter = Counter()
    for v in videos:
        ts = v.get("published_at")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            continue
        days[dt.strftime("%A")] += 1
        hours[dt.hour] += 1
    if not days or not hours:
        return None
    best_day = days.most_common(1)[0][0]
    best_hour = hours.most_common(1)[0][0]
    return f"{best_day}s around {best_hour:02d}:00 UTC"


def derive_growth_insights(insights: dict) -> dict:
    """Distil the full YouTube Intelligence payload into Growth Engine highlights."""
    patterns = insights.get("topic_patterns") or []
    best_cluster = patterns[0]["pattern"] if patterns else None
    best_cluster_count = patterns[0]["count"] if patterns else 0

    videos = (insights.get("top_videos") or []) + (insights.get("underperforming") or [])
    best_time = _best_posting_time(videos)

    suggested = insights.get("suggested_topics") or []
    if suggested:
        what_next = suggested[0]
    elif best_cluster:
        what_next = (
            f"Lean into your strongest theme — create more '{best_cluster}' content."
        )
    else:
        what_next = None

    return {
        "configured": True,
        "videos_analysed": insights.get("videos_analysed", 0),
        "best_cluster": best_cluster,
        "best_cluster_count": best_cluster_count,
        "best_posting_time": best_time,
        "what_to_post_next": what_next,
        "suggested_topics": suggested[:5],
        "top_clusters": [
            {"pattern": p.get("pattern"), "count": p.get("count")}
            for p in patterns[:5]
        ],
        "ai_note": insights.get("ai_note"),
    }
