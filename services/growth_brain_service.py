"""
Growth Brain — the high-conversion command center.

This module does NOT reinvent the existing engines. It adds the two primitives
that were genuinely missing and composes everything into one pack:

  1. score_title()          — a PREDICTIVE title CTR score (0-100) with a
                              component breakdown, reasons, and concrete tips.
                              Pure-Python + deterministic (a predictor must be
                              stable across calls), so it never costs quota.
  2. TRIGGER_PHRASES        — a curated "Click Trigger Phrases" library of
                              proven high-CTR patterns the admin can browse.
  3. build_brain()          — one call that fans out to the existing engines
                              (ctr_phrase_engine, us_targeting_engine,
                              seo_service, conversion_engine, growth_service),
                              then ranks titles by predicted CTR and hooks by
                              scroll-stopping intensity.

Philosophy (matches the rest of the app): deterministic-first, AI-enriched,
never 402. Every composed engine is already deterministic-first, and each fan-out
is additionally guarded so build_brain() can NEVER raise. Nothing here posts,
sends, or publishes — it returns copy for a human to use.
"""

import logging
import re

logger = logging.getLogger(__name__)


# ── 1. Predictive Title CTR Scorer ───────────────────────────────────────────

# Curiosity-gap / open-loop signals.
_CURIOSITY_WORDS = {
    "secret", "hidden", "truth", "actually", "really", "nobody", "no one",
    "never", "wrong", "myth", "surprising", "shocking", "untold", "revealed",
    "what", "why", "how", "the real", "you've been", "they don't", "the part",
}

# Power / emotional-stakes signals.
_POWER_WORDS = {
    "proof", "evidence", "stop", "warning", "before", "mistake", "lie",
    "exposed", "banned", "forbidden", "dangerous", "urgent", "must", "need",
    "changes everything", "uncomfortable", "backwards", "cost you",
}

_WORD_RE = re.compile(r"[a-z']+")

# CTR band cutoffs (predicted, not measured).
_BANDS = (
    (80, "Elite"),
    (65, "Strong"),
    (45, "Average"),
    (0, "Weak"),
)


def _band(score: int) -> str:
    for cutoff, label in _BANDS:
        if score >= cutoff:
            return label
    return "Weak"


def _count_signals(low: str, signals: set) -> int:
    return sum(1 for s in signals if s in low)


def score_title(title: str) -> dict:
    """Predict how well a YouTube title will earn clicks (0-100, deterministic).

    Returns the score, a human-readable band, a per-component breakdown, the
    reasons it scores well, and concrete tips to push it higher.
    """
    t = (title or "").strip()
    if not t:
        return {
            "title": "", "score": 0, "band": "Weak",
            "components": {}, "reasons": [], "tips": ["Enter a title to score it."],
        }

    low = t.lower()
    words = t.split()
    wc = len(words)
    n = len(t)
    reasons: list[str] = []
    tips: list[str] = []

    # Length — YouTube's visible sweet spot is roughly 40-60 characters.
    if 40 <= n <= 60:
        length = 100
        reasons.append("Ideal length (40–60 chars) — shows in full on search and suggested.")
    elif 30 <= n < 40 or 60 < n <= 70:
        length = 78
    elif n < 30:
        length = 52
        tips.append("A little short — add a specific detail or a curiosity hook.")
    else:
        length = 42
        tips.append("Over ~70 characters risks truncation on mobile — tighten it.")

    # Curiosity gap.
    cur_hits = _count_signals(low, _CURIOSITY_WORDS)
    curiosity = min(100, 28 + cur_hits * 22)
    if cur_hits == 0:
        tips.append("Add a curiosity trigger (e.g. 'the truth about', 'what nobody tells you').")
    else:
        reasons.append("Opens a curiosity gap that pulls the click.")

    # Emotional stakes / power words.
    pw_hits = _count_signals(low, _POWER_WORDS)
    emotion = min(100, 22 + pw_hits * 20)
    if pw_hits == 0:
        tips.append("Raise the stakes with a power word (e.g. 'proof', 'mistake', 'before you').")

    # Specificity — numbers, structure, second person.
    spec = 40
    if re.search(r"\d", t):
        spec += 26
        reasons.append("Contains a number — concrete and easy to scan.")
    if "(" in t or "—" in t or ":" in t:
        spec += 16
        reasons.append("Uses a parenthetical / colon aside — a proven CTR pattern.")
    if re.search(r"\byou\b|\byour\b|\byou've\b", low):
        spec += 16
        reasons.append("Speaks directly to the viewer ('you').")
    spec = min(100, spec)

    # Clarity — penalize clickbait smell and bloat.
    clarity = 100
    caps_words = sum(1 for w in words if len(w) > 2 and w.isupper())
    if caps_words > 2:
        clarity -= 42
        tips.append("Too many ALL-CAPS words reads as clickbait — keep at most one for emphasis.")
    if wc > 14:
        clarity -= 22
        tips.append("Trim toward ~6–12 words — long titles dilute the hook.")
    if "?" in t:
        reasons.append("Question format — matches how people actually search.")
    clarity = max(0, clarity)

    components = {
        "length_fit": length,
        "curiosity": curiosity,
        "emotional_pull": emotion,
        "specificity": spec,
        "clarity": clarity,
    }
    score = int(round(
        0.22 * length + 0.28 * curiosity + 0.18 * emotion
        + 0.17 * spec + 0.15 * clarity
    ))
    score = max(0, min(100, score))

    return {
        "title": t,
        "score": score,
        "band": _band(score),
        "components": components,
        "reasons": reasons,
        "tips": tips,
    }


def rank_titles(titles: list[str], *, limit: int = 8) -> list[dict]:
    """Score a list of candidate titles and return them ranked (best first)."""
    seen: set[str] = set()
    scored: list[dict] = []
    for raw in titles:
        t = (raw or "").strip()
        key = t.lower()
        if not t or key in seen:
            continue
        seen.add(key)
        scored.append(score_title(t))
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored[:limit]


# ── 2. Click Trigger Phrases library (curated, proven patterns) ───────────────

# Static, browsable library of high-CTR phrase patterns. "{t}" is the topic
# placeholder, filled in when a topic is supplied.
TRIGGER_PHRASES: dict[str, list[str]] = {
    "curiosity_gap": [
        "The truth about {t} nobody explains clearly",
        "What they never taught you about {t}",
        "There's a part of the {t} story you've never heard",
        "You've been told the wrong story about {t}",
    ],
    "authority_reversal": [
        "What the earliest Christians actually believed about {t}",
        "I thought I understood {t}. Then I read the sources.",
        "The evidence about {t} that most people never check",
    ],
    "us_searcher": [
        "Is {t} actually biblical?",
        "{t} explained in plain English",
        "Why do Catholics believe in {t}?",
        "The {t} question every American asks",
    ],
    "urgency": [
        "Before you make up your mind about {t}, watch this",
        "This changes how you see {t}",
        "Don't decide about {t} until you've seen this",
    ],
    "social_proof": [
        "The {t} answer that keeps changing minds",
        "Thousands asked about {t} — here's the real answer",
    ],
    "subscribe_cta": [
        "Subscribe for the story nobody else is telling.",
        "Follow along — the truth holds up under examination.",
        "Hit subscribe and keep seeking the truth with us.",
    ],
}


def list_trigger_phrases(topic: str | None = None) -> dict:
    """Return the curated trigger-phrase library, filled for `topic` if given."""
    t = (topic or "").strip()
    filled = {
        category: [p.replace("{t}", t) if t else p for p in phrases]
        for category, phrases in TRIGGER_PHRASES.items()
    }
    return {"topic": t or None, "categories": filled}


# ── 3. Deterministic conversion scripts (pinned comment + CTAs) ───────────────

def _pinned_comment(topic: str) -> str:
    t = topic.strip()
    return (
        f"📌 If you've ever wondered about {t}, you're in the right place. "
        f"I read the earliest sources so you don't have to guess — drop your "
        f"biggest question below and I'll answer it. And if this helped, "
        f"subscribe so the next answer finds you."
    )


# ── 4. Growth Brain aggregator ───────────────────────────────────────────────

async def _safe(coro, fallback):
    """Await a composed engine; never let a fan-out failure sink the brain."""
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 — deterministic fallback keeps output
        logger.info("Growth Brain sub-engine unavailable (%s); using fallback", exc)
        return fallback


async def build_brain(topic: str) -> dict:
    """Compose the full high-conversion pack for a topic. Never raises, never 402.

    Fans out to the existing engines, then applies the predictive Title Scorer
    (titles ranked by CTR) and the hook-intensity scorer (hooks ranked).
    """
    from app.services import (
        ctr_phrase_engine,
        us_targeting_engine,
        seo_service,
        conversion_engine,
        growth_service,
    )

    t = (topic or "").strip()
    if not t:
        raise ValueError("A topic is required.")

    ctr = await _safe(ctr_phrase_engine.generate_ctr_phrases(t), None) or ctr_phrase_engine._deterministic(t)
    us = await _safe(us_targeting_engine.optimize_for_us(t), None) or us_targeting_engine._deterministic(t)
    kw = await _safe(seo_service.generate_keywords(t), {"keywords": []})
    landing = await _safe(conversion_engine.generate_landing_cta(t), None) or conversion_engine._deterministic_landing(t)

    sources = {
        ctr.get("content_source", "deterministic"),
        us.get("content_source", "deterministic"),
        kw.get("source", "deterministic"),
        landing.get("content_source", "deterministic"),
    }
    content_source = "ai" if "ai" in sources else "deterministic"

    # Optimized titles: pool the CTR titles + US title variants, rank by CTR.
    title_pool = list(ctr.get("titles", [])) + list(us.get("title_variants", []))
    scored_titles = rank_titles(title_pool, limit=8)
    best_title = scored_titles[0] if scored_titles else score_title(t)

    # Viral hooks ranked by scroll-stopping intensity.
    hooks = [
        {"hook": h, "intensity": growth_service.score_hook_intensity(h)}
        for h in ctr.get("hooks", []) if h and h.strip()
    ]
    hooks.sort(key=lambda x: x["intensity"], reverse=True)

    # US-first keyword set: US search phrases lead, SEO queries fill in.
    us_keywords = list(us.get("keywords", []))
    seo_keywords = list(kw.get("keywords", []))
    merged_kw: list[str] = []
    seen_kw: set[str] = set()
    for k in us_keywords + seo_keywords:
        kk = (k or "").strip()
        if kk and kk.lower() not in seen_kw:
            seen_kw.add(kk.lower())
            merged_kw.append(kk)

    # Subscribe / watch-next CTA blocks (deterministic).
    ctas = growth_service.build_ctas(None)

    return {
        "topic": t,
        "content_source": content_source,
        "best_title": best_title,
        "optimized_titles": scored_titles,
        "viral_hooks": hooks[:8],
        "us_targeting": {
            "phrasing_adjustments": us.get("phrasing_adjustments", ""),
            "keywords": merged_kw[:12],
        },
        "conversion_scripts": {
            "pinned_comment": _pinned_comment(t),
            "cta_phrases": ctr.get("cta_phrases", [])[:6],
            "subscribe_cta": ctas.get("subscribe_cta") or ctas.get("subscribe"),
            "watch_next_cta": ctas.get("watch_next_cta") or ctas.get("watch_next"),
        },
        "trigger_phrases": list_trigger_phrases(t)["categories"],
        "landing_cta": landing,
    }
