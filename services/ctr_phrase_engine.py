"""
High-CTR Phrase Engine — generates click-psychology titles, hooks, and CTA
phrases for a topic, and tracks phrase performance for future scoring.

Deterministic-first + AI-enriched + quota-resilient (never 402s). Patterns:
curiosity gap, contradiction, hidden truth, authority reversal, "you've been
told X… but". Seeded rotation avoids duplicate output across topics/calls.
"""

import hashlib
import json
import logging
import random

from sqlalchemy.orm import Session

from app.models.db_models import CtrPerformance
from app.services.ai_service import generate_with_ai

logger = logging.getLogger(__name__)

PHRASE_TYPES = ("title", "hook", "cta")

_TITLE_PATTERNS = [
    "What Early Christians Actually Believed About {t} (Not What You Think)",
    "The Truth About {t} Nobody Explains Clearly",
    "You've Been Told the Wrong Story About {t}",
    "{t}: The Part They Never Taught You",
    "Why Everything You Heard About {t} Is Backwards",
    "The Hidden History of {t} (It Changes Everything)",
    "{t} — What the First Christians Would Say Today",
    "I Thought I Understood {t}. Then I Read the Sources.",
    "The {t} Question Nobody Wants to Answer",
    "{t}: What the Earliest Records Actually Show",
    "Before You Decide About {t}, Watch This",
    "The Uncomfortable Evidence About {t}",
]

_HOOK_PATTERNS = [
    "Something doesn't add up…",
    "This is where most people get it wrong.",
    "You've probably been told one side of this story.",
    "The earliest sources say something different.",
    "I didn't believe this either — until I checked.",
    "Here's what nobody mentions about {t}.",
    "Most explanations of {t} skip the most important part.",
    "What if the version you heard was incomplete?",
    "The real history of {t} starts earlier than you think.",
    "Everyone argues about {t}. Almost nobody reads the sources.",
    "There's a detail about {t} that changes the whole debate.",
    "This question about {t} deserves a straight answer.",
]

_CTA_PATTERNS = [
    "Watch this before you decide.",
    "This might change how you see everything.",
    "See the evidence for yourself.",
    "Don't take my word for it — check the sources.",
    "The full story is in the video.",
    "If you've ever wondered about {t}, start here.",
    "Get the answer the earliest Christians gave.",
    "Take 5 minutes and settle this for yourself.",
    "Your questions about {t} deserve real answers.",
    "Go deeper — the truth holds up.",
    "Subscribe for the story nobody else is telling.",
    "One video could change the whole conversation.",
]

_AI_PROMPT = """Generate high-CTR YouTube phrases for a Catholic truth-seeking channel on the topic: "{t}".

Use these psychological patterns: curiosity gap, contradiction, hidden truth, authority reversal, "you've been told X… but". Keep every phrase honest — intrigue, never clickbait lies.

Return ONLY JSON:
{{"titles": [10 strings], "hooks": [10 strings], "cta_phrases": [10 strings]}}"""


def _fill(patterns: list[str], topic: str, rng: random.Random, n: int = 10) -> list[str]:
    pool = patterns[:]
    rng.shuffle(pool)
    return [p.replace("{t}", topic) for p in pool[:n]]


def _deterministic(topic: str) -> dict:
    seed = int(hashlib.sha256(topic.lower().encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    t = topic.strip()
    return {
        "titles": _fill(_TITLE_PATTERNS, t, rng),
        "hooks": _fill(_HOOK_PATTERNS, t, rng),
        "cta_phrases": _fill(_CTA_PATTERNS, t, rng),
    }


def _valid_list(v, n_min: int = 5) -> bool:
    return isinstance(v, list) and len([x for x in v if isinstance(x, str) and x.strip()]) >= n_min


async def generate_ctr_phrases(topic: str) -> dict:
    """10 titles + 10 hooks + 10 CTAs. Deterministic-first, AI-enriched."""
    out = _deterministic(topic)
    out["content_source"] = "deterministic"
    try:
        raw = await generate_with_ai(_AI_PROMPT.format(t=topic.strip()[:200]))
        start, end = raw.find("{"), raw.rfind("}")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        if ai:
            for key in ("titles", "hooks", "cta_phrases"):
                if _valid_list(ai.get(key)):
                    out[key] = [x.strip() for x in ai[key] if isinstance(x, str) and x.strip()][:10]
                    out["content_source"] = "ai"
    except Exception as exc:
        logger.info("CTR AI enrichment unavailable (%s); using deterministic phrases", exc)
    return out


# ── Performance tracking (future scoring input) ─────────────────────────────

def record_phrase(db: Session, *, phrase: str, phrase_type: str) -> dict:
    """Save a phrase the admin chose to use (idempotent per phrase+type)."""
    ptype = phrase_type if phrase_type in PHRASE_TYPES else "title"
    row = (
        db.query(CtrPerformance)
        .filter(CtrPerformance.phrase == phrase[:500], CtrPerformance.phrase_type == ptype)
        .first()
    )
    if row is None:
        row = CtrPerformance(phrase=phrase[:500], phrase_type=ptype)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _serialize(row)


def log_result(db: Session, *, perf_id: int, clicks: int = 0, conversions: int = 0) -> dict | None:
    row = db.get(CtrPerformance, perf_id)
    if row is None:
        return None
    row.clicks += max(0, int(clicks))
    row.conversions += max(0, int(conversions))
    db.commit()
    return _serialize(row)


def list_performance(db: Session) -> list[dict]:
    rows = (
        db.query(CtrPerformance)
        .order_by(CtrPerformance.conversions.desc(), CtrPerformance.clicks.desc(), CtrPerformance.id.desc())
        .limit(200)
        .all()
    )
    return [_serialize(r) for r in rows]


def _serialize(r: CtrPerformance) -> dict:
    return {
        "id": r.id,
        "phrase": r.phrase,
        "type": r.phrase_type,
        "clicks": r.clicks,
        "conversions": r.conversions,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
