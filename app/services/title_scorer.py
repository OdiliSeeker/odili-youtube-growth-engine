"""
Title Scorer — a deterministic CTR *predictor* for YouTube titles.

score_title(title) rates a specific title 0-100 across five weighted dimensions
(curiosity, clarity, emotional pull, keyword strength, length) and returns a
verdict plus concrete improvement suggestions. Pure Python — NO AI, so it always
works and is instant.

generate_optimized_titles(topic) runs the full pipeline: build 10 candidate
titles (deterministic-first, AI-enriched when available), score each, and return
the ranked list plus the top 3.
"""

import hashlib
import json
import logging
import random
import re

logger = logging.getLogger(__name__)

# ── Signal vocabularies (Catholic apologetics niche) ────────────────────────
_CURIOSITY_MARKERS = (
    "what nobody", "what no one", "nobody tells", "no one tells", "what really",
    "what they never", "never taught", "what you weren't", "you weren't told",
    "you've been told", "youve been told", "the truth about", "the real",
    "what happened", "what if", "the part", "the reason", "before you",
    "the question", "here's why", "heres why", "what the", "the secret",
    "nobody explains", "the story", "actually",
)
_CONTRAST_MARKERS = (
    "not what you think", "backwards", "wrong", " vs ", " vs.", "instead of",
    "but the", "isn't what", "isnt what", "the opposite", "myth",
)
_EMOTIONAL_WORDS = (
    "truth", "shocking", "hidden", "real", "forbidden", "lost", "forgotten",
    "proof", "evidence", "exposed", "revealed", "revealing", "warning",
    "dangerous", "powerful", "stunning", "uncomfortable", "undeniable",
    "never", "everything", "changes everything", "wrong",
)
_KEYWORDS = (
    "catholic", "catholicism", "bible", "biblical", "early christians",
    "early church", "church fathers", "eucharist", "mary", "pope", "papacy",
    "protestant", "scripture", "saints", "mass", "confession", "purgatory",
    "salvation", "christian", "apostles", "gospel",
)
_VAGUE_WORDS = ("things", "stuff", "interesting", "amazing", "cool", "some", "various")

_VERDICT_HIGH, _VERDICT_MED = 75, 55


def _count_hits(text: str, needles) -> int:
    return sum(1 for n in needles if n in text)


def _score_curiosity(t: str) -> tuple[int, str | None]:
    hits = _count_hits(t, _CURIOSITY_MARKERS)
    contrast = _count_hits(t, _CONTRAST_MARKERS)
    has_q = "?" in t or bool(re.match(r"^(why|how|what|is|did|are|can|should|where)\b", t))
    pts = min(25, hits * 8 + contrast * 7 + (5 if has_q else 0))
    tip = None
    if pts < 12:
        tip = "Add a curiosity gap — e.g. \"what nobody tells you\", \"not what you think\", or open with Why/What/How."
    return pts, tip


def _score_clarity(t: str, words: list[str]) -> tuple[int, str | None]:
    pts = 20
    tip = None
    if len(words) > 14:
        pts -= 8
        tip = "Tighten it — aim for 14 words or fewer so the point lands instantly."
    elif len(words) < 3:
        pts -= 6
        tip = "Too short to be clear — say what the video actually reveals."
    if _count_hits(t, _VAGUE_WORDS):
        pts -= 6
        tip = "Replace vague words (things/stuff/interesting) with the concrete subject."
    if t.count(":") + t.count("—") + t.count("|") >= 3:
        pts -= 4
    return max(0, pts), tip


def _score_emotional(t: str) -> tuple[int, str | None]:
    hits = _count_hits(t, _EMOTIONAL_WORDS)
    pts = min(20, hits * 7)
    tip = None
    if pts < 7:
        tip = "Add an emotional trigger word like truth, hidden, real, proof, or forgotten."
    return pts, tip


def _score_keywords(t: str) -> tuple[int, str | None]:
    hits = _count_hits(t, _KEYWORDS)
    pts = min(20, hits * 10)
    tip = None
    if pts < 10:
        tip = "Include a searchable keyword (Catholic, Bible, early Church, Eucharist, Mary, Pope…) so it ranks."
    return pts, tip


def _score_length(t: str) -> tuple[int, str | None]:
    n = len(t)
    if 45 <= n <= 65:
        return 15, None
    if 35 <= n < 45 or 65 < n <= 75:
        return 10, "Nudge length toward the 45-65 character sweet spot."
    if 25 <= n < 35 or 75 < n <= 90:
        return 6, "Length is off — 45-65 characters gets the most clicks."
    return 2, "Length hurts clicks — rewrite to 45-65 characters."


def score_title(title: str) -> dict:
    """Deterministic 0-100 CTR prediction with breakdown + improvements."""
    t = (title or "").strip()
    low = t.lower()
    words = [w for w in re.split(r"\s+", t) if w]

    curiosity, c_tip = _score_curiosity(low)
    clarity, cl_tip = _score_clarity(low, words)
    emotional, e_tip = _score_emotional(low)
    keyword, k_tip = _score_keywords(low)
    length, l_tip = _score_length(t)

    score = curiosity + clarity + emotional + keyword + length
    verdict = "High CTR" if score >= _VERDICT_HIGH else "Medium" if score >= _VERDICT_MED else "Low"
    improvements = [tip for tip in (c_tip, cl_tip, e_tip, k_tip, l_tip) if tip]
    if not improvements:
        improvements = ["Strong title — test it against one more curiosity-driven variant."]

    return {
        "title": t,
        "score": score,
        "breakdown": {
            "curiosity": curiosity,
            "clarity": clarity,
            "emotional_pull": emotional,
            "keyword_strength": keyword,
            "length": length,
        },
        "verdict": verdict,
        "improvements": improvements,
    }


# ── Optimized-titles pipeline ───────────────────────────────────────────────
_TITLE_TEMPLATES = [
    "What Early Christians Actually Believed About {t}",
    "The Truth About {t} Nobody Taught You",
    "You've Been Told the Wrong Story About {t}",
    "{t}: The Part They Never Explained",
    "Why Everything You Heard About {t} Is Backwards",
    "The Hidden History of {t} Changes Everything",
    "{t} — What the First Christians Would Say",
    "The {t} Question Nobody Wants to Answer",
    "Is {t} Actually Biblical? The Evidence",
    "What the Bible Really Says About {t}",
    "The Forgotten Truth About {t}",
    "{t}: What the Earliest Sources Reveal",
    "Most Christians Get {t} Completely Wrong",
    "The Real Reason {t} Still Matters Today",
]

_AI_PROMPT = """Generate 10 high-CTR YouTube titles for a Catholic truth-seeking channel on the topic: "{t}".

Use curiosity gaps, contradiction, and hidden-truth framing. Keep every title honest (intrigue, never clickbait lies) and ideally 45-65 characters. Prefer including a searchable keyword.

Return ONLY a JSON array of 10 strings."""


def _core_subject(topic: str) -> str:
    t = (topic or "").strip().rstrip("?.!")
    t = re.sub(r"^(what|why|how|is|did|are|can|should|where|do|does)\b\s+", "", t, flags=re.I)
    return t.strip().capitalize() or (topic or "").strip()


def _deterministic_titles(topic: str) -> list[str]:
    core = _core_subject(topic)
    seed = int(hashlib.sha256(core.lower().encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    pool = _TITLE_TEMPLATES[:]
    rng.shuffle(pool)
    return [tpl.replace("{t}", core) for tpl in pool[:10]]


async def generate_optimized_titles(topic: str) -> dict:
    """Generate 10 titles → score each → return ranked list + top 3."""
    titles = _deterministic_titles(topic)
    source = "deterministic"
    try:
        from app.services.ai_service import generate_with_ai

        raw = (await generate_with_ai(_AI_PROMPT.format(t=(topic or "").strip()[:200]))).strip()
        start, end = raw.find("["), raw.rfind("]")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        if isinstance(ai, list):
            clean = [x.strip() for x in ai if isinstance(x, str) and x.strip()][:10]
            if len(clean) >= 5:
                titles = clean
                source = "ai"
    except Exception as exc:  # noqa: BLE001 — never 402, keep deterministic titles
        logger.info("Optimized-titles AI enrich skipped: %s", exc)

    ranked = sorted((score_title(t) for t in titles), key=lambda r: r["score"], reverse=True)
    return {
        "topic": (topic or "").strip(),
        "top_titles": ranked[:3],
        "all_titles_ranked": ranked,
        "content_source": source,
    }
