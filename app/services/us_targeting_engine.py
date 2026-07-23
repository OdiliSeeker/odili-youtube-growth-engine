"""
USA Traffic Optimization Engine — adapts a topic's phrasing/keywords/titles for
a North-American (especially US) audience. Deterministic-first + AI-enriched,
never 402s. Pure copy suggestions — changes nothing automatically.
"""

import hashlib
import json
import logging
import random

from app.services.ai_service import generate_with_ai

logger = logging.getLogger(__name__)

# Practical questions Americans actually search (seed list).
_US_SEARCH_SEEDS = [
    "Is Catholicism biblical",
    "Why do Catholics pray to Mary",
    "Did early Christians believe in the Pope",
    "Is the Eucharist really the body of Christ",
    "Where is confession in the Bible",
    "Is purgatory in the Bible",
    "Catholic vs Protestant differences explained",
    "What do Catholics actually believe",
    "Why do Catholics have saints",
    "Is the Catholic Church the first church",
]

_PHRASING_RULES = (
    "Use direct, conversational American phrasing (contractions are fine). "
    "Lead with the practical question, not the doctrine label. "
    "Avoid academic/European framing ('whilst', 'Holy Mass', long Latin phrases) — "
    "say 'Mass', 'the Bible', 'the early Church'. Frame answers as evidence a "
    "skeptical American can check, not as appeals to authority."
)

_AI_PROMPT = """Optimize the topic "{t}" for a UNITED STATES YouTube/search audience for a Catholic truth-seeking channel.

Rules: American conversational phrasing (not global/academic English); prioritize the practical questions Americans actually type into search (like "Is Catholicism biblical", "Why do Catholics pray to Mary"); avoid an overly academic tone.

Return ONLY JSON:
{{"phrasing_adjustments": "2-3 sentences of concrete phrasing advice for this topic",
"keywords": [8-10 US search phrases for this topic],
"title_variants": [5 US-optimized video titles]}}"""


def _deterministic(topic: str) -> dict:
    t = topic.strip()
    seed = int(hashlib.sha256(("us|" + t.lower()).encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    seeds = _US_SEARCH_SEEDS[:]
    rng.shuffle(seeds)
    return {
        "phrasing_adjustments": _PHRASING_RULES + f" For '{t}', open with the exact question a searcher would type, answer it in the first 30 seconds, then show the sources.",
        "keywords": [f"{t} explained", f"is {t} biblical", f"{t} catholic answer", f"what do catholics believe about {t}", f"{t} early church"] + seeds[:5],
        "title_variants": [
            f"Is {t} Actually Biblical? (What the Sources Say)",
            f"{t}: What Catholics Actually Believe",
            f"The {t} Question Every American Asks",
            f"{t} — Explained in Plain English",
            f"What Early Christians Believed About {t}",
        ],
    }


async def optimize_for_us(topic: str) -> dict:
    out = _deterministic(topic)
    out["content_source"] = "deterministic"
    try:
        raw = await generate_with_ai(_AI_PROMPT.format(t=topic.strip()[:200]))
        start, end = raw.find("{"), raw.rfind("}")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        if ai:
            used = False
            v = ai.get("phrasing_adjustments")
            if isinstance(v, str) and v.strip():
                out["phrasing_adjustments"] = v.strip()
                used = True
            for key in ("keywords", "title_variants"):
                lv = ai.get(key)
                if isinstance(lv, list) and len([x for x in lv if isinstance(x, str) and x.strip()]) >= 3:
                    out[key] = [x.strip() for x in lv if isinstance(x, str) and x.strip()][:10]
                    used = True
            if used:
                out["content_source"] = "ai"
    except Exception as exc:
        logger.info("US targeting AI unavailable (%s); using deterministic output", exc)
    return out
