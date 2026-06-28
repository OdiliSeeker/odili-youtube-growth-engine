"""
Traffic Engine — multi-platform content generation + distribution helpers.

Powers the admin "Weekly Distribution" and "Traffic Engine" tools: weekly social
posts, a Facebook distribution pack, Shorts packages, viral hooks, one-to-many
repurposing, and a static posting plan.

Design: deterministic-first + AI-enriched + quota-resilient (same philosophy as
the Growth/Viral layers). Every generator builds usable copy from pure-Python
templates and only *upgrades* it with AI when OpenAI is available — on any AI
failure (quota, auth, network) it silently keeps the deterministic output, so
these endpoints never hard-fail and always return copy-ready material.

It NEVER auto-posts anywhere. The Facebook pack only *suggests* the groups the
admin is authorised to share into, for manual copy/paste.
"""

import logging

from app.branding import APP_NAME, FACEBOOK_GROUPS, FEATURED_VIDEO_ID, YOUTUBE_URL
from app.services import featured_service
from app.services.ai_service import generate_with_ai
from app.services.growth_service import parse_ai_json

logger = logging.getLogger(__name__)

DEFAULT_HASHTAGS = ["#Catholic", "#Truth", "#Faith", "#Apologetics", "#Bible"]
IMAGE_PROMPT = (
    "A dramatic biblical scene, warm golden lighting, reverent Catholic theme, "
    "symbolic and cinematic, painterly detail, high contrast"
)
SHORTS_CTAS = [
    "Full explanation on my channel.",
    "Join the mission below.",
    "This is just the beginning.",
]

# Rotating hook openers (spec PART 2). {t} is the core subject.
_HOOK_TEMPLATES = [
    "Most Christians don't realize {t}.",
    "This is why the Church teaches the truth about {t}.",
    "If you believe this, listen carefully — {t} changes things.",
    "This changes everything about {t}.",
    "You've been told one thing about {t} your whole life…",
]


# ── Smart video linking (spec PART 4) ─────────────────────────────────────────

def _watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def latest_video_link(db) -> tuple[str | None, str]:
    """Best available "latest video" (title, url).

    Without a YouTube API key we can't read true upload dates, so "latest" is the
    admin-curated featured Short (the Content Hub list is admin-ordered, newest
    first), then the configured FEATURED_VIDEO_ID, then the channel itself. The
    Friday post always carries whichever link this returns.
    """
    try:
        shorts = (featured_service.get_featured(db) or {}).get("shorts") or []
        if shorts and shorts[0].get("id"):
            return (shorts[0].get("title") or None), _watch_url(shorts[0]["id"])
    except Exception:  # featured hub is best-effort, never block a post
        logger.debug("featured hub unavailable for latest_video_link", exc_info=True)
    if FEATURED_VIDEO_ID:
        return None, _watch_url(FEATURED_VIDEO_ID)
    return None, YOUTUBE_URL


def _core_subject(text: str) -> str:
    """A short lowercase subject phrase for hook templating."""
    t = (text or "").strip().rstrip(".!?")
    if not t:
        return "the Catholic faith"
    words = t.split()
    return " ".join(words[:8]).lower()


# ── Weekly social posts (spec File 1 · PART 2) ────────────────────────────────

def _fallback_weekly_posts(video_title: str | None, video_url: str) -> dict:
    promo = f'"{video_title}"' if video_title else "this week's teaching"
    return {
        "sunday_post": (
            "Today's readings remind us that grace meets us exactly where we are.\n\n"
            "Take a quiet moment this Sunday to ask: where is God inviting me deeper? "
            "Sometimes the verse we skip past is the one meant for us.\n\n"
            "What stood out to you in today's readings?"
        ),
        "wednesday_post": (
            "Most people assume the early Church believed exactly what they were taught growing up.\n\n"
            "History tells a richer story — one rooted in Scripture, the Fathers, and unbroken Tradition.\n\n"
            "Worth a second look."
        ),
        "friday_post": (
            f"New teaching is live. {promo} unpacks what most explanations leave out — "
            "clearly, and rooted in the faith of the earliest Christians.\n\n"
            f"Watch it here: {video_url}"
        ),
        "optional_image_prompt": IMAGE_PROMPT,
    }


async def generate_weekly_posts(db) -> dict:
    """Three platform-ready posts (Sunday/Wednesday/Friday) + an image prompt."""
    video_title, video_url = latest_video_link(db)
    result = _fallback_weekly_posts(video_title, video_url)

    title_hint = f'The latest video is titled "{video_title}".' if video_title else ""
    prompt = (
        f"Write three short social media posts for {APP_NAME}, a Catholic media ministry. "
        "Return STRICT JSON with keys: sunday_post, wednesday_post, friday_post, optional_image_prompt.\n"
        "- sunday_post: a reflective, thought-provoking reflection loosely tied to Catholic Mass "
        "readings; end with a soft curiosity hook. 2 short paragraphs.\n"
        "- wednesday_post: one punchy apologetics insight that respectfully challenges a common "
        "assumption. Short.\n"
        f"- friday_post: promote the latest YouTube video with a strong first line. {title_hint} "
        "Do NOT include the URL — it is appended automatically.\n"
        "- optional_image_prompt: one vivid image-generator prompt for a Catholic, cinematic scene.\n"
        "Each post: strong first line, natural (not spammy) tone, 1-2 short paragraphs."
    )
    try:
        data = parse_ai_json(await generate_with_ai(prompt))
        for key in ("sunday_post", "wednesday_post", "friday_post", "optional_image_prompt"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                result[key] = val.strip()
        # The Friday post must always carry the video link (spec PART 4).
        if video_url not in result["friday_post"]:
            result["friday_post"] = result["friday_post"].rstrip() + f"\n\nWatch it here: {video_url}"
    except Exception:
        logger.info("generate_weekly_posts falling back to deterministic copy", exc_info=True)
    return result


# ── Facebook distribution assistant (spec File 1 · PART 3) ────────────────────

def facebook_pack(db) -> dict:
    """A ready-to-paste post + the authorised groups to share it into manually."""
    video_title, video_url = latest_video_link(db)
    promo = f'"{video_title}"' if video_title else "our latest teaching"
    post_text = (
        f"Many of us were never told the full story of what the earliest Christians believed.\n\n"
        f"{APP_NAME} releases short, clear teachings rooted in Scripture, Tradition, and 2,000 years "
        f"of Catholic faith. If you're seeking the truth — not just opinions — start with {promo}.\n\n"
        f"Watch here: {video_url}"
    )
    return {
        "post_text": post_text,
        "suggested_groups": list(FACEBOOK_GROUPS),
        "instructions": [
            "Post in 3-5 groups max per session.",
            "Wait 10-15 minutes between posts.",
            "Rotate groups each week and vary the wording slightly.",
            "Engage with comments — don't just drop links.",
        ],
    }


# ── Shorts engine (spec File 2 · PART 1) ──────────────────────────────────────

def _fallback_shorts(subject: str, count: int = 3) -> list[dict]:
    core = _core_subject(subject)
    shorts = []
    for i in range(count):
        hook = _HOOK_TEMPLATES[i % len(_HOOK_TEMPLATES)].format(t=core)
        cta = SHORTS_CTAS[i % len(SHORTS_CTAS)]
        shorts.append({
            "hook": hook,
            "script": (
                f"{hook} Here's the part most people miss. The earliest Christians, "
                f"Scripture, and the Church Fathers all point the same direction on {core}. "
                f"Once you see it, it's hard to unsee. {cta}"
            ),
            "caption": f"The truth about {core}. Watch this carefully. {cta}",
            "on_screen_text": "You weren't told\nthe full story",
            "hashtags": list(DEFAULT_HASHTAGS),
        })
    return shorts


async def generate_shorts(subject: str, count: int = 3) -> dict:
    """3-5 Shorts packages, each with hook/script/caption/on-screen text/hashtags."""
    count = max(3, min(count, 5))
    result = {"shorts": _fallback_shorts(subject, count)}

    prompt = (
        f"Create {count} YouTube Shorts for {APP_NAME}, a Catholic media ministry, about: "
        f"\"{subject}\".\n"
        "Return STRICT JSON: an array under key \"shorts\". Each item has keys: hook, script, "
        "caption, on_screen_text, hashtags (array of strings).\n"
        "Rules per Short: 15-30 seconds; START with a strong hook in the first 2 seconds; deliver "
        "ONE idea only; end with curiosity or a soft CTA; conversational and direct, no filler. "
        "on_screen_text = 3-6 word punchy lines (use \\n between lines). hashtags: 4-6 relevant tags."
    )
    try:
        data = parse_ai_json(await generate_with_ai(prompt))
        items = data.get("shorts") if isinstance(data, dict) else data
        cleaned = []
        for it in (items or []):
            if not isinstance(it, dict):
                continue
            tags = it.get("hashtags")
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.replace(",", " ").split() if t.strip()]
            cleaned.append({
                "hook": str(it.get("hook", "")).strip(),
                "script": str(it.get("script", "")).strip(),
                "caption": str(it.get("caption", "")).strip(),
                "on_screen_text": str(it.get("on_screen_text", "")).strip(),
                "hashtags": tags if isinstance(tags, list) and tags else list(DEFAULT_HASHTAGS),
            })
        cleaned = [c for c in cleaned if c["hook"] and c["script"]]
        if cleaned:
            result["shorts"] = cleaned[:5]
    except Exception:
        logger.info("generate_shorts falling back to deterministic packages", exc_info=True)
    return result


# ── Viral hooks (spec File 2 · PART 2) ────────────────────────────────────────

def _fallback_hooks(topic: str) -> list[str]:
    core = _core_subject(topic)
    return [tpl.format(t=core) for tpl in _HOOK_TEMPLATES]


async def generate_hooks(topic: str) -> dict:
    """Five curiosity-driven, assumption-challenging hooks for a topic."""
    result = {"hooks": _fallback_hooks(topic)}
    prompt = (
        f"Write 5 scroll-stopping hooks (first lines) for short Catholic videos about \"{topic}\" "
        f"for {APP_NAME}. Each must trigger curiosity, gently challenge an assumption, and be "
        "emotionally engaging. Return STRICT JSON: an array of 5 strings under key \"hooks\"."
    )
    try:
        data = parse_ai_json(await generate_with_ai(prompt))
        hooks = data.get("hooks") if isinstance(data, dict) else data
        hooks = [str(h).strip() for h in (hooks or []) if str(h).strip()]
        if hooks:
            result["hooks"] = hooks[:5]
    except Exception:
        logger.info("generate_hooks falling back to deterministic hooks", exc_info=True)
    return result


# ── Repurposing engine (spec File 2 · PART 3) ─────────────────────────────────

def _fallback_repurpose(subject: str) -> dict:
    core = _core_subject(subject)
    return {
        "shorts": _fallback_shorts(subject, 3),
        "facebook_post": (
            f"Most people were never told the full story about {core}.\n\n"
            "Here's what Scripture and the earliest Christians actually reveal — clearly explained. "
            "Worth a few minutes of your time."
        ),
        "tiktok_caption": f"The truth about {core} 👀 #Catholic #Truth #Faith",
        "youtube_description": (
            f"In this teaching we explore {core} — rooted in Scripture, the Church Fathers, and "
            "authentic Catholic Tradition.\n\n"
            "🔔 Subscribe for new teachings every week.\n"
            f"▶ Channel: {YOUTUBE_URL}\n\n"
            "#Catholic #Apologetics #Faith #Bible #Truth"
        ),
        "email_teaser": (
            f"There's a part of the story about {core} most explanations skip. "
            "This week's teaching fills in the picture — clearly, and faithfully."
        ),
    }


async def repurpose(subject: str) -> dict:
    """Turn one topic/script into Shorts + Facebook + TikTok + YouTube + email."""
    result = _fallback_repurpose(subject)
    prompt = (
        f"Repurpose this Catholic video topic/script into multiple formats for {APP_NAME}: "
        f"\"{subject}\".\n"
        "Return STRICT JSON with keys: shorts (array of {hook, script, caption, on_screen_text, "
        "hashtags[]}), facebook_post (string), tiktok_caption (string), youtube_description "
        "(string), email_teaser (string). Keep each natural, faith-rooted, and not spammy."
    )
    try:
        data = parse_ai_json(await generate_with_ai(prompt))
        if isinstance(data, dict):
            for key in ("facebook_post", "tiktok_caption", "youtube_description", "email_teaser"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    result[key] = val.strip()
            shorts = data.get("shorts")
            cleaned = []
            for it in (shorts or []):
                if isinstance(it, dict) and str(it.get("hook", "")).strip():
                    tags = it.get("hashtags")
                    if isinstance(tags, str):
                        tags = [t.strip() for t in tags.replace(",", " ").split() if t.strip()]
                    cleaned.append({
                        "hook": str(it.get("hook", "")).strip(),
                        "script": str(it.get("script", "")).strip(),
                        "caption": str(it.get("caption", "")).strip(),
                        "on_screen_text": str(it.get("on_screen_text", "")).strip(),
                        "hashtags": tags if isinstance(tags, list) and tags else list(DEFAULT_HASHTAGS),
                    })
            if cleaned:
                result["shorts"] = cleaned[:5]
    except Exception:
        logger.info("repurpose falling back to deterministic formats", exc_info=True)
    return result


# ── Posting strategy plan (spec File 2 · PART 4) ──────────────────────────────

def posting_plan() -> dict:
    """A simple, static weekly posting strategy (deterministic — no AI/keys)."""
    return {
        "weekly_plan": {
            "monday": "Short clip — hook-based. Post one strong Short to open the week.",
            "wednesday": "Insight post — a clarifying or respectfully controversial apologetics point.",
            "friday": "Video promotion — share the latest YouTube teaching with a link.",
            "sunday": "Reflection — a thoughtful post tied to the Sunday Mass readings.",
        },
        "tips": [
            "Post 3-5 Shorts per video for maximum reach.",
            "End every Short with one soft CTA — never push links aggressively.",
            "Vary tone slightly each week; never repeat identical messages.",
        ],
    }
