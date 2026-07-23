"""
Conversion Engine — turns topics/comments into subscriber-converting copy.

Three generators (all deterministic-first + AI-enriched, never 402):
  generate_comment_reply(lead_text)   — human reply + soft CTA + link version
  generate_email_conversion(topic)    — CTR subject/hook/body/CTA/reply prompt
  generate_landing_cta(topic)         — headline / subheadline / button text

NOTE: nothing here posts or sends anything — output is copy for human use.
"""

import hashlib
import json
import logging
import random

from app.services.ai_service import generate_with_ai
from app.services import comment_reply_service, ctr_phrase_engine

logger = logging.getLogger(__name__)


# ── 1. Comment reply (thin wrapper over the Comment Reply Engine) ────────────

async def generate_comment_reply(lead_text: str, *, video_title: str = "", channel_name: str = "Odili Truth Seeker") -> dict:
    """{reply, soft_cta, direct_link_version} — answer first, one subtle CTA max."""
    pack = await comment_reply_service.generate_reply_pack(
        lead_text, video_title, channel_name
    )
    friendly = pack["tones"]["friendly"]
    gentle = pack["tones"]["gentle"]
    reply = friendly["primary"] or gentle["primary"]
    soft = friendly.get("soft_cta") or gentle.get("soft_cta")
    hard = friendly.get("hard_cta") or gentle.get("hard_cta")
    return {
        "intent": pack["intent"],
        "reply": reply,
        "soft_cta": soft or "(No CTA suggested for this intent — answer only.)",
        "direct_link_version": hard or "(Link version not recommended for this comment.)",
        "timing_suggestion": pack["timing_suggestion"],
        "content_source": pack["content_source"],
    }


# ── 2. Email conversion pack ─────────────────────────────────────────────────

_REPLY_PROMPTS = [
    "Hit reply and tell me: what's the one question about this you've never gotten a straight answer to?",
    "Reply to this email with the part you find hardest to believe — I read every response.",
    "What did you grow up hearing about this? Hit reply, I'd love to know.",
    "If you could ask one question about this, what would it be? Just hit reply.",
]

_EMAIL_AI_PROMPT = """Write a conversion-focused email for the Catholic media ministry "Odili Truth Seeker" on the topic: "{t}".

Return ONLY JSON:
{{"subject_line": "curiosity-gap subject, under 60 chars, no clickbait lies",
"opening_hook": "1-2 sentences that create an open loop",
"teaching_body": "3 short paragraphs, plain text, one insight rooted in Scripture/early Church, warm and human",
"youtube_cta": "one sentence inviting them to watch the video (no URL)",
"reply_prompt": "one sentence asking them to hit reply with a question or reaction"}}"""


def _deterministic_email(topic: str) -> dict:
    t = topic.strip()
    seed = int(hashlib.sha256(t.lower().encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    phrases = ctr_phrase_engine._deterministic(t)
    return {
        "subject_line": phrases["titles"][0][:78],
        "opening_hook": rng.choice([
            f"Most people have only ever heard one side of {t} — and it shows.",
            f"There's a detail about {t} that almost never makes it into the debate.",
            f"I used to think {t} was settled. Then I read the earliest sources.",
        ]),
        "teaching_body": (
            f"When people argue about {t}, they usually start centuries too late. "
            f"The earliest Christians — the generation taught by the apostles themselves — left us letters, homilies and records that speak directly to this.\n\n"
            f"And what they wrote is strikingly consistent. Not vague, not divided: consistent. That consistency is the strongest kind of historical evidence we have.\n\n"
            f"That's why we keep going back to the sources on this channel. Truth holds up under examination — {t} included."
        ),
        "youtube_cta": "I walk through the actual sources, step by step, in this week's video — come see the evidence for yourself.",
        "reply_prompt": rng.choice(_REPLY_PROMPTS),
    }


async def generate_email_conversion(email_topic: str) -> dict:
    out = _deterministic_email(email_topic)
    out["content_source"] = "deterministic"
    try:
        raw = await generate_with_ai(_EMAIL_AI_PROMPT.format(t=email_topic.strip()[:200]))
        start, end = raw.find("{"), raw.rfind("}")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        if ai:
            used = False
            for key in ("subject_line", "opening_hook", "teaching_body", "youtube_cta", "reply_prompt"):
                v = ai.get(key)
                if isinstance(v, str) and v.strip():
                    out[key] = v.strip()
                    used = True
            if used:
                out["content_source"] = "ai"
    except Exception as exc:
        logger.info("Email conversion AI unavailable (%s); using deterministic copy", exc)
    return out


# ── 3. Landing CTA pack ──────────────────────────────────────────────────────

_LANDING_AI_PROMPT = """Write landing-page conversion copy for the Catholic media ministry "Odili Truth Seeker" on the topic: "{t}". Audience: truth-seekers, skeptics, and curious Christians.

Return ONLY JSON:
{{"headline": "curiosity-driven, under 70 chars", "subheadline": "one sentence expanding the promise", "button_text": "2-4 words, action-first"}}"""


def _deterministic_landing(topic: str) -> dict:
    t = topic.strip()
    seed = int(hashlib.sha256(("landing|" + t.lower()).encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    return {
        "headline": rng.choice([
            f"The Truth About {t} Nobody Explains Clearly",
            f"What Early Christians Actually Believed About {t}",
            f"You've Been Told the Wrong Story About {t}",
        ]),
        "subheadline": rng.choice([
            "Go back to the earliest sources and see what the first Christians actually taught — the evidence might surprise you.",
            "Real questions deserve real answers — rooted in Scripture, history, and the early Church.",
        ]),
        "button_text": rng.choice(["Get the Truth", "Start Exploring", "Show Me the Evidence"]),
    }


async def generate_landing_cta(topic: str) -> dict:
    out = _deterministic_landing(topic)
    out["content_source"] = "deterministic"
    try:
        raw = await generate_with_ai(_LANDING_AI_PROMPT.format(t=topic.strip()[:200]))
        start, end = raw.find("{"), raw.rfind("}")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        if ai:
            used = False
            for key in ("headline", "subheadline", "button_text"):
                v = ai.get(key)
                if isinstance(v, str) and v.strip():
                    out[key] = v.strip()
                    used = True
            if used:
                out["content_source"] = "ai"
    except Exception as exc:
        logger.info("Landing CTA AI unavailable (%s); using deterministic copy", exc)
    return out
