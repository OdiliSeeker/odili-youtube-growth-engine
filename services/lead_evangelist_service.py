"""
The Lead Evangelist — a compliant, multi-platform lead accumulation engine.

Turns the app into a lead accumulator / email-list builder WITHOUT spamming:
  - Curated core marketing messages (supplied by the ministry) + per-platform
    etiquette and daily pace caps that keep outreach human and welcome.
  - personalize(): a per-target message variant (deterministic-first,
    AI-enriched, NEVER 402) with a tracked link (?src=<platform>) so every
    signup is attributed to the platform that produced it.
  - An outreach log (EvangelistOutreach) the admin fills in as they post —
    powering pace warnings (anti-spam) and a conversion dashboard.

**NOTHING here auto-posts anywhere.** The admin copies a message and posts it
as a human. That, plus per-target variation and daily pace caps, is what
prevents any spamming effect and keeps every platform's TOS respected.
"""

import asyncio
import hashlib
import json
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.db_models import AppSetting, Event, EvangelistOutreach
from app.services.ai_service import generate_with_ai

logger = logging.getLogger(__name__)

SITE_URL = "https://odilitheseekeroftruth.today"

STATUSES = ("logged", "responded", "subscribed")

# ── Core messages (ministry-supplied, verbatim) ────────────────────────────
CORE_MESSAGES: dict[str, dict] = {
    "universal": {
        "label": "Universal Marketing Message",
        "best_for": "Longer posts: Facebook groups, Reddit posts, email replies",
        "text": (
            "Deep down… you know something doesn't add up.\n\n"
            "What if the version of Christianity most people believe today isn't "
            "what the earliest Christians actually taught?\n\n"
            "I built something for you:\n\n"
            "👉 Go here: {link}\n\n"
            "- Test your instincts with interactive story quizzes\n"
            "- Vote on real faith questions people are asking\n"
            "- Get the first teaching instantly (no fluff, just truth)\n\n"
            "Start here and tell me what you think after.\n\n"
            "You might never see your faith the same way again."
        ),
    },
    "short_comment": {
        "label": "Shorter Version (comments/replies)",
        "best_for": "Quick comments and replies on any platform",
        "text": (
            "Quick one:\n\n"
            "Something about modern Christianity doesn't match what the early "
            "Church believed.\n\n"
            "Try this:\n"
            "👉 {link}\n\n"
            "Start with the quiz — it'll challenge how you think."
        ),
    },
    "high_conversion_comment": {
        "label": "High Conversion Comment",
        "best_for": "Replying to someone's genuine question (YouTube, Reddit, Facebook)",
        "text": (
            "That's actually a deeper question than most people realize.\n\n"
            "The early Christians answered this VERY differently.\n\n"
            "I put together something that breaks it down step by step:\n"
            "👉 {link}\n\n"
            "Start with the first teaching — curious what you'll think after."
        ),
    },
    "tiktok_short": {
        "label": "TikTok / Short Style",
        "best_for": "TikTok captions, YouTube Shorts, Instagram Reels",
        "text": (
            "Most Christians have never been told this…\n\n"
            "The early Church didn't believe what you think it did.\n\n"
            "I built a quick experience to test this:\n"
            "👉 {link}\n\n"
            "Start with the quiz.\n\n"
            "Don't skip it."
        ),
    },
}

# ── Rotation pool (ministry-supplied, verbatim) ────────────────────────────
# 20 alternate short posts that Auto-Cadence alternates with the core
# messages above, so the every-2-days cadence never looks monotonous.
ROTATION_MESSAGES: list[str] = [
    "Something about modern Christianity doesn’t feel complete…\n\nI finally found out why.\n\nTry this for yourself:\n👉 {link}\n\nStart with the first teaching.",
    "Most people were never told what the early Christians actually believed.\n\nThat’s where everything changes.\n\nSee for yourself:\n👉 {link}",
    "You ever feel like something doesn’t fully add up?\n\nI did too.\n\nThis helped me see things differently:\n👉 {link}",
    "If what you believe is true…\n\nit should match what the earliest Christians believed, right?\n\nTest that here:\n👉 {link}",
    "This might challenge everything you thought you knew about Christianity.\n\nStart here:\n👉 {link}\n\nDon’t skip the quiz.",
    "A lot of Christians believe things Jesus never actually taught.\n\nI didn’t realize it either.\n\nSee the difference here:\n👉 {link}",
    "There’s a version of Christianity most people have never seen.\n\nIt’s not modern.\nIt’s original.\n\nExplore it here:\n👉 {link}",
    "What if the truth has been right in front of us… but misunderstood?\n\nStart here:\n👉 {link}\n\nLet me know what you think after.",
    "Quick challenge:\n\nDo your beliefs match the early Church?\n\nFind out here:\n👉 {link}",
    "This changed how I understand Christianity completely.\n\nIt might do the same for you:\n\n👉 {link}",
    "Most people never question what they were taught.\n\nBut what if you did?\n\n👉 {link}",
    "Before you argue about Christianity…\n\nyou should see this.\n\n👉 {link}",
    "There’s a reason the early Christians believed differently.\n\nAnd it matters.\n\nStart here:\n👉 {link}",
    "You don’t need opinions.\n\nYou need what was originally taught.\n\nSee it here:\n👉 {link}",
    "This isn’t about religion.\n\nIt’s about truth.\n\n👉 {link}",
    "If you’ve ever had doubts…\n\nyou’re not alone.\n\nStart here:\n👉 {link}",
    "Something isn’t lining up…\n\nAnd you probably feel it.\n\nThis explains why:\n👉 {link}",
    "Most people skip this step…\n\nand miss everything.\n\nDon’t.\n\n👉 {link}",
    "There’s a gap between what’s taught today and what was believed before.\n\nThat gap matters.\n\n👉 {link}",
    "You don’t have to take my word for it.\n\nSee it yourself:\n\n👉 {link}",
]

# ── Platform playbook: etiquette + anti-spam pace caps ─────────────────────
PLATFORMS: dict[str, dict] = {
    "youtube": {
        "label": "YouTube",
        "daily_cap": 10,
        "recommended_messages": ["high_conversion_comment", "short_comment"],
        "etiquette": [
            "Reply to real questions in comments — never drop the link on unrelated videos.",
            "Lead with a genuine answer first; the link comes second.",
            "Use the Lead Discovery tab to find seekers already asking questions.",
        ],
    },
    "tiktok": {
        "label": "TikTok",
        "daily_cap": 8,
        "recommended_messages": ["tiktok_short", "short_comment"],
        "etiquette": [
            "Best as your OWN video captions — comment links get suppressed fast.",
            "In comments, answer the question and say 'link in my bio' instead of pasting the URL.",
            "Vary wording every time; TikTok downranks repeated comment text.",
        ],
    },
    "facebook": {
        "label": "Facebook",
        "daily_cap": 6,
        "recommended_messages": ["universal", "high_conversion_comment"],
        "etiquette": [
            "Only post in groups where faith discussion is on-topic and links are allowed.",
            "Engage with the thread first, then share when relevant.",
            "Never post the same text in multiple groups on the same day.",
        ],
    },
    "instagram": {
        "label": "Instagram",
        "daily_cap": 8,
        "recommended_messages": ["tiktok_short", "short_comment"],
        "etiquette": [
            "Links only work in bio/stories — in comments, point to the bio link.",
            "Reply personally to DMs that ask questions; never cold-DM strangers.",
        ],
    },
    "reddit": {
        "label": "Reddit",
        "daily_cap": 3,
        "recommended_messages": ["high_conversion_comment", "universal"],
        "etiquette": [
            "Read each subreddit's self-promotion rules FIRST — many ban link drops.",
            "Give a substantial answer; the link should feel like a footnote.",
            "Keep a 10:1 ratio of normal participation to link shares.",
        ],
    },
    "x": {
        "label": "X (Twitter)",
        "daily_cap": 8,
        "recommended_messages": ["short_comment", "tiktok_short"],
        "etiquette": [
            "Reply to conversations about faith questions — never mass-reply.",
            "Shorten the message to fit; the hook matters more than the details.",
        ],
    },
    "email": {
        "label": "Email (1-to-1)",
        "daily_cap": 15,
        "recommended_messages": ["universal"],
        "etiquette": [
            "Only people who asked you something or already know you — never cold lists.",
            "Bulk sending belongs in the Email Queue with proper unsubscribe links, not here.",
        ],
    },
}

# Deterministic personalization: alternate opening lines keyed by trigger style.
_OPENERS = [
    "You asked something most people are afraid to ask.",
    "I've wrestled with this exact question too.",
    "Honest answer? Most of us were never told the whole story.",
    "This comes up more than you'd think — and the real answer surprises people.",
    "I appreciate you asking this sincerely.",
]

_AI_PROMPT = """You are The Lead Evangelist for Odili Truth Seeker, a Catholic media ministry inviting people to {link}.

Platform: {platform}
Base message style: {style}
{context_block}

Rewrite the base message below as ONE personalized, natural, non-spammy {platform} message. Rules:
- Sound like a real human responding personally — never like a broadcast.
- Keep the link {link} exactly as given.
- Warm, respectful, curious tone. No pressure, no ALL-CAPS hype.
- Fit the platform's culture and typical length.

Base message:
---
{base}
---

Return ONLY JSON: {{"message": "<the personalized message>"}}"""


def _today_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)


def tracked_link(platform: str) -> str:
    """Site link with per-platform attribution (?src=) the funnel understands."""
    return f"{SITE_URL}/?src={platform}" if platform in PLATFORMS else SITE_URL


def get_playbook() -> dict:
    """The full Lead Evangelist playbook (pure deterministic, no AI/quota)."""
    return {
        "content_source": "deterministic",
        "site_url": SITE_URL,
        "principles": [
            "Nothing auto-posts. You copy, you post, as a human — that is the anti-spam guarantee.",
            "Every message is personalized per target so no two posts look copy-pasted.",
            "Respect the daily pace cap per platform; slower and sincere beats fast and flagged.",
            "Every link carries ?src=<platform>, so signups are attributed on the dashboard.",
        ],
        "messages": [
            {
                "key": k,
                "label": v["label"],
                "best_for": v["best_for"],
                "text": v["text"].replace("{link}", SITE_URL),
            }
            for k, v in CORE_MESSAGES.items()
        ],
        "rotation_pool": [t.replace("{link}", SITE_URL) for t in ROTATION_MESSAGES],
        "platforms": [
            {
                "key": k,
                "label": v["label"],
                "daily_cap": v["daily_cap"],
                "recommended_messages": v["recommended_messages"],
                "etiquette": v["etiquette"],
                "tracked_link": tracked_link(k),
            }
            for k, v in PLATFORMS.items()
        ],
    }


def _deterministic_personalize(platform: str, message_type: str, context: str) -> str:
    """Seeded variation of the core message so repeat use never looks identical."""
    base = CORE_MESSAGES[message_type]["text"].replace("{link}", tracked_link(platform))
    seed = int(hashlib.sha256(f"{platform}|{message_type}|{context.lower().strip()}".encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    if message_type in ("high_conversion_comment", "short_comment") and context.strip():
        opener = rng.choice(_OPENERS)
        return f"{opener}\n\n{base}"
    return base


def _pace(db: Session, platform: str) -> dict:
    """Today's outreach count vs the platform's anti-spam cap."""
    cap = PLATFORMS.get(platform, {}).get("daily_cap", 5)
    used = (
        db.query(func.count(EvangelistOutreach.id))
        .filter(
            EvangelistOutreach.platform == platform,
            EvangelistOutreach.created_at >= _today_utc_naive(),
        )
        .scalar()
        or 0
    )
    return {
        "daily_cap": cap,
        "used_today": used,
        "remaining_today": max(0, cap - used),
        "over_cap": used >= cap,
    }


async def personalize(
    db: Session,
    *,
    platform: str,
    message_type: str = "",
    context: str = "",
) -> dict:
    """A personalized, platform-fit, non-spammy message. Det-first + AI, never 402."""
    if platform not in PLATFORMS:
        platform = "youtube"
    if message_type not in CORE_MESSAGES:
        message_type = PLATFORMS[platform]["recommended_messages"][0]

    det = _deterministic_personalize(platform, message_type, context)
    out = {
        "platform": platform,
        "message_type": message_type,
        "message": det,
        "tracked_link": tracked_link(platform),
        "content_source": "deterministic",
        "spam_safety": {
            **_pace(db, platform),
            "etiquette": PLATFORMS[platform]["etiquette"],
            "reminder": "Post this yourself, once, where it genuinely answers someone. Log it below so pace tracking stays honest.",
        },
    }
    try:
        context_block = f'The person/thread you are answering: "{context.strip()[:400]}"' if context.strip() else "No specific thread — a general share."
        raw = await generate_with_ai(
            _AI_PROMPT.format(
                link=tracked_link(platform),
                platform=PLATFORMS[platform]["label"],
                style=CORE_MESSAGES[message_type]["label"],
                context_block=context_block,
                base=det,
            )
        )
        start, end = raw.find("{"), raw.rfind("}")
        ai = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        msg = (ai or {}).get("message")
        if isinstance(msg, str) and msg.strip() and tracked_link(platform) in msg:
            out["message"] = msg.strip()
            out["content_source"] = "ai"
    except Exception as exc:  # noqa: BLE001 — AI must never block the message
        logger.info("Lead Evangelist AI personalization unavailable (%s); using deterministic", exc)
    return out


# ── Outreach log ────────────────────────────────────────────────────────────

def log_outreach(
    db: Session,
    *,
    platform: str,
    target: str = "",
    message_type: str = "universal",
    message_text: str = "",
    notes: str = "",
) -> EvangelistOutreach:
    row = EvangelistOutreach(
        platform=platform if platform in PLATFORMS else "youtube",
        target=target.strip()[:500],
        message_type=message_type if message_type in CORE_MESSAGES else "universal",
        message_text=message_text.strip()[:5000],
        notes=notes.strip()[:1000],
        status="logged",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_status(db: Session, outreach_id: int, status: str) -> EvangelistOutreach | None:
    if status not in STATUSES:
        return None
    row = db.get(EvangelistOutreach, outreach_id)
    if row is None:
        return None
    row.status = status
    db.commit()
    db.refresh(row)
    return row


def _serialize(row: EvangelistOutreach) -> dict:
    return {
        "id": row.id,
        "platform": row.platform,
        "target": row.target,
        "message_type": row.message_type,
        "message_text": row.message_text,
        "status": row.status,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_outreach(db: Session, *, platform: str | None = None, limit: int = 100) -> dict:
    q = db.query(EvangelistOutreach).order_by(EvangelistOutreach.created_at.desc())
    if platform and platform in PLATFORMS:
        q = q.filter(EvangelistOutreach.platform == platform)
    rows = q.limit(max(1, min(limit, 500))).all()
    return {"items": [_serialize(r) for r in rows], "count": len(rows)}


def dashboard(db: Session) -> dict:
    """Per-platform outreach funnel + signup attribution + pace status."""
    per_platform = []
    for key, meta in PLATFORMS.items():
        counts = dict(
            db.query(EvangelistOutreach.status, func.count(EvangelistOutreach.id))
            .filter(EvangelistOutreach.platform == key)
            .group_by(EvangelistOutreach.status)
            .all()
        )
        total = sum(counts.values())
        per_platform.append(
            {
                "platform": key,
                "label": meta["label"],
                "outreach_total": total,
                "responded": counts.get("responded", 0),
                "subscribed": counts.get("subscribed", 0),
                **_pace(db, key),
            }
        )

    # Signup attribution from funnel events (?src= carried through /track).
    signup_sources: dict[str, int] = {}
    try:
        rows = db.query(Event.data).filter(Event.event_name == "signup").all()
        for (data,) in rows:
            try:
                src = (json.loads(data or "{}") or {}).get("src")
            except (ValueError, TypeError):
                src = None
            if src:
                signup_sources[src] = signup_sources.get(src, 0) + 1
    except Exception as exc:  # noqa: BLE001 — attribution is best-effort
        logger.info("Evangelist signup attribution unavailable (%s)", exc)

    return {
        "platforms": per_platform,
        "signup_sources": signup_sources,
        "totals": {
            "outreach": sum(p["outreach_total"] for p in per_platform),
            "responded": sum(p["responded"] for p in per_platform),
            "subscribed": sum(p["subscribed"] for p in per_platform),
        },
    }


# ── Auto-Cadence: every 2 days, at the best time, one post prepared & emailed ─
#
# The COMPLIANT automation layer: the app never posts to any platform (that
# would be bot behavior and get accounts banned). Instead, every 2 days at the
# hour the audience is historically most active, it rotates to the next
# platform, personalizes a message, and emails it to the admin ready to paste.

_AUTO_ENABLED_KEY = "evangelist_auto_enabled"
_AUTO_LAST_KEY = "evangelist_auto_last"
_AUTO_IDX_KEY = "evangelist_auto_idx"
_AUTO_MSG_IDX_KEY = "evangelist_auto_msg_idx"
_AUTO_INTERVAL_HOURS = 48
_AUTO_FALLBACK_HOUR = 17  # ~noon US Eastern — sensible default with no data

# Social rotation only — the "email" platform is 1-to-1 human outreach.
_AUTO_ROTATION = ["youtube", "facebook", "tiktok", "instagram", "reddit", "x"]


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(AppSetting, key)
    return row.value if row is not None else default


def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value
    db.commit()


def best_hour(db: Session) -> int:
    """The UTC hour with the most landing page views in the last 30 days.

    Deterministic and cheap; falls back to a sensible default with no data.
    """
    try:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        rows = (
            db.query(Event.created_at)
            .filter(Event.event_name == "page_view", Event.created_at >= cutoff)
            .all()
        )
        counts: dict[int, int] = {}
        for (ts,) in rows:
            if ts is not None:
                counts[ts.hour] = counts.get(ts.hour, 0) + 1
        if sum(counts.values()) >= 20:  # enough signal to trust the histogram
            return max(counts, key=lambda h: counts[h])
    except Exception as exc:  # noqa: BLE001 — never let analytics block cadence
        logger.info("best_hour unavailable (%s); using fallback", exc)
    return _AUTO_FALLBACK_HOUR


def auto_status(db: Session) -> dict:
    """Current Auto-Cadence state for the admin UI."""
    enabled = _get_setting(db, _AUTO_ENABLED_KEY, "1") == "1"
    last_raw = _get_setting(db, _AUTO_LAST_KEY, "")
    last = None
    if last_raw:
        try:
            last = datetime.fromisoformat(last_raw)
        except ValueError:
            last = None
    idx = 0
    try:
        idx = int(_get_setting(db, _AUTO_IDX_KEY, "0")) % len(_AUTO_ROTATION)
    except ValueError:
        pass
    next_due = (last + timedelta(hours=_AUTO_INTERVAL_HOURS)) if last else None
    return {
        "enabled": enabled,
        "interval_hours": _AUTO_INTERVAL_HOURS,
        "best_hour_utc": best_hour(db),
        "last_prepared_at": last.isoformat() if last else None,
        "next_due_at": next_due.isoformat() if next_due else None,
        "next_platform": _AUTO_ROTATION[idx],
        "rotation": _AUTO_ROTATION,
    }


def set_auto_enabled(db: Session, enabled: bool) -> dict:
    _set_setting(db, _AUTO_ENABLED_KEY, "1" if enabled else "0")
    return auto_status(db)


def run_auto_cadence(db: Session) -> dict:
    """Hourly scheduler entry point. Prepares + emails ONE post when due.

    Due = 48h since the last one AND it's the audience's best hour (UTC).
    If the server missed the best hour (downtime), a >24h-overdue catch-up
    fires at any hour so the cadence never stalls. Never auto-posts anywhere.

    Concurrency: the cadence slot is CLAIMED via an atomic compare-and-set
    UPDATE on the `last` setting (same pattern as the drip step claim), so
    overlapping runners can never both send. `last` + `idx` advance in one
    commit; an email failure reverts both in one commit so the next hourly
    run retries cleanly.
    """
    if _get_setting(db, _AUTO_ENABLED_KEY, "1") != "1":
        return {"prepared": False, "reason": "disabled"}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    last_raw = _get_setting(db, _AUTO_LAST_KEY, "")
    overdue_catchup = False
    if last_raw:
        try:
            last = datetime.fromisoformat(last_raw)
            if now < last + timedelta(hours=_AUTO_INTERVAL_HOURS):
                return {"prepared": False, "reason": "not_due"}
            overdue_catchup = now >= last + timedelta(hours=_AUTO_INTERVAL_HOURS + 24)
        except ValueError:
            overdue_catchup = True

    target_hour = best_hour(db)
    if now.hour != target_hour and not overdue_catchup:
        return {"prepared": False, "reason": "waiting_for_best_hour", "best_hour_utc": target_hour}

    try:
        idx = int(_get_setting(db, _AUTO_IDX_KEY, "0")) % len(_AUTO_ROTATION)
    except ValueError:
        idx = 0
    idx_raw = _get_setting(db, _AUTO_IDX_KEY, "")
    try:
        msg_idx = int(_get_setting(db, _AUTO_MSG_IDX_KEY, "0"))
    except ValueError:
        msg_idx = 0
    msg_idx_raw = _get_setting(db, _AUTO_MSG_IDX_KEY, "")
    platform = _AUTO_ROTATION[idx]
    meta = PLATFORMS[platform]

    # ── Atomic claim: advance last + idx + msg counter in ONE commit, gated
    # on the exact prior `last` value. If another runner already claimed this
    # slot, the compare-and-set matches 0 rows and we bail without sending.
    for key, default in (
        (_AUTO_LAST_KEY, ""),
        (_AUTO_IDX_KEY, "0"),
        (_AUTO_MSG_IDX_KEY, "0"),
    ):
        if db.get(AppSetting, key) is None:
            db.add(AppSetting(key=key, value=default))
    db.commit()
    prior_last = last_raw if last_raw else ""
    claimed = (
        db.query(AppSetting)
        .filter(AppSetting.key == _AUTO_LAST_KEY, AppSetting.value == prior_last)
        .update({AppSetting.value: now.isoformat()}, synchronize_session=False)
    )
    if not claimed:
        db.rollback()
        return {"prepared": False, "reason": "claimed_by_other_runner"}
    db.query(AppSetting).filter(AppSetting.key == _AUTO_IDX_KEY).update(
        {AppSetting.value: str((idx + 1) % len(_AUTO_ROTATION))},
        synchronize_session=False,
    )
    db.query(AppSetting).filter(AppSetting.key == _AUTO_MSG_IDX_KEY).update(
        {AppSetting.value: str(msg_idx + 1)},
        synchronize_session=False,
    )
    db.commit()

    def _release_claim() -> None:
        """Revert claimed state in one commit so the next hourly run retries."""
        try:
            db.query(AppSetting).filter(AppSetting.key == _AUTO_LAST_KEY).update(
                {AppSetting.value: prior_last}, synchronize_session=False
            )
            db.query(AppSetting).filter(AppSetting.key == _AUTO_IDX_KEY).update(
                {AppSetting.value: idx_raw if idx_raw else str(idx)},
                synchronize_session=False,
            )
            db.query(AppSetting).filter(AppSetting.key == _AUTO_MSG_IDX_KEY).update(
                {AppSetting.value: msg_idx_raw if msg_idx_raw else str(msg_idx)},
                synchronize_session=False,
            )
            db.commit()
        except Exception as release_exc:  # noqa: BLE001
            logger.error("Auto-Cadence claim release failed: %s", release_exc)

    # ── Alternate content: even runs use a personalized core message, odd
    # runs cycle through the 20-message rotation pool — so back-to-back
    # auto-prepared posts never sound alike.
    try:
        if msg_idx % 2 == 1 and ROTATION_MESSAGES:
            rotation_text = ROTATION_MESSAGES[
                (msg_idx // 2) % len(ROTATION_MESSAGES)
            ].replace("{link}", tracked_link(platform))
            pack = {
                "message": rotation_text,
                "tracked_link": tracked_link(platform),
                "content_source": "rotation_pool",
            }
        else:
            pack = asyncio.run(personalize(db, platform=platform))
    except Exception:
        _release_claim()
        raise

    from app.services.email_sender_service import send_admin_notice

    body = "\n".join(
        [
            f"It's posting time — today's platform: {meta['label']}.",
            f"(Chosen at your audience's most active hour: {target_hour:02d}:00 UTC.)",
            "",
            "Copy the message below and post it yourself where it genuinely fits:",
            "",
            "──────────────────────────────",
            pack["message"],
            "──────────────────────────────",
            "",
            f"Tracked link (already inside the message): {pack['tracked_link']}",
            "",
            f"{meta['label']} etiquette:",
            *[f"• {tip}" for tip in meta["etiquette"]],
            "",
            "After posting, log it in the 🕊️ Lead Evangelist tab (Outreach Log) "
            "so pace tracking and the dashboard stay accurate.",
            "",
            f"Next auto-prepared post: in about 2 days, platform: "
            f"{PLATFORMS[_AUTO_ROTATION[(idx + 1) % len(_AUTO_ROTATION)]]['label']}.",
        ]
    )
    try:
        result = send_admin_notice(
            f"🕊️ Your Lead Evangelist post is ready — {meta['label']}", body
        )
    except Exception:
        _release_claim()
        raise
    if not (result and result.success):
        # Release the claim so the next hourly run retries the email.
        _release_claim()
        raise RuntimeError(
            f"Auto-Cadence email failed: {(result.error if result else 'no result')}"
        )

    logger.info("Auto-Cadence prepared a %s post and emailed the admin.", platform)
    return {"prepared": True, "platform": platform, "content_source": pack["content_source"]}
