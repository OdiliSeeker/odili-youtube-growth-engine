"""
Startup validation — called once when the server boots.
Logs warnings for misconfigured secrets instead of crashing,
so the server stays up and surfaces errors at the endpoint level.
"""

import os
import logging

logger = logging.getLogger(__name__)


def _clean(raw: str) -> str:
    raw = raw.strip()
    if "=" in raw:
        raw = raw.split("=", 1)[1].strip()
    return raw


def validate_environment() -> None:
    """
    Check required environment variables and log warnings for any issues.
    Does NOT raise — the server stays up and individual endpoints handle
    missing/invalid credentials gracefully.
    """
    issues: list[str] = []

    # ── OpenAI ──────────────────────────────────────────────────────────────
    openai_key = _clean(os.getenv("OPENAI_API_KEY", ""))
    if not openai_key:
        issues.append("OPENAI_API_KEY is not set — AI generation endpoints will fail.")
    elif not openai_key.startswith("sk-"):
        issues.append(
            f"OPENAI_API_KEY prefix looks unexpected ('{openai_key[:8]}...') — expected 'sk-'."
        )

    # ── SendGrid ─────────────────────────────────────────────────────────────
    sg_key = _clean(os.getenv("SENDGRID_API_KEY", ""))
    if not sg_key:
        issues.append("SENDGRID_API_KEY is not set — newsletter sending will fail.")
    elif not sg_key.startswith("SG."):
        issues.append(
            f"SENDGRID_API_KEY prefix '{sg_key[:8]}...' looks wrong — expected 'SG.'. "
            "Copy your real key from sendgrid.com → Settings → API Keys."
        )

    sg_from = _clean(os.getenv("SENDGRID_FROM_EMAIL", ""))
    if not sg_from:
        issues.append("SENDGRID_FROM_EMAIL is not set — newsletter sending will fail.")
    elif "@" not in sg_from or "." not in sg_from.split("@")[-1]:
        issues.append(
            f"SENDGRID_FROM_EMAIL '{sg_from}' is not a valid email address."
        )

    # ── YouTube Intelligence ─────────────────────────────────────────────────
    yt_key = os.getenv("YOUTUBE_API_KEY", "")
    yt_ch  = os.getenv("YOUTUBE_CHANNEL_ID", "")
    if not yt_key:
        issues.append(
            "YOUTUBE_API_KEY is not set — GET /youtube/intelligence will return 400."
        )
    if not yt_ch:
        issues.append(
            "YOUTUBE_CHANNEL_ID is not set — GET /youtube/intelligence will return 400."
        )

    # ── Admin API Key ────────────────────────────────────────────────────────
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key:
        issues.append("ADMIN_API_KEY is not set — admin endpoints and dashboard will return 500.")
    elif len(admin_key) < 12:
        issues.append("ADMIN_API_KEY is very short — use a longer random string for security.")

    if issues:
        logger.warning("⚠️  Configuration warnings (server will still start):")
        for issue in issues:
            logger.warning("    ✗ %s", issue)
    else:
        logger.info("✓ Environment validation passed — all credentials look correct.")
