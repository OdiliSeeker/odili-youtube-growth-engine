"""
Viral Hook Engine — niche-tuned opening hooks for Catholic apologetics content.

generate_hooks(topic) returns short hooks, long hooks, and hooks grouped by
psychological pattern (curiosity, contradiction, challenge, hidden_truth).
Deterministic-first + AI-enriched + never-402. Tailored to the Catholic vs
Protestant / early-Church-vs-modern tension rather than generic AI fluff.
"""

import hashlib
import json
import logging
import random
import re

logger = logging.getLogger(__name__)

_PATTERNS = {
    "curiosity": [
        "Something doesn't add up about {t}…",
        "There's a detail about {t} almost nobody mentions.",
        "The real story of {t} starts earlier than you think.",
        "What if what you heard about {t} was only half true?",
        "Most explanations of {t} skip the most important part.",
    ],
    "contradiction": [
        "You've been told one thing about {t} — the early Church believed another.",
        "Everything you were taught about {t} points the wrong way.",
        "Modern churches and the first Christians disagree on {t}. Here's the proof.",
        "What you think about {t} isn't what the earliest records show.",
        "The popular version of {t} gets the history backwards.",
    ],
    "challenge": [
        "If this about {t} is true, everything changes.",
        "Be honest — were you ever actually taught the truth about {t}?",
        "Can you defend what you believe about {t}? Watch this first.",
        "Before you argue about {t}, read what the sources actually say.",
        "Here's the {t} question most people can't answer.",
    ],
    "hidden_truth": [
        "This about {t} was settled centuries ago — but almost nobody knows it.",
        "The earliest Christians left a record on {t}. It's been ignored.",
        "There's a forgotten truth about {t} hiding in plain sight.",
        "The Church answered {t} long before the debate you're hearing today.",
        "What history reveals about {t} isn't in most Sunday sermons.",
    ],
}

_SHORT_HOOKS = [
    "Something doesn't add up…",
    "This is where most people get it wrong.",
    "You've probably only heard one side.",
    "The earliest sources say something different.",
    "I didn't believe this either — until I checked.",
    "Most Christians miss this entirely.",
    "What if you were told only half the story?",
    "This changes how you read the whole thing.",
    "Almost nobody talks about this.",
    "The history here is not what you'd expect.",
]

_AI_PROMPT = """Generate viral opening hooks for a Catholic truth-seeking YouTube channel on the topic: "{t}".

Tailor to the Catholic-vs-Protestant tension and early-Church-vs-modern-belief angle. Honest intrigue, never clickbait lies.

Return ONLY JSON:
{{"short_hooks": [10 short punchy strings], "long_hooks": [5 one-to-two sentence strings], "pattern_types": {{"curiosity": [3 strings], "contradiction": [3 strings], "challenge": [3 strings], "hidden_truth": [3 strings]}}}}"""


def _core_subject(topic: str) -> str:
    t = (topic or "").strip().rstrip("?.!")
    t = re.sub(r"^(what|why|how|is|did|are|can|should|where|do|does)\b\s+", "", t, flags=re.I)
    return t.strip() or (topic or "").strip()


def _deterministic(topic: str) -> dict:
    core = _core_subject(topic)
    seed = int(hashlib.sha256(core.lower().encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    patterns = {k: [p.replace("{t}", core) for p in v] for k, v in _PATTERNS.items()}
    # One lead hook per pattern (4), plus a second curiosity hook so the
    # deterministic path always returns exactly 5 — the never-402 contract.
    long_hooks = [group[0] for group in patterns.values()]
    long_hooks.append(patterns["curiosity"][1])
    long_hooks = long_hooks[:5]
    shorts = _SHORT_HOOKS[:]
    rng.shuffle(shorts)
    return {
        "short_hooks": shorts[:10],
        "long_hooks": long_hooks,
        "pattern_types": {k: v[:3] for k, v in patterns.items()},
    }


def _valid_list(v, n_min: int) -> bool:
    return isinstance(v, list) and len([x for x in v if isinstance(x, str) and x.strip()]) >= n_min


async def generate_hooks(topic: str) -> dict:
    """Short + long + pattern-grouped hooks. Deterministic-first, AI-enriched."""
    out = _deterministic(topic)
    out["content_source"] = "deterministic"
    try:
        from app.services.ai_service import generate_with_ai

        raw = (await generate_with_ai(_AI_PROMPT.format(t=(topic or "").strip()[:200]))).strip()
        start, end = raw.find("{"), raw.rfind("}")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        if isinstance(ai, dict):
            enriched = False
            if _valid_list(ai.get("short_hooks"), 5):
                out["short_hooks"] = [x.strip() for x in ai["short_hooks"] if isinstance(x, str) and x.strip()][:10]
                enriched = True
            if _valid_list(ai.get("long_hooks"), 3):
                out["long_hooks"] = [x.strip() for x in ai["long_hooks"] if isinstance(x, str) and x.strip()][:5]
                enriched = True
            pt = ai.get("pattern_types")
            if isinstance(pt, dict):
                for key in _PATTERNS:
                    if _valid_list(pt.get(key), 2):
                        out["pattern_types"][key] = [x.strip() for x in pt[key] if isinstance(x, str) and x.strip()][:3]
                        enriched = True
            if enriched:
                out["content_source"] = "ai"
    except Exception as exc:  # noqa: BLE001 — never 402, keep deterministic hooks
        logger.info("Viral-hooks AI enrich skipped: %s", exc)
    return out
