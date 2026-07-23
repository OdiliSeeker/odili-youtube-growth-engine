"""
Subscriber Conversion Scripts — ready-to-use scripts that turn YouTube viewers
into subscribers: a pinned comment, comment-reply CTAs, spoken/end-screen
subscribe CTAs, and a description CTA block.

Deterministic-first + AI-enriched + NEVER 402 — AI failure silently keeps the
deterministic output. US-audience tuned. Generation only: the admin copies these
and posts them as a human. Nothing here auto-posts to YouTube.
"""

import hashlib
import json
import logging
import random

from app.branding import YOUTUBE_URL
from app.services.ai_service import generate_with_ai

logger = logging.getLogger(__name__)

_PINNED_TEMPLATES = [
    (
        "Quick question for you 👇 What's the ONE thing about {t} you were never "
        "given a straight answer on? Drop it below — I read every comment, and the "
        "best questions become future videos. If this helped, subscribe so you "
        "don't miss what's coming next."
    ),
    (
        "📌 If you've ever felt like the full story about {t} was kept from you — "
        "you're not alone. Tell me in the comments where you first heard about it. "
        "And if you want the truth, plainly explained, hit subscribe. That's what "
        "this channel is for."
    ),
    (
        "Before you scroll: most people never hear this side of {t}. What did YOU "
        "grow up believing about it? Comment below 👇 Subscribe if you'd rather have "
        "the real answer than the popular one."
    ),
]

_COMMENT_CTA_TEMPLATES = [
    "Great question — the short answer is in the video, but the full picture on {t} goes even deeper. Subscribed viewers get the next part.",
    "You're closer to the truth than you think. If {t} is on your heart, subscribe — the next video builds right on this.",
    "This is exactly why I made the video. Watch to the end, then subscribe so the rest of the story finds you.",
    "Appreciate you engaging honestly. If you want where this leads on {t}, the channel walks through it step by step — hit subscribe.",
]

_SUBSCRIBE_CTA_TEMPLATES = [
    "If this made you rethink {t}, subscribe — the next one goes even further.",
    "Don't leave the truth half-finished. Subscribe and turn on the bell.",
    "Thousands of Americans are seeking real answers about {t} — join them. Subscribe now.",
    "One click keeps the truth coming. Subscribe before you go.",
    "If you'd rather have the honest answer than the easy one, subscribe.",
]


def _description_cta(topic: str, youtube_url: str) -> str:
    t = topic.strip()
    sep = "&" if "?" in youtube_url else "?"
    sub_url = f"{youtube_url}{sep}sub_confirmation=1"
    return (
        f"🔔 SUBSCRIBE for the truth about {t} and more: {sub_url}\n\n"
        f"Most people never hear the full story about {t}. On this channel we go to "
        "the earliest sources — Scripture, the Church Fathers, and the Magisterium — "
        "and explain it plainly.\n\n"
        f"▶ Watch more: {youtube_url}\n"
        "💬 Have a question? Drop it in the comments — the best ones become videos."
    )


def _deterministic(topic: str, video_title: str, youtube_url: str) -> dict:
    t = topic.strip()
    seed_src = f"{t.lower()}|{video_title.strip().lower()}"
    seed = int(hashlib.sha256(seed_src.encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)

    pinned = rng.choice(_PINNED_TEMPLATES).replace("{t}", t)
    comment_ctas = [c.replace("{t}", t) for c in _COMMENT_CTA_TEMPLATES]
    rng.shuffle(comment_ctas)
    subscribe_ctas = [c.replace("{t}", t) for c in _SUBSCRIBE_CTA_TEMPLATES]
    rng.shuffle(subscribe_ctas)

    return {
        "pinned_comment": pinned,
        "comment_ctas": comment_ctas[:4],
        "subscribe_ctas": subscribe_ctas[:5],
        "description_cta": _description_cta(t, youtube_url),
    }


_AI_PROMPT = """You are a subscriber-conversion copywriter for Odili Truth Seeker, a Catholic media ministry targeting a United States audience.

Video topic: "{t}"
Video title: "{title}"

Write scripts that turn viewers into subscribers. Warm, human, honest — never spammy or clickbait. US phrasing.

Return ONLY JSON with these exact keys:
{{
  "pinned_comment": "<one pinned comment (50-70 words) that invites a reply AND asks for a subscribe>",
  "comment_ctas": [4 short ready-to-paste reply snippets that gently push a subscribe],
  "subscribe_ctas": [5 short spoken/end-screen subscribe lines],
  "description_cta": "<a YouTube description CTA block (3-5 short lines) driving to subscribe>"
}}"""


def _valid_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _valid_list(v, n_min: int = 2) -> bool:
    return isinstance(v, list) and len([x for x in v if _valid_str(x)]) >= n_min


async def generate_conversion_scripts(topic: str, video_title: str = "") -> dict:
    """Pinned comment + comment CTAs + subscribe CTAs + description CTA.

    Deterministic-first, AI-enriched, never 402.
    """
    youtube_url = YOUTUBE_URL or "https://www.youtube.com/@odilitheseekeroftruth"
    out = _deterministic(topic, video_title, youtube_url)
    out["topic"] = topic.strip()
    out["content_source"] = "deterministic"
    try:
        raw = await generate_with_ai(
            _AI_PROMPT.format(t=topic.strip()[:200], title=(video_title.strip() or "(untitled)")[:200])
        )
        start, end = raw.find("{"), raw.rfind("}")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        if isinstance(ai, dict):
            enriched = False
            if _valid_str(ai.get("pinned_comment")):
                out["pinned_comment"] = ai["pinned_comment"].strip()
                enriched = True
            if _valid_list(ai.get("comment_ctas")):
                out["comment_ctas"] = [x.strip() for x in ai["comment_ctas"] if _valid_str(x)][:4]
                enriched = True
            if _valid_list(ai.get("subscribe_ctas")):
                out["subscribe_ctas"] = [x.strip() for x in ai["subscribe_ctas"] if _valid_str(x)][:5]
                enriched = True
            if _valid_str(ai.get("description_cta")):
                out["description_cta"] = ai["description_cta"].strip()
                enriched = True
            if enriched:
                out["content_source"] = "ai"
    except Exception as exc:  # noqa: BLE001 — AI must never block the endpoint
        logger.info("Conversion-scripts AI unavailable (%s); using deterministic scripts", exc)
    return out
