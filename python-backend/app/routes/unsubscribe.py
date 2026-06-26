"""
One-click unsubscribe endpoint.

GET /unsubscribe?email=xxx&token=yyy
  — verifies HMAC token, soft-deletes the subscriber, returns a branded HTML confirmation.
"""

import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.branding import HEADER_CSS, header_html
from app.db import get_db
from app.services.email_service import remove_email
from app.services.token_service import verify_unsubscribe_token

logger = logging.getLogger(__name__)
router = APIRouter()

_STYLE = """
  body{font-family:Georgia,serif;background:#fdf6f0;display:flex;align-items:center;
       justify-content:center;min-height:100vh;margin:0;padding:96px 16px 24px;box-sizing:border-box}
  .card{background:#fff;max-width:480px;width:100%;padding:40px;border-radius:8px;
        box-shadow:0 2px 16px rgba(0,0,0,.08);text-align:center}
  .bar{height:4px;background:#8B0000;border-radius:4px 4px 0 0;margin:-40px -40px 32px}
  h1{font-size:20px;color:#1a1a1a;margin:0 0 12px}
  p{font-size:15px;color:#555;line-height:1.6;margin:0 0 24px}
  a{color:#8B0000;font-weight:bold;text-decoration:none}
  .badge{font-size:48px;margin-bottom:16px}
  .brand-logo{width:96px;height:96px;object-fit:contain;border-radius:14px;
              background:#000;padding:6px;margin:0 auto 20px;display:block}
"""


def _page(title: str, emoji: str, heading: str, body: str) -> HTMLResponse:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="icon" type="image/png" href="/static/logo.png">
  <title>{title} — Odili Truth Seeker</title>
  {HEADER_CSS}
  <style>{_STYLE}</style>
</head>
<body>
  {header_html()}
  <div class="card">
    <div class="bar"></div>
    <img class="brand-logo" src="/static/logo.png" alt="Odili Truth Seeker logo">
    <div class="badge">{emoji}</div>
    <h1>{heading}</h1>
    <p>{body}</p>
    <a href="https://www.youtube.com/@odilitheseekeroftruth">Visit our YouTube channel →</a>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/unsubscribe", tags=["Subscribers"], response_class=HTMLResponse)
async def unsubscribe_via_link(
    email: str = Query(..., description="Subscriber email address"),
    token: str = Query(..., description="HMAC verification token"),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    One-click unsubscribe. Validates the HMAC token then soft-deletes the subscriber.
    Returns a branded HTML confirmation page — no JSON, no extra clicks required.
    """
    email = email.strip().lower()

    if not verify_unsubscribe_token(email, token):
        logger.warning("Invalid unsubscribe token for %s", email)
        return _page(
            title="Invalid Link",
            emoji="⚠️",
            heading="This link is invalid or has expired.",
            body=(
                "We couldn't verify your unsubscribe request. "
                "Please use the link from your most recent email, "
                "or contact us directly."
            ),
        )

    removed = remove_email(db=db, email=email)

    if removed:
        logger.info("Unsubscribed via link: %s", email)
        return _page(
            title="Unsubscribed",
            emoji="✅",
            heading="You've been unsubscribed.",
            body=(
                f"<strong>{email}</strong> has been removed from our mailing list. "
                "We're sorry to see you go — you're always welcome back. "
                "God bless you."
            ),
        )
    else:
        return _page(
            title="Already Unsubscribed",
            emoji="ℹ️",
            heading="You're already unsubscribed.",
            body=(
                f"<strong>{email}</strong> is not on our active mailing list. "
                "No further action is needed."
            ),
        )
