"""
US Keyword Engine — targets real U.S. search demand for Catholic apologetics.

generate_us_keywords(topic) matches a topic against a seed database of real
American search queries, expands into long-tail keywords + questions, and
proposes search-optimized video titles. Biased toward USA phrasing, simple
English, and question-based searches. Deterministic-first + AI-enriched +
never-402.
"""

import hashlib
import json
import logging
import random
import re

logger = logging.getLogger(__name__)

# Hardcoded seed of real, high-intent U.S. search queries (question-based).
_SEED_QUERIES = [
    "Is Catholicism biblical",
    "Why do Catholics pray to Mary",
    "Did early Christians believe in the Pope",
    "Is the Eucharist symbolic or real",
    "What did the early Church believe",
    "Catholic vs Protestant truth",
    "Is the Catholic Church the original Church",
    "Where is purgatory in the Bible",
    "Did the early Christians go to Mass",
    "Is confession in the Bible",
    "Who started the Catholic Church",
    "What did the church fathers believe",
    "Is praying to saints biblical",
    "Was Peter the first Pope",
    "Did early Christians believe in the real presence",
]

_LONGTAIL_TEMPLATES = [
    "what did early Christians believe about {t}",
    "is {t} biblical Catholic teaching",
    "{t} in the early Church",
    "what does the Bible say about {t}",
    "{t} Catholic vs Protestant",
    "history of {t} in Christianity",
]

_QUESTION_TEMPLATES = [
    "Is {t} in the Bible?",
    "What did the early Church teach about {t}?",
    "Why do Catholics believe in {t}?",
    "Did the first Christians accept {t}?",
    "Is {t} biblical?",
]

_TITLE_TEMPLATES = [
    "What Early Christians Believed About {tc}",
    "Is {tc} Biblical? Here's the Evidence",
    "{tc}: Catholic vs Protestant Explained",
    "The Bible on {tc} — What It Really Says",
]

_AI_PROMPT = """Generate U.S. search-targeted keywords for a Catholic truth-seeking channel on the topic: "{t}".

Bias toward American phrasing, simple English, and question-based searches with real demand.

Return ONLY JSON:
{{"primary_keywords": [5 short phrases], "long_tail_keywords": [6 longer phrases], "questions": [5 question strings], "video_titles": [4 title strings]}}"""


def _core_subject(topic: str) -> str:
    t = (topic or "").strip().rstrip("?.!")
    t = re.sub(r"^(what|why|how|is|did|are|can|should|where|do|does)\b\s+", "", t, flags=re.I)
    return t.strip() or (topic or "").strip()


def _tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "of", "in", "to", "is", "did", "do", "does", "and", "on", "for", "what", "why", "how", "about"}
    return {w for w in re.split(r"[^a-z]+", text.lower()) if w and w not in stop}


def _match_seed(topic: str, limit: int = 5) -> list[str]:
    """Closest seed queries by token overlap (deterministic tie-break)."""
    topic_tokens = _tokens(topic)
    scored = []
    for q in _SEED_QUERIES:
        overlap = len(topic_tokens & _tokens(q))
        scored.append((overlap, q))
    scored.sort(key=lambda x: (-x[0], x[1]))
    matched = [q for ov, q in scored if ov > 0][:limit]
    if not matched:  # no overlap → seed a deterministic sample so output is never empty
        seed = int(hashlib.sha256(topic.lower().encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        matched = rng.sample(_SEED_QUERIES, min(limit, len(_SEED_QUERIES)))
    return matched


def _deterministic(topic: str) -> dict:
    core = _core_subject(topic)
    core_l = core.lower()
    core_c = core.capitalize()
    return {
        "primary_keywords": _match_seed(topic, 5),
        "long_tail_keywords": [tpl.replace("{t}", core_l) for tpl in _LONGTAIL_TEMPLATES],
        "questions": [tpl.replace("{t}", core_l) for tpl in _QUESTION_TEMPLATES],
        "video_titles": [tpl.replace("{tc}", core_c) for tpl in _TITLE_TEMPLATES],
    }


def _valid_list(v, n_min: int) -> bool:
    return isinstance(v, list) and len([x for x in v if isinstance(x, str) and x.strip()]) >= n_min


async def generate_us_keywords(topic: str) -> dict:
    """Primary + long-tail keywords, questions, and titles. Det-first, AI-enriched."""
    out = _deterministic(topic)
    out["content_source"] = "deterministic"
    try:
        from app.services.ai_service import generate_with_ai

        raw = (await generate_with_ai(_AI_PROMPT.format(t=(topic or "").strip()[:200]))).strip()
        start, end = raw.find("{"), raw.rfind("}")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        if isinstance(ai, dict):
            enriched = False
            specs = {"primary_keywords": 3, "long_tail_keywords": 3, "questions": 3, "video_titles": 2}
            for key, n_min in specs.items():
                if _valid_list(ai.get(key), n_min):
                    out[key] = [x.strip() for x in ai[key] if isinstance(x, str) and x.strip()]
                    enriched = True
            if enriched:
                out["content_source"] = "ai"
    except Exception as exc:  # noqa: BLE001 — never 402, keep deterministic keywords
        logger.info("US-keyword AI enrich skipped: %s", exc)
    return out
