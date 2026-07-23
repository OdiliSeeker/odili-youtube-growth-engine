"""
Click Trigger Phrases library — a curated set of proven, high-CTR psychological
phrases for a Catholic truth-seeking channel, organised by trigger category and
tuned for a United States audience.

Two modes:
  - get_library(category?)  → the curated static library (pure deterministic,
    instant, no AI, no quota). These are the "proven phrases" reference set.
  - adapt_to_topic(topic)   → topic-tailored trigger phrases (deterministic-first,
    AI-enriched, NEVER 402 — AI failure silently keeps the deterministic output).

Nothing here posts or sends — generation only.
"""

import hashlib
import json
import logging
import random

from app.services.ai_service import generate_with_ai

logger = logging.getLogger(__name__)

# Curated, proven high-CTR phrases. `{t}` marks where a topic can be injected by
# adapt_to_topic(); the static library returns them verbatim as reference copy.
CATEGORIES: dict[str, dict] = {
    "curiosity_gap": {
        "label": "Curiosity Gap",
        "why": "Opens a loop the viewer must close by clicking — the single strongest CTR lever.",
        "phrases": [
            "What nobody tells you about {t}",
            "The part of {t} they always skip",
            "You've only heard half the story about {t}",
            "There's a detail about {t} that changes everything",
            "The truth about {t} isn't what you were taught",
            "Something about {t} doesn't add up",
            "Before you decide about {t}, watch this",
            "The {t} question nobody wants to answer",
        ],
    },
    "urgency": {
        "label": "Urgency & Stakes",
        "why": "Raises the cost of scrolling past — makes watching feel time-sensitive.",
        "phrases": [
            "Watch this before you make up your mind about {t}",
            "Most Christians get {t} wrong — here's why it matters now",
            "This changes how you'll see {t} today",
            "Don't share your opinion on {t} until you've seen this",
            "If you've ever doubted {t}, start here",
            "5 minutes on {t} that could settle it for good",
        ],
    },
    "authority": {
        "label": "Authority & Proof",
        "why": "Borrows credibility from sources — reassures skeptics the claim is grounded.",
        "phrases": [
            "What the earliest Christians actually said about {t}",
            "The historical evidence about {t} they never show you",
            "Scripture and the early Church on {t} — side by side",
            "What the sources really say about {t}",
            "I checked the earliest records on {t}. Here's the truth.",
            "The uncomfortable evidence about {t}",
        ],
    },
    "us_targeted": {
        "label": "US Audience",
        "why": "Phrasing tuned for American searchers and viewers — maximises US watch-through.",
        "phrases": [
            "What most Americans get wrong about {t}",
            "The {t} question every American Christian is asking",
            "Why {t} matters for the Church in America right now",
            "A straight answer about {t} for American Catholics",
            "{t}: what they didn't teach you in Sunday school",
        ],
    },
    "subscribe_cta": {
        "label": "Subscribe CTA",
        "why": "Converts watchers into subscribers — the core growth goal.",
        "phrases": [
            "Subscribe for the story nobody else is telling.",
            "Hit subscribe — the truth gets clearer every week.",
            "If this made you think, subscribe. There's more coming.",
            "Join thousands seeking the truth — subscribe now.",
            "Don't miss the next one. Subscribe and turn on notifications.",
            "Subscribe if you'd rather have the real answer than the popular one.",
        ],
    },
    "comment_cta": {
        "label": "Comment CTA",
        "why": "Drives comments — the engagement signal that pushes videos into more feeds.",
        "phrases": [
            "What's the one question about {t} you still can't get answered? Drop it below.",
            "Were you taught something different about {t}? Tell me in the comments.",
            "Comment 'TRUTH' if this changed how you see {t}.",
            "Which part of {t} surprised you most? Let me know below.",
            "Disagree? Make your case in the comments — I read them all.",
            "Tag someone who needs to hear the truth about {t}.",
        ],
    },
}

_AI_PROMPT = """You are a high-CTR copywriter for Odili Truth Seeker, a Catholic media ministry targeting a United States audience.

For the topic: "{t}", write proven-style click-trigger phrases in these categories. Use honest curiosity — intrigue, never clickbait lies. Keep phrases short and punchy.

Return ONLY JSON with these exact keys, each an array of strings:
{{"curiosity_gap": [6 strings], "urgency": [5 strings], "authority": [5 strings], "us_targeted": [5 strings], "subscribe_cta": [5 strings], "comment_cta": [5 strings]}}"""


def get_library(category: str | None = None) -> dict:
    """Return the curated static trigger-phrase library (no AI, no quota)."""
    if category and category in CATEGORIES:
        keys = [category]
    else:
        keys = list(CATEGORIES.keys())
    return {
        "content_source": "deterministic",
        "categories": [
            {
                "key": k,
                "label": CATEGORIES[k]["label"],
                "why": CATEGORIES[k]["why"],
                "phrases": CATEGORIES[k]["phrases"],
            }
            for k in keys
        ],
    }


def _deterministic_topic(topic: str) -> dict:
    """Fill the curated phrases with the topic, seeded so output is stable."""
    t = topic.strip()
    seed = int(hashlib.sha256(t.lower().encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    out: dict[str, list[str]] = {}
    for key, meta in CATEGORIES.items():
        pool = [p.replace("{t}", t) for p in meta["phrases"]]
        rng.shuffle(pool)
        out[key] = pool
    return out


def _valid_list(v) -> bool:
    return isinstance(v, list) and any(isinstance(x, str) and x.strip() for x in v)


async def adapt_to_topic(topic: str) -> dict:
    """Topic-tailored trigger phrases. Deterministic-first, AI-enriched, never 402."""
    det = _deterministic_topic(topic)
    out: dict = {"topic": topic.strip(), "content_source": "deterministic", **det}
    try:
        raw = await generate_with_ai(_AI_PROMPT.format(t=topic.strip()[:200]))
        start, end = raw.find("{"), raw.rfind("}")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        if isinstance(ai, dict):
            enriched = False
            for key in CATEGORIES:
                if _valid_list(ai.get(key)):
                    out[key] = [x.strip() for x in ai[key] if isinstance(x, str) and x.strip()]
                    enriched = True
            if enriched:
                out["content_source"] = "ai"
    except Exception as exc:  # noqa: BLE001 — AI must never block the endpoint
        logger.info("Trigger-phrase AI enrichment unavailable (%s); using library", exc)
    return out


def top_phrases(topic: str, per_category: int = 2) -> list[str]:
    """A small flat list of topic-filled trigger phrases for embedding elsewhere.

    Pure deterministic (no AI) so callers can enrich other payloads fail-silently
    without any quota risk.
    """
    det = _deterministic_topic(topic)
    picks: list[str] = []
    for key in ("curiosity_gap", "us_targeted", "authority"):
        picks.extend(det.get(key, [])[:per_category])
    return picks
