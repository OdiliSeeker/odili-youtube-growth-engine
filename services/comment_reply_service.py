"""
Comment Reply Engine — generates high-conversion, HUMAN-LIKE reply suggestions
for YouTube comments. Generation-only:

HARD RULE: this module NEVER posts, replies, or automates anything on YouTube.
It only produces suggested text an admin can manually copy-paste.

Design (matches the codebase-wide pattern):
  deterministic-first  — pure-Python templates always produce a usable pack
  AI-enriched          — GPT upgrades the pack when available
  quota-resilient      — any AI failure silently keeps the deterministic pack
                         (these endpoints NEVER 402)

Safety guardrails:
  - no automation posting (nothing here touches the YouTube API at all)
  - no bulk generation (one comment per call + in-process rate limit)
  - no identical outputs (seeded variation per comment + regenerate nonce)
"""

import hashlib
import json
import logging
import random
import re
import threading
import time

from app.services.ai_service import generate_with_ai

logger = logging.getLogger(__name__)

# ── Session rate limit (in-process; single-process app) ─────────────────────

RATE_LIMIT_MAX = 20          # generations…
RATE_LIMIT_WINDOW = 600      # …per 10 minutes

_rate_lock = threading.Lock()
_rate_stamps: list[float] = []


class ReplyRateLimitError(Exception):
    """Raised when the per-session generation rate limit is exceeded."""


def _check_rate_limit() -> None:
    now = time.time()
    with _rate_lock:
        cutoff = now - RATE_LIMIT_WINDOW
        _rate_stamps[:] = [t for t in _rate_stamps if t > cutoff]
        if len(_rate_stamps) >= RATE_LIMIT_MAX:
            raise ReplyRateLimitError(
                f"Rate limit reached ({RATE_LIMIT_MAX} generations per "
                f"{RATE_LIMIT_WINDOW // 60} minutes). Please wait a bit."
            )
        _rate_stamps.append(now)


# ── Intent classification (pure Python) ─────────────────────────────────────

INTENT_TYPES = ("SEEKING", "CONFUSED", "HOSTILE", "CURIOUS", "TESTIMONY")

_HOSTILE_MARKERS = (
    "idolatry", "idol worship", "pagan", "unbiblical", "false church", "false religion",
    "brainwash", "cult", "wake up", "lies", "liar", "deceived", "antichrist",
    "man-made", "blasphemy", "heresy", "works based", "works-based", "nowhere in the bible",
)
_CONFUSED_MARKERS = (
    "i thought", "doesn't that mean", "doesnt that mean", "isn't that", "isnt that",
    "i don't understand", "i dont understand", "confused", "makes no sense",
    "contradicts", "but the bible says", "how can", "that can't be", "that cant be",
)
_TESTIMONY_MARKERS = (
    "i converted", "i came back", "i returned", "coming home", "rcia", "ocia",
    "i was received", "my conversion", "i used to be", "i grew up", "confirmed this easter",
    "pray for me", "praying for", "my testimony", "changed my life", "i'm catholic now",
    "im catholic now",
)
_SEEKING_MARKERS = (
    "how do i", "where do i start", "what should i read", "can you explain",
    "can someone explain", "recommend", "which translation", "how to pray",
    "want to learn", "want to know", "thinking about becoming", "considering",
    "should i", "is it true that", "what does the church teach", "why do catholics",
)
_CURIOUS_MARKERS = (
    "interesting", "never heard", "didn't know", "didnt know", "curious",
    "what about", "genuine question", "honest question", "always wondered",
    "can anyone", "does anyone know", "where does",
)


def classify_intent(text: str) -> str:
    """Classify a comment into one of INTENT_TYPES. Pure Python, no AI."""
    t = (text or "").lower()
    scores = {
        "HOSTILE": sum(2 for m in _HOSTILE_MARKERS if m in t),
        "TESTIMONY": sum(2 for m in _TESTIMONY_MARKERS if m in t),
        "CONFUSED": sum(2 for m in _CONFUSED_MARKERS if m in t),
        "SEEKING": sum(2 for m in _SEEKING_MARKERS if m in t),
        "CURIOUS": sum(1 for m in _CURIOUS_MARKERS if m in t),
    }
    if "?" in t:
        scores["SEEKING"] += 1
        scores["CURIOUS"] += 1
    # Aggressive punctuation / shouting leans hostile.
    if re.search(r"!{2,}", t) or (len(t) > 20 and t == t.upper()):
        scores["HOSTILE"] += 1
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "CURIOUS" if "?" in t else "TESTIMONY" if len(t) > 240 else "CURIOUS"
    return best


def _is_high_intent(text: str, intent: str) -> bool:
    """Hard CTA is RARE: clear sincere question, no hostility."""
    if intent not in ("SEEKING", "CURIOUS"):
        return False
    t = (text or "").lower()
    if "?" not in t:
        return False
    if any(m in t for m in _HOSTILE_MARKERS):
        return False
    return any(m in t for m in _SEEKING_MARKERS)


# ── Deterministic reply templates ────────────────────────────────────────────
# Each tone has several phrasing pools; a seeded RNG picks per comment so no
# two comments get identical wording, and the regenerate nonce reshuffles.

TONES = ("gentle", "logical", "friendly")

_TOPIC_FALLBACK = "this question"

_OPENERS = {
    "SEEKING": {
        "gentle": [
            "That's a really beautiful question to be asking.",
            "I love that you're asking this — it matters more than most people realize.",
            "This is one of those questions that quietly changes everything once you dig in.",
        ],
        "logical": [
            "Good question — and it actually has a more concrete answer than most people expect.",
            "This one has a surprisingly well-documented answer.",
            "Fair question. The historical record on this is clearer than you'd think.",
        ],
        "friendly": [
            "Great question honestly, I wondered the same thing for years.",
            "Oh man, this exact question is what sent me down the rabbit hole.",
            "You're asking the right question here.",
        ],
    },
    "CONFUSED": {
        "gentle": [
            "I can see why it looks that way at first — a lot of people share that impression.",
            "That's a really common misunderstanding, and it's not your fault — it's rarely explained well.",
            "This gets misrepresented so often that your confusion is completely understandable.",
        ],
        "logical": [
            "There's actually a distinction here that clears this up.",
            "The confusion usually comes from two ideas getting blended together.",
            "It looks like a contradiction until you see the missing piece.",
        ],
        "friendly": [
            "Totally get why that seems off — I thought the same until someone walked me through it.",
            "Yeah this one trips a lot of people up (me included, once).",
            "I used to think exactly that, so I get it.",
        ],
    },
    "HOSTILE": {
        "gentle": [
            "I hear the frustration — these topics touch something deep.",
            "That's a strong charge, and honestly it deserves a serious answer rather than a slogan.",
            "I understand why you'd say that; a lot of people have only ever heard one side.",
        ],
        "logical": [
            "That's a common objection — worth looking at what the earliest sources actually say.",
            "Fair challenge. The primary sources are the best place to test it.",
            "If that claim were true, we'd expect the earliest Christian writings to reflect it — it's worth checking whether they do.",
        ],
        "friendly": [
            "I'd genuinely rather have this conversation than avoid it.",
            "Honest pushback is welcome — better than indifference.",
            "I appreciate the directness, seriously.",
        ],
    },
    "CURIOUS": {
        "gentle": [
            "It's a lovely thing to be curious about.",
            "That curiosity is worth following — this topic goes deep.",
            "What a great thing to wonder about.",
        ],
        "logical": [
            "Interesting angle — there's real history behind this one.",
            "That's exactly the kind of detail the early sources address.",
            "Good instinct; this is where things get interesting.",
        ],
        "friendly": [
            "Right?? This is one of my favorite things to talk about.",
            "Glad someone else finds this fascinating.",
            "Ha, I've wondered the same — and the answer surprised me.",
        ],
    },
    "TESTIMONY": {
        "gentle": [
            "Thank you for sharing this — it's genuinely moving.",
            "What a gift to read this. God clearly isn't finished with your story.",
            "This is beautiful. Praying for you right now.",
        ],
        "logical": [
            "Stories like yours are their own kind of evidence — thank you for telling it.",
            "Experiences like this are exactly why these conversations matter.",
            "Thank you for writing this out — it will encourage more people than you know.",
        ],
        "friendly": [
            "This made my day — thank you for sharing it.",
            "So glad you shared this. Welcome (or welcome back!).",
            "Love this. Thanks for putting it into words.",
        ],
    },
}

_SUBSTANCE = {
    "gentle": [
        "The short version: the earliest Christians wrestled with {topic} too, and the answer they handed down is more hopeful than most people expect.",
        "When you look at how the first generations of Christians approached {topic}, a very consistent picture emerges — one rooted in Scripture and lived practice.",
    ],
    "logical": [
        "On {topic}, the writings of the first two centuries — people taught directly by the apostles or their students — are remarkably consistent, and that consistency is hard to explain away.",
        "The key is that {topic} wasn't invented later; you can trace it in documents from the first and second century, well before any of the usual 'it was added later' dates.",
    ],
    "friendly": [
        "What surprised me about {topic} is that the earliest sources are way more specific than people assume — it's not vague at all once you actually read them.",
        "Digging into {topic}, the thing that got me was how early the evidence shows up. Way earlier than I'd been told.",
    ],
}

_EXPANSION_ADDON = {
    "gentle": [
        "If you ever want to go deeper, the Church Fathers — Ignatius of Antioch, Justin Martyr, Irenaeus — wrote about this within living memory of the apostles, and their words are surprisingly tender.",
        "The early Church took {topic} seriously enough that men like Ignatius of Antioch (writing around 107 AD) treated it as settled — that's within one lifetime of the apostles.",
    ],
    "logical": [
        "For primary sources: Ignatius of Antioch (~107 AD), Justin Martyr (~155 AD) and Irenaeus (~180 AD) all address this directly. Those dates matter — they predate every alternative theory's timeline.",
        "Irenaeus, who was taught by Polycarp, who was taught by the apostle John, addresses {topic} explicitly. That's a two-link chain to an eyewitness.",
    ],
    "friendly": [
        "Fun fact: guys like Justin Martyr were writing about this stuff in the 100s AD — I had no idea any of that existed until a few years ago.",
        "If you like primary sources, the early Church Fathers are shockingly readable on {topic} — Ignatius's letters take like 20 minutes.",
    ],
}

_SOFT_CTA = {
    "gentle": [
        "I actually walked through this gently in a recent video on the channel — happy to point you to it if that would help.",
        "We covered this on our channel recently in a way people said finally made it click — glad to share it if you'd like.",
    ],
    "logical": [
        "I actually laid out the sources on this step-by-step in a recent video — happy to share it if you're interested.",
        "I went through the primary documents on this in a video not long ago; can link it if you want to check the evidence yourself.",
    ],
    "friendly": [
        "I actually covered this in a short video recently — happy to share it if you're curious.",
        "Funny enough I just made a video about exactly this — glad to send it your way if you want.",
    ],
}

_HARD_CTA = {
    "gentle": [
        "Here's the video that walks through it gently, step by step: [link placeholder]",
        "This one covers your exact question with a lot of care: [link placeholder]",
    ],
    "logical": [
        "Here's the video that lays out the sources on this clearly: [link placeholder]",
        "This video goes through the evidence point by point: [link placeholder]",
    ],
    "friendly": [
        "Here's the video that explains this clearly: [link placeholder]",
        "This is the one I mentioned — it answers your exact question: [link placeholder]",
    ],
}

_CLOSERS = {
    "gentle": ["Wishing you well on the journey.", "You're in my prayers as you explore this.", ""],
    "logical": ["Happy to point you to the primary sources if useful.", "Worth examining the evidence firsthand.", ""],
    "friendly": ["What do you think?", "Curious where you land on it.", ""],
}


def _derive_topic_phrase(comment_text: str, video_title: str) -> str:
    """Best-effort short phrase naming what the comment is about."""
    t = (comment_text or "").strip()
    m = re.search(r"(?:why|how|what|where|when|is|are|does|do|did|can|should)\b[^?.!]{8,80}", t, re.IGNORECASE)
    if m:
        return m.group(0).strip().rstrip(",;:").lower()
    vt = (video_title or "").strip()
    if vt:
        vt = re.sub(r"[#|].*$", "", vt).strip()
        if 4 < len(vt) < 80:
            return f'the question behind "{vt}"'
    return _TOPIC_FALLBACK


def _seed_for(comment_text: str, nonce: int) -> int:
    h = hashlib.sha256(f"{comment_text}|{nonce}".encode()).hexdigest()
    return int(h[:12], 16)


def _pick(rng: random.Random, pool: list[str], topic: str) -> str:
    return rng.choice(pool).replace("{topic}", topic)


def _deterministic_pack(comment_text: str, video_title: str, channel_name: str, nonce: int) -> dict:
    intent = classify_intent(comment_text)
    high_intent = _is_high_intent(comment_text, intent)
    topic = _derive_topic_phrase(comment_text, video_title)
    rng = random.Random(_seed_for(comment_text, nonce))
    include_soft = intent in ("SEEKING", "CURIOUS")

    tones = {}
    for tone in TONES:
        opener = _pick(rng, _OPENERS[intent][tone], topic)
        substance = _pick(rng, _SUBSTANCE[tone], topic)
        closer = _pick(rng, _CLOSERS[tone], topic)
        primary = " ".join(p for p in (opener, substance, closer) if p).strip()
        expansion = " ".join(p for p in (opener, substance, _pick(rng, _EXPANSION_ADDON[tone], topic)) if p).strip()
        tones[tone] = {
            "primary": primary,
            "expansion": expansion,
            "soft_cta": (primary + " " + _pick(rng, _SOFT_CTA[tone], topic)).strip() if include_soft else None,
            "hard_cta": (primary + " " + _pick(rng, _HARD_CTA[tone], topic)).strip() if high_intent else None,
        }

    return {
        "intent": intent,
        "high_intent": high_intent,
        "tones": tones,
        "timing_suggestion": _timing_suggestion(intent),
        "notes": _safety_note(intent),
    }


def _timing_suggestion(intent: str) -> str:
    if intent == "HOSTILE":
        return "Wait 12–24 hours before replying — never respond to hostility in the heat of the moment. One thoughtful reply only; don't chase the thread."
    if intent in ("SEEKING", "CURIOUS"):
        return "Reply within 2–6 hours while the commenter is still engaged. Avoid late-night reply bursts — they read as automated."
    if intent == "TESTIMONY":
        return "Reply within a day; warmth matters more than speed here."
    return "Reply within 2–6 hours. Space out replies — avoid bursts of many replies in a short window."


def _safety_note(intent: str) -> str:
    base = "Manual use only — copy, personalize a word or two, and post it yourself."
    if intent == "HOSTILE":
        return base + " No CTA for hostile comments: win the tone, not the argument."
    return base


# ── AI enrichment ────────────────────────────────────────────────────────────

_AI_PROMPT = """You are ghost-writing YouTube comment replies for the owner of the Catholic channel "{channel}". A viewer commented on the video "{video}":

COMMENT: "{comment}"

Detected intent: {intent}. High-intent (sincere direct question): {high}.

Write reply suggestions in THREE tone styles: gentle (pastoral), logical (apologetic), friendly (conversational). For each tone provide:
- "primary": a direct, conversational answer. NO link, NO channel plug, no preaching.
- "expansion": the primary idea plus a brief Church Fathers / early-Church reference (name + rough date).
- "soft_cta": ONLY if intent is SEEKING or CURIOUS — naturally mention you covered this in a recent video and offer to share it (no link). Otherwise null.
- "hard_cta": ONLY if high-intent is true — may include the text "[link placeholder]" where a link would go. Otherwise null.

STYLE RULES (critical):
- Sound like a real human commenter, NOT a brand. Slightly imperfect is good.
- Short-to-medium length. Never start with "As a Catholic".
- Never robotic, never aggressive, never repeat phrasing between tones.
- Answer the question FIRST; any CTA comes last and stays subtle.

Return ONLY JSON:
{{"tones": {{"gentle": {{"primary": "...", "expansion": "...", "soft_cta": null, "hard_cta": null}}, "logical": {{...}}, "friendly": {{...}}}}}}"""


def _extract_json(raw: str) -> dict | None:
    if not raw:
        return None
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except (ValueError, TypeError):
        return None


def _merge_ai_tones(pack: dict, ai: dict) -> bool:
    """Overlay AI tone text onto the deterministic pack. Returns True if used."""
    tones = ai.get("tones")
    if not isinstance(tones, dict):
        return False
    used = False
    include_soft = pack["intent"] in ("SEEKING", "CURIOUS")
    for tone in TONES:
        at = tones.get(tone)
        if not isinstance(at, dict):
            continue
        dt = pack["tones"][tone]
        for key in ("primary", "expansion"):
            v = at.get(key)
            if isinstance(v, str) and v.strip():
                dt[key] = v.strip()
                used = True
        soft = at.get("soft_cta")
        if include_soft and isinstance(soft, str) and soft.strip():
            dt["soft_cta"] = soft.strip()
        elif not include_soft:
            dt["soft_cta"] = None
        hard = at.get("hard_cta")
        if pack["high_intent"] and isinstance(hard, str) and hard.strip():
            dt["hard_cta"] = hard.strip()
        elif not pack["high_intent"]:
            dt["hard_cta"] = None
    return used


async def generate_reply_pack(
    comment_text: str,
    video_title: str = "",
    channel_name: str = "Odili Truth Seeker",
    *,
    nonce: int = 0,
) -> dict:
    """Full reply pack: intent + 3 tones × (primary/expansion/soft/hard CTA).

    Deterministic-first; AI silently upgrades when available. Raises only
    ReplyRateLimitError (never AI/quota errors).
    """
    _check_rate_limit()
    pack = _deterministic_pack(comment_text, video_title, channel_name, nonce)
    pack["content_source"] = "deterministic"
    try:
        raw = await generate_with_ai(_AI_PROMPT.format(
            channel=channel_name or "Odili Truth Seeker",
            video=(video_title or "(unknown video)")[:200],
            comment=(comment_text or "")[:1500],
            intent=pack["intent"],
            high=pack["high_intent"],
        ))
        ai = _extract_json(raw)
        if ai and _merge_ai_tones(pack, ai):
            pack["content_source"] = "ai"
    except Exception as exc:  # deterministic pack always survives
        logger.info("Reply AI enrichment unavailable (%s); using deterministic pack", exc)
    return pack


# ── Conversation Continuation Mode ───────────────────────────────────────────

_CONTINUE_PROMPT = """You are ghost-writing the NEXT reply in an ongoing YouTube comment thread for the owner of the Catholic channel "{channel}". Here is the thread so far (oldest first):

{thread}

Write 3 candidate follow-up replies (gentle, logical, friendly) that continue the conversation naturally. Keep answering first, stay human and unrepetitive, never aggressive, at most ONE subtle channel mention across all three (and only if the other person seems genuinely open). Return ONLY JSON:
{{"replies": {{"gentle": "...", "logical": "...", "friendly": "..."}}}}"""


async def continue_thread(thread_text: str, channel_name: str = "Odili Truth Seeker") -> dict:
    """Follow-up reply suggestions for a pasted reply thread. Never 402s."""
    _check_rate_limit()
    intent = classify_intent(thread_text)
    rng = random.Random(_seed_for(thread_text, 0))
    topic = _derive_topic_phrase(thread_text, "")
    fallback = {
        tone: (
            _pick(rng, _OPENERS[intent][tone], topic)
            + " " + _pick(rng, _SUBSTANCE[tone], topic)
        ).strip()
        for tone in TONES
    }
    out = {"intent": intent, "replies": fallback, "content_source": "deterministic",
           "timing_suggestion": _timing_suggestion(intent)}
    try:
        raw = await generate_with_ai(_CONTINUE_PROMPT.format(
            channel=channel_name or "Odili Truth Seeker",
            thread=(thread_text or "")[:3000],
        ))
        ai = _extract_json(raw)
        replies = (ai or {}).get("replies")
        if isinstance(replies, dict) and all(
            isinstance(replies.get(t), str) and replies[t].strip() for t in TONES
        ):
            out["replies"] = {t: replies[t].strip() for t in TONES}
            out["content_source"] = "ai"
    except Exception as exc:
        logger.info("Continuation AI unavailable (%s); using deterministic replies", exc)
    return out
