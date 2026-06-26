"""
SendGrid email sending service.

Required environment variables:
  SENDGRID_API_KEY    — SendGrid API key (required, must have Mail Send scope)
  SENDGRID_FROM_EMAIL — verified sender address (required)
  SENDGRID_FROM_NAME  — display name shown in From field (optional, default: Odili Truth Seeker)
"""

import os
import json
import logging
from dataclasses import dataclass

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From, PlainTextContent

logger = logging.getLogger(__name__)


@dataclass
class SendResult:
    success: bool
    status_code: int | None = None
    error: str | None = None


def _clean_value(raw: str) -> str:
    """
    Strip accidental 'KEY = value' prefixes that occur when users paste
    entire config lines (e.g. 'SENDGRID_API_KEY = SG.xxx') instead of
    just the value ('SG.xxx').
    """
    raw = raw.strip()
    if "=" in raw:
        raw = raw.split("=", 1)[1].strip()
    return raw


def _get_client() -> SendGridAPIClient:
    api_key = _clean_value(os.getenv("SENDGRID_API_KEY", ""))
    if not api_key:
        raise EnvironmentError(
            "SENDGRID_API_KEY is not set. Add it to your environment secrets."
        )
    if not api_key.startswith("SG."):
        raise EnvironmentError(
            f"SENDGRID_API_KEY looks wrong (got prefix '{api_key[:6]}...'). "
            "A valid SendGrid key starts with 'SG.' — copy it from "
            "sendgrid.com → Settings → API Keys."
        )
    return SendGridAPIClient(api_key=api_key)


def _get_from_address() -> tuple[str, str]:
    """Return (email, name) for the sender. Raises if SENDGRID_FROM_EMAIL is invalid."""
    from_email = _clean_value(os.getenv("SENDGRID_FROM_EMAIL", ""))
    if not from_email:
        raise EnvironmentError(
            "SENDGRID_FROM_EMAIL is not set. Add a verified sender address to your environment secrets."
        )
    if "@" not in from_email or "." not in from_email.split("@")[-1]:
        raise EnvironmentError(
            f"SENDGRID_FROM_EMAIL does not look like a valid email address (got: '{from_email}'). "
            "Set it to your verified sender email, e.g. odilitheseekeroftruth@gmail.com"
        )
    from_name = _clean_value(os.getenv("SENDGRID_FROM_NAME", "Odili Truth Seeker")) or "Odili Truth Seeker"
    return from_email, from_name


def _parse_sendgrid_error(exc: Exception) -> tuple[int, str]:
    """
    Extract status code and human-readable message from a SendGrid exception.
    SendGrid raises typed exceptions (UnauthorizedError, ForbiddenError, etc.)
    that carry .status_code and .body attributes.
    """
    status_code: int = getattr(exc, "status_code", 0) or 0

    # body is bytes or a JSON-parseable string
    body_raw = getattr(exc, "body", None)
    try:
        if isinstance(body_raw, (bytes, bytearray)):
            body_raw = body_raw.decode("utf-8")
        data = json.loads(body_raw or "{}")
        messages = [e.get("message", "") for e in data.get("errors", [])]
        detail = " | ".join(m for m in messages if m) or str(exc)
    except Exception:
        detail = str(exc)

    hints = {
        401: "Your SENDGRID_API_KEY is invalid or lacks 'Mail Send' permission. Regenerate it in SendGrid → Settings → API Keys.",
        403: "The From address is not verified in SendGrid. Go to Settings → Sender Authentication → Single Sender Verification.",
    }
    hint = hints.get(status_code, "")
    message = f"SendGrid HTTP {status_code}: {detail}"
    if hint:
        message += f" — {hint}"
    return status_code, message


def send_email(to_email: str, subject: str, content: str, text_content: str | None = None) -> SendResult:
    """
    Send a single email via SendGrid.

    Args:
        to_email:     Recipient email address.
        subject:      Email subject line.
        content:      HTML body content.
        text_content: Optional plain-text fallback (improves deliverability and
                      renders in clients that block HTML).

    Returns:
        SendResult with success flag, HTTP status code, and optional error message.
    """
    to_email = to_email.strip().lower()
    if not to_email or "@" not in to_email:
        return SendResult(success=False, error=f"Invalid email address: '{to_email}'")

    try:
        from_email, from_name = _get_from_address()
        client = _get_client()
    except EnvironmentError as exc:
        logger.error("SendGrid configuration error: %s", exc)
        return SendResult(success=False, error=str(exc))

    message = Mail(
        from_email=From(email=from_email, name=from_name),
        to_emails=To(email=to_email),
        subject=subject,
        html_content=content,
    )
    if text_content:
        # Add a plain-text part. SendGrid orders text/plain before text/html
        # automatically, so clients render the best version they support.
        message.content = PlainTextContent(text_content)

    try:
        response = client.send(message)
        success = 200 <= response.status_code < 300
        if not success:
            logger.warning(
                "SendGrid returned non-2xx status %s for %s", response.status_code, to_email
            )
        return SendResult(success=success, status_code=response.status_code)

    except Exception as exc:
        # SendGrid raises typed exceptions (UnauthorizedError, ForbiddenError, etc.)
        # all of which carry .status_code and .body attributes.
        if hasattr(exc, "status_code") or hasattr(exc, "body"):
            status_code, message_text = _parse_sendgrid_error(exc)
            logger.error("SendGrid HTTP error sending to %s: %s", to_email, message_text)
            return SendResult(success=False, status_code=status_code, error=message_text)
        logger.error("SendGrid unexpected error sending to %s: %s", to_email, exc)
        return SendResult(success=False, error=str(exc))


def send_bulk(recipients: list[str], subject: str, content: str, text_content: str | None = None) -> dict:
    """
    Send the same email to multiple recipients one at a time.

    If the HTML (or plain-text) content contains the placeholder
    ``{UNSUBSCRIBE_URL}`` it is replaced with a per-recipient signed unsubscribe
    link before sending.

    Returns a summary dict with counts and per-address failures.
    """
    from app.services.token_service import make_unsubscribe_url

    results: dict = {"sent": 0, "failed": 0, "failures": []}

    for address in recipients:
        unsub = make_unsubscribe_url(address)
        personalised = content.replace("{UNSUBSCRIBE_URL}", unsub)
        personalised_text = text_content.replace("{UNSUBSCRIBE_URL}", unsub) if text_content else None
        result = send_email(to_email=address, subject=subject, content=personalised, text_content=personalised_text)
        if result.success:
            results["sent"] += 1
        else:
            results["failed"] += 1
            results["failures"].append({
                "email": address,
                "error": result.error or f"HTTP {result.status_code}",
            })

    return results


def send_welcome_email(to_email: str) -> SendResult:
    """
    Send a one-time welcome email to a new subscriber.
    Uses the same branded template as newsletters.
    """
    from app.services.token_service import make_unsubscribe_url
    from app.services.newsletter_service import email_shell, _plain_text_footer

    unsubscribe_url = make_unsubscribe_url(to_email)

    inner = """
    <p style="font-size:15px">
      Peace be with you, and thank you for subscribing to Odili — The Seeker of Truth.
    </p>
    <p style="font-size:15px">
      You'll receive our Catholic insights covering truth, history, and apologetics —
      delivered straight to your inbox every Sunday, Wednesday, and Friday.
    </p>
    <p style="font-size:15px">God bless you on your journey of faith.</p>
    """.strip()

    html_body = email_shell(
        eyebrow="Welcome",
        title="Welcome to Odili — The Seeker of Truth ✝️",
        inner_html=inner,
    ).replace("{UNSUBSCRIBE_URL}", unsubscribe_url)

    text_body = (
        "Welcome to Odili — The Seeker of Truth\n\n"
        "Peace be with you, and thank you for subscribing.\n\n"
        "You'll receive our Catholic insights covering truth, history, and apologetics "
        "every Sunday, Wednesday, and Friday.\n\n"
        "God bless you on your journey of faith."
        + _plain_text_footer()
    ).replace("{UNSUBSCRIBE_URL}", unsubscribe_url)

    return send_email(
        to_email=to_email,
        subject="Welcome to Odili — The Seeker of Truth ✝️",
        content=html_body,
        text_content=text_body,
    )
