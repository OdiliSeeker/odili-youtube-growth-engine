"""
Newsletter content generation and email rendering service.

Uses GPT-4o to create a weekly Catholic insight newsletter, and provides a
single branded email "shell" (header logo + body + growth-loop footer CTAs)
shared by every email the ministry sends. Every email pushes readers back to
YouTube and the Growth Engine, closing the loop:

    YouTube → App → Email → YouTube → repeat
"""

import html
import json
import os

from app.services.ai_service import generate_with_ai
from app.services.token_service import get_base_url

YOUTUBE_URL = os.getenv("YOUTUBE_CHANNEL_URL", "https://www.youtube.com/@odilitheseekeroftruth")

# Unsubscribe placeholder — replaced per-recipient by the sender service.
_UNSUB = "{UNSUBSCRIBE_URL}"


def _email_urls() -> tuple[str, str, str]:
    """Return (logo_url, youtube_url, admin_url) as absolute public links for emails."""
    base = get_base_url()
    return f"{base}/static/logo.png", YOUTUBE_URL, f"{base}/admin"


def _with_email_tracking(url: str) -> str:
    """
    Append lightweight click-tracking params to a YouTube link so we can measure
    Email → YouTube conversion in YouTube Studio's traffic-source report.
    """
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}src=email&utm=odili_email"


# ── Shared branded email shell ─────────────────────────────────────────────
_EMAIL_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


def email_shell(eyebrow: str, title: str, inner_html: str) -> str:
    """
    Wrap inner body HTML in the shared Odili email template — the single
    reusable template used by every email the ministry sends.

    Dark, premium brand styling (black background, white text, gold accent,
    deep-red secondary, sans-serif). Layout:
        HEADER (logo) → TITLE → BODY → CTA (Watch on YouTube + Subscribe) → FOOTER.
    """
    logo_url, youtube_url, _admin_url = _email_urls()
    sep = "&" if "?" in youtube_url else "?"
    watch_url = _with_email_tracking(youtube_url)
    subscribe_url = _with_email_tracking(f"{youtube_url}{sep}sub_confirmation=1")
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#000000;font-family:{_EMAIL_FONT};color:#ffffff;line-height:1.7;-webkit-font-smoothing:antialiased">
  <div style="max-width:600px;margin:0 auto;background:#0c0c0e">

    <!-- HEADER (static logo, top-left) -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:#000000;border-bottom:3px solid #FFD700">
      <tr>
        <td style="padding:22px 28px;text-align:left">
          <img src="{logo_url}" alt="Odili — The Seeker of Truth"
               style="height:50px;max-height:50px;width:auto;vertical-align:middle;display:inline-block">
          <span style="color:#FFD700;font-size:15px;font-weight:bold;letter-spacing:1px;text-transform:uppercase;vertical-align:middle;margin-left:12px">
            Odili — The Seeker of Truth
          </span>
        </td>
      </tr>
    </table>

    <!-- TITLE + BODY -->
    <div style="padding:36px 30px;color:#eaeaea;font-size:15px">
      <p style="font-size:12px;color:#FFD700;font-weight:bold;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 10px">
        {html.escape(eyebrow)}
      </p>
      <h1 style="font-size:24px;color:#ffffff;margin:0 0 22px;line-height:1.3">{html.escape(title)}</h1>
      {inner_html}
    </div>

    <!-- CTA (growth loop → YouTube) -->
    <div style="background:#000000;padding:34px 28px;text-align:center;border-top:1px solid #1c1c1c">
      <p style="color:#cfcfcf;font-size:15px;margin:0 0 18px">Catch the latest truth on YouTube</p>
      <a href="{watch_url}"
         style="display:inline-block;background:#FFD700;color:#1a1300;padding:14px 34px;
                text-decoration:none;border-radius:8px;font-size:15px;font-weight:bold">
        ▶ Watch on YouTube
      </a>
      <div style="margin-top:16px">
        <a href="{subscribe_url}"
           style="display:inline-block;color:#FFD700;padding:11px 28px;border:1px solid #FFD700;
                  text-decoration:none;border-radius:8px;font-size:14px;font-weight:bold">
          Subscribe for more truth
        </a>
      </div>
    </div>

    <!-- FOOTER -->
    <div style="background:#000000;padding:22px 28px 30px;text-align:center;border-top:1px solid #1c1c1c">
      <div style="color:#FFD700;font-size:14px;font-weight:bold;letter-spacing:.5px;margin-bottom:8px">
        Odili — The Seeker of Truth
      </div>
      <p style="font-size:12px;color:#6f6f6f;margin:0;line-height:1.6">
        You are receiving this because you subscribed to Odili — The Seeker of Truth.<br>
        © Odili Truth Seeker Ministry · <a href="{_UNSUB}" style="color:#8a8a8a">Unsubscribe</a>
      </p>
    </div>

  </div>
</body>
</html>""".strip()


def _plain_text_footer() -> str:
    """Plain-text equivalent of the growth-loop footer."""
    _, youtube_url, _admin_url = _email_urls()
    sep = "&" if "?" in youtube_url else "?"
    watch_url = _with_email_tracking(youtube_url)
    subscribe_url = _with_email_tracking(f"{youtube_url}{sep}sub_confirmation=1")
    return (
        "\n\n— — — — —\n"
        f"▶ Watch on YouTube: {watch_url}\n"
        f"Subscribe for more truth: {subscribe_url}\n\n"
        "Odili — The Seeker of Truth\n"
        f"Unsubscribe: {_UNSUB}\n"
        "© Odili Truth Seeker Ministry"
    )


# ── AI weekly newsletter ───────────────────────────────────────────────────
_NEWSLETTER_PROMPT = """
You are writing a weekly email newsletter for Odili Truth Seeker, a Catholic media ministry.

Generate a newsletter with:
1. A compelling subject line (max 10 words, no quotes)
2. A warm greeting opening sentence
3. Exactly 3 short bullet-point insights (Catholic truth, history, or apologetics — 1-2 sentences each)
4. A closing call-to-action sentence encouraging readers to watch this week's video

Return ONLY a valid JSON object with these exact keys:
- "subject": the email subject line
- "greeting": the opening sentence
- "insights": an array of exactly 3 strings
- "cta": the call-to-action sentence

No extra text, no markdown, no code fences. Pure JSON only.
"""


async def generate_newsletter_content() -> dict:
    """
    Call GPT-4o to generate structured newsletter content.

    Returns a dict with keys: subject, greeting, insights, cta.
    Raises ValueError if the AI response cannot be parsed.
    """
    raw = await generate_with_ai(_NEWSLETTER_PROMPT)

    try:
        data = json.loads(raw)
        required = {"subject", "greeting", "insights", "cta"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"AI response missing keys: {missing}")
        if not isinstance(data["insights"], list) or len(data["insights"]) != 3:
            raise ValueError("'insights' must be a list of exactly 3 items.")
        return data
    except (json.JSONDecodeError, KeyError) as exc:
        raise ValueError(f"AI returned an unexpected format: {exc}. Raw: {raw[:400]}") from exc


# ── Weekly content plan (Step 4) ───────────────────────────────────────────
WEEKLY_PLAN_SUBJECT = "Your Weekly Catholic Content Plan"

_WEEKLY_PROMPT = """
You are planning a week of Catholic YouTube content for Odili — The Seeker of Truth,
a Catholic media ministry covering truth, history, apologetics, saints, and the liturgical season.

{topics_block}

Write an encouraging weekly content-plan email body for the creator. Include:
1. A short motivating intro sentence.
2. Between 4 and 5 video ideas. For each: a bold viral-style title followed by a one-line angle/hook.
3. A closing line of encouragement to publish consistently.

Return ONLY a valid JSON object with this exact key:
- "body": the full plain-text email body, using \\n line breaks between paragraphs and ideas.

No extra text, no markdown, no code fences. Pure JSON only.
"""


async def generate_weekly_plan_content(topics: list[str] | None = None) -> dict:
    """
    Generate a "Your Weekly Catholic Content Plan" email.

    Optionally seeded with trending `topics` (e.g. top topics from YouTube
    Intelligence). Returns a dict: {"subject", "body"}.
    """
    if topics:
        cleaned = [t.strip() for t in topics if t and t.strip()][:8]
    else:
        cleaned = []

    if cleaned:
        topics_block = "Base the plan on these trending/top topics:\n" + "\n".join(f"- {t}" for t in cleaned)
    else:
        topics_block = "Choose timely Catholic topics across truth, history, apologetics, saints, and the liturgical season."

    raw = await generate_with_ai(_WEEKLY_PROMPT.format(topics_block=topics_block))

    body = ""
    try:
        data = json.loads(raw)
        body = str(data.get("body", "")).strip()
    except (json.JSONDecodeError, TypeError):
        body = raw.strip()

    if not body:
        body = (
            "Here is your Catholic content plan for the week ahead. "
            "Pick the ideas that move your heart and start filming.\n\n"
            "Publish consistently — every video plants a seed of truth."
        )

    return {"subject": WEEKLY_PLAN_SUBJECT, "body": body}


# ── Renderers ──────────────────────────────────────────────────────────────
def render_custom_html(subject: str, body: str) -> str:
    """
    Render a hand-written newsletter into the shared branded HTML template.
    `body` can be plain text with newlines — each paragraph is wrapped in <p> tags.
    """
    paragraphs_html = "\n".join(
        f"<p style='font-size:15px;margin:0 0 14px'>{html.escape(para.strip())}</p>"
        for para in body.strip().split("\n")
        if para.strip()
    )
    return email_shell(eyebrow="Weekly Insight", title=subject, inner_html=paragraphs_html)


def render_custom_text(subject: str, body: str) -> str:
    """Plain-text fallback for a hand-written newsletter."""
    lines = [para.strip() for para in body.strip().split("\n") if para.strip()]
    return subject + "\n\n" + "\n\n".join(lines) + _plain_text_footer()


def render_newsletter_html(content: dict) -> str:
    """Render AI newsletter content dict into the shared branded HTML template."""
    insights_html = "\n".join(
        f"<li style='margin-bottom:10px'>{html.escape(str(insight))}</li>"
        for insight in content["insights"]
    )
    inner = f"""
    <p style="font-size:15px;color:#eaeaea;margin:0 0 18px">{html.escape(str(content["greeting"]))}</p>
    <h2 style="font-size:16px;color:#FFD700;border-bottom:1px solid #2a2a2a;padding-bottom:8px;margin:0 0 14px">
      This Week's Insights
    </h2>
    <ul style="font-size:15px;color:#eaeaea;padding-left:20px;margin:0 0 8px">
      {insights_html}
    </ul>
    <div style="background:#141414;border-left:4px solid #8B0000;padding:16px 20px;margin:24px 0;border-radius:0 6px 6px 0">
      <p style="margin:0;font-size:15px;color:#f0f0f0">{html.escape(str(content["cta"]))}</p>
    </div>
    """.strip()
    return email_shell(eyebrow="Weekly Insight", title=str(content["subject"]), inner_html=inner)


def render_newsletter_text(content: dict) -> str:
    """Plain-text fallback for an AI newsletter."""
    parts = [
        str(content["subject"]),
        "",
        str(content["greeting"]),
        "",
        "This Week's Insights:",
    ]
    parts.extend(f"- {insight}" for insight in content["insights"])
    parts.extend(["", str(content["cta"])])
    return "\n".join(parts) + _plain_text_footer()
